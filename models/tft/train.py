"""
SupplyMind — Temporal Fusion Transformer (TFT) for Demand Forecasting
Trains a PyTorch Forecasting TFT model on the synthetic demand dataset.

Pipeline:
  1. Load parquet → create PyTorch Forecasting TimeSeriesDataSet
  2. Define TFT architecture with QuantileLoss (P05, P50, P95)
  3. Train using PyTorch Lightning with early stopping and learning rate scheduling
  4. Log metrics, model, and tensorboard outputs to MLflow
"""

from __future__ import annotations

import sys
import logging
from pathlib import Path

import os
os.environ["MLFLOW_ALLOW_FILE_STORE"] = "true"

import mlflow
import numpy as np
import pandas as pd
import lightning.pytorch as pl
from lightning.pytorch.callbacks import EarlyStopping, LearningRateMonitor
from lightning.pytorch.loggers import TensorBoardLogger

from pytorch_forecasting import TimeSeriesDataSet, TemporalFusionTransformer
from pytorch_forecasting.metrics import QuantileLoss
from pytorch_forecasting.data import GroupNormalizer

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from config import settings

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# WRMSSE Implementation (Fix 4)
# WRMSSE = Weighted Root Mean Scaled Squared Error
# Per M5 competition specification:
#   scale_i   = mean of squared naive seasonal differences (lag-28) on training data
#   weight_i  = last-28d revenue share for series i (demand * price)
#   RMSSE_i   = sqrt(MSE_i / scale_i)
#   WRMSSE    = sum_i(weight_i * RMSSE_i)
# ──────────────────────────────────────────────────────────────────────────────

def compute_wrmsse(
    df: pd.DataFrame,
    forecasts_p50: dict[str, np.ndarray],
    actuals: dict[str, np.ndarray],
    horizon: int = 14,
) -> float:
    """
    Compute the Weighted Root Mean Scaled Squared Error (WRMSSE).

    This is run POST-TRAINING as a reported metric. QuantileLoss remains the
    optimisation objective; WRMSSE is the primary evaluation metric per spec.

    Args:
        df:            Full demand DataFrame (must have columns: sku_id, demand,
                       time_idx, sell_price).
        forecasts_p50: Dict mapping sku_id → 1-D np.ndarray of P50 point forecasts
                       for the validation horizon.
        actuals:       Dict mapping sku_id → 1-D np.ndarray of true demand values
                       over the same horizon.
        horizon:       Forecast horizon in days (default 14, matching MAX_PREDICTION_LENGTH).

    Returns:
        WRMSSE as a positive float. Lower is better.
    """
    sku_ids = list(forecasts_p50.keys())
    if not sku_ids:
        logger.warning("compute_wrmsse: no forecasts provided, returning NaN.")
        return float("nan")

    scales   = {}
    weights  = {}
    rmsse_vals = {}
    lag = 28  # M5 uses lag-28 (weekly seasonality in daily data)

    for sku in sku_ids:
        sku_df = df[df["sku_id"] == sku].sort_values("time_idx") if "sku_id" in df.columns else df.sort_values("time_idx")
        demand = sku_df["demand"].values

        # ── Scale: mean squared naive lag-28 difference on training portion ──
        if len(demand) > lag:
            naive_errors = demand[lag:] - demand[:-lag]
            scale_i = float(np.mean(naive_errors ** 2))
        else:
            scale_i = 1.0  # fallback to avoid div-by-zero on very short series
        scales[sku] = max(scale_i, 1e-8)  # guard zero scale

        # ── Weight: proportional to last-28d revenue (demand * sell_price) ──
        price_col = "sell_price" if "sell_price" in sku_df.columns else None
        if price_col and len(demand) >= lag:
            last_28d_revenue = float(np.sum(
                sku_df["demand"].values[-lag:] *
                sku_df[price_col].values[-lag:]
            ))
        else:
            last_28d_revenue = float(np.sum(demand[-lag:])) if len(demand) >= lag else float(np.sum(demand))
        weights[sku] = max(last_28d_revenue, 0.0)

        # ── RMSSE for this series ──────────────────────────────────────────
        y_hat = forecasts_p50[sku][:horizon]
        y_true = actuals[sku][:horizon]
        min_len = min(len(y_hat), len(y_true))
        if min_len == 0:
            rmsse_vals[sku] = 0.0
            continue
        mse_i = float(np.mean((y_hat[:min_len] - y_true[:min_len]) ** 2))
        rmsse_vals[sku] = float(np.sqrt(mse_i / scales[sku]))

    # ── Weighted average ──────────────────────────────────────────────────
    total_weight = sum(weights.values())
    if total_weight == 0:
        # Degenerate: all series have zero demand → unweighted average
        wrmsse = float(np.mean(list(rmsse_vals.values())))
    else:
        wrmsse = sum(
            (weights[sku] / total_weight) * rmsse_vals[sku]
            for sku in sku_ids
        )

    logger.info(
        "WRMSSE computed over %d series: %.6f (mean weight=%.2f, mean scale=%.6f)",
        len(sku_ids), wrmsse,
        total_weight / len(sku_ids) if sku_ids else 0,
        float(np.mean(list(scales.values()))),
    )
    return float(wrmsse)


