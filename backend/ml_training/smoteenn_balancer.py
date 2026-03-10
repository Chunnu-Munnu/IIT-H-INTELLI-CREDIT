"""
smoteenn_balancer.py
Handles class imbalance using SMOTEENN (SMOTE over-sampling + ENN under-sampling).
"""
import numpy as np
from loguru import logger


def balance_dataset(X: np.ndarray, y: np.ndarray) -> tuple:
    """
    Balance a binary classification dataset using SMOTEENN.
    Returns resampled (X_resampled, y_resampled).
    Falls back to class_weight if imbalanced-learn not available.
    """
    n_default = y.sum()
    n_healthy = len(y) - n_default
    ratio = n_default / len(y)
    logger.info(f"Pre-balance: {n_healthy} healthy, {n_default} default ({ratio*100:.1f}% default rate)")

    try:
        from imblearn.combine import SMOTEENN
        from imblearn.over_sampling import SMOTE
        from imblearn.under_sampling import EditedNearestNeighbours

        smoteenn = SMOTEENN(
            smote=SMOTE(
                sampling_strategy=0.4,   # Target 40% minority ratio after SMOTE
                k_neighbors=min(5, n_default - 1),
                random_state=42,
            ),
            enn=EditedNearestNeighbours(n_neighbors=3),
            random_state=42,
        )
        X_res, y_res = smoteenn.fit_resample(X, y)
        n_def_new = y_res.sum()
        logger.info(f"Post-SMOTEENN: {len(X_res)} samples, {n_def_new} default ({n_def_new/len(X_res)*100:.1f}%)")
        return X_res, y_res

    except ImportError:
        logger.warning("imbalanced-learn not installed. Using class_weight strategy instead.")
        return X, y
    except Exception as e:
        logger.warning(f"SMOTEENN failed ({e}). Returning original dataset with class_weight recommendation.")
        return X, y


def compute_class_weight(y: np.ndarray) -> dict:
    """Compute class weights for models that support it."""
    n = len(y)
    n_pos = y.sum()
    n_neg = n - n_pos
    w_neg = n / (2.0 * n_neg)
    w_pos = n / (2.0 * n_pos)
    logger.info(f"Class weights: 0={w_neg:.2f}, 1={w_pos:.2f}")
    return {0: w_neg, 1: w_pos}
