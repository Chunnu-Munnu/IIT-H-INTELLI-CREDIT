"""
model_store.py — Loads, saves, and runs inference on trained ensemble models.
No rule-based fallback. Falls back gracefully with clear error if models missing.
"""
import os
import json
import numpy as np
import pandas as pd
import joblib
from loguru import logger

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "models")


class ModelStore:

    def __init__(self):
        self._models = None
        self._feature_names = None
        self._metadata = None

    def load_latest(self) -> dict | None:
        meta_path = os.path.join(MODEL_DIR, "model_metadata.json")
        if not os.path.exists(meta_path):
            logger.warning(f"No model_metadata.json at {MODEL_DIR}. Run ml_training/run_training.py first.")
            return None

        with open(meta_path) as f:
            meta = json.load(f)

        version = meta["version"]
        models = {}

        for name in meta.get("model_names", []):
            path = os.path.join(MODEL_DIR, f"{name}_v{version}.joblib")
            if os.path.exists(path):
                models[name] = joblib.load(path)
                logger.debug(f"Loaded {name} from {path}")
            else:
                logger.warning(f"Model file missing: {path}")

        meta_path_model = os.path.join(MODEL_DIR, f"meta_learner_v{version}.joblib")
        if os.path.exists(meta_path_model):
            meta_artifact = joblib.load(meta_path_model)
            # Support both old (direct model) and new (dict with meta+calibrator) formats
            if isinstance(meta_artifact, dict):
                models["meta_learner"]    = meta_artifact["meta"]
                models["meta_calibrator"] = meta_artifact.get("calibrator")
                models["threshold"]       = meta_artifact.get("threshold", 0.5)
            else:
                models["meta_learner"]    = meta_artifact
                models["meta_calibrator"] = None
                models["threshold"]       = 0.5

        feat_path = os.path.join(MODEL_DIR, "feature_names.joblib")
        if os.path.exists(feat_path):
            models["feature_names"] = joblib.load(feat_path)

        scaler_path = os.path.join(MODEL_DIR, "scaler.joblib")
        if os.path.exists(scaler_path):
            models["scaler"] = joblib.load(scaler_path)

        self._models = models
        self._metadata = meta
        logger.info(f"Loaded ensemble v{version} | Val AUC: {meta.get('val_auc', '?')}")
        return models

    def predict_proba(self, features: dict, models: dict) -> dict:
        """
        Full inference pipeline.
        features: raw feature_vector dict from MongoDB
        Returns: dict with default_probability, credit_score, risk_grade, SHAP inputs
        """
        from app.constants import CREDIT_GRADE_THRESHOLDS

        # Build feature row
        feature_names = models.get("feature_names", [])
        scaler = models.get("scaler")

        # Import builder for feature engineering
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
        from ml_training.feature_dataset_builder import FeatureDatasetBuilder, FEATURE_DEFAULTS

        df = pd.DataFrame([features])
        builder = FeatureDatasetBuilder()
        # Manually apply feature engineering
        X_raw, _, _ = builder.build(df)

        if scaler is not None:
            X = scaler.transform(X_raw)
        else:
            X = X_raw

        # Base model probabilities
        base_preds = {}
        for name in ["xgboost", "lightgbm", "catboost"]:
            model = models.get(name)
            if model:
                try:
                    proba = float(model.predict_proba(X)[:, 1][0])
                    base_preds[name] = round(proba, 4)
                except Exception as e:
                    logger.warning(f"{name} predict failed: {e}")

        if not base_preds:
            raise RuntimeError("All base models failed to predict")

        # Meta-learner prediction + isotonic calibration
        meta_model   = models.get("meta_learner")
        meta_cal     = models.get("meta_calibrator")
        meta_input   = np.array([[base_preds.get(n, 0.5) for n in ["xgboost", "lightgbm", "catboost"]]])

        if meta_model:
            raw_proba = float(meta_model.predict_proba(meta_input)[:, 1][0])
            if meta_cal is not None:
                final_proba = float(np.clip(meta_cal.predict([raw_proba]), 0, 1)[0])
            else:
                final_proba = raw_proba
        else:
            final_proba = float(np.mean(list(base_preds.values())))

        # Credit score (300-850 scale, inversely proportional to default probability)
        score = max(0.0, min(100.0, (1 - final_proba) * 100.0))
        credit_score = int(300 + score * 5.5)

        # Binary default call using optimal threshold
        decision_threshold = models.get("threshold", 0.5)
        is_default_predicted = bool(final_proba >= decision_threshold)

        # Grade
        risk_grade = "D"
        for grade, (low, high) in CREDIT_GRADE_THRESHOLDS.items():
            if low <= score <= high:
                risk_grade = grade
                break

        return {
            "default_probability": round(final_proba, 4),
            "credit_score": credit_score,
            "risk_grade": risk_grade,
            "composite_score": round(score, 1),
            "base_model_probas": base_preds,
            "meta_model_proba": round(final_proba, 4),
            "X_raw": X_raw,
            "feature_names": feature_names or [],
        }
