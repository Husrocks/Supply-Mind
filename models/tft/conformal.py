"""
SupplyMind — Conformal Forecast Intervals
Uses absolute calibration residuals to compute guaranteed prediction coverage intervals.
"""

from __future__ import annotations

import numpy as np

class ConformalForecaster:
    """Computes conformal prediction bands around point forecasts."""
    def __init__(self, alpha: float = 0.05):
        self.alpha = alpha
        self.q_threshold = None

    def calibrate(self, actuals: np.ndarray, predictions: np.ndarray):
        """Calibrates threshold boundary using validation residuals."""
        residuals = np.abs(actuals - predictions)
        # Compute (1 - alpha) percentile of absolute residuals
        self.q_threshold = float(np.percentile(residuals, (1 - self.alpha) * 100))
        return self

    def predict_intervals(self, predictions: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Returns (lower_bound, upper_bound) conformal prediction bands."""
        if self.q_threshold is None:
            raise ValueError("Conformal forecaster must be calibrated first.")
        
        lower = predictions - self.q_threshold
        upper = predictions + self.q_threshold
        
        # Enforce non-negativity constraint
        lower = np.clip(lower, 0.0, None)
        return lower, upper
