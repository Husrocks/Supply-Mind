"""
SupplyMind — TFT Demand Predictor (Colab / M5 Compatible)
Loads the trained PyTorch Forecasting TFT model for demand inference on M5 data.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import numpy as np
import torch
from pydantic import BaseModel, Field

from pytorch_forecasting import TimeSeriesDataSet, TemporalFusionTransformer

from config import settings

logger = logging.getLogger(__name__)

# Constants matching Colab / M5 dataset
MAX_PREDICTION_LENGTH = 14
MAX_ENCODER_LENGTH = 28

class DemandForecast(BaseModel):
    sku_id: str
    days_to_stockout_p50: float | None = None
    days_to_stockout_p95: float | None = None
    p05_14day_total: float
    p50_14day_total: float
    p95_14day_total: float
    daily_forecasts: list[dict]

class DemandPredictor:
    def __init__(self, model_path: str | Path | None = None):
        self.model_path = Path(model_path or settings.tft_model_path)
        self.model = None
        self._load_model()

    def _load_model(self):
        if not self.model_path.exists():
            raise FileNotFoundError(f"TFT Model checkpoint not found at: {self.model_path}")
            
        logger.info("Loading TFT model from %s", self.model_path)
        import torchmetrics
        # Monkey-patch torchmetrics to prevent CUDA lookup errors during GPU->CPU model loading
        original_device = torchmetrics.Metric.device
        try:
            torchmetrics.Metric.device = property(lambda self: torch.device("cpu"))
            self.model = TemporalFusionTransformer.load_from_checkpoint(self.model_path, map_location="cpu")
        finally:
            torchmetrics.Metric.device = original_device
        self.model.eval()

    def predict(self, df: pd.DataFrame, current_inventory: dict[str, float]) -> dict[str, DemandForecast]:
        """
        Generate forecasts for the given M5 historical context dataframe.
        Calculates days_to_stockout using current_inventory mappings.
        """
        # Prepare data copy
        df_prep = df.copy()
        
        # Ensure correct column names matching training
        # If the df has 'sku_id', map it to 'id' (since TFT group_id was 'id')
        if "sku_id" in df_prep.columns and "id" not in df_prep.columns:
            df_prep["id"] = df_prep["sku_id"].astype(str)
        elif "id" in df_prep.columns:
            df_prep["id"] = df_prep["id"].astype(str)
            
        df_prep["item_id"] = df_prep.get("item_id", df_prep.get("sku_id", "item")).astype(str)
        df_prep["dept_id"] = df_prep.get("dept_id", "dept").astype(str)
        df_prep["cat_id"] = df_prep.get("cat_id", "cat").astype(str)
        df_prep["event_name_1"] = df_prep.get("event_name_1", "None").astype(str)
        
        if "sales" not in df_prep.columns and "demand" in df_prep.columns:
            df_prep["sales"] = df_prep["demand"].astype(float)
            
        # Ensure time_idx exists and is sequential integer
        if "time_idx" not in df_prep.columns:
            if "date" in df_prep.columns:
                df_prep["time_idx"] = (pd.to_datetime(df_prep["date"]) - pd.to_datetime(df_prep["date"].min())).dt.days
            elif "t" in df_prep.columns:
                df_prep["time_idx"] = df_prep["t"].astype(int)
            else:
                df_prep["time_idx"] = np.arange(len(df_prep))

        df_prep = df_prep.sort_values(by=["id", "time_idx"]).reset_index(drop=True)

        # Reconstruct TimeSeriesDataSet configuration matching training via dataset_parameters
        params = self.model.dataset_parameters
        
        # Determine the target column from training parameters (it will be "demand" or "sales")
        target_col = params.get("target", "demand")
        if target_col not in df_prep.columns:
            if target_col == "demand" and "sales" in df_prep.columns:
                df_prep["demand"] = df_prep["sales"]
            elif target_col == "sales" and "demand" in df_prep.columns:
                df_prep["sales"] = df_prep["demand"]

        # Re-map key categorical variables and index columns if they differ from what the training params require
        for g_id in (params.get("group_ids") or ["sku_id"]):
            if g_id not in df_prep.columns:
                if g_id == "sku_id" and "id" in df_prep.columns:
                    df_prep["sku_id"] = df_prep["id"]
                elif g_id == "id" and "sku_id" in df_prep.columns:
                    df_prep["id"] = df_prep["sku_id"]

        static_cats = params.get("static_categoricals") or []
        time_varying_known_cats = params.get("time_varying_known_categoricals") or []
        time_varying_known_rls = params.get("time_varying_known_reals") or []
        time_varying_unknown_cats = params.get("time_varying_unknown_categoricals") or []

        for col in static_cats:
            if col not in df_prep.columns:
                if col == "sku_id" and "id" in df_prep.columns:
                    df_prep["sku_id"] = df_prep["id"]
                elif col == "id" and "sku_id" in df_prep.columns:
                    df_prep["id"] = df_prep["sku_id"]
                elif col == "store_id":
                    df_prep["store_id"] = "CA_1"
                elif col == "category" and "cat_id" in df_prep.columns:
                    df_prep["category"] = df_prep["cat_id"]
                elif col == "dept" and "dept_id" in df_prep.columns:
                    df_prep["dept"] = df_prep["dept_id"]

        for col in time_varying_known_cats:
            if col not in df_prep.columns:
                if col == "day_of_week" and "date" in df_prep.columns:
                    df_prep["day_of_week"] = pd.to_datetime(df_prep["date"]).dt.day_name()
                elif col == "month" and "date" in df_prep.columns:
                    df_prep["month"] = pd.to_datetime(df_prep["date"]).dt.month.astype(str)
                elif col == "is_promo":
                    df_prep["is_promo"] = "0"

        for col in time_varying_known_rls:
            if col not in df_prep.columns:
                if col == "sell_price":
                    df_prep["sell_price"] = 1.0
                elif col == "snap_CA":
                    df_prep["snap_CA"] = 0.0

        for col in time_varying_unknown_cats:
            if col not in df_prep.columns:
                if col == "stockout_flag":
                    df_prep["stockout_flag"] = "0"

        # Apply continuous types
        for col in static_cats:
            df_prep[col] = df_prep[col].astype(str)
        for col in time_varying_known_cats:
            df_prep[col] = df_prep[col].astype(str)
        for col in time_varying_unknown_cats:
            df_prep[col] = df_prep[col].astype(str)

        # Reconstruct TimeSeriesDataSet configuration matching training
        training_dataset = TimeSeriesDataSet.from_parameters(
            params,
            df_prep,
            predict=True,
            stop_randomization=True
        )

        # Predict using model
        # We need validation data structure to pass to predict
        predictions = self.model.predict(
            training_dataset, 
            mode="quantiles", 
            return_x=False
        ) # Shape: (n_series, max_prediction_length, n_quantiles)
        
        results = {}
        unique_ids = df_prep["id"].unique()
        
        for i, uid in enumerate(unique_ids):
            pred_tensor = predictions[i]
            
            # Enforce physical non-negativity constraint on demand forecasts
            p05_series = np.clip(pred_tensor[:, 0].numpy(), a_min=0.0, a_max=None).tolist()
            p50_series = np.clip(pred_tensor[:, 1].numpy(), a_min=0.0, a_max=None).tolist()
            p95_series = np.clip(pred_tensor[:, 2].numpy(), a_min=0.0, a_max=None).tolist()
            
            daily_forecasts = []
            cumulative_p50 = 0.0
            cumulative_p95 = 0.0
            stockout_p50 = None
            stockout_p95 = None
            
            inv = current_inventory.get(uid, 0.0)
            
            for day in range(min(len(p50_series), MAX_PREDICTION_LENGTH)):
                d_p05 = p05_series[day]
                d_p50 = p50_series[day]
                d_p95 = p95_series[day]
                
                cumulative_p50 += d_p50
                cumulative_p95 += d_p95
                
                # Check stockout days
                if stockout_p50 is None and cumulative_p50 > inv:
                    prev_cum = cumulative_p50 - d_p50
                    fraction = (inv - prev_cum) / d_p50 if d_p50 > 0 else 0
                    stockout_p50 = day + fraction
                    
                if stockout_p95 is None and cumulative_p95 > inv:
                    prev_cum = cumulative_p95 - d_p95
                    fraction = (inv - prev_cum) / d_p95 if d_p95 > 0 else 0
                    stockout_p95 = day + fraction

                daily_forecasts.append({
                    "day_offset": day + 1,
                    "p05": d_p05,
                    "p50": d_p50,
                    "p95": d_p95
                })

            forecast = DemandForecast(
                sku_id=uid,
                days_to_stockout_p50=stockout_p50,
                days_to_stockout_p95=stockout_p95,
                p05_14day_total=sum(p05_series),
                p50_14day_total=sum(p50_series),
                p95_14day_total=sum(p95_series),
                daily_forecasts=daily_forecasts
            )
            results[uid] = forecast
            
        return results

# Singleton
_predictor = None

def get_predictor() -> DemandPredictor:
    global _predictor
    if _predictor is None:
        _predictor = DemandPredictor()
    return _predictor
