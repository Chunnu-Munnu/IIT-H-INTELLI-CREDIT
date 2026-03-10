import re
from datetime import date
from typing import Optional
from models.financial import FinancialPeriod


class PeriodNormalizer:
    """
    Normalizes various Indian FY period text formats to FinancialPeriod.
    Handles: FY23, FY2023, 2022-23, 2022-2023, year ended March 31 2023, etc.
    """

    FY_PATTERNS = [
        (re.compile(r'fy[\s-]*(2\d{3})[-/](2\d{3})', re.IGNORECASE), 'fy_full_range'),
        (re.compile(r'fy[\s-]*(2\d{3})[-/](\d{2})', re.IGNORECASE), 'fy_range'),
        (re.compile(r'(2\d{3})[\s-]+(2\d{3})', re.IGNORECASE), 'year_range'),
        (re.compile(r'(2\d{3})[\s/-](\d{2})\b', re.IGNORECASE), 'short_range'),
        (re.compile(r'fy[\s]*(2\d{3})\b', re.IGNORECASE), 'fy_year'),
        (re.compile(r'fy[\s]*(\d{2})\b', re.IGNORECASE), 'fy_short'),
        (re.compile(r'year[\s]+ended[\s]+.*?(\d{1,2})(?:st|nd|rd|th)?[\s]+march[\s,]+(\d{4})', re.IGNORECASE), 'year_ended'),
        (re.compile(r'march[\s,]+(\d{4})', re.IGNORECASE), 'march_year'),
        (re.compile(r'31[-/]03[-/](20\d{2})', re.IGNORECASE), 'date_format'),
    ]

    def normalize(self, text: str) -> Optional[FinancialPeriod]:
        """Returns FinancialPeriod with start_date, end_date, fy_label."""
        if not text:
            return None
        text = text.strip()

        for pattern, ptype in self.FY_PATTERNS:
            m = pattern.search(text)
            if m:
                try:
                    period = self._parse_match(m, ptype)
                    if period:
                        return period
                except Exception:
                    continue

        return None

    def _parse_match(self, m, ptype: str) -> Optional[FinancialPeriod]:
        groups = m.groups()

        if ptype == 'fy_full_range':
            start_year = int(groups[0])
            end_year = int(groups[1])
        elif ptype == 'fy_range':
            start_year = int(groups[0])
            end_year = start_year + 1
        elif ptype == 'year_range':
            start_year = int(groups[0])
            end_year = int(groups[1])
        elif ptype == 'short_range':
            start_year = int(groups[0])
            end_suffix = int(groups[1])
            end_year = (start_year // 100) * 100 + end_suffix
            if end_year <= start_year:
                end_year += 100
        elif ptype == 'fy_year':
            end_year = int(groups[0])
            start_year = end_year - 1
        elif ptype == 'fy_short':
            short = int(groups[0])
            end_year = 2000 + short if short < 100 else short
            start_year = end_year - 1
        elif ptype == 'year_ended':
            end_year = int(groups[1])
            start_year = end_year - 1
        elif ptype == 'march_year':
            end_year = int(groups[0])
            start_year = end_year - 1
        elif ptype == 'date_format':
            end_year = int(groups[0])
            start_year = end_year - 1
        else:
            return None

        fy_label = f"FY_{end_year}"
        start_date = date(start_year, 4, 1)
        end_date = date(end_year, 3, 31)

        return FinancialPeriod(fy_label=fy_label, start_date=start_date, end_date=end_date)

    def get_fy_year(self, period_text: str) -> Optional[int]:
        """Returns just the ending FY year as integer."""
        period = self.normalize(period_text)
        if period:
            return period.end_date.year
        return None
