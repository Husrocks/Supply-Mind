"""
SupplyMind — Data Drift Detection Monitor
Runs statistical tests (KS-test for numericals, Chi-Square for categoricals)
to identify shifts in input feature distributions between training and serving data.
"""

from __future__ import annotations

import logging
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import ks_2samp, chi2_contingency

logger = logging.getLogger(__name__)

def check_numerical_drift(reference: pd.Series, current: pd.Series, alpha: float = 0.05) -> dict:
    """Run Kolmogorov-Smirnov test on numerical features."""
    stat, p_val = ks_2samp(reference.dropna(), current.dropna())
    return {
        "statistic": float(stat),
        "p_value": float(p_val),
        "drift_detected": bool(p_val < alpha)
    }

def check_categorical_drift(reference: pd.Series, current: pd.Series, alpha: float = 0.05) -> dict:
    """Run Chi-Square contingency test on categorical features."""
    ref_counts = reference.value_counts()
    cur_counts = current.value_counts()
    
    # Align classes
    all_classes = list(set(ref_counts.index).union(set(cur_counts.index)))
    ref_aligned = [ref_counts.get(c, 0) for c in all_classes]
    cur_aligned = [cur_counts.get(c, 0) for c in all_classes]
    
    # Add small constant to prevent zero-sum errors
    contingency = np.array([ref_aligned, cur_aligned]) + 1e-5
    
    try:
        stat, p_val, _, _ = chi2_contingency(contingency)
        drift = p_val < alpha
    except Exception:
        stat, p_val, drift = 0.0, 1.0, False
        
    return {
        "statistic": float(stat),
        "p_value": float(p_val),
        "drift_detected": bool(drift)
    }

def run_drift_analysis(reference_path: Path | str, current_path: Path | str) -> dict:
    """Runs full drift analysis between reference and current serving dataframes."""
    ref_df = pd.read_parquet(reference_path)
    cur_df = pd.read_parquet(current_path)
    
    # Define features to track
    numerical_features = [
        "tenure_years", "prev_otd", "prev_lead_time", "prev_po_accept",
        "otd_mean_4w", "otd_mean_12w", "lead_time_mean_4w", "lead_time_std_4w",
        "lead_time_mean_12w", "po_accept_mean_4w", "lead_time_slope_6w"
    ]
    categorical_features = ["country", "contract_tier"]
    
    results = {}
    drifted_count = 0
    
    for col in numerical_features:
        if col in ref_df.columns and col in cur_df.columns:
            res = check_numerical_drift(ref_df[col], cur_df[col])
            results[col] = res
            if res["drift_detected"]:
                drifted_count += 1
                logger.warning("Drift detected in numerical feature: %s (p-val: %.6f)", col, res["p_value"])
                
    for col in categorical_features:
        if col in ref_df.columns and col in cur_df.columns:
            res = check_categorical_drift(ref_df[col], cur_df[col])
            results[col] = res
            if res["drift_detected"]:
                drifted_count += 1
                logger.warning("Drift detected in categorical feature: %s (p-val: %.6f)", col, res["p_value"])
                
    summary = {
        "total_features_checked": len(results),
        "drifted_features_count": drifted_count,
        "drift_alerts": bool(drifted_count > 0),
        "feature_details": results
    }
    return summary

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from config import settings
    ref = Path(settings.data_processed_dir) / "supplier_train.parquet"
    cur = Path(settings.data_processed_dir) / "supplier_val.parquet"
    if ref.exists() and cur.exists():
        analysis = run_drift_analysis(ref, cur)
        print(f"Drift Analysis Summary: Alert={analysis['drift_alerts']} | Drifted count={analysis['drifted_features_count']}")
    else:
        print("Data files not found to run script execution demonstration.")
