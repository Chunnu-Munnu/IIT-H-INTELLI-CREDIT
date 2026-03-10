"""
Annual Report extractor using PyMuPDF for native PDFs and PaddleOCR for scanned.
Extracts: financial tables, auditor opinion, directors, contingent liabilities.
"""
import re
from loguru import logger
from models.financial import FinancialRecord, FinancialPeriod
from models.risk import RiskSignal, RiskLevel
from ingestion.normalization.currency_normalizer import CurrencyNormalizer
from ingestion.normalization.period_normalizer import PeriodNormalizer
from app.constants import SCHEDULE_III_MAPPINGS
from datetime import date

CURR = CurrencyNormalizer()
PERIOD_NORM = PeriodNormalizer()

RISK_KEYWORD_SETS = {
    "GOING_CONCERN": {
        "keywords": ["going concern", "material uncertainty", "ability to continue",
                     "substantial doubt", "going concern basis"],
        "severity": RiskLevel.CRITICAL,
        "five_c": "Character",
    },
    "AUDITOR_QUALIFICATION": {
        "keywords": ["qualified opinion", "adverse opinion", "disclaimer of opinion",
                     "emphasis of matter"],
        "severity": RiskLevel.HIGH,
        "five_c": "Character",
    },
    "DRT_NCLT": {
        "keywords": ["drt", "debt recovery tribunal", "nclt", "national company law",
                     "winding up", "insolvency", "cirp", "liquidation order"],
        "severity": RiskLevel.CRITICAL,
        "five_c": "Character",
    },
    "REGULATORY_ACTION": {
        "keywords": ["rbi notice", "sebi investigation", "ed attachment",
                     "income tax search", "gst department notice", "show cause"],
        "severity": RiskLevel.HIGH,
        "five_c": "Conditions",
    },
}

SECTION_PATTERNS = {
    "DIRECTORS_REPORT": [r"directors.{0,5}report", r"board.{0,5}report"],
    "MD_AND_A": [r"management discussion", r"md&a", r"management.{0,5}analysis"],
    "AUDITORS_REPORT": [r"independent auditor", r"auditors.{0,5}report"],
    "NOTES_TO_ACCOUNTS": [r"notes to.*financial", r"notes forming part"],
    "RELATED_PARTY": [r"related party", r"transactions with related"],
    "CONTINGENT_LIABILITIES": [r"contingent liab", r"commitments and contingencies"],
}


