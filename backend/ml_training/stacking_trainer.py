"""
stacking_trainer.py
Full stacking ensemble training pipeline:
  Base models: XGBoost, LightGBM, CatBoost
  Meta-learner: RandomForestClassifier
  Calibration: CalibratedClassifierCV (isotonic)
  Evaluation: ROC-AUC, PR-AUC, Brier score, KS statistic
"""
import os
import json
import numpy as np
import joblib
from datetime import datetime
from loguru import logger
from sklearn.model_selection import StratifiedKFold
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    roc_auc_score, average_precision_score,
    brier_score_loss, classification_report,
    confusion_matrix,
)

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "models")


def ks_statistic(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    from scipy.stats import ks_2samp
    pos = y_prob[y_true == 1]
    neg = y_prob[y_true == 0]
    return ks_2samp(pos, neg).statistic


def train_and_save(X_train: np.ndarray, y_train: np.ndarray,
                   X_val: np.ndarray, y_val: np.ndarray,
                   xgb_params: dict, lgbm_params: dict, cat_params: dict,
                   feature_names: list) -> dict:

    os.makedirs(MODEL_DIR, exist_ok=True)
    version = datetime.now().strftime("%Y%m%d_%H%M%S")
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    base_names = ["xgboost", "lightgbm", "catboost"]
    reports = {}

    # ── Base Models ──────────────────────────────────────────────────────────
    base_train_preds = {}  # OOF predictions for meta-learner training
    base_val_preds = {}

    # XGBoost
    logger.info("Training XGBoost...")
    import xgboost as xgb
    xgb_model = xgb.XGBClassifier(**xgb_params)
    oof_xgb = np.zeros(len(X_train))
    for fold, (tr_idx, val_idx) in enumerate(cv.split(X_train, y_train)):
        xgb_fold = xgb.XGBClassifier(**xgb_params)
        xgb_fold.fit(X_train[tr_idx], y_train[tr_idx], eval_set=[(X_train[val_idx], y_train[val_idx])], verbose=False)
        oof_xgb[val_idx] = xgb_fold.predict_proba(X_train[val_idx])[:, 1]
    xgb_model.fit(X_train, y_train)
    base_train_preds["xgboost"] = oof_xgb
    base_val_preds["xgboost"] = xgb_model.predict_proba(X_val)[:, 1]
    auc = roc_auc_score(y_val, base_val_preds["xgboost"])
    reports["xgboost"] = {"val_auc": round(float(auc), 4)}
    logger.info(f"XGBoost Val AUC: {auc:.4f}")

    # LightGBM
    logger.info("Training LightGBM...")
    import lightgbm as lgb
    lgbm_model = lgb.LGBMClassifier(**lgbm_params)
    oof_lgbm = np.zeros(len(X_train))
    for fold, (tr_idx, val_idx) in enumerate(cv.split(X_train, y_train)):
        lgbm_fold = lgb.LGBMClassifier(**lgbm_params)
        lgbm_fold.fit(X_train[tr_idx], y_train[tr_idx],
                      eval_set=[(X_train[val_idx], y_train[val_idx])],
                      callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(-1)])
        oof_lgbm[val_idx] = lgbm_fold.predict_proba(X_train[val_idx])[:, 1]
    lgbm_model.fit(X_train, y_train, callbacks=[lgb.log_evaluation(-1)])
    base_train_preds["lightgbm"] = oof_lgbm
    base_val_preds["lightgbm"] = lgbm_model.predict_proba(X_val)[:, 1]
    auc = roc_auc_score(y_val, base_val_preds["lightgbm"])
    reports["lightgbm"] = {"val_auc": round(float(auc), 4)}
    logger.info(f"LightGBM Val AUC: {auc:.4f}")

    # CatBoost
    logger.info("Training CatBoost...")
    from catboost import CatBoostClassifier
    cat_model = CatBoostClassifier(**cat_params)
    oof_cat = np.zeros(len(X_train))
    for fold, (tr_idx, val_idx) in enumerate(cv.split(X_train, y_train)):
        cat_fold = CatBoostClassifier(**cat_params)
        cat_fold.fit(X_train[tr_idx], y_train[tr_idx], eval_set=(X_train[val_idx], y_train[val_idx]), verbose=False)
        oof_cat[val_idx] = cat_fold.predict_proba(X_train[val_idx])[:, 1]
    cat_model.fit(X_train, y_train, verbose=False)
    base_train_preds["catboost"] = oof_cat
    base_val_preds["catboost"] = cat_model.predict_proba(X_val)[:, 1]
    auc = roc_auc_score(y_val, base_val_preds["catboost"])
    reports["catboost"] = {"val_auc": round(float(auc), 4)}
    logger.info(f"CatBoost Val AUC: {auc:.4f}")

    # ── Meta-Learner ─────────────────────────────────────────────────────────
    logger.info("Training meta-learner (RandomForest on OOF predictions)...")
    meta_X_train = np.column_stack([base_train_preds[n] for n in base_names])
    meta_X_val   = np.column_stack([base_val_preds[n]   for n in base_names])

    meta_model = RandomForestClassifier(
        n_estimators=200, max_depth=4, class_weight="balanced",
        random_state=42, n_jobs=-1,
    )
    meta_model.fit(meta_X_train, y_train)
    final_proba_val = meta_model.predict_proba(meta_X_val)[:, 1]

    # ── Calibration (isotonic regression on held-out val set) ──────────────
    logger.info("Calibrating ensemble probabilities (isotonic regression)...")
    from sklearn.isotonic import IsotonicRegression
    iso_reg = IsotonicRegression(out_of_bounds='clip')
    iso_reg.fit(final_proba_val, y_val)
    final_proba_cal = iso_reg.predict(final_proba_val).clip(0, 1)

    # ── Evaluation ───────────────────────────────────────────────────────────
    val_auc  = roc_auc_score(y_val, final_proba_cal)
    val_pr   = average_precision_score(y_val, final_proba_cal)
    val_bs   = brier_score_loss(y_val, final_proba_cal)
    try:
        val_ks = ks_statistic(y_val, final_proba_cal)
    except Exception:
        val_ks = 0.0

    # ── Optimal Threshold (Youden's J: maximise TPR - FPR) ─────────────────
    from sklearn.metrics import roc_curve
    fpr_arr, tpr_arr, thresh_arr = roc_curve(y_val, final_proba_cal)
    youden_j = tpr_arr - fpr_arr
    optimal_idx = int(np.argmax(youden_j))
    optimal_threshold = float(thresh_arr[optimal_idx])
    optimal_threshold = round(max(0.05, min(0.7, optimal_threshold)), 4)  # sanity clip
    logger.info(f"Optimal threshold (Youden J): {optimal_threshold:.4f}  "
                f"(TPR={tpr_arr[optimal_idx]:.3f}, FPR={fpr_arr[optimal_idx]:.3f})")

    threshold = optimal_threshold
    y_pred = (final_proba_cal >= threshold).astype(int)

    logger.info(f"\n{'='*50}")
    logger.info(f"ENSEMBLE FINAL VALIDATION RESULTS (v{version})")
    logger.info(f"ROC-AUC  : {val_auc:.4f}")
    logger.info(f"PR-AUC   : {val_pr:.4f}")
    logger.info(f"Brier    : {val_bs:.4f}")
    logger.info(f"KS stat  : {val_ks:.4f}")
    logger.info(f"\n{classification_report(y_val, y_pred, target_names=['Healthy','Default'])}")
    logger.info(f"Confusion Matrix:\n{confusion_matrix(y_val, y_pred)}")

    logger.info(f"Saving models to {MODEL_DIR} ...")
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(xgb_model,  os.path.join(MODEL_DIR, f"xgboost_v{version}.joblib"))
    joblib.dump(lgbm_model, os.path.join(MODEL_DIR, f"lightgbm_v{version}.joblib"))
    joblib.dump(cat_model,  os.path.join(MODEL_DIR, f"catboost_v{version}.joblib"))
    # Save optimal threshold alongside meta-learner
    joblib.dump({"meta": meta_model, "calibrator": iso_reg, "threshold": optimal_threshold},
                os.path.join(MODEL_DIR, f"meta_learner_v{version}.joblib"))
    joblib.dump(feature_names, os.path.join(MODEL_DIR, "feature_names.joblib"))

    # Save feature importances (average of all base models)
    fi = {}
    try:
        fi["xgboost"]  = dict(zip(feature_names, xgb_model.feature_importances_.tolist()))
        fi["lightgbm"] = dict(zip(feature_names, lgbm_model.feature_importances_.tolist()))
    except Exception:
        pass

    metadata = {
        "version": version,
        "train_date": datetime.now().isoformat(),
        "model_names": ["xgboost", "lightgbm", "catboost"],
        "meta_learner": "meta_learner",
        "val_auc": round(float(val_auc), 4),
        "val_pr_auc": round(float(val_pr), 4),
        "val_brier": round(float(val_bs), 4),
        "val_ks": round(float(val_ks), 4),
        "optimal_threshold": optimal_threshold,
        "base_model_aucs": {k: v["val_auc"] for k, v in reports.items()},
        "feature_importances": fi,
        "n_features": len(feature_names),
    }

    with open(os.path.join(MODEL_DIR, "model_metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Models saved OK. Ensemble Val AUC = {val_auc:.4f}")
    return metadata
