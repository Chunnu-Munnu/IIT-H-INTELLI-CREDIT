from pydantic import BaseModel
from datetime import date
from typing import Optional


class BankTransaction(BaseModel):
    date: date
    description: str
    debit_paise: int
    credit_paise: int
    balance_paise: int
    transaction_type: str   # NACH | GST_PAYMENT | CASH | RTGS | IMPS | OTHER


class BankAnalysis(BaseModel):
    account_number: str = ""
    bank_name: str = ""
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    average_monthly_balance_paise: int = 0
    total_deposits_paise: int = 0
    total_withdrawals_paise: int = 0
    nach_emi_total_paise: int = 0        # inferred loan EMIs
    gst_payments_paise: int = 0          # actual GST paid (cross-checks 3B)
    cash_withdrawal_ratio: float = 0.0   # cash / total debits
    end_of_period_spike: bool = False    # window dressing indicator
    nach_bounce_count: int = 0
    monthly_balance_series: dict = {}    # YYYY-MM -> avg balance paise
    monthly_deposit_series: dict = {}    # YYYY-MM -> total deposits paise
    transactions: list[BankTransaction] = []
