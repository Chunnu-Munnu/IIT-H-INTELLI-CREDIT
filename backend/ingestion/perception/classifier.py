import re
import os
import json
from loguru import logger
from models.document import DocumentType
from ingestion.perception.fingerprints import (
    GST_FINGERPRINTS, ANNUAL_REPORT_FINGERPRINTS,
    RATING_REPORT_FINGERPRINTS, LEGAL_NOTICE_FINGERPRINTS,
    SANCTION_LETTER_FINGERPRINTS, CIBIL_FINGERPRINTS, MCA_FINGERPRINTS,
    ALM_FINGERPRINTS, SHAREHOLDING_FINGERPRINTS,
    BORROWING_PROFILE_FINGERPRINTS, PORTFOLIO_PERFORMANCE_FINGERPRINTS,
)

BANK_FINGERPRINTS = {
    "SBI": {
        "header_patterns": [r"state bank of india", r"\bsbi\b"],
        "column_patterns": [r"txn date", r"value date", r"description", r"debit", r"credit", r"balance"],
    },
    "HDFC": {
        "header_patterns": [r"hdfc bank", r"h\.d\.f\.c"],
        "column_patterns": [r"date", r"narration", r"chq\.?/ref\.?", r"withdrawal", r"deposit", r"closing balance"],
    },
    "ICICI": {
        "header_patterns": [r"icici bank"],
        "column_patterns": [r"s no", r"value date", r"transaction date", r"cheque number", r"transaction remarks"],
    },
    "AXIS": {
        "header_patterns": [r"axis bank"],
        "column_patterns": [r"tran date", r"chq no", r"particulars", r"withdrawals", r"deposits", r"balance"],
    },
    "KOTAK": {
        "header_patterns": [r"kotak mahindra", r"kotak bank"],
        "column_patterns": [r"date", r"description", r"debit", r"credit", r"balance"],
    },
    "YES": {
        "header_patterns": [r"yes bank"],
        "column_patterns": [r"value date", r"description", r"debit", r"credit", r"balance"],
    },
}


async def classify_document(file_path: str) -> tuple[DocumentType, float]:
    """
    Returns (DocumentType, confidence_score 0.0-1.0)
    """
    ext = os.path.splitext(file_path)[1].lower()

    # JSON files — check structure for GST return type
    if ext == ".json":
        try:
            with open(file_path) as f:
                data = json.load(f)
            keys = set(str(k).lower() for k in data.keys())
            if any(k in keys for k in ["b2b", "b2cl", "hsnsac", "exp"]):
                return DocumentType.GST_GSTR1, 0.92
            if any(k in keys for k in ["sup_details", "itc_elg", "intr_ltfee"]):
                return DocumentType.GST_GSTR3B, 0.92
            if "docdet" in keys or "inum" in keys:
                return DocumentType.GST_GSTR2A, 0.88
            if "pt_i" in keys or "pt_ii" in keys:
                return DocumentType.GST_GSTR9, 0.90
        except Exception as e:
            logger.warning(f"JSON parse error for {file_path}: {e}")
        return DocumentType.UNKNOWN, 0.3

    # PDF/CSV files — text-based classification
    if ext == ".pdf":
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(file_path)
            text = ""
            for page_num in range(min(5, len(doc))):
                text += doc[page_num].get_text().lower()
            doc.close()

            # If very little text, mark as scanned
            if len(text.strip()) < 200:
                # For scanned docs, return generic unknown for now
                # OCR will be applied during extraction
                return DocumentType.UNKNOWN, 0.4

            return _classify_from_text(text)
        except Exception as e:
            logger.warning(f"PDF classification error for {file_path}: {e}")
            return DocumentType.UNKNOWN, 0.3

    if ext == ".csv":
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read(5000).lower()
            return _classify_from_text(text)
        except Exception:
            return DocumentType.UNKNOWN, 0.3

    return DocumentType.UNKNOWN, 0.2


