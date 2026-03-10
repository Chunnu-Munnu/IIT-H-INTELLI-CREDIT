"""
feature_dataset_builder.py
Builds feature matrix from the credit dataset with:
- Feature definitions and ordering
- Imputation with domain-appropriate defaults
- Feature engineering (lag ratios, trend slopes)
"""
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
import joblib
import os
from loguru import logger

pd.set_option('future.no_silent_downcasting', True)

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "models")

# Canonical feature list — must match ingestion/orchestrator._build_feature_vector
FEATURE_COLUMNS = [
    # Capacity — Debt Service
    "dscr_fy1", "dscr_fy2", "dscr_fy3",
    "interest_coverage_fy1", "interest_coverage_fy2",
    "ebitda_margin_fy1", "ebitda_margin_fy2", "ebitda_margin_fy3",
    "pat_margin_fy1", "pat_margin_fy2",
    # Capital — Leverage
    "debt_equity_fy1", "debt_equity_fy2", "debt_equity_fy3",
    "tol_tnw_fy1", "tol_tnw_fy2",
    # Liquidity
    "current_ratio_fy1", "current_ratio_fy2",
    "quick_ratio_fy1",
    # Efficiency
    "debtor_days_fy1", "debtor_days_fy2",
    "creditor_days_fy1",
    "inventory_days_fy1",
    "asset_turnover_fy1",
    "revenue_growth_fy1",
    # Profitability
    "roce_fy1", "roce_fy2",
    # GST/Bank Cross-Validation
    "gst_compliance_score",
    "gst_bank_inflation_ratio",
    # Fraud Binary Flags
    "itc_inflation_flag",
    "circular_trading_flag",
    "window_dressing_flag",
    "undisclosed_borrowing_flag",
    # EWS
    "total_ews_score_deduction",
    "ews_character_flags",
    "ews_capacity_flags",
    "ews_capital_flags",
    "ews_conditions_flags",
    # Banking Behaviour
    "nach_bounce_count",
    # Character
    "going_concern_flag",
    "director_cirp_linked",
    "drt_case_count",
    "nclt_case_count",
    "auditor_opinion_score",
    # MCA
    "mca_compliance_score",
    "director_risk_score",
    "company_age_score",
    # Rating
    "rating_direction",
    # Graph Intelligence
    "network_risk_score",
    "supplier_default_risk",
    "promoter_network_risk",
    # Research
    "negative_news_score",
    "litigation_count",
    "regulatory_risk_score",
    # Sector
    "sector_risk_score",
    # Collateral
    "collateral_type_score",
    "security_coverage_ratio",
]

# Domain-appropriate imputation defaults
FEATURE_DEFAULTS = {
    "dscr_fy1": 1.0, "dscr_fy2": 1.0, "dscr_fy3": 1.0,
    "interest_coverage_fy1": 2.0, "interest_coverage_fy2": 2.0,
    "ebitda_margin_fy1": 0.10, "ebitda_margin_fy2": 0.10, "ebitda_margin_fy3": 0.10,
    "pat_margin_fy1": 0.04, "pat_margin_fy2": 0.04,
    "debt_equity_fy1": 2.0, "debt_equity_fy2": 2.0, "debt_equity_fy3": 2.0,
    "tol_tnw_fy1": 3.0, "tol_tnw_fy2": 3.0,
    "current_ratio_fy1": 1.2, "current_ratio_fy2": 1.2,
    "quick_ratio_fy1": 1.0,
    "debtor_days_fy1": 60.0, "debtor_days_fy2": 65.0,
    "creditor_days_fy1": 45.0, "inventory_days_fy1": 60.0,
    "asset_turnover_fy1": 1.0, "revenue_growth_fy1": 0.05,
    "roce_fy1": 0.12, "roce_fy2": 0.12,
    "gst_compliance_score": 5.0, "gst_bank_inflation_ratio": 1.0,
    "itc_inflation_flag": 0, "circular_trading_flag": 0,
    "window_dressing_flag": 0, "undisclosed_borrowing_flag": 0,
    "total_ews_score_deduction": 0.0, "ews_character_flags": 0,
    "ews_capacity_flags": 0, "ews_capital_flags": 0, "ews_conditions_flags": 0,
    "nach_bounce_count": 0, "going_concern_flag": 0, "director_cirp_linked": 0,
    "drt_case_count": 0, "nclt_case_count": 0, "auditor_opinion_score": 7.0,
    "mca_compliance_score": 5.0, "director_risk_score": 2.0, "company_age_score": 5.0,
    "rating_direction": 0, "network_risk_score": 2.0, "supplier_default_risk": 2.0,
    "promoter_network_risk": 2.0, "negative_news_score": 0.0, "litigation_count": 0,
    "regulatory_risk_score": 0.0, "sector_risk_score": 5, "collateral_type_score": 2,
    "security_coverage_ratio": 1.5,
}


