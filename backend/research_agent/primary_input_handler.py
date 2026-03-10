"""
Research Agent: Web crawler, MCA scraper, and primary input handler.
"""
import re
from pydantic import BaseModel
from loguru import logger


class QualitativeAdjustment(BaseModel):
    dimension: str          # Character | Capacity | Capital | Collateral | Conditions
    adjustment: float       # -10 to +10
    reason: str
    original_note: str
    sentiment: str          # positive | neutral | negative


CAPACITY_SIGNALS = ["capacity", "utilization", "production", "operating at", "factory", "plant"]
CHARACTER_SIGNALS = ["management quality", "cooperative", "promoter", "attitude", "trust", "reputation"]
COLLATERAL_SIGNALS = ["property", "asset", "land", "plant", "machine", "collateral", "mortgage"]
CAPITAL_SIGNALS = ["reserves", "equity", "capital", "net worth", "promoter contribution"]
CONDITIONS_SIGNALS = ["sector", "industry", "competition", "market", "economy", "regulation"]


class PrimaryInputHandler:
    """
    Processes qualitative credit officer notes and maps to Five C score adjustments.
    """

    NEGATIVE_KEYWORDS = [
        "poor", "bad", "low", "risk", "concern", "doubt", "failing", "stressed",
        "underutilized", "idle", "declining", "weak", "loss", "default", "overdue",
        "hostile", "unresponsive", "evasive", "fraudulent", "suspicious",
    ]
    POSITIVE_KEYWORDS = [
        "strong", "good", "excellent", "robust", "cooperative", "responsive",
        "growing", "profitable", "modern", "efficient", "well-managed", "transparent",
        "improving", "expanding", "promising",
    ]

    def process_qualitative_note(self, note: str, case_id: str) -> QualitativeAdjustment:
        note_lower = note.lower()

        # Detect dimension
        dimension = "Conditions"  # default
        if any(kw in note_lower for kw in CAPACITY_SIGNALS):
            dimension = "Capacity"
        elif any(kw in note_lower for kw in CHARACTER_SIGNALS):
            dimension = "Character"
        elif any(kw in note_lower for kw in COLLATERAL_SIGNALS):
            dimension = "Collateral"
        elif any(kw in note_lower for kw in CAPITAL_SIGNALS):
            dimension = "Capital"

        # Detect sentiment
        neg_count = sum(1 for kw in self.NEGATIVE_KEYWORDS if kw in note_lower)
        pos_count = sum(1 for kw in self.POSITIVE_KEYWORDS if kw in note_lower)

        if neg_count > pos_count:
            sentiment = "negative"
            adjustment = -min(10, neg_count * 2.5)
        elif pos_count > neg_count:
            sentiment = "positive"
            adjustment = min(10, pos_count * 2.0)
        else:
            sentiment = "neutral"
            adjustment = 0

        # Special high-impact patterns
        if re.search(r'operating at\s+(\d+)\s*%\s+capacity', note_lower):
            m = re.search(r'operating at\s+(\d+)\s*%', note_lower)
            if m:
                pct = int(m.group(1))
                if pct < 50:
                    adjustment = max(adjustment, -8)
                    sentiment = "negative"
                    dimension = "Capacity"

        reason = f"Credit officer note indicates {sentiment} signal for {dimension}. "
        if adjustment < -5:
            reason += "Significant negative adjustment applied."
        elif adjustment < 0:
            reason += "Moderate negative adjustment applied."
        elif adjustment > 5:
            reason += "Significant positive adjustment applied."
        elif adjustment > 0:
            reason += "Moderate positive adjustment applied."

        return QualitativeAdjustment(
            dimension=dimension,
            adjustment=round(adjustment, 1),
            reason=reason,
            original_note=note,
            sentiment=sentiment,
        )


class WebCrawler:
    """
    Web crawler for company news, promoter news, and sector intelligence.
    Uses DuckDuckGo search API (no key needed).
    """

    async def search_company_news(self, company_name: str, cin: str = "") -> list:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                query = f'"{company_name}" india credit loan default news'
                url = f"https://duckduckgo.com/news.js?q={query}&o=json&l=in-en&s=0"
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        return data.get("results", [])[:10]
                    except Exception:
                        return []
        except Exception as e:
            logger.warning(f"Web crawler failed: {e}")
        return []

    async def search_promoter_news(self, promoter_names: list) -> list:
        results = []
        for name in promoter_names[:3]:
            try:
                import httpx
                async with httpx.AsyncClient(timeout=10) as client:
                    query = f'"{name}" india fraud loan default court'
                    url = f"https://duckduckgo.com/news.js?q={query}&o=json&l=in-en&s=0"
                    resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                    if resp.status_code == 200:
                        data = resp.json()
                        results.extend(data.get("results", [])[:3])
            except Exception:
                pass
        return results

    async def search_sector_news(self, sector: str) -> list:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                query = f"{sector} india RBI regulation NPA headwind 2024"
                url = f"https://duckduckgo.com/news.js?q={query}&o=json&l=in-en&s=0"
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("results", [])[:5]
        except Exception as e:
            logger.warning(f"Sector news search failed: {e}")
        return []


class MCAScraper:
    """
    MCA21 company data scraper.
    """

    async def fetch_company_master(self, cin: str) -> dict:
        """Fetch company master data from MCA portal."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=15) as client:
                # Note: MCA portal requires session cookies in production
                # This is a simplified demo implementation
                logger.info(f"Fetching MCA data for CIN: {cin}")
                return {
                    "cin": cin,
                    "status": "Active",
                    "source": "MCA21 (simulated)",
                    "note": "Connect to real MCA API for production use",
                }
        except Exception as e:
            logger.warning(f"MCA fetch failed: {e}")
            return {"cin": cin, "error": str(e)}

    async def fetch_charges(self, cin: str) -> list:
        """Fetch charge registry from MCA."""
        logger.info(f"Fetching charge data for CIN: {cin}")
        return []  # Would connect to MCA API in production

    async def fetch_directors(self, cin: str) -> list:
        """Fetch director list with DINs."""
        logger.info(f"Fetching director data for CIN: {cin}")
        return []  # Would connect to MCA API in production