def _extract_val_predictions(
    tft: TemporalFusionTransformer,
    val_dataloader,
    df: pd.DataFrame,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    """
    Run inference on the validation dataloader and extract P50 predictions
    plus ground-truth actuals, indexed by sku_id.

    Returns:
        (forecasts_p50, actuals) — both are dict[sku_id → np.ndarray].
    """
    import torch

    tft.eval()
    forecasts_p50: dict[str, list] = {}
    actuals_map:   dict[str, list] = {}

    with torch.no_grad():
        for batch in val_dataloader:
            x, y = batch
            # TFT prediction output shape: (batch, horizon, n_quantiles)
            preds = tft(x)  # returns a dict with 'prediction' key
            if isinstance(preds, dict):
                pred_tensor = preds["prediction"]
            else:
                pred_tensor = preds

            # P50 is quantile index 1 (quantiles=[0.05, 0.50, 0.95])
            p50 = pred_tensor[:, :, 1].cpu().numpy()

            # Ground truth
            if isinstance(y, (list, tuple)):
                target = y[0].cpu().numpy()
            else:
                target = y.cpu().numpy()

            # Map by group — use encoder_lengths if available
            groups = x.get("groups", None)
            if groups is not None:
                group_ids = groups.cpu().numpy()
                for i, gid in enumerate(group_ids):
                    key = str(gid[0]) if hasattr(gid, "__len__") else str(gid)
                    forecasts_p50.setdefault(key, []).append(p50[i])
                    actuals_map.setdefault(key, []).append(target[i])
            else:
                # Fallback: use sequential index as key
                for i in range(len(p50)):
                    key = f"series_{i}"
                    forecasts_p50.setdefault(key, []).append(p50[i])
                    actuals_map.setdefault(key, []).append(target[i])

    # Concatenate lists into arrays
    fcast = {k: np.concatenate(v, axis=0) for k, v in forecasts_p50.items()}
    acts  = {k: np.concatenate(v, axis=0) for k, v in actuals_map.items()}
    return fcast, acts

# ──────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────
CHECKPOINT_DIR = Path(settings.tft_model_path).parent
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

MAX_PREDICTION_LENGTH = 14  # Forecast horizon (days)
MAX_ENCODER_LENGTH = 60     # Lookback window (days)

# ──────────────────────────────────────────────────────────────
# Data Loading & Preparation
# ──────────────────────────────────────────────────────────────

def load_and_prepare(path: str | Path) -> pd.DataFrame:
    """Load parquet and prepare for TimeSeriesDataSet."""
    df = pd.read_parquet(path)
    logger.info("Loaded demand data: %s", df.shape)

    # Convert datatypes
    df["sku_id"] = df["sku_id"].astype(str)
    df["store_id"] = df["store_id"].astype(str)
    df["category"] = df["category"].astype(str)
    df["dept"] = df["dept"].astype(str)
    
    # Time index must be continuous int
    df["time_idx"] = df["t"].astype(int)
    
    # Categoricals for TFT
    df["day_of_week"] = df["day_of_week"].astype(str)
    df["month"] = df["month"].astype(str)
    df["is_promo"] = df["is_promo"].astype(str)
    df["holiday_flag"] = df["holiday_flag"].astype(str)
    df["stockout_flag"] = df["stockout_flag"].astype(str)
    
    # Reals
    df["temperature_c"] = df["temperature_c"].astype(float)
    df["demand"] = df["demand"].astype(float)
    
    return df

def create_datasets(df: pd.DataFrame) -> tuple[TimeSeriesDataSet, TimeSeriesDataSet]:
    """Create training and validation TimeSeriesDataSets."""
    training_cutoff = df["time_idx"].max() - MAX_PREDICTION_LENGTH

    training_dataset = TimeSeriesDataSet(
        df[lambda x: x.time_idx <= training_cutoff],
        time_idx="time_idx",
        target="demand",
        group_ids=["sku_id"],
        min_encoder_length=MAX_ENCODER_LENGTH // 2,
        max_encoder_length=MAX_ENCODER_LENGTH,
        min_prediction_length=1,
        max_prediction_length=MAX_PREDICTION_LENGTH,
        static_categoricals=["sku_id", "store_id", "category", "dept"],
        time_varying_known_categoricals=["day_of_week", "month", "is_promo", "holiday_flag"],
        time_varying_known_reals=["time_idx", "sell_price", "temperature_c"],
        time_varying_unknown_categoricals=["stockout_flag"],
        time_varying_unknown_reals=["demand"],
        target_normalizer=GroupNormalizer(
            groups=["sku_id"], transformation="softplus"
        ),
        add_relative_time_idx=True,
        add_target_scales=True,
        add_encoder_length=True,
    )

    validation_dataset = TimeSeriesDataSet.from_dataset(
        training_dataset, df, predict=True, stop_randomization=True
    )
    
    return training_dataset, validation_dataset

# ──────────────────────────────────────────────────────────────
# Training Entry Point
# ──────────────────────────────────────────────────────────────

def train(
    data_path: str | Path | None = None,
    epochs: int = 15,
    batch_size: int = 128,
    experiment_name: str | None = None,
) -> Path:
    """
    Train the TFT model. Returns path to saved model checkpoint.
    """
    data_path = data_path or (Path(settings.data_synthetic_dir) / "demand_series.parquet")
    exp_name = experiment_name or f"{settings.mlflow_experiment_name}/tft_demand_forecast"

    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    mlflow.set_experiment(exp_name)

    # ── Load data ──
    df = load_and_prepare(data_path)
    train_dataset, val_dataset = create_datasets(df)

    train_dataloader = train_dataset.to_dataloader(train=True, batch_size=batch_size, num_workers=0)
    val_dataloader = val_dataset.to_dataloader(train=False, batch_size=batch_size, num_workers=0)

    with mlflow.start_run(run_name="tft_training") as run:
        # ── Setup Model & Trainer ──
        logger.info("Initializing TFT model...")
        tft = TemporalFusionTransformer.from_dataset(
            train_dataset,
            learning_rate=0.005,
            hidden_size=35,
            attention_head_size=1,
            dropout=0.11,
            hidden_continuous_size=8,
            loss=QuantileLoss([0.05, 0.50, 0.95]),
            log_interval=10,
            optimizer="adam",
            reduce_on_plateau_patience=4,
        )

        early_stop_callback = EarlyStopping(
            monitor="val_loss", min_delta=1e-4, patience=5, verbose=True, mode="min"
        )
        lr_logger = LearningRateMonitor(logging_interval="step")
        tb_logger = TensorBoardLogger("models/tft", name="lightning_logs")

        trainer = pl.Trainer(
            max_epochs=30,
            accelerator="auto",
            gradient_clip_val=0.74,
            callbacks=[lr_logger, early_stop_callback],
            logger=tb_logger,
        )

        # ── Train ──
        logger.info("Starting training...")
        mlflow.log_params({
            "hidden_size": 35,
            "attention_head_size": 1,
            "dropout": 0.11,
            "learning_rate": 0.005,
            "epochs": epochs,
            "batch_size": batch_size,
        })
        
        trainer.fit(
            tft,
            train_dataloaders=train_dataloader,
            val_dataloaders=val_dataloader,
        )

        # ── Save ──
        best_model_path = trainer.checkpoint_callback.best_model_path if trainer.checkpoint_callback else None
        if not best_model_path:
            # Save current state if no best model
            best_model_path = str(CHECKPOINT_DIR / "best.ckpt")
            trainer.save_checkpoint(best_model_path)
            
        logger.info("Best model saved at: %s", best_model_path)
        
        # Log to MLflow
        val_loss = trainer.callback_metrics.get("val_loss", 0.0)
        mlflow.log_metric("val_loss", float(val_loss))
        mlflow.log_artifact(best_model_path, artifact_path="model_checkpoints")
        mlflow.log_param("run_id", run.info.run_id)

        # ── WRMSSE Post-Training Evaluation (Fix 4) ───────────────────────
        # QuantileLoss is the optimisation objective; WRMSSE is the reported
        # primary metric per the project specification.
        logger.info("Computing WRMSSE on validation set...")
        try:
            fcast_p50, acts = _extract_val_predictions(tft, val_dataloader, df)
            val_wrmsse = compute_wrmsse(
                df=df,
                forecasts_p50=fcast_p50,
                actuals=acts,
                horizon=MAX_PREDICTION_LENGTH,
            )
            mlflow.log_metric("val_wrmsse", val_wrmsse)
            logger.info("val_wrmsse = %.6f", val_wrmsse)
        except Exception as exc:
            logger.error("WRMSSE computation failed: %s", exc)
            mlflow.log_metric("val_wrmsse", float("nan"))

    return Path(best_model_path)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ckpt = train(epochs=10) # Keep epochs low for fast demo execution
    print(f"TFT Model saved: {ckpt}")
