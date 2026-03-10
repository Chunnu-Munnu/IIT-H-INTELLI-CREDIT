"""
dataset_connectors.py
Connectors for all 3 Kaggle datasets.
Each connector:
  1. Reads raw files
  2. Engineers features that map to our canonical feature schema
  3. Returns a clean DataFrame with [feature_cols..., 'default'] label

Feature mapping principle:
  home_credit  → credit behaviour / repayment patterns / cashflow stability
  corporate    → financial ratios / leverage / profitability
  sme          → SME risk scores / working capital / growth

ALL output features are mapped to the canonical FEATURE_COLUMNS list
so they can be stacked and trained as one unified matrix.
"""
import os
import numpy as np
import pandas as pd
from loguru import logger

DATASET_DIR = os.path.join(os.path.dirname(__file__), "datasets")

# ─── Paths ────────────────────────────────────────────────────────────────────
HC_DIR  = os.path.join(DATASET_DIR, "home_credit")
CORP_DIR = os.path.join(DATASET_DIR, "corporate_credit")
SME_DIR  = os.path.join(DATASET_DIR, "sme_credit")


# ─── Dataset 1: Home Credit Default Risk ─────────────────────────────────────

def load_home_credit(sample_n: int = 50_000) -> pd.DataFrame:
    """
    Load Home Credit Default Risk dataset.
    Maps borrower-level features to corporate credit schema.

    Key raw features used:
      AMT_CREDIT     → total loan amount
      AMT_ANNUITY    → annual repayment
      AMT_INCOME_TOTAL → income (proxy for revenue)
      CODE_GENDER, DAYS_EMPLOYED, DAYS_BIRTH
      EXT_SOURCE_1/2/3 → bureau credit scores
      TARGET         → default label
    """
    app_path = os.path.join(HC_DIR, "application_train.csv")
    if not os.path.exists(app_path):
        logger.warning(f"Home Credit not found at {app_path}. Skipping.")
        return pd.DataFrame()

    logger.info("Loading Home Credit application_train.csv...")
    app = pd.read_csv(app_path, nrows=sample_n)
    logger.info(f"  application_train: {len(app):,} rows")

    # Optional enrichment files (large — load if available)
    bureau_agg = _load_bureau_agg()
    prev_agg   = _load_prev_app_agg()
    inst_agg   = _load_installments_agg()

    df = app.copy()
    if not bureau_agg.empty:
        df = df.merge(bureau_agg, on="SK_ID_CURR", how="left")
    if not prev_agg.empty:
        df = df.merge(prev_agg, on="SK_ID_CURR", how="left")
    if not inst_agg.empty:
        df = df.merge(inst_agg, on="SK_ID_CURR", how="left")

    return _engineer_home_credit_features(df)


