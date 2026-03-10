#!/usr/bin/env python3
"""
run_training.py — Intelli-Credit ML Ensemble Training Entry Point

Usage:
    python run_training.py --status          (check which datasets are available)
    python run_training.py --no-tune         (fast training, ~2 min)
    python run_training.py --tune            (full Optuna tuning, ~5-10 min)
    python run_training.py --rebuild         (force rebuild unified dataset cache)
    python run_training.py --dataset custom.csv  (use a specific CSV)
"""
import sys
import os
import argparse
import numpy as np
from datetime import datetime
from sklearn.model_selection import train_test_split
from loguru import logger

logger.remove()
logger.add(sys.stdout, format="<cyan>{time:HH:mm:ss}</cyan> | <level>{level: <8}</level> | {message}", level="INFO")
logger.add(os.path.join(os.path.dirname(__file__), "..", "..", "logs", "training.log"),
           rotation="10 MB", level="DEBUG", backtrace=True)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def show_status():
    """Print dataset availability report."""
    from ml_training.data_loader import get_dataset_status
    status = get_dataset_status()

    print("\n" + "=" * 60)
    print("    Intelli-Credit Dataset Status Report")
    print("=" * 60)

    for key, info in status.items():
        if key in ("training_ready", "uses_real_data"):
            continue
        avail = info.get("available", False)
        icon = "[OK]" if avail else "[X] "
        print(f"\n  {icon} {key}")
        print(f"      Path: {info.get('path', info.get('path', ''))}")
        if "files_found" in info:
            if info["files_found"]:
                print(f"      Found: {', '.join(info['files_found'])}")
            else:
                expected = info.get("files_expected", [])
                print(f"      Missing: {', '.join(expected)}")

    print()
    print(f"  Training ready  : {'YES' if status['training_ready'] else 'NO'}")
    print(f"  Uses real data  : {'YES' if status['uses_real_data'] else 'NO -- will use synthetic fallback'}")
    print("=" * 60)

    if not status["uses_real_data"]:
        print("\n  To use real data, download from Kaggle:")
        print("  1. Home Credit: https://www.kaggle.com/c/home-credit-default-risk/data")
        print("     -> backend/ml_training/datasets/home_credit/application_train.csv")
        print("  2. Corporate:   https://www.kaggle.com/datasets/yashsaxena005/corporate-credit-risk")
        print("     -> backend/ml_training/datasets/corporate_credit/corporate_credit_risk.csv")
        print("  3. SME:         https://www.kaggle.com/datasets/examsgovt/sme-financial-decision-risk-prediction-dataset")
        print("     -> backend/ml_training/datasets/sme_credit/sme_financial_decision_dataset.csv")
        print()