def _classify_from_text(text: str) -> tuple[DocumentType, float]:
    """Score each document type fingerprint against extracted text."""
    scores: dict[DocumentType, float] = {}

    # GST Returns
    for gst_type, fp in GST_FINGERPRINTS.items():
        score = _score_fingerprint(text, fp.get("required_keywords", []))
        excl_keywords = fp.get("exclusion_keywords", [])
        for excl in excl_keywords:
            if excl in text:
                score *= 0.5
        if score > 0:
            doc_type_map = {
                "GSTR1": DocumentType.GST_GSTR1,
                "GSTR3B": DocumentType.GST_GSTR3B,
                "GSTR2A": DocumentType.GST_GSTR2A,
                "GSTR9": DocumentType.GST_GSTR9,
                "GSTR9C": DocumentType.GST_GSTR9C,
            }
            scores[doc_type_map[gst_type]] = score

    # Bank statements
    for bank, fp in BANK_FINGERPRINTS.items():
        header_score = _score_patterns(text, fp["header_patterns"])
        col_score = _score_patterns(text, fp["column_patterns"])
        combined = (header_score * 0.5 + col_score * 0.5)
        if combined > 0.3:
            bank_type_map = {
                "SBI": DocumentType.BANK_STATEMENT_SBI,
                "HDFC": DocumentType.BANK_STATEMENT_HDFC,
                "ICICI": DocumentType.BANK_STATEMENT_ICICI,
                "AXIS": DocumentType.BANK_STATEMENT_AXIS,
                "KOTAK": DocumentType.BANK_STATEMENT_GENERIC,
                "YES": DocumentType.BANK_STATEMENT_GENERIC,
            }
            scores[bank_type_map[bank]] = combined

    # Annual Report
    ar_score = _score_fingerprint(text, ANNUAL_REPORT_FINGERPRINTS["required_keywords"])
    if ar_score > 0:
        scores[DocumentType.ANNUAL_REPORT] = ar_score

    # Rating Report
    rr_score = _score_fingerprint(text, RATING_REPORT_FINGERPRINTS["required_keywords"])
    if rr_score > 0:
        scores[DocumentType.RATING_REPORT] = rr_score

    # Legal Notice
    ln_score = _score_fingerprint(text, LEGAL_NOTICE_FINGERPRINTS["required_keywords"])
    if ln_score > 0:
        scores[DocumentType.LEGAL_NOTICE] = ln_score

    # Sanction Letter
    sl_score = _score_fingerprint(text, SANCTION_LETTER_FINGERPRINTS["required_keywords"])
    if sl_score > 0:
        scores[DocumentType.SANCTION_LETTER] = sl_score

    # CIBIL
    cibil_score = _score_fingerprint(text, CIBIL_FINGERPRINTS["required_keywords"])
    if cibil_score > 0:
        scores[DocumentType.CIBIL_COMMERCIAL] = cibil_score

    # MCA
    mca_score = _score_fingerprint(text, MCA_FINGERPRINTS["required_keywords"])
    if mca_score > 0:
        scores[DocumentType.MCA_COMPANY_MASTER] = mca_score

    # ALM (Asset-Liability Management)
    alm_score = _score_fingerprint(text, ALM_FINGERPRINTS["required_keywords"])
    if alm_score > 0.15:  # Lower threshold — ALM docs use specific jargon
        scores[DocumentType.ALM_REPORT] = alm_score

    # Shareholding Pattern
    sh_score = _score_fingerprint(text, SHAREHOLDING_FINGERPRINTS["required_keywords"])
    if sh_score > 0.15:
        scores[DocumentType.SHAREHOLDING_PATTERN] = sh_score

    # Borrowing Profile
    bp_score = _score_fingerprint(text, BORROWING_PROFILE_FINGERPRINTS["required_keywords"])
    if bp_score > 0.15:
        scores[DocumentType.BORROWING_PROFILE] = bp_score

    # Portfolio Performance
    pp_score = _score_fingerprint(text, PORTFOLIO_PERFORMANCE_FINGERPRINTS["required_keywords"])
    if pp_score > 0.15:
        scores[DocumentType.PORTFOLIO_PERFORMANCE] = pp_score

    if not scores:
        return DocumentType.UNKNOWN, 0.3

    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]

    if best_score < 0.4:
        return DocumentType.UNKNOWN, best_score

    # Normalize confidence
    confidence = min(0.98, best_score)
    return best_type, confidence


def _score_fingerprint(text: str, keywords: list[str]) -> float:
    """Score how well keywords match the text."""
    if not keywords:
        return 0.0
    matched = sum(1 for kw in keywords if kw.lower() in text)
    return matched / len(keywords)


def _score_patterns(text: str, patterns: list[str]) -> float:
    """Score regex patterns against text."""
    if not patterns:
        return 0.0
    matched = sum(1 for p in patterns if re.search(p, text, re.IGNORECASE))
    return matched / len(patterns)
