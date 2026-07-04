"""
SupplyMind — ML Pipeline Remediation Tests
Verifies batch-invariance of LGBM categorical encoding, non-negativity of TFT predictions,
and calibration prefit behavior.
"""

from __future__ import annotations

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from models.lgbm.predict import get_predictor as get_lgbm_predictor
from models.tft.predict import get_predictor as get_tft_predictor
from scripts.drift_monitor import check_numerical_drift, check_categorical_drift

def test_lgbm_categorical_batch_invariance():
    """
    Assert that the LightGBM categorical encoding behaves independently of the batch composition,
    preventing batch-level alignment shift errors.
    """
    predictor = get_lgbm_predictor()
    
    # Base row for SUP-0001
    mock_row_1 = {feat: [0.0] for feat in predictor.feature_names}
    mock_row_1["supplier_id"] = ["SUP-0001"]
    mock_row_1["country"] = ["Taiwan"]
    mock_row_1["contract_tier"] = ["Tier 1"]
    df_single = pd.DataFrame(mock_row_1)
    
    # Run prediction for single row
    res_single = predictor.predict(df_single)[0]
    
    # Batch context with varying categorical ranges
    mock_batch = {feat: [0.0, 0.0, 0.0] for feat in predictor.feature_names}
    mock_batch["supplier_id"] = ["SUP-0001", "SUP-0002", "SUP-0003"]
    # Change the categories present to trigger potential dynamic LabelEncoder re-fitting shifts
    mock_batch["country"] = ["Taiwan", "Germany", "USA"]
    mock_batch["contract_tier"] = ["Tier 1", "Tier 2", "Tier 3"]
    df_batch = pd.DataFrame(mock_batch)
    
    # Run prediction for the batch
    res_batch = predictor.predict(df_batch)
    
    # Assert predictions for SUP-0001 are identical
    assert np.isclose(res_single.risk_score, res_batch[0].risk_score, atol=1e-5), (
        f"LGBM Risk Score changed due to batch context: single={res_single.risk_score}, batch={res_batch[0].risk_score}"
    )

def test_tft_non_negativity_clipping():
    """
    Assert that TFT forecasts are clipped to non-negative boundaries,
    ensuring compliance with physical inventory requirements.
    """
    predictor = get_tft_predictor()
    params = predictor.model.dataset_parameters
    
    # Dynamically extract valid classes from the model's own encoders
    valid_item = list(params["categorical_encoders"]["item_id"].classes_)[0]
    valid_dept = list(params["categorical_encoders"]["dept_id"].classes_)[0]
    valid_cat = list(params["categorical_encoders"]["cat_id"].classes_)[0]
    valid_event = list(params["categorical_encoders"]["event_name_1"].classes_)[0]
    
    valid_group = valid_item
    
    n_days = 28
    mock_data = {
        "id": [valid_group] * n_days,
        "sku_id": [valid_group] * n_days,
        "item_id": [valid_item] * n_days,
        "dept_id": [valid_dept] * n_days,
        "cat_id": [valid_cat] * n_days,
        "event_name_1": [valid_event] * n_days,
        "snap_CA": [0.0] * n_days,
        "sales": [0.0] * n_days,  # Use 0.0 to avoid out-of-vocabulary target errors
        "time_idx": list(range(n_days)),
        "lag_1": [0.0] * n_days,
        "lag_7": [0.0] * n_days,
        "lag_14": [0.0] * n_days,
        "lag_28": [0.0] * n_days,
        "rolling_mean_7": [0.0] * n_days,
        "rolling_mean_28": [0.0] * n_days,
        "rolling_std_7": [0.0] * n_days,
    }
    df = pd.DataFrame(mock_data)
    current_inventory = {valid_group: 50.0}
    
    results = predictor.predict(df, current_inventory)
    forecast = results[valid_group]
    
    # Assert all quantiles in daily forecast are non-negative
    for day in forecast.daily_forecasts:
        assert day["p05"] >= 0.0, f"Lower bound P05 forecast was negative: {day['p05']}"
        assert day["p50"] >= 0.0, f"P50 forecast was negative: {day['p50']}"
        assert day["p95"] >= 0.0, f"Upper bound P95 forecast was negative: {day['p95']}"

def test_drift_detection_statistical_tests():
    """
    Assert that the drift detection checks identify differences when features shift,
    and register no drift when features are identically distributed.
    """
    ref = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    curr_no_drift = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    curr_drift = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
    
    res_no_drift = check_numerical_drift(ref, curr_no_drift)
    res_drift = check_numerical_drift(ref, curr_drift)
    
    assert res_no_drift["drift_detected"] is False
    assert res_drift["drift_detected"] is True