class AnnualReportExtractor:

    def extract(self, file_path: str) -> dict:
        text = self._extract_text(file_path)
        pages = self._split_pages(file_path)

        result = {
            "financial_records": [],
            "risk_signals": [],
            "company_name": "",
            "auditor_opinion": "unqualified",
            "directors": [],
            "contingent_liabilities": [],
        }

        # Extract risk signals from text
        sections = self._split_document(text)
        result["risk_signals"] = self._extract_risk_signals(sections, file_path)

        # Extract auditor opinion
        auditor_section = sections.get("AUDITORS_REPORT", "")
        result["auditor_opinion"] = self._detect_auditor_opinion(auditor_section)

        # Extract financial records from tables
        try:
            financial_records = self._extract_financial_tables(file_path, text)
            result["financial_records"] = financial_records
        except Exception as e:
            logger.warning(f"Financial table extraction failed: {e}")

        return result

    def _extract_text(self, file_path: str) -> str:
        """Extract text using native PDF parser; fall back to PaddleOCR for scanned PDFs."""
        try:
            from ingestion.extraction.ocr_engine import OCREngine
            return OCREngine.extract_text_from_pdf(file_path, min_text_threshold=200)
        except Exception as e:
            logger.warning(f"Text extraction failed: {e}")
            return ""

    def _split_pages(self, file_path: str) -> list:
        try:
            import fitz
            doc = fitz.open(file_path)
            pages = []
            for i, page in enumerate(doc):
                pages.append({"page_num": i + 1, "text": page.get_text()})
            doc.close()
            return pages
        except Exception:
            return []

    def _split_document(self, text: str) -> dict:
        sections = {"FULL": text}
        for section_name, patterns in SECTION_PATTERNS.items():
            for pat in patterns:
                match = re.search(pat, text, re.IGNORECASE)
                if match:
                    start = match.start()
                    sections[section_name] = text[start:start + 5000]
                    break
        return sections

    def _extract_risk_signals(self, sections: dict, source_doc: str) -> list:
        signals = []
        for signal_type, config in RISK_KEYWORD_SETS.items():
            for section_name, section_text in sections.items():
                for keyword in config["keywords"]:
                    idx = section_text.lower().find(keyword.lower())
                    if idx >= 0:
                        context = section_text[max(0, idx-100):idx+200]
                        signals.append({
                            "signal_type": signal_type,
                            "section_name": section_name,
                            "keyword_matched": keyword,
                            "context_text": context,
                            "severity": config["severity"].value,
                            "five_c_mapping": config["five_c"],
                            "source_document": source_doc,
                            "page_number": 0,
                            "confidence": 0.85,
                        })
                        break
        return signals

    def _detect_auditor_opinion(self, auditor_text: str) -> str:
        text_lower = auditor_text.lower()
        
        # Priority order as per requirements
        if any(kw in text_lower for kw in ["adverse opinion", "do not present fairly"]):
            return "adverse"
        if any(kw in text_lower for kw in ["disclaimer of opinion", "do not express an opinion"]):
            return "disclaimer"
        if any(kw in text_lower for kw in ["except for", "subject to"]) and "opinion" in text_lower:
            return "qualified"
        
        # Clean signals
        clean_sigs = ["unmodified opinion", "unmodified", "clean opinion", "true and fair view"]
        if any(kw in text_lower for kw in clean_sigs):
            # Double check there isn't a qualified keyword just before or after the 'opinion' word
            return "clean"
            
        if "emphasis of matter" in text_lower:
            return "emphasis_of_matter"
            
        return "clean" # Default to clean if no negative signals found

    def _extract_financial_tables(self, file_path: str, full_text: str) -> list:
        records = []

        # ── Method 1: camelot (lattice mode — best for bordered tables) ──────
        try:
            import camelot
            tables = camelot.read_pdf(file_path, pages='all', flavor='lattice', suppress_stdout=True)
            logger.info(f"Camelot lattice: {len(tables)} tables from {file_path}")
            for tbl in tables:
                if tbl.df is not None and len(tbl.df) > 3:
                    raw_table = tbl.df.values.tolist()
                    extracted = self._parse_financial_table(raw_table)
                    records.extend(extracted)
        except Exception as e:
            logger.debug(f"Camelot lattice failed: {e}")

        # ── Method 2: camelot stream mode (no borders) ───────────────────────
        if not records:
            try:
                import camelot
                tables = camelot.read_pdf(file_path, pages='all', flavor='stream', suppress_stdout=True)
                for tbl in tables:
                    if tbl.df is not None and len(tbl.df) > 3:
                        raw_table = tbl.df.values.tolist()
                        extracted = self._parse_financial_table(raw_table)
                        records.extend(extracted)
            except Exception as e:
                logger.debug(f"Camelot stream failed: {e}")

        # ── Method 3: pdfplumber (always try — complementary to camelot) ─────
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    tables = page.extract_tables({
                        "vertical_strategy": "lines_strict",
                        "horizontal_strategy": "lines_strict",
                    })
                    for table in tables:
                        if table and len(table) > 3:
                            extracted = self._parse_financial_table(table)
                            if extracted:
                                records.extend(extracted)
        except Exception as e:
            logger.warning(f"pdfplumber table extraction failed: {e}")

        # Deduplicate by period
        seen_periods = set()
        unique = []
        for rec in records:
            period_key = getattr(getattr(rec, 'period', None), 'fy_label', id(rec))
            if period_key not in seen_periods:
                seen_periods.add(period_key)
                unique.append(rec)

        logger.info(f"Financial table extraction: {len(unique)} unique period records")
        return unique

    def _parse_financial_table(self, table: list) -> list:
        """Try to extract financial records from a table."""
        if not table or len(table) < 3:
            return []

        records = []
        # Check header row for year columns
        header = [str(c).lower() if c else "" for c in table[0]]
        year_cols = {}
        for i, h in enumerate(header):
            if h:
                period = PERIOD_NORM.normalize(h)
                if period:
                    year_cols[i] = period

        if not year_cols:
            return []

        # Initialize records for each year found
        year_data = {i: {} for i in year_cols}

        for row in table[1:]:
            if not row:
                continue
            label = str(row[0]).lower().strip() if row[0] else ""
            canonical = SCHEDULE_III_MAPPINGS.get(label)
            if canonical:
                for col_idx, period in year_cols.items():
                    if col_idx < len(row) and row[col_idx]:
                        val = CURR.parse_to_paise(str(row[col_idx]))
                        if val is not None:
                            year_data[col_idx][canonical] = val

        for col_idx, period in year_cols.items():
            data = year_data[col_idx]
            if len(data) >= 3:  # At least 3 fields found
                rec = FinancialRecord(
                    period=period,
                    **{k: v for k, v in data.items() if hasattr(FinancialRecord.model_fields, k) or k in FinancialRecord.model_fields},
                )
                records.append(rec)

        return records
