import re
from loguru import logger


class LegalNoticeExtractor:

    CASE_TYPE_PATTERNS = {
        "DRT": [r"debt recovery tribunal", r"d\.r\.t\.", r"drt[-\s]\d", r"\bdrt\b"],
        "NCLT": [r"national company law tribunal", r"n\.c\.l\.t\.", r"\bnclt\b"],
        "CIVIL": [r"civil suit", r"civil case", r"o\.s\. no", r"civil court"],
        "CRIMINAL": [r"fir no", r"complaint no", r"criminal case", r"police case"],
    }

    def extract_from_file(self, file_path: str) -> dict | None:
        text = self._extract_text(file_path)
        if not text:
            return None
        return self.extract(text, file_path)

    def extract(self, text: str, source_doc: str = "") -> dict:
        result = {
            "case_type": "UNKNOWN",
            "court_name": "",
            "case_number": "",
            "filing_date": None,
            "petitioner": "",
            "respondent": "",
            "amount_in_dispute_paise": 0,
            "current_status": "",
            "source_document": source_doc,
        }

        # Detect case type
        text_lower = text.lower()
        for ctype, patterns in self.CASE_TYPE_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, text_lower):
                    result["case_type"] = ctype
                    break

        # Extract case number
        case_num = re.search(
            r'case\s+(?:no\.?|number)\s*[:\-]?\s*([A-Z0-9\-/]+)',
            text, re.IGNORECASE
        )
        if case_num:
            result["case_number"] = case_num.group(1)

        # Extract amount
        amount_patterns = [
            r'(?:sum|amount|claim|dues?).*?(?:rs\.?|₹)\s*([\d,]+(?:\.\d+)?)\s*(?:crore|cr|lakh|lac)?',
            r'(?:rs\.?|₹)\s*([\d,]+(?:\.\d+)?)\s*(?:crore|cr|lakh|lac)',
        ]
        for pat in amount_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                from ingestion.normalization.currency_normalizer import CurrencyNormalizer
                curr = CurrencyNormalizer()
                val = curr.parse_to_paise(m.group(0))
                if val:
                    result["amount_in_dispute_paise"] = val
                    break

        # Extract petitioner/respondent
        pet = re.search(r'petitioner\s*[:\-]?\s*([A-Z][A-Za-z\s&,.]+?)(?:\n|respondent)', text, re.IGNORECASE)
        if pet:
            result["petitioner"] = pet.group(1).strip()

        resp = re.search(r'respondent\s*[:\-]?\s*([A-Z][A-Za-z\s&,.]+?)(?:\n|vs)', text, re.IGNORECASE)
        if resp:
            result["respondent"] = resp.group(1).strip()

        return result

    def _extract_text(self, file_path: str) -> str:
        try:
            import fitz
            doc = fitz.open(file_path)
            return "".join(page.get_text() for page in doc)
        except Exception:
            return ""


class RatingReportExtractor:

    RATING_PATTERN = re.compile(
        r'\b(AA\+|AA-|AAA|AA|A\+|A-|BBB\+|BBB-|BBB|BB\+|BB-|BB|B\+|B-|CCC|CC|C|D)\b'
    )
    AGENCY_PATTERNS = {
        "CRISIL": r"crisil",
        "ICRA": r"icra",
        "CARE": r"care ratings",
        "INDIA_RATINGS": r"india ratings|ind-ra",
        "BRICKWORK": r"brickwork",
    }

    def extract_from_file(self, file_path: str) -> dict:
        text = self._extract_text(file_path)
        return self.extract(text, file_path)

    def extract(self, text: str, source_doc: str = "") -> dict:
        result = {
            "agency": "UNKNOWN",
            "current_rating": None,
            "previous_rating": None,
            "direction": "stable",   # upgrade | downgrade | stable
            "outlook": "Stable",
            "source_document": source_doc,
        }

        # Detect agency
        text_lower = text.lower()
        for agency, pat in self.AGENCY_PATTERNS.items():
            if re.search(pat, text_lower):
                result["agency"] = agency
                break

        # Extract ratings
        ratings = self.RATING_PATTERN.findall(text)
        if ratings:
            result["current_rating"] = ratings[0]
            if len(ratings) > 1:
                result["previous_rating"] = ratings[1]

        # Detect direction
        if "upgraded" in text_lower or "upgrade" in text_lower:
            result["direction"] = "upgrade"
        elif "downgraded" in text_lower or "downgrade" in text_lower:
            result["direction"] = "downgrade"

        # Outlook
        if "positive" in text_lower:
            result["outlook"] = "Positive"
        elif "negative" in text_lower:
            result["outlook"] = "Negative"
        elif "watch" in text_lower:
            result["outlook"] = "CreditWatch"

        return result

    def _extract_text(self, file_path: str) -> str:
        try:
            import fitz
            doc = fitz.open(file_path)
            return "".join(page.get_text() for page in doc)
        except Exception:
            return ""
