import re
import numpy as np
from loguru import logger
from app.constants import CRORE, LAKH


class CurrencyNormalizer:
    """
    Converts any Indian amount string to paise integer.
    ALL monetary values are stored as paise (integer).
    ₹1 Crore = 10,000,000 rupees = 1,000,000,000 paise
    """

    CRORE_PATTERN = re.compile(
        r'(?:rs\.?|₹|inr)?[\s]*([,\d]+\.?\d*)\s*(?:crore|crores|cr\.?)\b',
        re.IGNORECASE
    )
    LAKH_PATTERN = re.compile(
        r'(?:rs\.?|₹|inr)?[\s]*([,\d]+\.?\d*)\s*(?:lakh|lakhs|lac|lacs)\b',
        re.IGNORECASE
    )
    THOUSAND_PATTERN = re.compile(
        r'(?:rs\.?|₹|inr)?[\s]*([,\d]+\.?\d*)\s*(?:thousand|k)\b',
        re.IGNORECASE
    )
    BRACKET_NEGATIVE = re.compile(r'\(([,\d\.]+)\)')
    PLAIN_AMOUNT = re.compile(
        r'(?:rs\.?|₹|inr)[\s]*([,\d]+\.?\d*)',
        re.IGNORECASE
    )

    # Indian number words
    WORD_MAP = {
        "one lakh": LAKH,
        "two lakh": 2 * LAKH,
        "five lakh": 5 * LAKH,
        "ten lakh": 10 * LAKH,
        "twenty lakh": 20 * LAKH,
        "fifty lakh": 50 * LAKH,
        "one crore": CRORE,
        "two crore": 2 * CRORE,
        "five crore": 5 * CRORE,
        "ten crore": 10 * CRORE,
        "twenty crore": 20 * CRORE,
        "fifty crore": 50 * CRORE,
        "hundred crore": 100 * CRORE,
    }

    def parse_to_paise(self, text: str) -> int | None:
        """
        Converts any Indian amount string to paise integer.
        Returns None if unparseable.
        """
        if not text or not isinstance(text, str):
            try:
                val = float(text)
                return int(val * 100)
            except (TypeError, ValueError):
                return None

        text = text.strip()

        # Handle negative brackets like (42,000)
        is_negative = bool(self.BRACKET_NEGATIVE.search(text))

        # Remove commas for parsing
        clean = text.replace(',', '').strip()

        # Try crore pattern first
        m = self.CRORE_PATTERN.search(clean)
        if m:
            try:
                val_rupees = float(m.group(1)) * CRORE
                paise = int(val_rupees * 100)
                return -paise if is_negative else paise
            except ValueError:
                pass

        # Try lakh pattern
        m = self.LAKH_PATTERN.search(clean)
        if m:
            try:
                val_rupees = float(m.group(1)) * LAKH
                paise = int(val_rupees * 100)
                return -paise if is_negative else paise
            except ValueError:
                pass

        # Try thousand pattern
        m = self.THOUSAND_PATTERN.search(clean)
        if m:
            try:
                val_rupees = float(m.group(1)) * 1000
                paise = int(val_rupees * 100)
                return -paise if is_negative else paise
            except ValueError:
                pass

        # Plain amount with ₹ or Rs prefix
        m = self.PLAIN_AMOUNT.search(clean)
        if m:
            try:
                val_rupees = float(m.group(1))
                paise = int(val_rupees * 100)
                return -paise if is_negative else paise
            except ValueError:
                pass

        # Try word forms
        lower_text = text.lower()
        for phrase, rupees in self.WORD_MAP.items():
            if phrase in lower_text:
                paise = int(rupees * 100)
                return -paise if is_negative else paise

        # Try plain number
        # Remove Rs., ₹ symbols and try pure number
        pure = re.sub(r'[₹rRs\.\s]', '', clean).replace(',', '')
        if is_negative:
            pure = re.sub(r'[()]', '', pure)
        try:
            val = float(pure)
            if val > 0:
                paise = int(val * 100)
                return -paise if is_negative else paise
        except ValueError:
            pass

        return None

    def normalize_dataframe_column(self, series) -> any:
        """Apply parse_to_paise to entire DataFrame column, return int64 series."""
        import pandas as pd
        return series.apply(lambda x: self.parse_to_paise(str(x)) if x is not None else None).astype('Int64')

    def paise_to_crore(self, paise: int) -> float:
        """Convert paise to crores for display."""
        return paise / (CRORE * 100)

    def paise_to_lakh(self, paise: int) -> float:
        """Convert paise to lakhs for display."""
        return paise / (LAKH * 100)

    def format_indian(self, paise: int) -> str:
        """Format paise as Indian currency string."""
        rupees = paise / 100
        if abs(rupees) >= CRORE:
            return f"₹{rupees / CRORE:.2f} Cr"
        elif abs(rupees) >= LAKH:
            return f"₹{rupees / LAKH:.2f} Lakh"
        else:
            return f"₹{rupees:,.0f}"
