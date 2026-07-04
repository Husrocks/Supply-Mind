"""
SupplyMind — Rolling-Origin Backtesting Framework
Validates forecasting performance across shifting historical windows.
"""

from __future__ import annotations

import logging
import numpy as np
import pandas as pd
from models.tft.baselines import SeasonalNaiveForecaster

logger = logging.getLogger(__name__)

def execute_rolling_backtest(
    df: pd.DataFrame,
    group_col: str = "sku_id",
    time_col: str = "time_idx",
    target_col: str = "demand",
    n_splits: int = 3,
    horizon: int = 14,
    season_length: int = 7
) -> dict[str, list[float]]:
    """
    Executes a rolling-origin evaluation backtest using Seasonal Naive baseline.
    Returns validation metrics across splits.
    """
    df_sorted = df.sort_values(by=[group_col, time_col]).reset_index(drop=True)
    max_time = df_sorted[time_col].max()
    
    metrics = {"rmse": [], "mae": []}
    
    # Run backtest splits backwards from max_time
    for split in range(n_splits):
        cutoff = max_time - (split * horizon)
        
        train_data = df_sorted[df_sorted[time_col] <= cutoff - horizon]
        test_data = df_sorted[(df_sorted[time_col] > cutoff - horizon) & (df_sorted[time_col] <= cutoff)]
        
        if train_data.empty or test_data.empty:
            logger.warning("Empty split encountered at cutoff %d, skipping.", cutoff)
            continue
            
        split_rmse = []
        split_mae = []
        
        # Evaluate per group
        for gid, group_train in train_data.groupby(group_col):
            group_test = test_data[test_data[group_col] == gid]
            if group_test.empty:
                continue
                
            forecaster = SeasonalNaiveForecaster(season_length=season_length)
            forecaster.fit(group_train[target_col].values)
            preds = forecaster.predict(len(group_test))
            
            actuals = group_test[target_col].values
            
            # Metrics
            squared_errors = (preds - actuals) ** 2
            abs_errors = np.abs(preds - actuals)
            
            split_rmse.append(float(np.sqrt(np.mean(squared_errors))))
            split_mae.append(float(np.mean(abs_errors)))
            
        if split_rmse:
            metrics["rmse"].append(float(np.mean(split_rmse)))
            metrics["mae"].append(float(np.mean(split_mae)))
            logger.info("Backtest split %d (cutoff %d) completed: RMSE=%.4f, MAE=%.4f", 
                        split + 1, cutoff, metrics["rmse"][-1], metrics["mae"][-1])
            
    return metrics
