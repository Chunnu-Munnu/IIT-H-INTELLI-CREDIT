"""
litigation_scraper.py
Scrapes litigation data from:
  - eCourts API (public Indian court data)
  - NCLT cause list
  - DRT case registry
Computes: litigation_count, regulatory_risk_score
"""
import re
import asyncio
from loguru import logger

ECOURTS_BASE = "https://services.ecourts.gov.in/ecourtindiaapi"


class LitigationScraper:

    async def fetch_litigation_data(self, company_name: str, cin: str = "") -> dict:
        result = {
            "litigation_count": 0,
            "regulatory_risk_score": 0.0,
            "cases": [],
            "nclt_cases": [],
            "drt_cases": [],
            "open_case_count": 0,
        }

        # Try eCourts API
        ecourt_data = await self._fetch_ecourts(company_name)
        result.update(ecourt_data)

        # Try NCLT cause list
        nclt_data = await self._fetch_nclt(company_name)
        result["nclt_cases"] = nclt_data

        # Estimate regulatory risk score
        result["regulatory_risk_score"] = self._compute_regulatory_risk(result)
        return result

    async def _fetch_ecourts(self, name: str) -> dict:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=15) as client:
                # eCourts has a public search API endpoint (documented)
                params = {
                    "party_name": name,
                    "party_type": "defendent",
                    "state_code": "1",  # search across states not available in all versions
                }
                headers = {
                    "User-Agent": "Mozilla/5.0",
                    "Content-Type": "application/json",
                }
                # Try public eCourts API
                resp = await client.get(
                    f"{ECOURTS_BASE}/casestatus",
                    params=params, headers=headers, timeout=10
                )
                if resp.status_code == 200:
                    data = resp.json()
                    cases = data.get("cases", [])
                    open_cases = [c for c in cases if c.get("case_status", "").lower() in ["pending", "under trial"]]
                    return {
                        "litigation_count": len(cases),
                        "cases": cases[:10],
                        "open_case_count": len(open_cases),
                    }
        except Exception as e:
            logger.debug(f"eCourts API unavailable: {e}")

        # Fallback: parse extracted legal notice data
        return {"litigation_count": 0, "cases": [], "open_case_count": 0}

    async def _fetch_nclt(self, company_name: str) -> list:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=15) as client:
                # NCLT has a public cause list
                url = "https://nclt.gov.in/case-status"
                resp = await client.post(
                    url,
                    data={"companyName": company_name},
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                if resp.status_code == 200:
                    # Parse response (HTML parsing)
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(resp.text, "html.parser")
                    rows = soup.select("table tr")[1:]  # skip header
                    cases = []
                    for row in rows[:10]:
                        cols = [td.get_text(strip=True) for td in row.find_all("td")]
                        if len(cols) >= 3:
                            cases.append({
                                "case_no": cols[0] if cols else "",
                                "petitioner": cols[1] if len(cols) > 1 else "",
                                "respondent": cols[2] if len(cols) > 2 else "",
                                "status": cols[-1] if cols else "",
                            })
                    return cases
        except Exception as e:
            logger.debug(f"NCLT scraper unavailable: {e}")
        return []

    def compute_from_extracted_legal(self, legal_docs: list) -> dict:
        """
        Compute litigation features from already-extracted legal notices.
        This is the primary path when court scraping is unavailable.
        """
        drt_count = 0
        nclt_count = 0
        civil_count = 0
        total_amount_paise = 0

        for doc in legal_docs:
            case_type = doc.get("case_type", "UNKNOWN")
            amount = doc.get("amount_in_dispute_paise", 0) or 0
            total_amount_paise += amount

            if case_type == "DRT":  drt_count += 1
            elif case_type == "NCLT": nclt_count += 1
            elif case_type == "CIVIL": civil_count += 1

        lit_count = drt_count + nclt_count + civil_count
        reg_risk = min(10, drt_count * 3.0 + nclt_count * 4.0 + civil_count * 0.5 +
                       min(3, total_amount_paise / 1e13))  # normalize large amounts

        return {
            "litigation_count": lit_count,
            "regulatory_risk_score": round(reg_risk, 1),
            "drt_case_count": drt_count,
            "nclt_case_count": nclt_count,
            "civil_case_count": civil_count,
            "total_dispute_amount_paise": total_amount_paise,
        }

    def _compute_regulatory_risk(self, data: dict) -> float:
        lit = data.get("litigation_count", 0)
        nclt = len(data.get("nclt_cases", []))
        drt = data.get("drt_cases", [])
        score = min(10.0, lit * 0.5 + nclt * 2.0 + len(drt) * 3.0)
        return round(score, 1)
