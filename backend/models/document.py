from enum import Enum
from pydantic import BaseModel
from datetime import datetime


class DocumentType(str, Enum):
    ANNUAL_REPORT = "annual_report"
    FINANCIAL_STATEMENT_STANDALONE = "financial_statement_standalone"
    FINANCIAL_STATEMENT_CONSOLIDATED = "financial_statement_consolidated"
    GST_GSTR1 = "gst_gstr1"
    GST_GSTR3B = "gst_gstr3b"
    GST_GSTR2A = "gst_gstr2a"
    GST_GSTR9 = "gst_gstr9"
    GST_GSTR9C = "gst_gstr9c"
    BANK_STATEMENT_SBI = "bank_sbi"
    BANK_STATEMENT_HDFC = "bank_hdfc"
    BANK_STATEMENT_ICICI = "bank_icici"
    BANK_STATEMENT_AXIS = "bank_axis"
    BANK_STATEMENT_GENERIC = "bank_generic"
    ITR_6 = "itr_6"
    SANCTION_LETTER = "sanction_letter"
    LEGAL_NOTICE = "legal_notice"
    DRT_FILING = "drt_filing"
    RATING_REPORT = "rating_report"
    MCA_FORM_CHG1 = "mca_chg1"
    MCA_COMPANY_MASTER = "mca_company_master"
    SHAREHOLDING_PATTERN = "shareholding_pattern"
    ALM_REPORT = "alm_report"
    BORROWING_PROFILE = "borrowing_profile"
    PORTFOLIO_PERFORMANCE = "portfolio_performance"
    BOARD_MINUTES = "board_minutes"
    CIBIL_COMMERCIAL = "cibil_commercial"
    VALUATION_REPORT = "valuation_report"
    UNKNOWN = "unknown"


MIME_TYPE_MAP = {
    ".pdf": "application/pdf",
    ".json": "application/json",
    ".csv": "text/csv",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
}


class DocumentInfo(BaseModel):
    file_id: str
    filename: str
    doc_type: DocumentType
    classification_confidence: float
    page_count: int
    is_scanned: bool
    ocr_applied: bool
    file_size_bytes: int
    upload_timestamp: datetime
