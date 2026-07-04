"""
SupplyMind — Demand Feature Engineering Pipeline (M5)
Processes raw M5 dataset into structured features for TFT forecasting.
Includes downcasting and filtering to avoid out-of-memory issues.
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path
from loguru import logger

RAW_DATA_DIR = Path("data/raw/m5-forecasting-accuracy")
PROCESSED_DATA_DIR = Path("data/processed")

def downcast_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """Optimize pandas datatypes to save memory."""
    for col in df.columns:
        if df[col].dtype == "float64":
            df[col] = df[col].astype("float32")
        elif df[col].dtype == "int64":
            df[col] = df[col].astype("int32")
    return df

def main():
    logger.info("Starting demand feature engineering...")
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    if not (RAW_DATA_DIR / "sales_train_evaluation.csv").exists():
        logger.error("M5 sales files not found. Ensure they are placed in data/raw/m5-forecasting-accuracy/")
        return

    # 1. Load data
    logger.info("Loading calendar and sales datasets...")
    calendar = pd.read_csv(RAW_DATA_DIR / "calendar.csv")
    sales = pd.read_csv(RAW_DATA_DIR / "sales_train_evaluation.csv")
    
    # 2. Subset to CA_1 store to keep local memory usage and TFT training fast (~3,049 items)
    logger.info("Subsetting data to store 'CA_1' to optimize memory and training speed...")
    sales = sales[sales["store_id"] == "CA_1"].reset_index(drop=True)
    
    # 3. Melt sales to long format (days as rows)
    logger.info("Melting sales data to long format...")
    d_cols = [c for c in sales.columns if c.startswith("d_")]
    sales_long = pd.melt(
        sales,
        id_vars=["id", "item_id", "dept_id", "cat_id", "store_id", "state_id"],
        value_vars=d_cols,
        var_name="d",
        value_name="sales"
    )
    
    # Free up raw sales memory
    del sales
    
    # 4. Merge with calendar features
    logger.info("Merging with calendar metadata...")
    # Convert 'd' to int for merging if calendar uses 'd'
    sales_long = sales_long.merge(calendar[["d", "date", "event_name_1", "snap_CA"]], on="d", how="left")
    sales_long["date"] = pd.to_datetime(sales_long["date"])
    
    # Sort to ensure correct time order per item
    sales_long = sales_long.sort_values(by=["id", "date"]).reset_index(drop=True)
    
    # 5. Generate Lags & Rolling Features
    logger.info("Generating lag and rolling features...")
    # Lags
    sales_long["lag_1"] = sales_long.groupby("id")["sales"].shift(1)
    sales_long["lag_7"] = sales_long.groupby("id")["sales"].shift(7)
    sales_long["lag_14"] = sales_long.groupby("id")["sales"].shift(14)
    sales_long["lag_28"] = sales_long.groupby("id")["sales"].shift(28)
    
    # Rolling averages (using lag_1 to avoid time leakage)
    sales_long["rolling_mean_7"] = sales_long.groupby("id")["lag_1"].transform(lambda x: x.rolling(7).mean())
    sales_long["rolling_mean_28"] = sales_long.groupby("id")["lag_1"].transform(lambda x: x.rolling(28).mean())
    sales_long["rolling_std_7"] = sales_long.groupby("id")["lag_1"].transform(lambda x: x.rolling(7).std())
    
    # Drop rows with NaN due to lags/rolling windows
    logger.info("Cleaning missing values from window functions...")
    sales_long = sales_long.dropna().reset_index(drop=True)
    
    # Convert features to optimized datatypes
    sales_long = downcast_dtypes(sales_long)
    
    # Convert categorical strings to category code representations
    for col in ["item_id", "dept_id", "cat_id"]:
        sales_long[col] = sales_long[col].astype("category")
        
    # Fill event name missing values as 'None'
    sales_long["event_name_1"] = sales_long["event_name_1"].fillna("None").astype("category")
    
    # 6. Save processed output
    output_path = PROCESSED_DATA_DIR / "demand_features.parquet"
    logger.info(f"Saving processed demand features to {output_path}...")
    sales_long.to_parquet(output_path, index=False)
    logger.info(f"✅ Processed demand shape: {sales_long.shape}")

if __name__ == "__main__":
    main()
