GST_FINGERPRINTS = {
    "GSTR1": {
        "required_keywords": ["outward supplies", "b2b", "hsn", "invoice details", "gstr-1"],
        "structural_indicators": {"min_pages": 1, "has_tables": True},
        "exclusion_keywords": ["tax liability", "input tax credit"],
        "weight": 1.0,
    },
    "GSTR3B": {
        "required_keywords": ["3.1", "3.2", "4", "tax on outward", "input tax credit", "tax payable", "gstr-3b"],
        "structural_indicators": {"page_range": (1, 5)},
        "exclusion_keywords": ["annual return"],
        "weight": 1.0,
    },
    "GSTR2A": {
        "required_keywords": ["auto-populated", "inward supplies", "2a", "supplier gstin"],
        "structural_indicators": {},
        "weight": 1.0,
    },
    "GSTR9": {
        "required_keywords": ["annual return", "gstr-9", "pt. i", "pt. ii", "aggregate turnover"],
        "structural_indicators": {"min_pages": 5},
        "weight": 1.0,
    },
    "GSTR9C": {
        "required_keywords": ["gstr-9c", "reconciliation statement", "certified", "9c"],
        "structural_indicators": {},
        "weight": 1.0,
    },
}

ANNUAL_REPORT_FINGERPRINTS = {
    "required_keywords": [
        "annual report", "directors report", "board of directors",
        "auditors report", "financial statements", "notes to accounts",
        "profit and loss", "balance sheet",
    ],
    "weight": 1.0,
}

RATING_REPORT_FINGERPRINTS = {
    "required_keywords": [
        "rating rationale", "crisil", "icra", "care ratings",
        "brickwork", "ind-ra", "credit rating", "rated",
    ],
    "weight": 1.0,
}

LEGAL_NOTICE_FINGERPRINTS = {
    "required_keywords": [
        "legal notice", "show cause", "drt", "nclt", "debt recovery",
        "national company law", "winding up", "respondent", "petitioner",
        "court", "tribunal", "suit",
    ],
    "weight": 1.0,
}

SANCTION_LETTER_FINGERPRINTS = {
    "required_keywords": [
        "sanction letter", "sanctioned", "working capital", "term loan",
        "rate of interest", "collateral", "primary security", "repayment",
        "overdraft", "cash credit",
    ],
    "weight": 1.0,
}

CIBIL_FINGERPRINTS = {
    "required_keywords": [
        "cibil", "commercial", "credit information", "dpd", "days past due",
        "credit utilization", "outstanding loan",
    ],
    "weight": 1.0,
}

MCA_FINGERPRINTS = {
    "required_keywords": [
        "mca", "ministry of corporate affairs", "company master",
        "charge", "cin", "director identification", "din",
    ],
    "weight": 1.0,
}

# -- NEW: 4 Hackathon Critical Document Types ----------------------------------

ALM_FINGERPRINTS = {
    "required_keywords": [
        "asset liability", "alm", "maturity bucket", "rate sensitive",
        "liquidity gap", "mismatched", "gap analysis", "cumulative gap",
        "assets and liabilities", "maturity profile", "residual maturity",
        "1 day", "2-7 days", "8-14 days", "15-30 days", "1-3 months",
        "rsa", "rsl", "nse", "cumulative surplus", "structural liquidity",
        "statement of structural liquidity", "interest rate sensitivity",
    ],
    "weight": 1.0,
}

SHAREHOLDING_FINGERPRINTS = {
    "required_keywords": [
        "shareholding pattern", "promoter group", "promoter",
        "public shareholding", "fii", "fpi", "dii", "institutional investor",
        "public float", "pledge", "pledged", "shares held",
        "total no. of shareholders", "category of shareholder",
        "percentage of holding", "encumbered",
    ],
    "weight": 1.0,
}

BORROWING_PROFILE_FINGERPRINTS = {
    "required_keywords": [
        "borrowing profile", "schedule of borrowings", "facilities availed",
        "lender", "sanctioned amount", "outstanding", "rate of interest",
        "repayment schedule", "security", "collateral description",
        "principal outstanding", "maturity date", "consortium",
        "working capital facilities", "term loans availed",
        "fund based", "non-fund based",
        "external commercial borrowings", "ecb", "debentures", "bond",
    ],
    "weight": 1.0,
}

PORTFOLIO_PERFORMANCE_FINGERPRINTS = {
    "required_keywords": [
        "portfolio performance", "npa", "gross npa", "net npa",
        "collection efficiency", "dpd", "days past due",
        "provision coverage", "pcr", "write off",
        "aum", "portfolio size", "disbursements",
        "vintage", "bucket", "delinquency", "recovery rate",
        "credit cost", "collection efficiency", "par",
        "assets under management", "loan book",
    ],
    "weight": 1.0,
}

