from pydantic import BaseModel
from typing import Optional


class GSTRMonthlyEntry(BaseModel):
    month: str             # "2023-04" (YYYY-MM)
    gstin: str
    outward_taxable: int   # paise
    itc_claimed: int       # paise (from 3B)
    itc_eligible: int      # paise (from 2A)
    tax_paid: int          # paise
    filing_status: str     # "filed" | "not_filed" | "late_filed"


class GSTReconciliationResult(BaseModel):
    gstr1_annual_turnover: int = 0
    gstr3b_annual_turnover: int = 0
    gstr2a_total_itc_eligible: int = 0
    gstr3b_total_itc_claimed: int = 0
    gstr9_annual_turnover: Optional[int] = None

    # Computed flags
    gstr1_vs_3b_delta_paise: int = 0
    itc_excess_claim_paise: int = 0         # claimed - eligible
    gstr9_vs_3b_sum_delta: Optional[int] = None

    # Flags triggered
    turnover_suppression_flag: bool = False
    itc_inflation_flag: bool = False
    annual_reconciliation_gap_flag: bool = False

    # Narratives
    itc_narrative: str = ""
    turnover_narrative: str = ""
    overall_gst_risk: str = "LOW"  # LOW | MEDIUM | HIGH | CRITICAL

    # Monthly data
    monthly_entries: list[GSTRMonthlyEntry] = []


class GSTR1Result(BaseModel):
    gstin: str = ""
    period: str = ""
    annual_turnover_paise: int = 0
    b2b_turnover_paise: int = 0
    b2c_turnover_paise: int = 0
    export_turnover_paise: int = 0
    monthly_turnover: dict = {}     # YYYY-MM -> paise
    buyer_list: list[dict] = []     # [{gstin, value}]


class GSTR3BResult(BaseModel):
    gstin: str = ""
    period: str = ""
    annual_outward_paise: int = 0
    total_itc_claimed_paise: int = 0
    total_itc_reversed_paise: int = 0
    net_itc_paise: int = 0
    tax_paid_cash_paise: int = 0
    tax_paid_credit_paise: int = 0
    monthly_data: dict = {}         # YYYY-MM -> {outward, itc}


class GSTR2AResult(BaseModel):
    gstin: str = ""
    period: str = ""
    total_itc_eligible_paise: int = 0
    supplier_list: list[dict] = []  # [{gstin, value, filing_status}]
    monthly_itc: dict = {}          # YYYY-MM -> paise


class GSTR9Result(BaseModel):
    gstin: str = ""
    fy: str = ""
    annual_turnover_paise: int = 0
    itc_availed_paise: int = 0
    tax_payable_paise: int = 0
    tax_paid_paise: int = 0
