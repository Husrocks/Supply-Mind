"""
SupplyMind — Time Series Naive Baseline Estimators
Defines simple forecasting baselines (Naive, Seasonal Naive)
to establish lower-bound forecasting targets.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

class NaiveForecaster:
    """Predicts last observed value forward."""
    def __init__(self):
        self.last_value = None

    def fit(self, y: pd.Series | np.ndarray):
        y_arr = np.asarray(y)
        if len(y_arr) == 0:
            self.last_value = 0.0
        else:
            self.last_value = float(y_arr[-1])
        return self

    def predict(self, horizon: int) -> np.ndarray:
        return np.full(horizon, self.last_value)

class SeasonalNaiveForecaster:
    """Repeats the last full season (e.g. 7 days for weekly seasonality)."""
    def __init__(self, season_length: int = 7):
        self.season_length = season_length
        self.season_values = None

    def fit(self, y: pd.Series | np.ndarray):
        y_arr = np.asarray(y)
        if len(y_arr) < self.season_length:
            # Fallback to mean if series is too short
            self.season_values = np.full(self.season_length, np.mean(y_arr) if len(y_arr) > 0 else 0.0)
        else:
            self.season_values = y_arr[-self.season_length:]
        return self

    def predict(self, horizon: int) -> np.ndarray:
        repeats = int(np.ceil(horizon / self.season_length))
        return np.tile(self.season_values, repeats)[:horizon]
