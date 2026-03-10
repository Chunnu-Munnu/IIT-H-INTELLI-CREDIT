from enum import Enum
from pydantic import BaseModel
from typing import Optional, Any


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EWSFlag(BaseModel):
    flag_name: str           # from EWS_FLAGS constant
    triggered: bool
    severity: RiskLevel
    evidence_summary: str
    five_c_impact: str       # Character | Capacity | Capital | Collateral | Conditions
    score_deduction: int     # 0-20, used by ensemble model
    source_documents: list[str] = []


class EWSReport(BaseModel):
    case_id: str
    flags: list[EWSFlag] = []
    total_score_deduction: int = 0
    overall_risk_classification: RiskLevel = RiskLevel.LOW
    triggered_count: int = 0
    critical_count: int = 0
    high_count: int = 0


class RiskSignal(BaseModel):
    signal_type: str
    section_name: str
    keyword_matched: str
    context_text: str
    severity: RiskLevel
    five_c_mapping: str
    source_document: str
    page_number: int = 0
    confidence: float = 0.8
