"""
hyperparameter_tuner.py
Optuna-based hyperparameter tuning for XGBoost, LightGBM, CatBoost.
"""
import numpy as np
from loguru import logger
from sklearn.model_selection import StratifiedKFold, cross_val_score


def tune_xgboost(X: np.ndarray, y: np.ndarray, n_trials: int = 40) -> dict:
    try:
        import optuna
        import xgboost as xgb
        optuna.logging.set_verbosity(optuna.logging.WARNING)

        def objective(trial):
            params = {
                "n_estimators": trial.suggest_int("n_estimators", 200, 800),
                "max_depth": trial.suggest_int("max_depth", 3, 8),
                "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
                "subsample": trial.suggest_float("subsample", 0.6, 1.0),
                "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
                "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
                "gamma": trial.suggest_float("gamma", 0.0, 1.0),
                "reg_alpha": trial.suggest_float("reg_alpha", 1e-4, 10.0, log=True),
                "reg_lambda": trial.suggest_float("reg_lambda", 1e-4, 10.0, log=True),
                "scale_pos_weight": (len(y) - y.sum()) / y.sum(),
                "eval_metric": "auc",
                "random_state": 42,
                "n_jobs": -1,
            }
            model = xgb.XGBClassifier(**params)
            cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
            scores = cross_val_score(model, X, y, cv=cv, scoring="roc_auc", n_jobs=-1)
            return scores.mean()

        study = optuna.create_study(direction="maximize")
        study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
        best = study.best_params
        best["scale_pos_weight"] = (len(y) - y.sum()) / y.sum()
        best["eval_metric"] = "auc"
        best["random_state"] = 42
        logger.info(f"XGBoost best AUC: {study.best_value:.4f} | params: {study.best_params}")
        return best

    except ImportError:
        logger.warning("optuna not installed — using default XGBoost params")
        return _default_xgb_params(y)


def tune_lightgbm(X: np.ndarray, y: np.ndarray, n_trials: int = 40) -> dict:
    try:
        import optuna
        import lightgbm as lgb
        optuna.logging.set_verbosity(optuna.logging.WARNING)

        def objective(trial):
            params = {
                "n_estimators": trial.suggest_int("n_estimators", 200, 800),
                "num_leaves": trial.suggest_int("num_leaves", 20, 150),
                "max_depth": trial.suggest_int("max_depth", 3, 10),
                "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
                "subsample": trial.suggest_float("subsample", 0.5, 1.0),
                "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
                "min_child_samples": trial.suggest_int("min_child_samples", 10, 60),
                "reg_alpha": trial.suggest_float("reg_alpha", 1e-4, 10.0, log=True),
                "reg_lambda": trial.suggest_float("reg_lambda", 1e-4, 10.0, log=True),
                "is_unbalance": True,
                "random_state": 42,
                "n_jobs": -1,
                "verbose": -1,
            }
            model = lgb.LGBMClassifier(**params)
            cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
            scores = cross_val_score(model, X, y, cv=cv, scoring="roc_auc", n_jobs=-1)
            return scores.mean()

        study = optuna.create_study(direction="maximize")
        study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
        best = study.best_params
        best.update({"is_unbalance": True, "random_state": 42, "verbose": -1})
        logger.info(f"LightGBM best AUC: {study.best_value:.4f}")
        return best

    except ImportError:
        logger.warning("optuna not installed — using default LightGBM params")
        return _default_lgbm_params()


def tune_catboost(X: np.ndarray, y: np.ndarray, n_trials: int = 30) -> dict:
    try:
        import optuna
        from catboost import CatBoostClassifier
        optuna.logging.set_verbosity(optuna.logging.WARNING)

        def objective(trial):
            params = {
                "iterations": trial.suggest_int("iterations", 200, 600),
                "depth": trial.suggest_int("depth", 3, 8),
                "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
                "l2_leaf_reg": trial.suggest_float("l2_leaf_reg", 1.0, 20.0),
                "bagging_temperature": trial.suggest_float("bagging_temperature", 0.0, 1.5),
                "auto_class_weights": "Balanced",
                "random_seed": 42,
                "verbose": 0,
            }
            model = CatBoostClassifier(**params)
            cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
            scores = cross_val_score(model, X, y, cv=cv, scoring="roc_auc", n_jobs=1)
            return scores.mean()

        study = optuna.create_study(direction="maximize")
        study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
        best = study.best_params
        best.update({"auto_class_weights": "Balanced", "random_seed": 42, "verbose": 0})
        logger.info(f"CatBoost best AUC: {study.best_value:.4f}")
        return best

    except ImportError:
        logger.warning("optuna not installed — using default CatBoost params")
        return _default_catboost_params()


def _default_xgb_params(y) -> dict:
    scale = (len(y) - y.sum()) / max(y.sum(), 1)
    return {
        "n_estimators": 400, "max_depth": 5, "learning_rate": 0.05,
        "subsample": 0.8, "colsample_bytree": 0.8, "min_child_weight": 3,
        "gamma": 0.1, "reg_alpha": 0.5, "reg_lambda": 1.0,
        "scale_pos_weight": scale, "eval_metric": "auc",
        "random_state": 42,
    }


def _default_lgbm_params() -> dict:
    return {
        "n_estimators": 400, "num_leaves": 63, "max_depth": -1,
        "learning_rate": 0.05, "subsample": 0.8, "colsample_bytree": 0.8,
        "min_child_samples": 20, "is_unbalance": True,
        "random_state": 42, "verbose": -1,
    }


def _default_catboost_params() -> dict:
    return {
        "iterations": 400, "depth": 6, "learning_rate": 0.05,
        "l2_leaf_reg": 5.0, "bagging_temperature": 0.5,
        "auto_class_weights": "Balanced", "random_seed": 42, "verbose": 0,
    }
