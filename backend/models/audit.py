from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime
from models.risk import RiskLevel


class AuditTrailEntry(BaseModel):
    entry_id: str            # uuid4
    case_id: str
    finding_type: str
    source_document: str
    page_number: int = 0
    section_name: str = ""
    extracted_value: Any = None
    comparison_source: str = ""
    comparison_value: Any = None
    delta_paise: Optional[int] = None
    delta_percentage: Optional[float] = None
    rule_triggered: str = ""
    five_c_mapping: str = ""
    risk_level: RiskLevel = RiskLevel.LOW
    ocr_confidence: float = 0.80
    narrative: str = ""          # plain English auto-generated paragraph
    timestamp: datetime = None

    def model_post_init(self, __context):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