class FeatureDatasetBuilder:

    def __init__(self):
        self.scaler = StandardScaler()
        self.imputer = SimpleImputer(strategy="constant")
        self._fitted = False

    def build(self, df: pd.DataFrame) -> tuple:
        """Returns X (feature matrix), y (target), feature_names."""
        missing = set(FEATURE_COLUMNS) - set(df.columns)
        if missing:
            logger.warning(f"Missing columns, filling with defaults: {missing}")
            for col in missing:
                df[col] = FEATURE_DEFAULTS.get(col, 0)

        X = df[FEATURE_COLUMNS].copy()

        # Fill NaN with domain defaults
        for col in FEATURE_COLUMNS:
            default = FEATURE_DEFAULTS.get(col, 0)
            X[col] = X[col].fillna(default)

        # Feature engineering — trend slopes
        X["dscr_trend"] = (X["dscr_fy1"] - X.get("dscr_fy3", X["dscr_fy1"])).clip(-5, 5)
        X["de_trend"] = (X["debt_equity_fy1"] - X.get("debt_equity_fy3", X["debt_equity_fy1"])).clip(-10, 10)
        X["ebitda_trend"] = (X["ebitda_margin_fy1"] - X.get("ebitda_margin_fy3", X["ebitda_margin_fy1"])).clip(-1, 1)
        X["fraud_flag_sum"] = (
            X["itc_inflation_flag"] + X["circular_trading_flag"] +
            X["window_dressing_flag"] + X["undisclosed_borrowing_flag"] +
            (X["nach_bounce_count"] > 2).astype(int) + X["going_concern_flag"]
        )
        X["liq_stress"] = (X["current_ratio_fy1"] < 1.1).astype(int) * 2 + (X["quick_ratio_fy1"] < 0.8).astype(int)
        X["leverage_stress"] = (X["debt_equity_fy1"] > 3.0).astype(int) + (X["tol_tnw_fy1"] > 5.0).astype(int)

        y = df["default"].values if "default" in df.columns else None
        feature_names = list(X.columns)
        X_values = X.values.astype(np.float32)

        logger.info(f"Feature matrix: {X_values.shape}, features: {len(feature_names)}")
        return X_values, y, feature_names

    def fit_transform(self, df: pd.DataFrame) -> tuple:
        X, y, names = self.build(df)
        X_scaled = self.scaler.fit_transform(X)
        self._fitted = True
        os.makedirs(MODEL_DIR, exist_ok=True)
        joblib.dump(self.scaler, os.path.join(MODEL_DIR, "scaler.joblib"))
        joblib.dump(names, os.path.join(MODEL_DIR, "feature_names.joblib"))
        return X_scaled, y, names

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        X, _, _ = self.build(df)
        if not self._fitted:
            scaler_path = os.path.join(MODEL_DIR, "scaler.joblib")
            if os.path.exists(scaler_path):
                self.scaler = joblib.load(scaler_path)
                self._fitted = True
            else:
                return X
        return self.scaler.transform(X)

    @classmethod
    def transform_case_features(cls, feature_dict: dict) -> np.ndarray:
        """Convert a case's feature_vector dict into a scaled numpy row."""
        builder = cls()
        df = pd.DataFrame([feature_dict])
        return builder.transform(df)
