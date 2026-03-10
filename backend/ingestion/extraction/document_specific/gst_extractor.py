"""
GST document extractor for GSTR-1, GSTR-3B, GSTR-2A, GSTR-9.
Handles both JSON (portal exports) and PDF formats.
"""
import json
import re
from loguru import logger
from models.gst import GSTR1Result, GSTR3BResult, GSTR2AResult, GSTR9Result
from ingestion.normalization.currency_normalizer import CurrencyNormalizer


CURR = CurrencyNormalizer()


class GSTExtractor:

    # ─── GSTR-1 ───────────────────────────────────────────────────────────────

    def extract_gstr1_from_file(self, file_path: str) -> GSTR1Result:
        if file_path.endswith(".json"):
            with open(file_path) as f:
                data = json.load(f)
            return self.extract_gstr1(data)
        else:
            text = self._pdf_to_text(file_path)
            return self.extract_gstr1(text)

    def extract_gstr1(self, data) -> GSTR1Result:
        if isinstance(data, dict):
            return self._extract_gstr1_json(data)
        return self._extract_gstr1_text(str(data))

    def _extract_gstr1_json(self, data: dict) -> GSTR1Result:
        result = GSTR1Result()
        result.gstin = data.get("gstin", "")
        result.period = data.get("fp", data.get("ret_period", ""))

        # B2B invoices
        b2b_total = 0
        buyer_map = {}
        for b2b in data.get("b2b", []):
            buyer_gstin = b2b.get("ctin", "")
            for inv in b2b.get("inv", []):
                val = self._parse_json_amount(inv.get("val", 0))
                b2b_total += val
                buyer_map[buyer_gstin] = buyer_map.get(buyer_gstin, 0) + val
                # Monthly tracking
                idt = inv.get("idt", "")
                month = self._extract_month(idt)
                if month:
                    result.monthly_turnover[month] = result.monthly_turnover.get(month, 0) + val

        result.b2b_turnover_paise = b2b_total
        result.buyer_list = [{"gstin": g, "value": v} for g, v in buyer_map.items()]

        # B2C, exports
        for b2cl in data.get("b2cl", []):
            for inv in b2cl.get("inv", []):
                result.b2c_turnover_paise += self._parse_json_amount(inv.get("val", 0))

        for exp in data.get("exp", []):
            for inv in exp.get("inv", []):
                result.export_turnover_paise += self._parse_json_amount(inv.get("val", 0))

        result.annual_turnover_paise = (
            result.b2b_turnover_paise + result.b2c_turnover_paise + result.export_turnover_paise
        )
        return result

    def _extract_gstr1_text(self, text: str) -> GSTR1Result:
        result = GSTR1Result()
        amounts = re.findall(r'(?:total|aggregate).*?(?:turnover|supply).*?([\d,]+(?:\.\d+)?)', text, re.IGNORECASE)
        if amounts:
            result.annual_turnover_paise = self._parse_text_amount(amounts[0])
        return result

    # ─── GSTR-3B ──────────────────────────────────────────────────────────────

    def extract_gstr3b_from_file(self, file_path: str) -> GSTR3BResult:
        if file_path.endswith(".json"):
            with open(file_path) as f:
                data = json.load(f)
            return self.extract_gstr3b(data)
        else:
            return self._extract_gstr3b_pdf_structured(file_path)

    def extract_gstr3b(self, data) -> GSTR3BResult:
        if isinstance(data, dict):
            return self._extract_gstr3b_json(data)
        return self._extract_gstr3b_text(str(data))

    def _extract_gstr3b_json(self, data: dict) -> GSTR3BResult:
        result = GSTR3BResult()
        result.gstin = data.get("gstin", "")
        result.period = data.get("ret_period", "")

        sup = data.get("sup_details", {})
        result.annual_outward_paise = self._parse_json_amount(sup.get("osup_det", {}).get("txval", 0))

        itc = data.get("itc_elg", {}).get("itc_avl", {})
        result.total_itc_claimed_paise = sum(
            self._parse_json_amount(itc.get(k, 0))
            for k in ["igst", "cgst", "sgst", "cess"]
        )

        itc_rev = data.get("itc_elg", {}).get("itc_rev", {})
        result.total_itc_reversed_paise = sum(
            self._parse_json_amount(itc_rev.get(k, 0))
            for k in ["igst", "cgst", "sgst", "cess"]
        )
        result.net_itc_paise = result.total_itc_claimed_paise - result.total_itc_reversed_paise

        vtax = data.get("vtax", {})
        result.tax_paid_cash_paise = self._parse_json_amount(vtax.get("igst", 0))
        return result

    def _extract_gstr3b_text(self, text: str) -> GSTR3BResult:
        """Fallback regex-based extraction for GSTR-3B text."""
        result = GSTR3BResult()
        # Outward supplies (Table 3.1)
        outward = re.findall(r'(?:3\.1|outward).*?(?:taxable|value).*?([\d,]+\.?\d*)', text, re.IGNORECASE | re.DOTALL)
        if outward:
            result.annual_outward_paise = self._parse_text_amount(outward[0])
        
        # ITC (Table 4)
        itc = re.findall(r'(?:4|itc).*?(?:eligible|available).*?([\d,]+\.?\d*)', text, re.IGNORECASE | re.DOTALL)
        if itc:
            result.total_itc_claimed_paise = self._parse_text_amount(itc[0])
            
        return result

    def _extract_gstr3b_pdf_structured(self, file_path: str) -> GSTR3BResult:
        """Use pdfplumber to extract GSTR-3B data from structured tables."""
        result = GSTR3BResult()
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                full_text = ""
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    full_text += page_text
                    
                    if not result.gstin:
                        gstin_match = re.search(r'GSTIN[:\s]+([0-9A-Z]{15})', page_text)
                        if gstin_match: result.gstin = gstin_match.group(1)
                    if not result.period:
                        period_match = re.search(r'Period[:\s]+((?:April|May|June|July|August|September|October|November|December|January|February|March)[-\s]\d{4}|\d{2}-\d{4})', page_text)
                        if period_match: result.period = period_match.group(1)

                    tables = page.extract_tables()
                    for table in tables:
                        if not table: continue
                        for row in table:
                            row_str = " ".join([str(c) for c in row if c]).lower()
                            if ("3.1" in row_str or "outward" in row_str) and ("taxable" in row_str or "val" in row_str):
                                for cell in row:
                                    val = self._parse_text_amount(str(cell))
                                    if val > 0 and val > result.annual_outward_paise:
                                        result.annual_outward_paise = val
                                        month = self._extract_month(result.period)
                                        if month:
                                            result.monthly_data.setdefault(month, {})["outward"] = val
                            
                            if ("4" in row_str or "eligible" in row_str) and ("itc" in row_str or "available" in row_str):
                                for cell in row:
                                    val = self._parse_text_amount(str(cell))
                                    if val > 0 and val > result.total_itc_claimed_paise:
                                        result.total_itc_claimed_paise = val
                                        month = self._extract_month(result.period)
                                        if month:
                                            result.monthly_data.setdefault(month, {})["itc"] = val

        except Exception as e:
            logger.warning(f"Structured GSTR-3B extraction failed: {e}. Falling back to text.")
            return self._extract_gstr3b_text(self._pdf_to_text(file_path))
            
        return result

    # ─── GSTR-2A ──────────────────────────────────────────────────────────────

    def extract_gstr2a_from_file(self, file_path: str) -> GSTR2AResult:
        if file_path.endswith(".json"):
            with open(file_path) as f:
                data = json.load(f)
            return self.extract_gstr2a(data)
        else:
            return self._extract_gstr2a_pdf_structured(file_path)

    def extract_gstr2a(self, data) -> GSTR2AResult:
        if isinstance(data, dict):
            return self._extract_gstr2a_json(data)
        return GSTR2AResult()

    def _extract_gstr2a_json(self, data: dict) -> GSTR2AResult:
        result = GSTR2AResult()
        result.gstin = data.get("gstin", "")
        supplier_map = {}

        for b2b in data.get("b2b", []):
            s_gstin = b2b.get("ctin", "")
            for inv in b2b.get("inv", []):
                val = self._parse_json_amount(inv.get("val", 0))
                result.total_itc_eligible_paise += val
                supplier_map[s_gstin] = supplier_map.get(s_gstin, 0) + val
                
                idt = inv.get("idt", "")
                month = self._extract_month(idt)
                if month:
                    result.monthly_itc[month] = result.monthly_itc.get(month, 0) + val

        result.supplier_list = [{"gstin": g, "value": v} for g, v in supplier_map.items()]
        return result

    def _extract_gstr2a_pdf_structured(self, file_path: str) -> GSTR2AResult:
        """Extract supplier list and ITC from GSTR-2A PDF tables."""
        result = GSTR2AResult()
        supplier_map = {}
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    p_match = re.search(r'Period[:\s]+((?:April|May|June|July|August|September|October|November|December|January|February|March)[-\s]\d{4}|\d{2}-\d{4})', page_text)
                    page_period = p_match.group(1) if p_match else None
                    if page_period and not result.period: result.period = page_period

                    tables = page.extract_tables()
                    for table in tables:
                        if not table or len(table) < 2: continue
                        headers = [str(c).lower() if c else "" for c in table[0]]
                        gstin_idx = -1
                        val_idx = -1
                        for i, h in enumerate(headers):
                            if "gstin" in h or "supplier" in h: gstin_idx = i
                            if "itc" in h or "eligible" in h or "amount" in h or "tax" in h: val_idx = i
                        
                        if gstin_idx != -1 and val_idx != -1:
                            for row in table[1:]:
                                s_gstin = str(row[gstin_idx]) if gstin_idx < len(row) else ""
                                if re.match(r'[0-9A-Z]{15}', s_gstin):
                                    val = self._parse_text_amount(str(row[val_idx])) if val_idx < len(row) else 0
                                    supplier_map[s_gstin] = supplier_map.get(s_gstin, 0) + val
                                    result.total_itc_eligible_paise += val
                                    
                                    month = self._extract_month(page_period or result.period)
                                    if month:
                                        result.monthly_itc[month] = result.monthly_itc.get(month, 0) + val

            result.supplier_list = [{"gstin": g, "value": v} for g, v in supplier_map.items()]
        except Exception as e:
            logger.warning(f"Structured GSTR-2A extraction failed: {e}")
        
        return result

    # ─── GSTR-9 ───────────────────────────────────────────────────────────────

    def extract_gstr9_from_file(self, file_path: str) -> GSTR9Result:
        if file_path.endswith(".json"):
            with open(file_path) as f:
                data = json.load(f)
            return self.extract_gstr9(data)
        else:
            text = self._pdf_to_text(file_path)
            return self.extract_gstr9(text)

    def extract_gstr9(self, data) -> GSTR9Result:
        if isinstance(data, dict):
            result = GSTR9Result()
            result.gstin = data.get("gstin", "")
            result.fy = data.get("fp", "")
            pt2 = data.get("pt_ii", {})
            result.annual_turnover_paise = self._parse_json_amount(pt2.get("sup_det", {}).get("osup_det", 0))
            return result
        return GSTR9Result()

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _parse_json_amount(self, val) -> int:
        """Convert JSON numeric to paise."""
        try:
            return int(float(val) * 100)
        except (TypeError, ValueError):
            return 0

    def _parse_text_amount(self, text: str) -> int:
        """Convert text amount to paise."""
        if not text: return 0
        try:
            # Clean symbols like ₹, Cr, Lakh etc. if they appear
            clean = str(text).replace(",", "").replace("₹", "").strip()
            # Handle crore/lakh suffix if present
            multiplier = 1
            if "cr" in clean.lower(): multiplier = 10_000_000; clean = clean.lower().replace("cr", "")
            if "lakh" in clean.lower(): multiplier = 100_000; clean = clean.lower().replace("lakh", "")
            
            return int(float(clean) * multiplier * 100)
        except (TypeError, ValueError):
            return 0

    def _extract_month(self, date_str: str) -> str | None:
        """Extract YYYY-MM from date string like 01/04/2023 or 'April 2023'."""
        if not date_str: return None
        months_map = {
            "january": "01", "february": "02", "march": "03", "april": "04",
            "may": "05", "june": "06", "july": "07", "august": "08",
            "september": "09", "october": "10", "november": "11", "december": "12"
        }
        
        # Pattern 1: DD/MM/YYYY or DD-MM-YYYY
        m = re.search(r'(\d{2})[/-](\d{2})[/-](\d{4})', str(date_str))
        if m: return f"{m.group(3)}-{m.group(2)}"
        
        # Pattern 2: MM-YYYY
        m = re.search(r'(\d{2})-(\d{4})', str(date_str))
        if m: return f"{m.group(2)}-{m.group(1)}"

        # Pattern 3: Month YYYY
        m = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)[-\s](\d{4})', str(date_str), re.I)
        if m:
            mm = months_map.get(m.group(1).lower())
            return f"{m.group(2)}-{mm}"
            
        return None

    def _pdf_to_text(self, file_path: str) -> str:
        """Extract text using native PDF parser; fall back to PaddleOCR for scanned PDFs."""
        try:
            from ingestion.extraction.ocr_engine import OCREngine
            return OCREngine.extract_text_from_pdf(file_path, min_text_threshold=150)
        except Exception as e:
            logger.warning(f"PDF text extraction failed: {e}")
            return ""
