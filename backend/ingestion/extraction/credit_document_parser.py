import re
import pdfplumber
import traceback
from loguru import logger

class CreditDocumentParser:
    """
    Deterministic Parser for structured Indian Credit Documents.
    Extracted from battle-tested architecture for high accuracy.
    """
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.text = self._extract_text()

    def _extract_text(self):
        text = ""
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
                    text += "\n"
        except Exception as e:
            logger.error(f"pdfplumber failed: {e}")
        return text

    def extract_financials(self):
        revenue = re.search(r"Revenue from Operations.*?([\d,.]+)", self.text, re.IGNORECASE)
        ebitda = re.search(r"EBITDA.*?([\d,.]+)", self.text, re.IGNORECASE)
        pat = re.search(r"PAT.*?([\d,.]+)", self.text, re.IGNORECASE)

        def to_float(val):
            if not val: return None
            return float(val.replace(",", ""))

        return {
            "revenue_cr": to_float(revenue.group(1)) if revenue else None,
            "ebitda_cr": to_float(ebitda.group(1)) if ebitda else None,
            "pat_cr": to_float(pat.group(1)) if pat else None
        }

    def extract_ratios(self):
        ratios = {}
        patterns = {
            "current_ratio": r"Current Ratio\s+([\d.]+)",
            "de_ratio": r"Debt/Equity Ratio\s+([\d.]+)",
            "interest_coverage": r"Interest Coverage Ratio\s+([\d.]+)",
            "dscr": r"Debt Service Coverage Ratio:\s*([\d.]+)"
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                ratios[key] = float(match.group(1))
            else:
                ratios[key] = None

        return ratios

    def extract_debt_metrics(self):
        debt = re.search(r"Total Funded Debt:\s*INR\s*([\d.]+)", self.text, re.IGNORECASE)
        dscr = re.search(r"Debt Service Coverage Ratio:\s*([\d.]+)", self.text, re.IGNORECASE)

        def to_float(val):
            if not val: return None
            return float(val.replace(",", ""))

        return {
            "total_debt_cr": to_float(debt.group(1)) if debt else None,
            "dscr": float(dscr.group(1)) if dscr else None
        }

    def extract_shareholding(self):
        # Match "Promoter & Promoter Group 53.00%"
        promoter = re.search(
            r"Promoter\s*&\s*Promoter\s*Group.*?([\d.]+)%",
            self.text, re.IGNORECASE
        )
        # Match pledged if exists
        pledged = re.search(r"Shares Pledged.*?([\d.]+)%", self.text, re.IGNORECASE)

        return {
            "promoter_shareholding": float(promoter.group(1)) if promoter else None,
            "pledged_pct": float(pledged.group(1)) if pledged else 0.0
        }

    def extract_alm(self):
        assets = re.search(
            r"TOTAL ASSETS\s+([\d.]+)",
            self.text, re.IGNORECASE
        )
        lcr = re.search(r"Liquidity Cover.*?Ratio.*?\s+([\d.]+)", self.text, re.IGNORECASE)

        return {
            "total_assets_cr": float(assets.group(1).replace(",", "")) if assets else None,
            "lcr": float(lcr.group(1)) if lcr else None
        }

    def parse(self):
        """Master parse function used by IngestionOrchestrator."""
        try:
            return {
                "financials": self.extract_financials(),
                "ratios": self.extract_ratios(),
                "debt_metrics": self.extract_debt_metrics(),
                "shareholding": self.extract_shareholding(),
                "alm": self.extract_alm()
            }
        except Exception as e:
            logger.error(f"Detailed parse failed: {e}\n{traceback.format_exc()}")
            return {}
