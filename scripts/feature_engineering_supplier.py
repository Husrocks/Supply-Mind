"""
SupplyMind — Supplier Feature Engineering Pipeline
Processes synthetic supplier dataset into rolling and trend metrics for LightGBM.
Implements time-aware train/val/test splits to prevent future leakage.
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path
from loguru import logger
from sklearn.linear_model import LinearRegression

SYNTHETIC_DATA_PATH = Path("data/synthetic/supplier_dataset.parquet")
PROCESSED_DATA_DIR = Path("data/processed")

def calculate_slope(series: pd.Series) -> float:
    """Calculate the slope of a rolling series using Linear Regression."""
    if len(series) < 2 or series.isna().any():
        return 0.0
    x = np.arange(len(series)).reshape(-1, 1)
    y = series.values
    model = LinearRegression().fit(x, y)
    return float(model.coef_[0])

def main():
    logger.info("Starting supplier feature engineering...")
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    if not SYNTHETIC_DATA_PATH.exists():
        logger.error(f"Synthetic supplier data not found at {SYNTHETIC_DATA_PATH}. Run simulation first.")
        return
        
    # 1. Load data
    logger.info("Loading synthetic supplier dataset...")
    df = pd.read_parquet(SYNTHETIC_DATA_PATH)
    
    # Sort to ensure temporal consistency
    df = df.sort_values(by=["supplier_id", "week_num"]).reset_index(drop=True)
    
    # 2. Rolling features (using shift(1) to avoid time leakage of the current week's target/performance)
    logger.info("Generating rolling lag features (OTD, lead times, capacity)...")
    # Shift performance features by 1 week to represent historical window known at start of the week
    df["prev_otd"] = df.groupby("supplier_id")["on_time_delivery_pct"].shift(1)
    df["prev_lead_time"] = df.groupby("supplier_id")["avg_lead_time_days"].shift(1)
    df["prev_po_accept"] = df.groupby("supplier_id")["po_acceptance_rate"].shift(1)
    
    # Rolling means
    df["otd_mean_4w"] = df.groupby("supplier_id")["prev_otd"].transform(lambda x: x.rolling(4).mean())
    df["otd_mean_12w"] = df.groupby("supplier_id")["prev_otd"].transform(lambda x: x.rolling(12).mean())
    
    df["lead_time_mean_4w"] = df.groupby("supplier_id")["prev_lead_time"].transform(lambda x: x.rolling(4).mean())
    df["lead_time_std_4w"] = df.groupby("supplier_id")["prev_lead_time"].transform(lambda x: x.rolling(4).std())
    df["lead_time_mean_12w"] = df.groupby("supplier_id")["prev_lead_time"].transform(lambda x: x.rolling(12).mean())
    
    df["po_accept_mean_4w"] = df.groupby("supplier_id")["prev_po_accept"].transform(lambda x: x.rolling(4).mean())
    
    # 3. Trend features (slope over last 6 weeks)
    logger.info("Calculating lead time slopes over last 6 weeks...")
    df["lead_time_slope_6w"] = (
        df.groupby("supplier_id")["prev_lead_time"]
        .transform(lambda x: x.rolling(6).apply(calculate_slope, raw=False))
    )
    
    # 4. Enriched features for LSTM-AE
    logger.info("Calculating enriched features for LSTM-AE...")
    # Rolling standard deviations (volatility) of lead times
    df["lead_time_volatility_4w"] = df.groupby("supplier_id")["prev_lead_time"].transform(lambda x: x.rolling(4).std().fillna(0))
    df["lead_time_volatility_12w"] = df.groupby("supplier_id")["prev_lead_time"].transform(lambda x: x.rolling(12).std().fillna(0))
    
    # Coefficient of variation (CV)
    df["lead_time_cv"] = df["lead_time_volatility_4w"] / (df["lead_time_mean_4w"] + 1e-5)
    
    # Defect rate
    df["defect_rate"] = df["defect_rate_pct"]
    
    # Financial stress score (derived from defect rate and lower PO acceptance, with random walk noise)
    # Let's seed for reproducibility
    np.random.seed(42)
    noise = np.random.normal(0.2, 0.05, len(df))
    df["financial_stress_score"] = np.clip(df["defect_rate_pct"] * 3.0 + (1.0 - df["po_acceptance_rate"]) * 2.0 + noise, 0, 1)
    
    # Capacity utilization (derived from PO acceptance and random walk noise)
    noise_cap = np.random.normal(0, 0.05, len(df))
    df["capacity_utilization"] = np.clip(0.6 + 0.3 * (1.0 - df["po_acceptance_rate"]) + noise_cap, 0, 1)
    
    # Logistics & Weather Signals
    # Regional delay factor (derived from country risk tier + noise)
    country_risk = df["country"].map({"USA": 0.05, "Germany": 0.08, "Taiwan": 0.15, "China": 0.20, "Mexico": 0.18, "Vietnam": 0.22}).fillna(0.15)
    df["regional_delay_factor"] = np.clip(country_risk + np.random.normal(0, 0.02, len(df)), 0, 1)
    
    # Port congestion index
    df["port_congestion_index"] = np.clip(df["capacity_utilization"] * 0.7 + (df["country"] == "China").astype(float) * 0.15 + np.random.normal(0, 0.05, len(df)), 0, 1)
    
    # Weather alerts
    df["weather_alerts"] = np.clip(np.random.poisson(0.1, len(df)), 0, 5).astype(float)
    
    # Macro-economic variables
    # Interest rates (trend over weeks)
    df["interest_rate"] = 0.05 + 0.02 * np.sin(df["week_num"] / 26.0) + np.random.normal(0, 0.002, len(df))
    # Inflation index (slowly increasing)
    df["inflation_index"] = 1.0 + 0.04 * (df["week_num"] / 52.0) + np.random.normal(0, 0.01, len(df))
    # Raw material cost
    df["raw_material_cost"] = 100.0 + df["week_num"] * 0.2 + df["financial_stress_score"] * 10.0 + np.random.normal(0, 2.0, len(df))
    
    # Drop rows with NaN due to rolling windows
    logger.info("Cleaning missing values from window functions...")
    df = df.dropna().reset_index(drop=True)
    
    # Convert categorical strings to category code representations
    for col in ["country", "contract_tier"]:
        df[col] = df[col].astype("category")
        
    # 4. Time-Aware Split (chronological train/val/test)
    # Total weeks: 104. Since we dropped first 11 weeks due to rolling 12w, remaining weeks are 12 to 104.
    # We split:
    # Train: weeks 12 to 80
    # Val: weeks 81 to 95
    # Test: weeks 96 to 104
    logger.info("Performing chronological time-aware train/val/test split...")
    
    train_df = df[df["week_num"] <= 80].reset_index(drop=True)
    val_df = df[(df["week_num"] > 80) & (df["week_num"] <= 95)].reset_index(drop=True)
    test_df = df[df["week_num"] > 95].reset_index(drop=True)
    
    logger.info(f"Train set shape: {train_df.shape} (weeks 12-80)")
    logger.info(f"Val set shape: {val_df.shape} (weeks 81-95)")
    logger.info(f"Test set shape: {test_df.shape} (weeks 96-104)")
    
    # Save datasets
    train_df.to_parquet(PROCESSED_DATA_DIR / "supplier_train.parquet", index=False)
    val_df.to_parquet(PROCESSED_DATA_DIR / "supplier_val.parquet", index=False)
    test_df.to_parquet(PROCESSED_DATA_DIR / "supplier_test.parquet", index=False)
    df.to_parquet(PROCESSED_DATA_DIR / "supplier_features_all.parquet", index=False)
    
    logger.info("✅ Processed supplier features successfully saved to data/processed/")

if __name__ == "__main__":
    main()
