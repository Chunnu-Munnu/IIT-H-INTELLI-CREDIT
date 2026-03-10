from pydantic import BaseModel
from datetime import date
from typing import Optional


class FinancialPeriod(BaseModel):
    fy_label: str          # "FY_2023"
    start_date: date       # 2022-04-01
    end_date: date         # 2023-03-31


class FinancialLineItem(BaseModel):
    canonical_label: str   # from SCHEDULE_III_MAPPINGS
    original_label: str    # as found in document
    value_paise: int       # ALL amounts stored as paise integers
    period: FinancialPeriod
    source_doc: str        # filename
    page_number: int
    table_id: str
    row_label: str
    confidence: float


class FinancialRecord(BaseModel):
    period: FinancialPeriod
    # P&L
    revenue_from_ops: Optional[int] = None
    total_income: Optional[int] = None
    other_income: Optional[int] = None
    employee_costs: Optional[int] = None
    finance_costs: Optional[int] = None
    depreciation: Optional[int] = None
    pbt: Optional[int] = None
    pat: Optional[int] = None
    ebitda: Optional[int] = None
    ebit: Optional[int] = None
    gross_profit: Optional[int] = None
    cogs: Optional[int] = None
    other_expenses: Optional[int] = None
    # Balance Sheet
    total_assets: Optional[int] = None
    non_current_assets: Optional[int] = None
    fixed_assets: Optional[int] = None
    current_assets: Optional[int] = None
    current_liabilities: Optional[int] = None
    total_debt: Optional[int] = None
    long_term_debt: Optional[int] = None
    short_term_debt: Optional[int] = None
    net_worth: Optional[int] = None
    share_capital: Optional[int] = None
    reserves: Optional[int] = None
    debtors: Optional[int] = None
    inventory: Optional[int] = None
    creditors: Optional[int] = None
    cash: Optional[int] = None
    investments: Optional[int] = None
    loans_advances: Optional[int] = None
    # Cash Flow
    cfo: Optional[int] = None    # cash from operations
    cfi: Optional[int] = None    # cash from investing
    cff: Optional[int] = None    # cash from financing
    capex: Optional[int] = None
    # Data quality
    data_source_reliability: float = 0.85
    extraction_confidence: float = 0.80
    combined_confidence_score: float = 0.82


class RatioResult(BaseModel):
    period: FinancialPeriod
    current_ratio: Optional[float] = None
    quick_ratio: Optional[float] = None
    debt_equity: Optional[float] = None
    tol_tnw: Optional[float] = None     # total outside liabilities / tangible net worth
    interest_coverage: Optional[float] = None
    dscr: Optional[float] = None        # debt service coverage ratio
    pat_margin: Optional[float] = None
    ebitda_margin: Optional[float] = None
    roce: Optional[float] = None
    roe: Optional[float] = None
    debtor_days: Optional[float] = None
    creditor_days: Optional[float] = None
    inventory_days: Optional[float] = None
    asset_turnover: Optional[float] = None
    revenue_growth: Optional[float] = None
    confidence: float = 0.80
