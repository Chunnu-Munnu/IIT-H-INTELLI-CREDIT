"""
shap_explainer.py — Real SHAP explanations using shap.TreeExplainer.
Falls back to permutation importance if SHAP unavailable.
"""
import os
import json
import numpy as np
from loguru import logger

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "models")

FIVE_C_FEATURE_MAP = {
    # Character
    "going_concern_flag": "Character", "director_cirp_linked": "Character",
    "drt_case_count": "Character", "nclt_case_count": "Character",
    "auditor_opinion_score": "Character", "mca_compliance_score": "Character",
    "director_risk_score": "Character", "negative_news_score": "Character",
    "litigation_count": "Character", "regulatory_risk_score": "Character",
    "ews_character_flags": "Character",
    # Capacity
    "dscr_fy1": "Capacity", "dscr_fy2": "Capacity", "dscr_fy3": "Capacity",
    "interest_coverage_fy1": "Capacity", "interest_coverage_fy2": "Capacity",
    "ebitda_margin_fy1": "Capacity", "ebitda_margin_fy2": "Capacity",
    "pat_margin_fy1": "Capacity", "pat_margin_fy2": "Capacity",
    "nach_bounce_count": "Capacity", "ews_capacity_flags": "Capacity",
    "dscr_trend": "Capacity",
    # Capital
    "debt_equity_fy1": "Capital", "debt_equity_fy2": "Capital", "debt_equity_fy3": "Capital",
    "tol_tnw_fy1": "Capital", "tol_tnw_fy2": "Capital",
    "current_ratio_fy1": "Capital", "current_ratio_fy2": "Capital",
    "quick_ratio_fy1": "Capital", "roce_fy1": "Capital",
    "asset_turnover_fy1": "Capital", "revenue_growth_fy1": "Capital",
    "ews_capital_flags": "Capital", "leverage_stress": "Capital",
    # Collateral
    "collateral_type_score": "Collateral", "security_coverage_ratio": "Collateral",
    # Conditions
    "gst_compliance_score": "Conditions", "gst_bank_inflation_ratio": "Conditions",
    "itc_inflation_flag": "Conditions", "circular_trading_flag": "Conditions",
    "window_dressing_flag": "Conditions", "undisclosed_borrowing_flag": "Conditions",
    "sector_risk_score": "Conditions", "rating_direction": "Conditions",
    "network_risk_score": "Conditions", "supplier_default_risk": "Conditions",
    "promoter_network_risk": "Conditions", "ews_conditions_flags": "Conditions",
    "total_ews_score_deduction": "Conditions", "fraud_flag_sum": "Conditions",
}


def compute_shap_values(X_raw: np.ndarray, models: dict, feature_names: list) -> dict:
    """
    Compute SHAP values for a single prediction row using TreeExplainer.
    Returns dict with feature-level contributions for the top 15 features.
    """
    try:
        import shap

        xgb_model = models.get("xgboost")
        lgbm_model = models.get("lightgbm")
        cat_model  = models.get("catboost")

        all_shap = []

        for model_name, model in [("xgboost", xgb_model), ("lightgbm", lgbm_model), ("catboost", cat_model)]:
            if model is None:
                continue

            try:
                # FIXED VERSION (no feature_perturbation / model_output)
                explainer = shap.TreeExplainer(model)

                shap_vals = explainer.shap_values(X_raw)

                if isinstance(shap_vals, list):
                    shap_row = shap_vals[1][0]
                else:
                    shap_row = shap_vals[0]

                all_shap.append(shap_row)
                logger.debug(f"SHAP from {model_name}: {len(shap_row)} values")

            except Exception as e:
                logger.warning(f"SHAP TreeExplainer failed for {model_name}: {e}")
                continue

        if not all_shap:
            return _fallback_shap(X_raw, models, feature_names)

        avg_shap = np.mean(all_shap, axis=0)
        base_val = 0.5

        contributions = []

        fn = feature_names if len(feature_names) == len(avg_shap) else list(range(len(avg_shap)))

        for i, (shap_val, name) in enumerate(zip(avg_shap, fn)):

            feat_val = float(X_raw[0][i]) if X_raw.shape[1] > i else None

            five_c = FIVE_C_FEATURE_MAP.get(str(name), "Conditions")

            contributions.append({
                "feature_name": str(name),
                "feature_value": round(feat_val, 4) if feat_val is not None else None,
                "shap_value": round(float(shap_val), 5),
                "abs_contribution": round(abs(float(shap_val)), 5),
                "impact_direction": "INCREASES_DEFAULT_RISK" if shap_val > 0 else "DECREASES_DEFAULT_RISK",
                "five_c_mapping": five_c,
            })

        contributions.sort(key=lambda x: x["abs_contribution"], reverse=True)

        top_risk = [c["feature_name"] for c in contributions if c["impact_direction"] == "INCREASES_DEFAULT_RISK"][:5]

        protective = [c["feature_name"] for c in contributions if c["impact_direction"] == "DECREASES_DEFAULT_RISK"][:5]

        return {
            "feature_contributions": contributions[:15],
            "base_value": round(base_val, 4),
            "top_risk_drivers": top_risk,
            "top_protective_factors": protective,
            "shap_method": "TreeExplainer",
            "models_used": len(all_shap),
        }

    except ImportError:

        logger.warning("shap library not installed. Using permutation importance fallback.")

        return _fallback_shap(X_raw, models, feature_names)


def _fallback_shap(X_raw: np.ndarray, models: dict, feature_names: list) -> dict:
    """
    Permutation importance fallback when SHAP is unavailable.
    Measures feature importance by symmetric difference in prediction when feature is zeroed.
    """

    xgb_model = models.get("xgboost")

    if xgb_model is None:
        return {
            "feature_contributions": [],
            "base_value": 0.5,
            "top_risk_drivers": [],
            "top_protective_factors": [],
            "shap_method": "none",
            "models_used": 0
        }

    base_proba = float(xgb_model.predict_proba(X_raw)[:, 1][0])

    contributions = []

    for i, name in enumerate(feature_names):

        X_perturbed = X_raw.copy()

        original = X_perturbed[0, i]

        X_perturbed[0, i] = 0

        perturbed_proba = float(xgb_model.predict_proba(X_perturbed)[:, 1][0])

        impact = base_proba - perturbed_proba

        contributions.append({
            "feature_name": str(name),
            "feature_value": round(float(original), 4),
            "shap_value": round(impact, 5),
            "abs_contribution": round(abs(impact), 5),
            "impact_direction": "INCREASES_DEFAULT_RISK" if impact > 0 else "DECREASES_DEFAULT_RISK",
            "five_c_mapping": FIVE_C_FEATURE_MAP.get(str(name), "Conditions"),
        })

    contributions.sort(key=lambda x: x["abs_contribution"], reverse=True)

    top_risk = [c["feature_name"] for c in contributions if c["impact_direction"] == "INCREASES_DEFAULT_RISK"][:5]

    protective = [c["feature_name"] for c in contributions if c["impact_direction"] == "DECREASES_DEFAULT_RISK"][:5]

    return {
        "feature_contributions": contributions[:15],
        "base_value": round(1 - base_proba, 4),
        "top_risk_drivers": top_risk,
        "top_protective_factors": protective,
        "shap_method": "permutation_importance_fallback",
        "models_used": 1,
    }