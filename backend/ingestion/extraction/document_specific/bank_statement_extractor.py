"""
Bank statement extractor supporting SBI, HDFC, ICICI, AXIS, and generic formats.
"""
import re
import pandas as pd
from datetime import date, datetime
from loguru import logger
from models.bank import BankAnalysis, BankTransaction
from ingestion.normalization.currency_normalizer import CurrencyNormalizer

CURR = CurrencyNormalizer()

BANK_COLUMN_MAPS = {
    "HDFC": {
        "date": ["date"],
        "description": ["narration"],
        "debit": ["withdrawal amt.", "withdrawal", "debit"],
        "credit": ["deposit amt.", "deposit", "credit"],
        "balance": ["closing balance", "balance"],
    },
    "SBI": {
        "date": ["txn date", "date"],
        "description": ["description", "particulars"],
        "debit": ["debit"],
        "credit": ["credit"],
        "balance": ["balance"],
    },
    "ICICI": {
        "date": ["value date", "transaction date", "date"],
        "description": ["transaction remarks", "narration"],
        "debit": ["withdrawal (dr)", "debit", "withdrawal"],
        "credit": ["deposit (cr)", "credit", "deposit"],
        "balance": ["balance"],
    },
    "AXIS": {
        "date": ["tran date", "date"],
        "description": ["particulars"],
        "debit": ["withdrawals", "debit"],
        "credit": ["deposits", "credit"],
        "balance": ["balance"],
    },
    "GENERIC": {
        "date": ["date", "txn date", "value date", "tran date"],
        "description": ["narration", "description", "particulars", "transaction remarks"],
        "debit": ["debit", "withdrawal", "withdrawals", "dr"],
        "credit": ["credit", "deposit", "deposits", "cr"],
        "balance": ["balance", "closing balance"],
    },
}

NACH_KEYWORDS = ["nach", "ecs", "emi", "loan repay", "loan instalment", "equated"]
GST_KEYWORDS = ["gst", "igst", "cgst", "sgst"]
CASH_KEYWORDS = ["cash withdrawal", "atm", "atw", "cash"]
RTGS_KEYWORDS = ["rtgs", "neft", "imps"]
RETURN_KEYWORDS = ["return", "ecs return", "bounce", "dishonour", "chq ret"]