def _load_bureau_agg() -> pd.DataFrame:
    path = os.path.join(HC_DIR, "bureau.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    logger.info("  Loading bureau.csv...")
    bureau = pd.read_csv(path)
    agg = bureau.groupby("SK_ID_CURR").agg(
        bureau_loan_count=("SK_ID_BUREAU", "count"),
        bureau_overdue_sum=("AMT_CREDIT_SUM_OVERDUE", "sum"),
        bureau_debt_sum=("AMT_CREDIT_SUM_DEBT", "sum"),
        bureau_max_overdue_days=("CREDIT_DAY_OVERDUE", "max"),
        bureau_active_loans=("CREDIT_ACTIVE", lambda x: (x == "Active").sum()),
    ).reset_index()
    return agg


def _load_prev_app_agg() -> pd.DataFrame:
    path = os.path.join(HC_DIR, "previous_application.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    logger.info("  Loading previous_application.csv...")
    prev = pd.read_csv(path)
    agg = prev.groupby("SK_ID_CURR").agg(
        prev_app_count=("SK_ID_PREV", "count"),
        prev_refused_count=("NAME_CONTRACT_STATUS", lambda x: (x == "Refused").sum()),
        prev_approved_count=("NAME_CONTRACT_STATUS", lambda x: (x == "Approved").sum()),
        prev_avg_annuity=("AMT_ANNUITY", "mean"),
        prev_max_credit=("AMT_CREDIT", "max"),
    ).reset_index()
    return agg


def _load_installments_agg() -> pd.DataFrame:
    path = os.path.join(HC_DIR, "installments_payments.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    logger.info("  Loading installments_payments.csv (chunked)...")
    chunks = []
    for chunk in pd.read_csv(path, chunksize=200_000):
        chunk["payment_delay"] = chunk["DAYS_INSTALMENT"] - chunk["DAYS_ENTRY_PAYMENT"]
        chunk["short_payment"] = (chunk["AMT_PAYMENT"] < chunk["AMT_INSTALMENT"]).astype(int)
        chunks.append(chunk.groupby("SK_ID_CURR").agg(
            inst_avg_delay=("payment_delay", "mean"),
            inst_max_delay=("payment_delay", "max"),
            inst_short_pay_count=("short_payment", "sum"),
            inst_total_payments=("AMT_PAYMENT", "sum"),
        ))
    if not chunks:
        return pd.DataFrame()
    agg = pd.concat(chunks).groupby(level=0).mean().reset_index()
    agg.columns = ["SK_ID_CURR"] + list(agg.columns[1:])
    return agg


def _engineer_home_credit_features(df: pd.DataFrame) -> pd.DataFrame:
    """Map Home Credit raw columns → canonical feature schema."""
    out = pd.DataFrame()
    eps = 1e-9

    out["default"] = df["TARGET"].astype(int)

    # ── Capacity (Debt Service) ─────────────────────────────────────────────
    # DSCR proxy: income / annuity
    income = df["AMT_INCOME_TOTAL"].clip(lower=1)
    annuity = df["AMT_ANNUITY"].clip(lower=1)
    credit  = df["AMT_CREDIT"].clip(lower=1)

    out["dscr_fy1"] = (income / annuity).clip(0, 10)
    out["dscr_fy2"] = out["dscr_fy1"] * np.random.uniform(0.85, 1.05, len(df))
    out["dscr_fy3"] = out["dscr_fy1"] * np.random.uniform(0.80, 1.10, len(df))

    # Interest coverage proxy
    goods = df.get("AMT_GOODS_PRICE", pd.Series(np.zeros(len(df)))).fillna(0)
    out["interest_coverage_fy1"] = ((income - goods) / (annuity * 0.3 + eps)).clip(0, 15)
    out["interest_coverage_fy2"] = out["interest_coverage_fy1"] * np.random.uniform(0.9, 1.1, len(df))

    # EBITDA proxy: income - annuity as operating surplus
    income_adj = (income - annuity * 0.7).clip(0)
    out["ebitda_margin_fy1"] = (income_adj / income).clip(0, 1)
    out["ebitda_margin_fy2"] = out["ebitda_margin_fy1"] * np.random.uniform(0.9, 1.05, len(df))
    out["ebitda_margin_fy3"] = out["ebitda_margin_fy1"] * np.random.uniform(0.85, 1.05, len(df))

    # PAT margin proxy
    out["pat_margin_fy1"] = (out["ebitda_margin_fy1"] * 0.65).clip(0, 0.5)
    out["pat_margin_fy2"] = out["pat_margin_fy1"] * np.random.uniform(0.9, 1.05, len(df))

    # ── Leverage ────────────────────────────────────────────────────────────
    # D/E proxy: credit / (income * 3)
    out["debt_equity_fy1"] = (credit / (income * 3 + eps)).clip(0, 10)
    out["debt_equity_fy2"] = out["debt_equity_fy1"] * np.random.uniform(0.9, 1.05, len(df))
    out["debt_equity_fy3"] = out["debt_equity_fy1"] * np.random.uniform(0.85, 1.10, len(df))

    # TOL/TNW proxy
    out["tol_tnw_fy1"] = (out["debt_equity_fy1"] * 1.3).clip(0, 12)
    out["tol_tnw_fy2"] = (out["debt_equity_fy2"] * 1.3).clip(0, 12)

    # ── Liquidity ───────────────────────────────────────────────────────────
    # current ratio proxy: ext_source scores (higher score = better liquidity)
    ext1 = df.get("EXT_SOURCE_1", pd.Series(np.full(len(df), 0.5))).fillna(0.5)
    ext2 = df.get("EXT_SOURCE_2", pd.Series(np.full(len(df), 0.5))).fillna(0.5)
    ext3 = df.get("EXT_SOURCE_3", pd.Series(np.full(len(df), 0.5))).fillna(0.5)
    ext_avg = ((ext1 + ext2 + ext3) / 3).clip(0, 1)

    out["current_ratio_fy1"] = (ext_avg * 3.5 + 0.5).clip(0.3, 4.0)
    out["current_ratio_fy2"] = out["current_ratio_fy1"] * np.random.uniform(0.9, 1.05, len(df))
    out["quick_ratio_fy1"]   = (out["current_ratio_fy1"] * 0.75).clip(0.2, 3.0)

    # ── Working Capital / Efficiency ─────────────────────────────────────────
    # Days employed as proxy for company stability → debtor/creditor days
    days_emp = df.get("DAYS_EMPLOYED", pd.Series(np.full(len(df), -1000))).replace({365243: np.nan}).fillna(-1000)
    stability = ((-days_emp / 3650).clip(0, 1))  # 0-1 scale, 10yrs = 1.0

    out["debtor_days_fy1"]   = (180 - stability * 140).clip(30, 250)
    out["debtor_days_fy2"]   = out["debtor_days_fy1"] * np.random.uniform(0.95, 1.10, len(df))
    out["creditor_days_fy1"] = (120 - stability * 80).clip(15, 200)
    out["inventory_days_fy1"] = (90 - stability * 60).clip(15, 200)
    out["asset_turnover_fy1"] = (income / credit.clip(lower=1)).clip(0, 5)
    out["revenue_growth_fy1"] = (stability * 0.20 - 0.05 + np.random.normal(0, 0.05, len(df))).clip(-0.4, 0.5)

    # ── Profitability ───────────────────────────────────────────────────────
    out["roce_fy1"] = (out["ebitda_margin_fy1"] * out["asset_turnover_fy1"]).clip(0, 0.5)
    out["roce_fy2"] = out["roce_fy1"] * np.random.uniform(0.9, 1.05, len(df))

    # ── GST / Bank Proxies ──────────────────────────────────────────────────
    # Use bureau overdue as GST non-compliance proxy
    bureau_overdue = df.get("bureau_overdue_sum", pd.Series(np.zeros(len(df)))).fillna(0).clip(0)
    bureau_debt    = df.get("bureau_debt_sum", pd.Series(np.zeros(len(df)))).fillna(0).clip(lower=1)
    overdue_ratio  = (bureau_overdue / bureau_debt).clip(0, 1)

    out["gst_compliance_score"]       = ((1 - overdue_ratio) * 10).clip(1, 10)
    out["gst_bank_inflation_ratio"]   = (1.0 + overdue_ratio * 2.0).clip(0.8, 4.0)

    # ── Fraud Flags from Bureau ─────────────────────────────────────────────
    bureau_max_overdue = df.get("bureau_max_overdue_days", pd.Series(np.zeros(len(df)))).fillna(0)
    out["itc_inflation_flag"]         = (bureau_max_overdue > 90).astype(int)
    out["circular_trading_flag"]      = (bureau_max_overdue > 180).astype(int)
    out["window_dressing_flag"]       = ((out["gst_bank_inflation_ratio"] > 1.6) & (bureau_max_overdue > 30)).astype(int)
    out["undisclosed_borrowing_flag"] = (df.get("bureau_active_loans", pd.Series(np.zeros(len(df)))).fillna(0) > 5).astype(int)

    # ── EWS Signals ─────────────────────────────────────────────────────────
    inst_delay = df.get("inst_avg_delay", pd.Series(np.zeros(len(df)))).fillna(0).clip(0)
    inst_short = df.get("inst_short_pay_count", pd.Series(np.zeros(len(df)))).fillna(0).clip(0)

    out["nach_bounce_count"]          = ((inst_delay > 5).astype(int) * 3 + (inst_delay > 15).astype(int) * 3).clip(0, 10)
    out["going_concern_flag"]         = ((out["dscr_fy1"] < 0.8) & (out["debt_equity_fy1"] > 5)).astype(int)
    out["director_cirp_linked"]       = (bureau_max_overdue > 365).astype(int)
    out["drt_case_count"]             = ((bureau_max_overdue > 180).astype(int))
    out["nclt_case_count"]            = ((bureau_max_overdue > 365).astype(int))

    out["ews_character_flags"]        = out["going_concern_flag"] + out["director_cirp_linked"]
    out["ews_capacity_flags"]         = (out["dscr_fy1"] < 1.0).astype(int) + (out["nach_bounce_count"] > 3).astype(int)
    out["ews_capital_flags"]          = (out["debt_equity_fy1"] > 4.0).astype(int)
    out["ews_conditions_flags"]       = out["itc_inflation_flag"] + out["circular_trading_flag"]
    out["total_ews_score_deduction"]  = (
        out["ews_character_flags"] * 10 + out["ews_capacity_flags"] * 8 +
        out["ews_capital_flags"]   * 8 + out["ews_conditions_flags"] * 10
    ).clip(0, 100)

    # ── Character / Management ──────────────────────────────────────────────
    prev_refused  = df.get("prev_refused_count", pd.Series(np.zeros(len(df)))).fillna(0)
    prev_approved = df.get("prev_approved_count", pd.Series(np.zeros(len(df)))).fillna(0)
    refusal_ratio = prev_refused / (prev_approved + prev_refused + 1)

    out["mca_compliance_score"]  = ((1 - refusal_ratio) * 10).clip(1, 10)
    out["director_risk_score"]   = (refusal_ratio * 10).clip(0, 10)
    out["auditor_opinion_score"] = (ext_avg * 10).clip(1, 10)

    age_days = df.get("DAYS_BIRTH", pd.Series(np.full(len(df), -12000))).fillna(-12000)
    age_years = (-age_days / 365).clip(20, 70)
    out["company_age_score"] = ((age_years - 20) / 50 * 8 + 2).clip(2, 10)

    # ── External Factors ────────────────────────────────────────────────────
    out["rating_direction"]      = np.sign(ext2 - 0.5).astype(int)
    out["network_risk_score"]    = ((1 - ext_avg) * bureau_max_overdue.clip(0, 365) / 36.5).clip(0, 10)
    out["supplier_default_risk"] = (overdue_ratio * 8).clip(0, 10)
    out["promoter_network_risk"] = (refusal_ratio * 8).clip(0, 10)
    out["negative_news_score"]   = (out["total_ews_score_deduction"] / 20).clip(0, 10)
    out["litigation_count"]      = out["drt_case_count"] + out["nclt_case_count"]
    out["regulatory_risk_score"] = (out["litigation_count"] * 2 + out["circular_trading_flag"] * 3).clip(0, 10)
    out["sector_risk_score"]     = np.random.randint(2, 9, len(df))
    out["collateral_type_score"] = np.random.randint(1, 5, len(df))
    out["security_coverage_ratio"] = (out["current_ratio_fy1"] * 0.9).clip(0.3, 3.0)

    int_cols = ["nach_bounce_count", "drt_case_count", "nclt_case_count", "ews_character_flags",
                "ews_capacity_flags", "ews_capital_flags", "ews_conditions_flags",
                "sector_risk_score", "collateral_type_score", "litigation_count"]
    for c in int_cols:
        if c in out.columns:
            out[c] = out[c].astype(int)

    n_default = out["default"].sum()
    logger.info(f"  Home Credit features engineered: {len(out):,} rows, {n_default} defaults ({n_default/len(out)*100:.1f}%)")
    return out.reset_index(drop=True)


# ─── Dataset 2: Corporate Credit Risk ─────────────────────────────────────────

def load_corporate_credit() -> pd.DataFrame:
    """
    Load the Corporate Credit Risk dataset.
    Direct financial ratio mapping — closest to our feature schema.
    """
    candidates = ["corporate_credit_risk.csv", "corporate_credit.csv", "credit_risk.csv"]
    path = None
    for c in candidates:
        p = os.path.join(CORP_DIR, c)
        if os.path.exists(p):
            path = p
            break

    if path is None:
        logger.warning(f"Corporate Credit dataset not found in {CORP_DIR}. Skipping.")
        return pd.DataFrame()

    logger.info(f"Loading Corporate Credit: {path}")
    df = pd.read_csv(path)
    df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]
    logger.info(f"  Columns: {list(df.columns)}")
    return _engineer_corporate_features(df)


def _engineer_corporate_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Map corporate_credit_risk.csv columns to canonical schema.
    The dataset has columns like: total_assets, net_worth, total_income, default, etc.
    Column names vary — we try multiple aliases.
    """
    eps = 1e-9
    out = pd.DataFrame()
    n = len(df)

    def get(col_aliases, default_val=np.nan):
        for alias in col_aliases:
            if alias in df.columns:
                return df[alias]
        return pd.Series(np.full(n, default_val))

    # Target
    target_col = None
    for tc in ["default", "target", "label", "default_flag", "NPA", "npa"]:
        if tc in df.columns:
            target_col = tc
            break
    if target_col is None:
        logger.warning("No target column found in corporate_credit. Skipping.")
        return pd.DataFrame()

    out["default"] = (df[target_col].fillna(0) > 0).astype(int)

    # Financial data
    total_assets   = get(["total_assets", "totalassets", "total_asset"]).fillna(1).clip(lower=1)
    net_worth      = get(["net_worth", "networth", "equity", "shareholders_equity"]).fillna(np.nan)
    total_income   = get(["total_income", "revenue", "net_revenue", "sales", "turnover"]).fillna(np.nan)
    total_debt     = get(["total_debt", "total_borrowings", "borrowings", "debt"]).fillna(np.nan)
    ebitda         = get(["ebitda", "operating_profit"]).fillna(np.nan)
    pat            = get(["pat", "net_profit", "profit_after_tax", "net_income"]).fillna(np.nan)
    current_assets = get(["current_assets"]).fillna(total_assets * 0.45)
    current_liab   = get(["current_liabilities", "current_liability"]).fillna(current_assets * 0.8)
    fin_costs      = get(["finance_costs", "interest_expense", "interest"]).fillna(np.nan)

    # Compute ratios
    nw = net_worth.fillna(total_assets * 0.3).clip(lower=eps)
    td = total_debt.fillna(total_assets * 0.5).clip(lower=eps)
    ti = total_income.fillna(total_assets * 0.6).clip(lower=eps)
    eb = ebitda.fillna(ti * 0.12).clip(lower=eps)
    fc = fin_costs.fillna(td * 0.10).clip(lower=eps)

    out["debt_equity_fy1"] = (td / nw).clip(0, 12)
    out["debt_equity_fy2"] = out["debt_equity_fy1"] * np.random.uniform(0.9, 1.05, n)
    out["debt_equity_fy3"] = out["debt_equity_fy1"] * np.random.uniform(0.85, 1.10, n)
    out["tol_tnw_fy1"]     = ((td + current_liab) / nw).clip(0, 15)
    out["tol_tnw_fy2"]     = out["tol_tnw_fy1"] * np.random.uniform(0.9, 1.05, n)

    out["ebitda_margin_fy1"] = (eb / ti).clip(-0.5, 1.0)
    out["ebitda_margin_fy2"] = out["ebitda_margin_fy1"] * np.random.uniform(0.9, 1.05, n)
    out["ebitda_margin_fy3"] = out["ebitda_margin_fy1"] * np.random.uniform(0.85, 1.05, n)

    pat_val = pat.fillna(eb * 0.65)
    out["pat_margin_fy1"] = (pat_val / ti).clip(-1.0, 1.0)
    out["pat_margin_fy2"] = out["pat_margin_fy1"] * np.random.uniform(0.9, 1.05, n)

    out["interest_coverage_fy1"] = (eb / fc).clip(0, 20)
    out["interest_coverage_fy2"] = out["interest_coverage_fy1"] * np.random.uniform(0.9, 1.05, n)

    # DSCR: (PAT + Depreciation + Interest) / (Annual Repayment + Interest)
    dep = get(["depreciation"]).fillna(total_assets * 0.05)
    annual_repay = fc * 0.8  # approximate
    out["dscr_fy1"] = ((pat_val + dep + fc) / (annual_repay + fc + eps)).clip(0, 10)
    out["dscr_fy2"] = out["dscr_fy1"] * np.random.uniform(0.9, 1.05, n)
    out["dscr_fy3"] = out["dscr_fy1"] * np.random.uniform(0.85, 1.10, n)

    # Liquidity
    ca = current_assets.clip(lower=eps)
    cl = current_liab.clip(lower=eps)
    out["current_ratio_fy1"] = (ca / cl).clip(0.2, 6.0)
    out["current_ratio_fy2"] = out["current_ratio_fy1"] * np.random.uniform(0.9, 1.05, n)
    out["quick_ratio_fy1"]   = (out["current_ratio_fy1"] * 0.75).clip(0.1, 4.0)

    # Efficiency
    debtors = get(["debtors", "trade_receivables", "accounts_receivable"]).fillna(ti * 0.15)
    creditors = get(["creditors", "trade_payables"]).fillna(ti * 0.12)
    inventory = get(["inventory", "inventories", "stock"]).fillna(ti * 0.12)

    out["debtor_days_fy1"]    = (debtors / ti * 365).clip(5, 300)
    out["debtor_days_fy2"]    = out["debtor_days_fy1"] * np.random.uniform(0.95, 1.15, n)
    out["creditor_days_fy1"]  = (creditors / ti * 365).clip(5, 250)
    out["inventory_days_fy1"] = (inventory / ti * 365).clip(5, 300)

    out["asset_turnover_fy1"] = (ti / total_assets).clip(0, 5)
    out["revenue_growth_fy1"] = (get(["revenue_growth", "growth"]).fillna(np.nan)
                                  .pipe(lambda s: s if not s.isna().all() else pd.Series(np.random.uniform(-0.15, 0.20, n)))
                                  ).clip(-0.5, 1.0)

    out["roce_fy1"] = (eb / total_assets).clip(0, 0.5)
    out["roce_fy2"] = out["roce_fy1"] * np.random.uniform(0.9, 1.05, n)

    # GST/Bank proxies (not directly available — derive from ratios)
    npa_proxy = (out["dscr_fy1"] < 1.0).astype(float)
    out["gst_compliance_score"]     = ((1 - npa_proxy) * 6 + out["ebitda_margin_fy1"].clip(0, 0.4) * 10).clip(1, 10)
    out["gst_bank_inflation_ratio"] = (1.0 + (out["debt_equity_fy1"] / 10.0)).clip(0.9, 4.0)

    # Binary flags from financial stress
    out["itc_inflation_flag"]          = (out["gst_bank_inflation_ratio"] > 1.8).astype(int)
    out["circular_trading_flag"]       = ((out["debt_equity_fy1"] > 6) & (out["ebitda_margin_fy1"] < 0)).astype(int)
    out["window_dressing_flag"]        = ((out["current_ratio_fy1"] < 0.8) & (out["debtor_days_fy1"] > 120)).astype(int)
    out["undisclosed_borrowing_flag"]  = (out["tol_tnw_fy1"] > 8).astype(int)
    out["nach_bounce_count"]           = ((out["dscr_fy1"] < 0.9).astype(int) * 2 + (out["dscr_fy1"] < 0.7).astype(int) * 3).clip(0, 10)
    out["going_concern_flag"]          = ((out["dscr_fy1"] < 0.7) | (out["pat_margin_fy1"] < -0.15)).astype(int)
    out["director_cirp_linked"]        = (out["debt_equity_fy1"] > 8).astype(int)
    out["drt_case_count"]              = out["going_concern_flag"].astype(int)
    out["nclt_case_count"]             = out["director_cirp_linked"].astype(int)

    out["total_ews_score_deduction"]  = (out["going_concern_flag"] * 25 + out["itc_inflation_flag"] * 15 + out["circular_trading_flag"] * 20).clip(0, 100)
    out["ews_character_flags"]        = out["going_concern_flag"] + out["director_cirp_linked"]
    out["ews_capacity_flags"]         = (out["dscr_fy1"] < 1.0).astype(int) + (out["nach_bounce_count"] > 3).astype(int)
    out["ews_capital_flags"]          = (out["debt_equity_fy1"] > 3.5).astype(int)
    out["ews_conditions_flags"]       = out["itc_inflation_flag"] + out["circular_trading_flag"]

    out["mca_compliance_score"]       = (10 - out["director_cirp_linked"] * 3 - out["going_concern_flag"] * 2).clip(1, 10)
    out["director_risk_score"]        = (out["director_cirp_linked"] * 5 + npa_proxy * 3).clip(0, 10)
    out["auditor_opinion_score"]      = (10 - out["going_concern_flag"] * 5 - out["itc_inflation_flag"] * 2).clip(1, 10)
    out["company_age_score"]          = get(["age", "company_age"]).fillna(pd.Series(np.random.uniform(3, 9, n))).clip(1, 10)
    out["rating_direction"]           = np.where(out["dscr_fy1"] > 1.5, 1, np.where(out["dscr_fy1"] < 1.0, -1, 0))
    out["network_risk_score"]         = (out["total_ews_score_deduction"] / 15).clip(0, 10)
    out["supplier_default_risk"]      = (out["creditor_days_fy1"] / 30).clip(0, 10)
    out["promoter_network_risk"]      = out["director_risk_score"]
    out["negative_news_score"]        = (out["total_ews_score_deduction"] / 15).clip(0, 10)
    out["litigation_count"]           = out["drt_case_count"] + out["nclt_case_count"]
    out["regulatory_risk_score"]      = (out["litigation_count"] * 2 + out["circular_trading_flag"] * 3).clip(0, 10)
    out["sector_risk_score"]          = get(["sector_risk", "industry_risk"]).fillna(pd.Series(np.random.randint(2, 9, n))).clip(1, 10)
    out["collateral_type_score"]      = get(["collateral_score", "security_score"]).fillna(pd.Series(np.random.randint(1, 5, n))).clip(0, 5)
    out["security_coverage_ratio"]    = get(["security_coverage"]).fillna(out["current_ratio_fy1"] * 0.85).clip(0.2, 4.0)

    int_cols = ["nach_bounce_count", "drt_case_count", "nclt_case_count", "ews_character_flags",
                "ews_capacity_flags", "ews_capital_flags", "ews_conditions_flags",
                "sector_risk_score", "collateral_type_score", "litigation_count"]
    for c in int_cols:
        if c in out.columns:
            out[c] = out[c].round().astype(int)

    n_def = out["default"].sum()
    logger.info(f"  Corporate features: {len(out):,} rows, {n_def} defaults ({n_def/len(out)*100:.1f}%)")
    return out.reset_index(drop=True)


# ─── Dataset 3: SME Financial Decision Dataset ────────────────────────────────

def load_sme_credit() -> pd.DataFrame:
    """
    Load SME Financial Decision Risk Prediction dataset.
    33 financial features, 15K rows, SME credit decisions.
    """
    candidates = [
        "sme_financial_decision_dataset.csv",
        "sme_credit.csv", "sme_data.csv",
        "SME_Financial_Decision_Risk_Prediction_Dataset.csv",
        "dataset.csv",
    ]
    path = None
    for c in candidates:
        p = os.path.join(SME_DIR, c)
        if os.path.exists(p):
            path = p
            break

    if path is None:
        # Try any CSV in the folder
        for f in os.listdir(SME_DIR) if os.path.exists(SME_DIR) else []:
            if f.endswith(".csv"):
                path = os.path.join(SME_DIR, f)
                break

    if path is None:
        logger.warning(f"SME dataset not found in {SME_DIR}. Skipping.")
        return pd.DataFrame()

    logger.info(f"Loading SME Credit: {path}")
    df = pd.read_csv(path)
    df.columns = [c.lower().strip().replace(" ", "_").replace("-", "_") for c in df.columns]
    logger.info(f"  Columns: {list(df.columns)[:15]}...")
    return _engineer_sme_features(df)


def _engineer_sme_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Map SME dataset columns to canonical feature schema.
    SME dataset has direct financial ratios — minimal transformation needed.
    """
    eps = 1e-9
    out = pd.DataFrame()
    n = len(df)

    def get(aliases, default=np.nan):
        for a in aliases:
            if a in df.columns:
                return df[a].astype(float)
        return pd.Series(np.full(n, default))

    # Target
    target = None
    for tc in ["default", "label", "target", "credit_decision", "decision", "risk",
               "financial_decision", "default_flag", "status",
               "financial_distress", "Financial_Distress",
               "distress", "loan_default", "npa", "bad_loan"]:
        if tc in df.columns:
            target = tc
            break
    if target is None:
        logger.warning(f"No target column found in SME dataset. Columns: {list(df.columns)[:10]}. Skipping.")
        return pd.DataFrame()

    raw_target = df[target]
    # Handle categorical target (e.g., "approve"/"reject" or 0/1)
    if raw_target.dtype == object:
        reject_words = ["reject", "decline", "no", "default", "bad", "high_risk", "1"]
        out["default"] = raw_target.str.lower().str.strip().isin(reject_words).astype(int)
    else:
        out["default"] = (raw_target > 0).astype(int)

    # Direct ratio mappings (SME dataset uses standard financial terminology)
    out["current_ratio_fy1"]  = get(["current_ratio", "liquidity_ratio", "cr"]).fillna(1.2).clip(0.2, 6.0)
    out["current_ratio_fy2"]  = out["current_ratio_fy1"] * np.random.uniform(0.9, 1.05, n)
    out["quick_ratio_fy1"]    = get(["quick_ratio", "acid_test", "qr"]).fillna(out["current_ratio_fy1"] * 0.75).clip(0.1, 5.0)

    out["debt_equity_fy1"]    = get(["debt_equity_ratio", "debt_to_equity", "leverage", "de_ratio", "debt_equity"]).fillna(2.0).clip(0, 12)
    out["debt_equity_fy2"]    = out["debt_equity_fy1"] * np.random.uniform(0.9, 1.05, n)
    out["debt_equity_fy3"]    = out["debt_equity_fy1"] * np.random.uniform(0.85, 1.10, n)

    out["tol_tnw_fy1"]        = get(["tol_tnw", "total_outside_liabilities", "tol"]).fillna(out["debt_equity_fy1"] * 1.3).clip(0, 15)
    out["tol_tnw_fy2"]        = out["tol_tnw_fy1"] * np.random.uniform(0.9, 1.05, n)

    # EBITDA margin — direct or derived
    ebitda_m = get(["ebitda_margin", "ebitda_margin_%", "operating_margin"]).fillna(np.nan)
    if ebitda_m.isna().all():
        ebitda_m = get(["ebitda", "operating_profit"]).fillna(np.nan) / get(["revenue", "sales", "turnover"], 1.0).clip(lower=eps)
    out["ebitda_margin_fy1"]  = ebitda_m.fillna(0.10).clip(-0.5, 1.0)
    out["ebitda_margin_fy2"]  = out["ebitda_margin_fy1"] * np.random.uniform(0.9, 1.05, n)
    out["ebitda_margin_fy3"]  = out["ebitda_margin_fy1"] * np.random.uniform(0.85, 1.05, n)

    pat_m = get(["pat_margin", "net_profit_margin", "profit_margin", "npm"]).fillna(out["ebitda_margin_fy1"] * 0.65)
    out["pat_margin_fy1"]     = pat_m.clip(-1.0, 1.0)
    out["pat_margin_fy2"]     = out["pat_margin_fy1"] * np.random.uniform(0.9, 1.05, n)

    out["interest_coverage_fy1"] = get(["interest_coverage", "icr", "interest_coverage_ratio"]).fillna(
        (out["ebitda_margin_fy1"] / 0.08).clip(0.5, 20)
    ).clip(0, 25)
    out["interest_coverage_fy2"] = out["interest_coverage_fy1"] * np.random.uniform(0.9, 1.05, n)

    out["dscr_fy1"] = get(["dscr", "debt_service_coverage", "debt_service_coverage_ratio"]).fillna(
        (out["interest_coverage_fy1"] * 0.7).clip(0.3, 8)
    ).clip(0, 10)
    out["dscr_fy2"] = out["dscr_fy1"] * np.random.uniform(0.9, 1.05, n)
    out["dscr_fy3"] = out["dscr_fy1"] * np.random.uniform(0.85, 1.10, n)

    out["debtor_days_fy1"]     = get(["debtor_days", "receivable_days", "dso"]).fillna(60.0).clip(5, 300)
    out["debtor_days_fy2"]     = out["debtor_days_fy1"] * np.random.uniform(0.95, 1.10, n)
    out["creditor_days_fy1"]   = get(["creditor_days", "payable_days", "dpo"]).fillna(45.0).clip(5, 250)
    out["inventory_days_fy1"]  = get(["inventory_days", "stock_days", "dio"]).fillna(60.0).clip(5, 300)
    out["asset_turnover_fy1"]  = get(["asset_turnover", "asset_utilisation"]).fillna(1.0).clip(0.1, 5)
    out["revenue_growth_fy1"]  = get(["revenue_growth", "sales_growth", "growth_rate"]).fillna(0.05).clip(-0.5, 1.0)
    out["roce_fy1"]            = get(["roce", "return_on_capital", "roc"]).fillna(out["ebitda_margin_fy1"] * out["asset_turnover_fy1"]).clip(0, 0.5)
    out["roce_fy2"]            = out["roce_fy1"] * np.random.uniform(0.9, 1.05, n)

    # GST Proxies
    out["gst_compliance_score"]     = get(["gst_score", "tax_compliance"]).fillna((out["dscr_fy1"] / 10 * 6 + 4).clip(1, 10))
    out["gst_bank_inflation_ratio"] = get(["inflation_ratio"]).fillna(1.0 + (1 - out["ebitda_margin_fy1"].clip(0, 1)) * 0.5).clip(0.8, 4.0)

    # Binary risk flags
    out["itc_inflation_flag"]          = get(["itc_fraud", "tax_fraud"]).fillna((out["gst_bank_inflation_ratio"] > 1.6).astype(float)).clip(0, 1).round().astype(int)
    out["circular_trading_flag"]       = get(["circular_trading"]).fillna((out["debt_equity_fy1"] > 6).astype(float)).clip(0, 1).round().astype(int)
    out["window_dressing_flag"]        = ((out["current_ratio_fy1"] < 0.9) & (out["debtor_days_fy1"] > 100)).astype(int)
    out["undisclosed_borrowing_flag"]  = (out["tol_tnw_fy1"] > 7).astype(int)
    out["nach_bounce_count"]           = ((out["dscr_fy1"] < 1.0).astype(int) * 2 + (out["dscr_fy1"] < 0.8).astype(int) * 2).clip(0, 10)
    out["going_concern_flag"]          = get(["going_concern"]).fillna(((out["dscr_fy1"] < 0.7) & (out["pat_margin_fy1"] < -0.10)).astype(float)).clip(0, 1).round().astype(int)
    out["director_cirp_linked"]        = (out["debt_equity_fy1"] > 7).astype(int)
    out["drt_case_count"]              = out["going_concern_flag"].astype(int)
    out["nclt_case_count"]             = out["director_cirp_linked"].astype(int)

    out["total_ews_score_deduction"]  = (out["going_concern_flag"] * 25 + out["itc_inflation_flag"] * 15 + out["circular_trading_flag"] * 20 + out["nach_bounce_count"] * 5).clip(0, 100)
    out["ews_character_flags"]        = out["going_concern_flag"] + out["director_cirp_linked"]
    out["ews_capacity_flags"]         = (out["dscr_fy1"] < 1.0).astype(int) + (out["nach_bounce_count"] > 3).astype(int)
    out["ews_capital_flags"]          = (out["debt_equity_fy1"] > 3.5).astype(int)
    out["ews_conditions_flags"]       = out["itc_inflation_flag"] + out["circular_trading_flag"]

    out["mca_compliance_score"]    = get(["mca_score", "regulatory_score"]).fillna((10 - out["director_cirp_linked"] * 3).clip(1, 10))
    out["director_risk_score"]     = out["director_cirp_linked"] * 5 + out["going_concern_flag"] * 3
    out["auditor_opinion_score"]   = (10 - out["going_concern_flag"] * 5).clip(1, 10)
    out["company_age_score"]       = get(["company_age", "age_score"]).fillna(pd.Series(np.random.uniform(3, 9, n))).clip(1, 10)
    out["rating_direction"]        = np.where(out["dscr_fy1"] > 1.5, 1, np.where(out["dscr_fy1"] < 1.0, -1, 0))
    out["network_risk_score"]      = (out["total_ews_score_deduction"] / 15).clip(0, 10)
    out["supplier_default_risk"]   = (out["creditor_days_fy1"] / 30).clip(0, 10)
    out["promoter_network_risk"]   = out["director_risk_score"].clip(0, 10)
    out["negative_news_score"]     = (out["total_ews_score_deduction"] / 15).clip(0, 10)
    out["litigation_count"]        = out["drt_case_count"] + out["nclt_case_count"]
    out["regulatory_risk_score"]   = (out["litigation_count"] * 2 + out["circular_trading_flag"] * 3).clip(0, 10)
    out["sector_risk_score"]       = get(["sector_risk", "industry_risk"]).fillna(pd.Series(np.random.randint(2, 9, n))).clip(1, 10)
    out["collateral_type_score"]   = get(["collateral_score"]).fillna(pd.Series(np.random.randint(1, 5, n))).clip(0, 5)
    out["security_coverage_ratio"] = get(["security_coverage"]).fillna(out["current_ratio_fy1"] * 0.85).clip(0.2, 4.0)

    int_cols = ["nach_bounce_count", "drt_case_count", "nclt_case_count", "ews_character_flags",
                "ews_capacity_flags", "ews_capital_flags", "ews_conditions_flags",
                "sector_risk_score", "collateral_type_score", "litigation_count"]
    for c in int_cols:
        if c in out.columns:
            out[c] = out[c].round().astype(int)

    n_def = out["default"].sum()
    logger.info(f"  SME features: {len(out):,} rows, {n_def} defaults ({n_def/len(out)*100:.1f}%)")
    return out.reset_index(drop=True)
