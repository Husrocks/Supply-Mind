"""
SupplyMind — Advanced Forecasting tests
Verifies naive baselines, rolling backtests, bottom-up reconciliation, and conformal prediction bands.
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from models.tft.baselines import NaiveForecaster, SeasonalNaiveForecaster
from models.tft.backtest import execute_rolling_backtest
from models.tft.reconciliation import reconcile_bottom_up
from models.tft.conformal import ConformalForecaster

def test_naive_forecaster():
    y = np.array([10.0, 12.0, 15.0])
    forecaster = NaiveForecaster().fit(y)
    preds = forecaster.predict(3)
    assert np.allclose(preds, [15.0, 15.0, 15.0])

def test_seasonal_naive_forecaster():
    y = np.array([1.0, 2.0, 3.0, 1.0, 2.0, 3.0])
    forecaster = SeasonalNaiveForecaster(season_length=3).fit(y)
    preds = forecaster.predict(4)
    assert np.allclose(preds, [1.0, 2.0, 3.0, 1.0])

def test_rolling_backtest_execution():
    # Construct a small mock time series dataset
    data = {
        "sku_id": ["SKU1"] * 40 + ["SKU2"] * 40,
        "time_idx": list(range(40)) * 2,
        "demand": np.random.poisson(lam=5, size=80).astype(float)
    }
    df = pd.DataFrame(data)
    metrics = execute_rolling_backtest(df, n_splits=2, horizon=7, season_length=7)
    
    assert "rmse" in metrics
    assert "mae" in metrics
    assert len(metrics["rmse"]) == 2

def test_bottom_up_reconciliation():
    sku_forecasts = {
        "SKU1": np.array([10.0, 20.0]),
        "SKU2": np.array([15.0, 25.0])
    }
    hierarchy = pd.DataFrame({
        "sku_id": ["SKU1", "SKU2"],
        "category": ["Electronics", "Electronics"]
    })
    
    reconciled = reconcile_bottom_up(sku_forecasts, hierarchy)
    assert "sku_SKU1" in reconciled
    assert "parent_Electronics" in reconciled
    assert np.allclose(reconciled["parent_Electronics"], [25.0, 45.0])

def test_conformal_forecaster():
    actuals = np.array([10.0, 12.0, 14.0])
    predictions = np.array([9.5, 12.5, 13.8])
    
    conformal = ConformalForecaster(alpha=0.05).calibrate(actuals, predictions)
    # The absolute residuals are [0.5, 0.5, 0.2]. The 95th percentile is <= 0.5
    assert conformal.q_threshold <= 0.5
    
    lower, upper = conformal.predict_intervals(np.array([10.0]))
    assert lower[0] >= 0.0
    assert upper[0] >= 10.0
