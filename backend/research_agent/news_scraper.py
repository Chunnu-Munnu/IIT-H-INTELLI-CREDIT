"""
news_scraper.py
Scrapes company and promoter news from:
  - Google News RSS (free, no API key needed)
  - DuckDuckGo HTML (fallback)
  - Economic Times RSS
Produces sentiment-tagged research items with title, source, date, snippet, 
relevance_type fields — all fields that the frontend ResearchCard component expects.
"""
import re
import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from urllib.parse import quote_plus
from loguru import logger

NEGATIVE_KEYWORDS = [
    "fraud", "default", "npa", "bankruptcy", "insolvency", "closure", "shutdown",
    "layoff", "penalty", "arrested", "investigation", "notice", "show cause",
    "drt", "nclt", "cirp", "seized", "attached", "raided", "chargesheet",
    "money laundering", "hawala", "ed raid", "it raid", "gst evasion",
    "loan default", "cheque bounce", "winding up", "rating downgrade",
    "cbi probe", "sfio investigation", "sebi action", "rera violation",
    "npa account", "willful defaulter", "rbi penalty", "income tax search",
    "customs duty", "smuggling", "misappropriation", "embezzlement",
]

POSITIVE_KEYWORDS = [
    "expansion", "profit", "turnover growth", "revenue growth", "new order",
    "rating upgrade", "capacity expansion", "ipo listing", "acquisition successful",
    "ebitda growth", "dividend declared", "exports", "award", "recognition",
    "contract win", "empanelled", "partnership", "debt free", "repaid",
    "credit rating improved", "upgrade", "market share gain",
]

RELEVANCE_TYPE_KEYWORDS = {
    "LEGAL_REGULATORY": ["nclt", "drt", "sebi", "rbi penalty", "rera", "ed raid", "cbi", "sfio", "cirp", "court"],
    "FINANCIAL_DISTRESS": ["default", "npa", "insolvency", "bankruptcy", "winding up", "cheque bounce", "willful defaulter"],
    "BUSINESS_PERFORMANCE": ["revenue", "profit", "ebitda", "turnover", "growth", "order", "contract", "export"],
    "MANAGEMENT_GOVERNANCE": ["ceo", "director", "promoter", "management", "board", "governance", "cfo", "appointed", "resigned"],
    "RATING_CHANGE": ["rating upgrade", "rating downgrade", "credit watch", "outlook", "placed on"],
    "SECTOR_RISK": ["rbi", "regulation", "policy", "npa", "nbfc", "banking sector", "credit squeeze"],
    "FRAUD": ["fraud", "hawala", "money laundering", "it raid", "gst evasion", "misappropriation"],
}


