"""
SupplyMind — Hierarchical Forecast Reconciliation
Implements Bottom-Up reconciliation to align forecasts across nodes.
"""

from __future__ import annotations

import pandas as pd
import numpy as np

def reconcile_bottom_up(
    sku_forecasts: dict[str, np.ndarray],
    hierarchy_mapping: pd.DataFrame,
    sku_col: str = "sku_id",
    parent_col: str = "category"
) -> dict[str, np.ndarray]:
    """
    Performs bottom-up reconciliation.
    Sums SKU-level predictions to parent category level.
    """
    reconciled: dict[str, np.ndarray] = {}
    
    # Store bottom-level SKU predictions
    for sku, pred in sku_forecasts.items():
        reconciled[f"sku_{sku}"] = pred
        
    # Map and aggregate to parent levels
    for parent, group in hierarchy_mapping.groupby(parent_col):
        parent_forecast = None
        for _, row in group.iterrows():
            sku = str(row[sku_col])
            if sku in sku_forecasts:
                pred = sku_forecasts[sku]
                if parent_forecast is None:
                    parent_forecast = np.zeros_like(pred)
                parent_forecast += pred
                
        if parent_forecast is not None:
            reconciled[f"parent_{parent}"] = parent_forecast
            
    return reconciled