def main():
    parser = argparse.ArgumentParser(description="Intelli-Credit ML Training Pipeline")
    parser.add_argument("--status",    action="store_true", help="Show dataset availability status")
    parser.add_argument("--no-tune",   action="store_true", help="Use default hyperparameters (fast, ~2 min)")
    parser.add_argument("--tune",      action="store_true", help="Full Optuna tuning (~5-10 min)")
    parser.add_argument("--trials",    type=int, default=30, help="Optuna trials per model (default: 30)")
    parser.add_argument("--dataset",   type=str, default=None, help="Path to custom CSV dataset")
    parser.add_argument("--rebuild",   action="store_true", help="Force rebuild unified dataset cache")
    parser.add_argument("--sample",    type=int, default=None, help="Subsample N rows from merged data")
    args = parser.parse_args()

    if args.status:
        show_status()
        return

    logger.info("══════════════════════════════════════════════════════════")
    logger.info("   Intelli-Credit ML Ensemble Training Pipeline")
    logger.info(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("══════════════════════════════════════════════════════════")

    # ── Step 0: Dataset status ─────────────────────────────────────────────
    from ml_training.data_loader import get_dataset_status
    status = get_dataset_status()
    if status["uses_real_data"]:
        logger.info("✓ Real Kaggle datasets found — training on real data")
    else:
        logger.warning("No real datasets found — training on synthetic data")
        logger.warning("Download Kaggle datasets to backend/ml_training/datasets/ for production training")

    # ── Step 1: Load data ──────────────────────────────────────────────────
    from ml_training.data_loader import load_dataset
    df = load_dataset(args.dataset, force_rebuild=args.rebuild)

    if args.sample and args.sample < len(df):
        from sklearn.model_selection import train_test_split as _tts
        # Use train_test_split as a stratified sampler
        df, _ = _tts(df, train_size=args.sample, stratify=df["default"], random_state=42)
        df = df.reset_index(drop=True)
        logger.info(f"Subsampled to {len(df):,} rows")

    # ── Step 2: Build feature matrix ────────────────────────────────────────
    from ml_training.feature_dataset_builder import FeatureDatasetBuilder
    builder = FeatureDatasetBuilder()
    X, y, feat_names = builder.fit_transform(df)
    logger.info(f"Feature matrix: {X.shape} | Canonical features: {len(feat_names)}")

    # ── Step 3: Train/val split ────────────────────────────────────────────
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.20, stratify=y, random_state=42
    )
    logger.info(f"Split: train={X_train.shape[0]:,} val={X_val.shape[0]:,} "
                f"| train default rate: {y_train.mean()*100:.1f}%")

    # ── Step 4: SMOTEENN balancing ─────────────────────────────────────────
    from ml_training.smoteenn_balancer import balance_dataset, compute_class_weight
    X_bal, y_bal = balance_dataset(X_train, y_train)
    cw = compute_class_weight(y_bal)

    # ── Step 5: Hyperparameter tuning / defaults ───────────────────────────
    from ml_training.hyperparameter_tuner import (
        tune_xgboost, tune_lightgbm, tune_catboost,
        _default_xgb_params, _default_lgbm_params, _default_catboost_params,
    )

    use_tuning = args.tune and not args.no_tune
    n_trials = args.trials

    if use_tuning:
        logger.info(f"Running Optuna hyperparameter tuning ({n_trials} trials per model)...")
        xgb_params  = tune_xgboost(X_bal, y_bal, n_trials=n_trials)
        lgbm_params = tune_lightgbm(X_bal, y_bal, n_trials=n_trials)
        cat_params  = tune_catboost(X_bal, y_bal, n_trials=max(n_trials // 2, 15))
    else:
        mode = "default params" if args.no_tune else "default params (use --tune for Optuna)"
        logger.info(f"Using {mode}...")
        xgb_params  = _default_xgb_params(y_bal)
        lgbm_params = _default_lgbm_params()
        cat_params  = _default_catboost_params()

    # ── Step 6: Train stacking ensemble & save ─────────────────────────────
    from ml_training.stacking_trainer import train_and_save
    metadata = train_and_save(
        X_bal, y_bal, X_val, y_val,
        xgb_params, lgbm_params, cat_params,
        feat_names,
    )

    # ── Step 7: Summary ─────────────────────────────────────────────────────
    model_dir = os.path.join(os.path.dirname(__file__), "..", "data", "models")
    logger.info("\n" + "=" * 60)
    logger.info("  TRAINING COMPLETE")
    logger.info("=" * 60)
    logger.info(f"  Model version  : {metadata['version']}")
    logger.info(f"  Dataset rows   : {len(df):,} total ({y.sum():,} defaults)")
    logger.info(f"  Real data used : {'Yes' if status['uses_real_data'] else 'No (synthetic)'}")
    logger.info(f"  Ensemble Val AUC  : {metadata['val_auc']:.4f}")
    logger.info(f"  PR-AUC            : {metadata['val_pr_auc']:.4f}")
    logger.info(f"  Brier Score       : {metadata['val_brier']:.4f}")
    logger.info(f"  KS Statistic      : {metadata['val_ks']:.4f}")
    logger.info(f"\n  Base model AUCs:")
    for name, auc in metadata.get("base_model_aucs", {}).items():
        logger.info(f"    {name:<12}: {auc:.4f}")
    logger.info(f"\n  Models saved to: {os.path.abspath(model_dir)}")
    logger.info("=" * 60)

    # Trigger API model reload if server is running
    _try_reload_api()


def _try_reload_api():
    """Signal FastAPI server to reload models (if running)."""
    try:
        import httpx
        r = httpx.post("http://127.0.0.1:8000/internal/reload-models", timeout=3)
        if r.status_code == 200:
            logger.info("✓ API server reloaded models successfully")
    except Exception:
        pass  # Server not running, that's fine


if __name__ == "__main__":
    main()
