"""
data_loader.py
Multi-source dataset loader for Intelli-Credit ML training.

Priority order:
  1. Home Credit Default Risk  (Kaggle — largest, best default labels)
  2. Corporate Credit Risk     (Kaggle — direct financial ratio dataset)
  3. SME Financial Dataset     (Kaggle — SME-specific features)
  4. Synthetic fallback        (generated if NO real datasets found)

All sources are merged into one canonical feature matrix and saved as
a unified training CSV at datasets/unified_training_data.csv.
"""

import os
import numpy as np
import pandas as pd
from loguru import logger

DATASET_DIR   = os.path.join(os.path.dirname(__file__), "datasets")
SYNTHETIC_PATH     = os.path.join(DATASET_DIR, "synthetic_credit_data.csv")
UNIFIED_CACHE_PATH = os.path.join(DATASET_DIR, "unified_training_data.csv")

HC_DIR   = os.path.join(DATASET_DIR, "home_credit")
CORP_DIR = os.path.join(DATASET_DIR, "corporate_credit")
SME_DIR  = os.path.join(DATASET_DIR, "sme_credit")


def load_dataset(path: str = None, force_rebuild: bool = False) -> pd.DataFrame:
    """
    Master entry point.
    If a unified cache exists and force_rebuild=False, load it directly.
    Otherwise, load from real datasets (or synthetic) and merge.
    """
    if path and os.path.exists(path):
        logger.info(f"Loading custom dataset from {path}")
        df = pd.read_csv(path)
        _log_stats(df)
        return df

    if not force_rebuild and os.path.exists(UNIFIED_CACHE_PATH):
        logger.info(f"Loading cached unified dataset from {UNIFIED_CACHE_PATH}")
        df = pd.read_csv(UNIFIED_CACHE_PATH)
        _log_stats(df)
        return df

    logger.info("Building unified training dataset from all available sources...")
    df = _build_unified_dataset()
    _log_stats(df)
    return df


def _build_unified_dataset() -> pd.DataFrame:
    """Try real datasets first; fall back to synthetic if none found."""
    from ml_training.dataset_connectors import (
        load_home_credit,
        load_corporate_credit,
        load_sme_credit,
    )

    frames = []
    sources_used = []

    # ── Source 1: Home Credit (up to 50K rows for memory) ──────────────────
    try:
        hc = load_home_credit(sample_n=50_000)
        if not hc.empty:
            hc["_source"] = "home_credit"
            frames.append(hc)
            sources_used.append(f"home_credit ({len(hc):,} rows)")
        else:
            logger.info("Home Credit: no data returned")
    except Exception as e:
        logger.warning(f"Home Credit load failed: {e}")

    # ── Source 2: Corporate Credit ──────────────────────────────────────────
    try:
        corp = load_corporate_credit()
        if not corp.empty:
            corp["_source"] = "corporate_credit"
            frames.append(corp)
            sources_used.append(f"corporate_credit ({len(corp):,} rows)")
        else:
            logger.info("Corporate Credit: no data returned")
    except Exception as e:
        logger.warning(f"Corporate Credit load failed: {e}")

    # ── Source 3: SME ───────────────────────────────────────────────────────
    try:
        sme = load_sme_credit()
        if not sme.empty:
            sme["_source"] = "sme_credit"
            frames.append(sme)
            sources_used.append(f"sme_credit ({len(sme):,} rows)")
        else:
            logger.info("SME Credit: no data returned")
    except Exception as e:
        logger.warning(f"SME Credit load failed: {e}")

    # ── Fallback: Synthetic ─────────────────────────────────────────────────
    if not frames:
        logger.warning("No real datasets found. Generating synthetic dataset.")
        logger.warning("Download datasets from Kaggle and place in backend/ml_training/datasets/")
        synth = _generate_synthetic_dataset(n_samples=5_000)
        synth["_source"] = "synthetic"
        frames.append(synth)
        sources_used.append(f"synthetic ({len(synth):,} rows)")

    # ── Merge ───────────────────────────────────────────────────────────────
    logger.info(f"Sources loaded: {', '.join(sources_used)}")
    df = pd.concat(frames, ignore_index=True)

    # Ensure all canonical columns exist (fill missing with defaults)
    from ml_training.feature_dataset_builder import FEATURE_COLUMNS, FEATURE_DEFAULTS
    for col in FEATURE_COLUMNS:
        if col not in df.columns:
            df[col] = FEATURE_DEFAULTS.get(col, 0)

    if "default" not in df.columns:
        raise RuntimeError("No 'default' target column found after merging datasets")

    # Final clean
    df["default"] = df["default"].fillna(0).astype(int)
    df = df.dropna(subset=["default"])
    df = df.reset_index(drop=True)

    # Shuffle
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)

    # Save cache
    os.makedirs(DATASET_DIR, exist_ok=True)
    df.to_csv(UNIFIED_CACHE_PATH, index=False)
    logger.info(f"Unified dataset saved to {UNIFIED_CACHE_PATH}")

    return df