class NewsScraperAsync:

    async def fetch_company_news(self, company_name: str, gstin: str = "") -> dict:
        """
        Fetch news articles for a company name.
        Returns structured result with sentiment-tagged research items.
        """
        all_items = []

        # Search 1: Company name + fraud/default signals (adversarial search)
        items1 = await self._fetch_google_news(f"{company_name} India fraud default NPA NCLT")
        all_items.extend(items1)

        # Search 2: General company news (positive and business news)
        items2 = await self._fetch_google_news(f"{company_name} India business financial")
        all_items.extend(items2)

        # Search 3: DuckDuckGo fallback for NCLT / DRT
        items3 = await self._fetch_duckduckgo(f"{company_name} NCLT DRT insolvency")
        all_items.extend(items3)

        # Deduplicate by title
        seen_titles = set()
        unique_items = []
        for item in all_items:
            title_key = item["title"][:60].lower()
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_items.append(item)

        # Tag sentiment and relevance on each item
        tagged = [self._tag_item(item, company_name) for item in unique_items]

        # Separate by sentiment for scoring
        negative = [i for i in tagged if i["sentiment"] == "NEGATIVE"]
        positive = [i for i in tagged if i["sentiment"] == "POSITIVE"]
        neutral = [i for i in tagged if i["sentiment"] == "NEUTRAL"]

        negative_score = min(10, len(negative) * 2.5 - len(positive) * 0.5)
        negative_score = round(max(0, negative_score), 1)

        logger.info(f"[NewsScraperAsync] company='{company_name}' | total={len(tagged)} | neg={len(negative)} | pos={len(positive)}")

        return {
            "negative_news_score": negative_score,
            "total_articles": len(tagged),
            "relevant_articles": len(tagged),
            "negative_count": len(negative),
            "positive_count": len(positive),
            "top_negative_keywords": self._top_negative_keywords(tagged),
            "items": tagged,  # Full items for frontend ResearchCard
            # Legacy field (used in feature extraction)
            "articles": [{"title": i["title"], "link": i.get("url", "")} for i in tagged[:5]],
        }

    async def fetch_sector_news(self, sector: str) -> dict:
        """Fetch sector-level news for context in SWOT analysis."""
        items = await self._fetch_google_news(f"{sector} India RBI NPA credit risk 2024 2025")
        tagged = [self._tag_item(item, sector) for item in items]

        negative = [i for i in tagged if i["sentiment"] == "NEGATIVE"]
        sector_risk = min(10, len(negative) * 1.5)

        return {
            "sector_risk_score": round(sector_risk, 1),
            "total_articles": len(tagged),
            "items": tagged,
        }

    # ── GOOGLE NEWS RSS ──────────────────────────────────────────────────────

    async def _fetch_google_news(self, query: str, max_items: int = 15) -> list:
        encoded = quote_plus(query)
        url = f"https://news.google.com/rss/search?q={encoded}&hl=en-IN&gl=IN&ceid=IN:en"
        try:
            import httpx
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (compatible; research-bot)"})
                if resp.status_code == 200:
                    items = self._parse_rss(resp.text)
                    return items[:max_items]
        except Exception as e:
            logger.debug(f"Google News RSS failed for '{query}': {e}")
        return []

    def _parse_rss(self, xml_text: str) -> list:
        """Parse Google News RSS XML into article dicts."""
        items = []
        try:
            root = ET.fromstring(xml_text)
            cutoff = datetime.now() - timedelta(days=365 * 2)  # Last 2 years

            for elem in root.findall(".//item"):
                title_el = elem.find("title")
                desc_el = elem.find("description")
                pub_date_el = elem.find("pubDate")
                link_el = elem.find("link")
                source_el = elem.find("source")

                title = (title_el.text or "").strip() if title_el is not None else ""
                desc = (desc_el.text or "").strip() if desc_el is not None else ""
                # Strip HTML from desc
                desc = re.sub(r'<[^>]+>', '', desc).strip()
                link = (link_el.text or "").strip() if link_el is not None else ""
                source = ""
                if source_el is not None:
                    source = source_el.text or source_el.get("url", "")
                    # Extract just the domain for display
                    m = re.search(r'(?:https?://)?(?:www\.)?([^/\s]+)', source)
                    if m:
                        source = m.group(1)

                pub_date_str = (pub_date_el.text or "").strip() if pub_date_el is not None else ""

                # Parse date
                pub_date_iso = None
                try:
                    from email.utils import parsedate_to_datetime
                    dt = parsedate_to_datetime(pub_date_str)
                    if dt.replace(tzinfo=None) < cutoff:
                        continue
                    pub_date_iso = dt.isoformat()
                except Exception:
                    pub_date_iso = None

                if not title:
                    continue

                # Snippet = first 200 chars of description
                snippet = desc[:200] if desc else title[:120]

                items.append({
                    "title": title,
                    "url": link,
                    "source": source or "Google News",
                    "date": pub_date_iso,
                    "snippet": snippet,
                    "raw_text": f"{title} {desc}".lower(),
                })
        except Exception as e:
            logger.debug(f"RSS parse error: {e}")
        return items

    # ── DUCKDUCKGO HTML SCRAPER ──────────────────────────────────────────────

    async def _fetch_duckduckgo(self, query: str) -> list:
        """Scrape DuckDuckGo HTML search results — no API key needed."""
        encoded = quote_plus(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded}"
        items = []
        try:
            import httpx
            async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
                resp = await client.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept-Language": "en-IN,en;q=0.9",
                })
                if resp.status_code == 200:
                    items = self._parse_duckduckgo_html(resp.text)
        except Exception as e:
            logger.debug(f"DuckDuckGo scrape failed: {e}")
        return items

    def _parse_duckduckgo_html(self, html: str) -> list:
        """Parse DuckDuckGo HTML results into article dicts."""
        items = []
        # Find result blocks
        result_blocks = re.findall(
            r'class="result__body"[^>]*>.*?<a class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?class="result__snippet"[^>]*>(.*?)</div>',
            html, re.DOTALL | re.IGNORECASE
        )
        for url, title_raw, snippet_raw in result_blocks[:8]:
            title = re.sub(r'<[^>]+>', '', title_raw).strip()
            snippet = re.sub(r'<[^>]+>', '', snippet_raw).strip()
            if not title:
                continue
            # Extract domain
            domain_m = re.search(r'(?:https?://)?(?:www\.)?([^/\s]+)', url)
            source = domain_m.group(1) if domain_m else "Web"
            items.append({
                "title": title,
                "url": url,
                "source": source,
                "date": None,
                "snippet": snippet[:200],
                "raw_text": f"{title} {snippet}".lower(),
            })
        return items

    # ── SENTIMENT AND RELEVANCE TAGGING ──────────────────────────────────────

    def _tag_item(self, item: dict, entity_name: str) -> dict:
        """Add sentiment, relevance_type, and cleaned fields to an article."""
        raw = item.get("raw_text", "").lower()
        title = item.get("title", "")

        # Count keyword hits
        neg_hits = [kw for kw in NEGATIVE_KEYWORDS if kw in raw]
        pos_hits = [kw for kw in POSITIVE_KEYWORDS if kw in raw]

        # Determine sentiment
        if len(neg_hits) >= 2 or (neg_hits and not pos_hits):
            sentiment = "NEGATIVE"
        elif len(pos_hits) >= 2 or (pos_hits and not neg_hits):
            sentiment = "POSITIVE"
        elif neg_hits and pos_hits:
            sentiment = "MIXED"
        else:
            sentiment = "NEUTRAL"

        # Determine relevance type
        relevance_type = "GENERAL_NEWS"
        for rtype, keywords in RELEVANCE_TYPE_KEYWORDS.items():
            if any(kw in raw for kw in keywords):
                relevance_type = rtype
                break

        return {
            "title": title,
            "url": item.get("url", ""),
            "source": item.get("source", "News"),
            "date": item.get("date"),
            "snippet": item.get("snippet", title[:120]),
            "sentiment": sentiment,
            "relevance_type": relevance_type,
            "negative_keywords": neg_hits[:3],
            "positive_keywords": pos_hits[:3],
        }

    def _top_negative_keywords(self, items: list) -> list:
        all_kws = []
        for item in items:
            all_kws.extend(item.get("negative_keywords", []))
        # Return top unique keywords sorted by frequency
        from collections import Counter
        return [kw for kw, _ in Counter(all_kws).most_common(5)]

    # ── LEGACY COMPUTE SCORES (kept for backward compat) ────────────────────

    def _compute_scores(self, articles: list, entity_name: str) -> dict:
        tagged = [self._tag_item(a, entity_name) for a in articles]
        negative = [i for i in tagged if i["sentiment"] == "NEGATIVE"]
        positive = [i for i in tagged if i["sentiment"] == "POSITIVE"]
        score = min(10, round(max(0, len(negative) * 2.5 - len(positive) * 0.5), 1))
        return {
            "negative_news_score": score,
            "total_articles": len(tagged),
            "relevant_articles": len(tagged),
            "negative_count": len(negative),
            "positive_count": len(positive),
            "top_negative_keywords": self._top_negative_keywords(tagged),
            "items": tagged,
            "articles": [{"title": i["title"], "link": i.get("url", "")} for i in tagged[:5]],
        }
