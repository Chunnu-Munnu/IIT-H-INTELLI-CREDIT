"""
mca_scraper.py
Playwright-based MCA21 company data scraper.
Extracts: company master, director list, charge registry.
Falls back to MCA API v3 if available.
"""
import asyncio
import re
from loguru import logger

MCA_BASE = "https://www.mca.gov.in"
MCA_COMPANY_SEARCH = f"{MCA_BASE}/mcafoportal/viewCompanyMasterData.do"


class MCAScraper:

    async def fetch_company_data(self, cin: str = None, company_name: str = None) -> dict:
        """
        Fetch company master data, directors, and charges from MCA21.
        Returns structured dict.
        """
        result = {
            "cin": cin or "",
            "company_name": company_name or "",
            "status": "Unknown",
            "roc_code": "",
            "registration_number": "",
            "category": "",
            "sub_category": "",
            "class_of_company": "",
            "date_of_incorporation": None,
            "authorised_capital": 0,
            "paid_up_capital": 0,
            "registered_address": "",
            "email": "",
            "directors": [],
            "charges": [],
            "compliance_status": "Unknown",
            "annual_return_filed": None,
            "financials_filed": None,
            "source": "mca21_scraper",
        }

        try:
            async with self._get_browser() as browser:
                page = await browser.new_page()
                await page.set_extra_http_headers({
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                })

                logger.info(f"Fetching MCA data for CIN: {cin}")

                # Navigate to company search
                await page.goto(MCA_COMPANY_SEARCH, wait_until="networkidle", timeout=30000)
                await page.fill("input[name='companyCin']", cin or "")
                await page.click("input[type='submit']")
                await page.wait_for_selector("table.table", timeout=15000)

                # Extract company master table
                rows = await page.query_selector_all("table.table tr")
                for row in rows:
                    cells = await row.query_selector_all("td")
                    if len(cells) >= 2:
                        label = (await cells[0].inner_text()).strip().lower()
                        value = (await cells[1].inner_text()).strip()
                        self._map_mca_field(result, label, value)

                # Extract directors
                directors = await self._extract_directors(page)
                result["directors"] = directors

                # Extract charges
                charges = await self._extract_charges(page, cin)
                result["charges"] = charges

                # Compliance check
                result["compliance_status"] = self._compute_compliance(result)

                await page.close()

        except ImportError:
            logger.warning("playwright not installed. Using HTTP fallback for MCA.")
            result = await self._fetch_via_http(cin, company_name, result)
        except Exception as e:
            logger.warning(f"MCA scraper failed: {e}. Using HTTP fallback.")
            result = await self._fetch_via_http(cin, company_name, result)

        return result

    async def _get_browser(self):
        from playwright.async_api import async_playwright
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def _ctx():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
                try:
                    yield browser
                finally:
                    await browser.close()

        return _ctx()

    def _map_mca_field(self, result: dict, label: str, value: str):
        mapping = {
            "company status": "status",
            "roc code": "roc_code",
            "registration number": "registration_number",
            "company category": "category",
            "company sub category": "sub_category",
            "class of company": "class_of_company",
            "date of incorporation": "date_of_incorporation",
            "registered office address": "registered_address",
            "email id": "email",
        }
        for key, field in mapping.items():
            if key in label:
                if field in ("authorised_capital", "paid_up_capital"):
                    val = re.sub(r"[^\d.]", "", value)
                    try:
                        result[field] = int(float(val) * 100)  # paise
                    except (ValueError, TypeError):
                        pass
                else:
                    result[field] = value
                break

    async def _extract_directors(self, page) -> list:
        try:
            rows = await page.query_selector_all("table#directorTable tr")
            directors = []
            for row in rows[1:]:  # skip header
                cells = await row.query_selector_all("td")
                if len(cells) >= 3:
                    directors.append({
                        "din": (await cells[0].inner_text()).strip(),
                        "name": (await cells[1].inner_text()).strip(),
                        "designation": (await cells[2].inner_text()).strip(),
                        "date_of_appointment": (await cells[3].inner_text()).strip() if len(cells) > 3 else "",
                    })
            return directors
        except Exception:
            return []

    async def _extract_charges(self, page, cin: str) -> list:
        try:
            # Navigate to charges section
            await page.click("a[href*='charge']", timeout=5000)
            await page.wait_for_selector("table#chargeTable", timeout=10000)
            rows = await page.query_selector_all("table#chargeTable tr")
            charges = []
            for row in rows[1:]:
                cells = await row.query_selector_all("td")
                if len(cells) >= 4:
                    charges.append({
                        "charge_id": (await cells[0].inner_text()).strip(),
                        "holder": (await cells[1].inner_text()).strip(),
                        "amount_paise": self._parse_amount(await cells[2].inner_text()),
                        "status": (await cells[3].inner_text()).strip(),
                    })
            return charges
        except Exception:
            return []

    def _parse_amount(self, text: str) -> int:
        try:
            return int(float(re.sub(r"[^\d.]", "", text)) * 100)
        except (ValueError, TypeError):
            return 0

    def _compute_compliance(self, result: dict) -> str:
        """Compute compliance status based on scraped data."""
        status = result.get("status", "").lower()
        if "active" in status:
            return "Compliant"
        elif "dormant" in status or "inactive" in status:
            return "Lapsed"
        elif "struck off" in status or "dissolved" in status:
            return "Dissolved"
        return "Unknown"

    async def _fetch_via_http(self, cin: str, company_name: str, base_result: dict) -> dict:
        """
        HTTP-based fallback using MCA API v3 or free MCA data endpoint.
        Returns partially filled result on failure.
        """
        try:
            import httpx
            async with httpx.AsyncClient(timeout=15) as client:
                # Try unofficial MCA data API (public company search)
                if cin:
                    url = f"https://api.mca.gov.in/mca-api/v1/company/companymasterdata?CIN={cin}"
                    headers = {"Content-Type": "application/json"}
                    resp = await client.get(url, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        return {**base_result, **self._parse_api_response(data), "source": "mca_api_v1"}

                # Fallback: search by company name on opencorporates-style data
                if company_name:
                    url = f"https://api.opencorporates.com/v0.4/companies/search?q={company_name}&jurisdiction_code=in"
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        companies = data.get("results", {}).get("companies", [])
                        if companies:
                            co = companies[0]["company"]
                            base_result.update({
                                "company_name": co.get("name", company_name),
                                "status": co.get("current_status", "Unknown"),
                                "date_of_incorporation": co.get("incorporation_date"),
                                "registered_address": co.get("registered_address", {}).get("street_address", ""),
                                "source": "opencorporates",
                            })

        except Exception as e:
            logger.warning(f"MCA HTTP fallback failed: {e}")

        return base_result

    def _parse_api_response(self, data: dict) -> dict:
        return {
            "company_name": data.get("companyName", ""),
            "status": data.get("companyStatus", "Unknown"),
            "date_of_incorporation": data.get("dateOfIncorporation"),
            "registered_address": data.get("registeredOfficeAddress", ""),
            "authorised_capital": int(float(data.get("authorisedCapital", 0)) * 100),
            "paid_up_capital": int(float(data.get("paidUpCapital", 0)) * 100),
        }

    def compute_mca_scores(self, mca_data: dict) -> dict:
        """
        Compute MCA-based feature scores for the ML model.
        """
        # MCA Compliance Score (0-10, higher = better)
        compliance = mca_data.get("compliance_status", "Unknown")
        if compliance == "Compliant":
            mca_score = 9.0
        elif compliance == "Lapsed":
            mca_score = 4.0
        elif compliance == "Dissolved":
            mca_score = 0.0
        else:
            mca_score = 5.0

        # Director Risk Score (0-10, higher = riskier)
        directors = mca_data.get("directors", [])
        dir_risk = 0.0
        for d in directors:
            designation = d.get("designation", "").lower()
            if "resigned" in designation: dir_risk += 1.5
            if "disqualified" in designation: dir_risk += 5.0

        # Company Age Score (0-10, older = better)
        inc_date = mca_data.get("date_of_incorporation")
        age_score = 5.0
        if inc_date:
            try:
                from datetime import date
                from dateutil.parser import parse
                age_years = (date.today() - parse(inc_date).date()).days / 365
                if age_years >= 10:   age_score = 9.0
                elif age_years >= 5:  age_score = 7.0
                elif age_years >= 2:  age_score = 5.0
                else:                 age_score = 2.0
            except Exception:
                pass

        # Charge analysis
        charges = mca_data.get("charges", [])
        open_charges = [c for c in charges if "open" in str(c.get("status", "")).lower()]
        charge_risk = min(10, len(open_charges) * 2.5)

        return {
            "mca_compliance_score": round(min(10, max(0, mca_score - charge_risk * 0.3)), 1),
            "director_risk_score": round(min(10, dir_risk), 1),
            "company_age_score": round(age_score, 1),
            "open_charge_count": len(open_charges),
        }