def _log_stats(df: pd.DataFrame):
    if "default" not in df.columns:
        logger.info(f"Dataset: {len(df):,} rows, {len(df.columns)} columns")
        return
    n_def = df["default"].sum()
    n_total = len(df)
    sources = df.get("_source", pd.Series()).value_counts().to_dict() if "_source" in df.columns else {}
    logger.info(f"Dataset: {n_total:,} rows | {n_def:,} defaults ({n_def/n_total*100:.1f}%) | {len(df.columns)} features")
    if sources:
        for src, cnt in sources.items():
            logger.info(f"  {src}: {cnt:,} rows")


def get_dataset_status() -> dict:
    """Check which real datasets are available."""
    status = {}

    # Home Credit
    hc_files = ["application_train.csv", "bureau.csv"]
    hc_found = [f for f in hc_files if os.path.exists(os.path.join(HC_DIR, f))]
    status["home_credit"] = {
        "available": len(hc_found) > 0,
        "path": HC_DIR,
        "files_found": hc_found,
        "files_expected": hc_files,
    }

    # Corporate
    corp_candidates = ["corporate_credit_risk.csv", "corporate_credit.csv", "credit_risk.csv"]
    corp_found = [f for f in corp_candidates if os.path.exists(os.path.join(CORP_DIR, f))]
    status["corporate_credit"] = {
        "available": len(corp_found) > 0,
        "path": CORP_DIR,
        "files_found": corp_found,
        "files_expected": corp_candidates[:1],
    }

    # SME
    sme_found = []
    if os.path.exists(SME_DIR):
        sme_found = [f for f in os.listdir(SME_DIR) if f.endswith(".csv")]
    status["sme_credit"] = {
        "available": len(sme_found) > 0,
        "path": SME_DIR,
        "files_found": sme_found,
        "files_expected": ["sme_financial_decision_dataset.csv"],
    }

    status["unified_cache"] = {
        "available": os.path.exists(UNIFIED_CACHE_PATH),
        "path": UNIFIED_CACHE_PATH,
    }

    any_real = any(v["available"] for k, v in status.items() if k != "unified_cache")
    status["training_ready"] = any_real or status["unified_cache"]["available"]
    status["uses_real_data"] = any_real

    return status


# ─── Synthetic Fallback (unchanged logic, kept here for self-containment) ─────