class BankStatementExtractor:

    def extract_from_file(self, file_path: str, bank_name: str = "GENERIC") -> BankAnalysis | None:
        try:
            if file_path.endswith(".csv"):
                df = pd.read_csv(file_path, encoding='utf-8', errors='ignore')
            elif file_path.endswith((".xlsx", ".xls")):
                df = pd.read_excel(file_path)
            elif file_path.endswith(".pdf"):
                df = self._pdf_to_dataframe(file_path)
            else:
                return None

            if df is None or df.empty:
                return None

            return self.extract(df, bank_name)
        except Exception as e:
            logger.warning(f"Bank extraction failed for {file_path}: {e}")
            return None

    def extract(self, df: pd.DataFrame, bank_name: str = "GENERIC") -> BankAnalysis | None:
        if df.empty:
            return None

        # Normalize column names
        df.columns = [c.strip().lower() for c in df.columns]

        # Map columns
        col_map = BANK_COLUMN_MAPS.get(bank_name.upper(), BANK_COLUMN_MAPS["GENERIC"])
        mapped = self._map_columns(df, col_map)
        if mapped is None:
            return None

        transactions = []
        monthly_deposits: dict[str, int] = {}
        monthly_balances: dict[str, list] = {}

        for _, row in mapped.iterrows():
            try:
                txn_date = self._parse_date(row.get("date", ""))
                if not txn_date:
                    continue
                month_key = txn_date.strftime("%Y-%m")

                desc = str(row.get("description", "")).lower()
                debit_raw = row.get("debit", 0)
                credit_raw = row.get("credit", 0)
                balance_raw = row.get("balance", 0)

                debit = self._parse_amount(debit_raw)
                credit = self._parse_amount(credit_raw)
                balance = self._parse_amount(balance_raw)

                txn_type = self._classify_transaction(desc, debit, credit)

                txn = BankTransaction(
                    date=txn_date,
                    description=str(row.get("description", "")),
                    debit_paise=debit,
                    credit_paise=credit,
                    balance_paise=balance,
                    transaction_type=txn_type,
                )
                transactions.append(txn)

                if credit > 0:
                    monthly_deposits[month_key] = monthly_deposits.get(month_key, 0) + credit

                if balance > 0:
                    if month_key not in monthly_balances:
                        monthly_balances[month_key] = []
                    monthly_balances[month_key].append(balance)

            except Exception as e:
                continue

        if not transactions:
            return None

        # Monthly averages
        monthly_balance_series = {m: int(sum(v) / len(v)) for m, v in monthly_balances.items()}
        avg_monthly_balance = int(sum(monthly_balance_series.values()) / len(monthly_balance_series)) if monthly_balance_series else 0

        total_deposits = sum(t.credit_paise for t in transactions)
        total_withdrawals = sum(t.debit_paise for t in transactions)
        nach_total = sum(t.debit_paise for t in transactions if t.transaction_type == "NACH")
        gst_payments = sum(t.debit_paise for t in transactions if t.transaction_type == "GST_PAYMENT")
        cash_debits = sum(t.debit_paise for t in transactions if t.transaction_type == "CASH")
        cash_ratio = cash_debits / total_withdrawals if total_withdrawals > 0 else 0

        # NACH bounce detection
        nach_bounces = 0
        for i, txn in enumerate(transactions):
            if txn.transaction_type == "NACH" and txn.debit_paise > 0:
                close_txns = transactions[max(0, i-3):min(len(transactions), i+3)]
                for close in close_txns:
                    if any(kw in close.description.lower() for kw in RETURN_KEYWORDS):
                        nach_bounces += 1
                        break

        # End-of-period spike (March 28-31)
        march_credits = [t.credit_paise for t in transactions if t.date.month == 3 and t.date.day >= 28]
        march_credit_total = sum(march_credits)
        avg_monthly_credit = total_deposits / 12 if total_deposits > 0 else 0
        end_of_period_spike = march_credit_total > (avg_monthly_credit * 1.5)

        return BankAnalysis(
            bank_name=bank_name,
            average_monthly_balance_paise=avg_monthly_balance,
            total_deposits_paise=total_deposits,
            total_withdrawals_paise=total_withdrawals,
            nach_emi_total_paise=nach_total,
            gst_payments_paise=gst_payments,
            cash_withdrawal_ratio=cash_ratio,
            end_of_period_spike=end_of_period_spike,
            nach_bounce_count=nach_bounces,
            monthly_balance_series=monthly_balance_series,
            monthly_deposit_series=monthly_deposits,
            transactions=transactions[:100],  # Store first 100 only
        )

    def _map_columns(self, df: pd.DataFrame, col_map: dict) -> pd.DataFrame | None:
        mapped = {}
        for target, candidates in col_map.items():
            for cand in candidates:
                matching = [c for c in df.columns if cand in c.lower()]
                if matching:
                    mapped[target] = matching[0]
                    break
        if not all(k in mapped for k in ["date", "credit"]):
            return None
        return df.rename(columns={v: k for k, v in mapped.items()})

    def _parse_date(self, val) -> date | None:
        if pd.isna(val) if hasattr(pd, 'isna') else val is None:
            return None
        val = str(val).strip()
        for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d %b %Y", "%d-%b-%Y"]:
            try:
                return datetime.strptime(val, fmt).date()
            except ValueError:
                continue
        return None

    def _parse_amount(self, val) -> int:
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return 0
        try:
            clean = str(val).replace(",", "").replace("Dr", "").replace("Cr", "").strip()
            return max(0, int(float(clean) * 100))
        except (ValueError, TypeError):
            return 0

    def _classify_transaction(self, desc: str, debit: int, credit: int) -> str:
        desc_lower = desc.lower()
        if any(kw in desc_lower for kw in NACH_KEYWORDS):
            return "NACH"
        if any(kw in desc_lower for kw in GST_KEYWORDS):
            return "GST_PAYMENT"
        if any(kw in desc_lower for kw in CASH_KEYWORDS):
            return "CASH"
        if any(kw in desc_lower for kw in RTGS_KEYWORDS):
            return "RTGS"
        return "OTHER"

    def _pdf_to_dataframe(self, file_path: str) -> pd.DataFrame | None:
        try:
            import pdfplumber
            all_tables = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables:
                        if table and len(table) > 1:
                            # Handle duplicate columns to avoid "Reindexing only valid with uniquely valued Index objects"
                            cols = []
                            counts = {}
                            for c in table[0]:
                                c_str = str(c) if c else "Unnamed"
                                if c_str in counts:
                                    counts[c_str] += 1
                                    cols.append(f"{c_str}_{counts[c_str]}")
                                else:
                                    counts[c_str] = 0
                                    cols.append(c_str)
                            df = pd.DataFrame(table[1:], columns=cols)
                            all_tables.append(df)
            if all_tables:
                return pd.concat(all_tables, ignore_index=True)
        except Exception as e:
            logger.warning(f"pdfplumber table extraction failed: {e}")
        return None