def _generate_synthetic_dataset(n_samples: int = 5000, default_rate: float = 0.18, seed: int = 42) -> pd.DataFrame:
    """
    Realistic synthetic fallback.
    Calibrated to RBI NPA statistics for Indian corporate loans.
    """
    rng = np.random.default_rng(seed)
    n_default = int(n_samples * default_rate)
    n_healthy  = n_samples - n_default

    def _sample(is_default: bool, n: int) -> dict:
        if not is_default:
            return dict(
                dscr_fy1=rng.uniform(1.3, 3.5, n),      dscr_fy2=rng.uniform(1.2, 3.0, n),      dscr_fy3=rng.uniform(1.1, 2.8, n),
                ebitda_margin_fy1=rng.uniform(0.10, 0.35, n), ebitda_margin_fy2=rng.uniform(0.09, 0.32, n), ebitda_margin_fy3=rng.uniform(0.08, 0.30, n),
                pat_margin_fy1=rng.uniform(0.04, 0.18, n), pat_margin_fy2=rng.uniform(0.03, 0.16, n),
                interest_coverage_fy1=rng.uniform(2.5, 8.0, n), interest_coverage_fy2=rng.uniform(2.0, 7.0, n),
                debt_equity_fy1=rng.uniform(0.3, 2.5, n),  debt_equity_fy2=rng.uniform(0.3, 2.8, n),  debt_equity_fy3=rng.uniform(0.3, 3.0, n),
                tol_tnw_fy1=rng.uniform(0.5, 3.5, n),      tol_tnw_fy2=rng.uniform(0.5, 4.0, n),
                current_ratio_fy1=rng.uniform(1.1, 3.5, n), current_ratio_fy2=rng.uniform(1.0, 3.0, n),
                quick_ratio_fy1=rng.uniform(0.8, 2.5, n),
                debtor_days_fy1=rng.uniform(30, 90, n),   debtor_days_fy2=rng.uniform(35, 100, n),
                creditor_days_fy1=rng.uniform(20, 80, n), inventory_days_fy1=rng.uniform(20, 90, n),
                roce_fy1=rng.uniform(0.10, 0.28, n),      roce_fy2=rng.uniform(0.08, 0.25, n),
                asset_turnover_fy1=rng.uniform(0.6, 2.0, n), revenue_growth_fy1=rng.uniform(-0.02, 0.20, n),
                gst_compliance_score=rng.uniform(7, 10, n), gst_bank_inflation_ratio=rng.uniform(0.9, 1.3, n),
                itc_inflation_flag=rng.binomial(1, 0.05, n), circular_trading_flag=rng.binomial(1, 0.03, n),
                window_dressing_flag=rng.binomial(1, 0.08, n), undisclosed_borrowing_flag=rng.binomial(1, 0.02, n),
                nach_bounce_count=rng.integers(0, 2, n),
                going_concern_flag=rng.binomial(1, 0.01, n), director_cirp_linked=rng.binomial(1, 0.02, n),
                drt_case_count=rng.integers(0, 1, n), nclt_case_count=rng.integers(0, 1, n),
                mca_compliance_score=rng.uniform(7, 10, n), director_risk_score=rng.uniform(0, 3, n),
                company_age_score=rng.uniform(6, 10, n), auditor_opinion_score=rng.uniform(7, 10, n),
                rating_direction=rng.choice([-1, 0, 1], n, p=[0.05, 0.80, 0.15]),
                network_risk_score=rng.uniform(0, 4, n), supplier_default_risk=rng.uniform(0, 3, n),
                promoter_network_risk=rng.uniform(0, 3, n), negative_news_score=rng.uniform(0, 2, n),
                litigation_count=rng.integers(0, 2, n), regulatory_risk_score=rng.uniform(0, 2, n),
                sector_risk_score=rng.integers(2, 7, n), total_ews_score_deduction=rng.uniform(0, 20, n),
                ews_character_flags=rng.integers(0, 2, n), ews_capacity_flags=rng.integers(0, 2, n),
                ews_capital_flags=rng.integers(0, 2, n), ews_conditions_flags=rng.integers(0, 2, n),
                collateral_type_score=rng.integers(2, 5, n), security_coverage_ratio=rng.uniform(1.2, 3.0, n),
                default=np.zeros(n, dtype=int),
            )
        else:
            return dict(
                dscr_fy1=rng.uniform(0.3, 1.2, n),      dscr_fy2=rng.uniform(0.4, 1.3, n),      dscr_fy3=rng.uniform(0.5, 1.5, n),
                ebitda_margin_fy1=rng.uniform(-0.05, 0.12, n), ebitda_margin_fy2=rng.uniform(-0.03, 0.14, n), ebitda_margin_fy3=rng.uniform(0.00, 0.15, n),
                pat_margin_fy1=rng.uniform(-0.10, 0.05, n), pat_margin_fy2=rng.uniform(-0.08, 0.06, n),
                interest_coverage_fy1=rng.uniform(0.5, 2.0, n), interest_coverage_fy2=rng.uniform(0.8, 2.5, n),
                debt_equity_fy1=rng.uniform(2.5, 8.0, n),  debt_equity_fy2=rng.uniform(2.0, 7.0, n),  debt_equity_fy3=rng.uniform(1.8, 6.0, n),
                tol_tnw_fy1=rng.uniform(3.5, 10.0, n),     tol_tnw_fy2=rng.uniform(3.0, 9.0, n),
                current_ratio_fy1=rng.uniform(0.4, 1.1, n), current_ratio_fy2=rng.uniform(0.5, 1.2, n),
                quick_ratio_fy1=rng.uniform(0.2, 0.9, n),
                debtor_days_fy1=rng.uniform(90, 200, n),  debtor_days_fy2=rng.uniform(80, 180, n),
                creditor_days_fy1=rng.uniform(80, 180, n), inventory_days_fy1=rng.uniform(90, 250, n),
                roce_fy1=rng.uniform(-0.05, 0.08, n),     roce_fy2=rng.uniform(-0.03, 0.10, n),
                asset_turnover_fy1=rng.uniform(0.2, 0.8, n), revenue_growth_fy1=rng.uniform(-0.25, 0.05, n),
                gst_compliance_score=rng.uniform(2, 7, n), gst_bank_inflation_ratio=rng.uniform(1.3, 3.5, n),
                itc_inflation_flag=rng.binomial(1, 0.55, n), circular_trading_flag=rng.binomial(1, 0.40, n),
                window_dressing_flag=rng.binomial(1, 0.45, n), undisclosed_borrowing_flag=rng.binomial(1, 0.35, n),
                nach_bounce_count=rng.integers(1, 8, n),
                going_concern_flag=rng.binomial(1, 0.45, n), director_cirp_linked=rng.binomial(1, 0.30, n),
                drt_case_count=rng.integers(0, 4, n), nclt_case_count=rng.integers(0, 3, n),
                mca_compliance_score=rng.uniform(1, 6, n), director_risk_score=rng.uniform(3, 9, n),
                company_age_score=rng.uniform(2, 7, n), auditor_opinion_score=rng.uniform(1, 6, n),
                rating_direction=rng.choice([-1, 0, 1], n, p=[0.50, 0.40, 0.10]),
                network_risk_score=rng.uniform(3, 9, n), supplier_default_risk=rng.uniform(3, 9, n),
                promoter_network_risk=rng.uniform(4, 10, n), negative_news_score=rng.uniform(2, 8, n),
                litigation_count=rng.integers(1, 6, n), regulatory_risk_score=rng.uniform(3, 9, n),
                sector_risk_score=rng.integers(5, 10, n), total_ews_score_deduction=rng.uniform(25, 100, n),
                ews_character_flags=rng.integers(1, 5, n), ews_capacity_flags=rng.integers(1, 4, n),
                ews_capital_flags=rng.integers(1, 4, n), ews_conditions_flags=rng.integers(1, 5, n),
                collateral_type_score=rng.integers(0, 3, n), security_coverage_ratio=rng.uniform(0.5, 1.3, n),
                default=np.ones(n, dtype=int),
            )

    h = pd.DataFrame(_sample(False, n_healthy))
    d = pd.DataFrame(_sample(True, n_default))
    df = pd.concat([h, d], ignore_index=True).sample(frac=1, random_state=seed).reset_index(drop=True)

    # Light noise
    for col in df.select_dtypes(include=[np.floating]).columns:
        if col != "default" and col not in ("gst_bank_inflation_ratio",):
            df[col] += rng.normal(0, df[col].std() * 0.03, len(df))

    logger.info(f"Generated {len(df)} synthetic samples ({default_rate*100:.0f}% default rate)")
    return df
