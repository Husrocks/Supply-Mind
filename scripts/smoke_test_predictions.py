"""
SupplyMind — ML Predictor Integration Smoke Test
Tests loading of LightGBM, LSTM Autoencoder, and TFT models and running inference.
"""

import os
os.environ["MLFLOW_ALLOW_FILE_STORE"] = "true"
import sys
import logging
from pathlib import Path
import pandas as pd
import numpy as np

# Ensure project root is in PATH
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from models.lgbm.predict import get_predictor as get_lgbm_predictor
from models.lstm_ae.predict import get_predictor as get_lstm_predictor
from models.tft.predict import get_predictor as get_tft_predictor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_lgbm():
    logger.info("=== Testing LightGBM Supplier Risk Predictor ===")
    predictor = get_lgbm_predictor()
    # Create mock data with same columns
    mock_data = {feat: [0.0] for feat in predictor.feature_names}
    mock_data["supplier_id"] = ["SUP-0001"]
    df = pd.DataFrame(mock_data)
    results = predictor.predict(df)
    logger.info("LGBM prediction output:")
    print(results[0].model_dump_json(indent=2))

def test_lstm_ae():
    logger.info("=== Testing LSTM Autoencoder Anomaly Predictor ===")
    predictor = get_lstm_predictor()
    # Create mock sequence of 12 steps for 1 supplier with all features
    mock_data = {
        "supplier_id": ["SUP-0001"] * 12,
        "week_num": list(range(1, 13)),
        "prev_lead_time": [10.0, 11.2, 12.0, 10.5, 9.8, 15.6, 10.0, 11.2, 12.0, 10.5, 9.8, 15.6],
        "lead_time_cv": [0.1] * 12,
        "prev_otd": [0.9] * 12,
        "defect_rate": [0.01] * 12,
        "financial_stress_score": [0.2] * 12,
        "capacity_utilization": [0.7] * 12,
        "regional_delay_factor": [0.05] * 12,
        "port_congestion_index": [0.4] * 12,
        "weather_alerts": [0.0] * 12,
        "interest_rate": [0.05] * 12,
        "inflation_index": [1.0] * 12,
        "raw_material_cost": [100.0] * 12,
        "lead_time_volatility_4w": [0.5] * 12,
        "lead_time_volatility_12w": [0.8] * 12
    }
    df = pd.DataFrame(mock_data)
    results = predictor.predict(df)
    logger.info("LSTM Autoencoder prediction output:")
    if results:
        print(results[0].model_dump_json(indent=2))
    else:
        logger.info("No prediction results (empty output).")

def test_tft():
    logger.info("=== Testing TFT Demand Predictor ===")
    predictor = get_tft_predictor()
    
    # Create mock history for 1 SKU of 28 steps (max encoder length)
    n_days = 28
    mock_data = {
        "id": ["item_1"] * n_days,
        "sku_id": ["item_1"] * n_days,
        "item_id": ["item_1"] * n_days,
        "dept_id": ["dept_1"] * n_days,
        "cat_id": ["cat_1"] * n_days,
        "event_name_1": ["None"] * n_days,
        "snap_CA": [0.0] * n_days,
        "sales": [5.0] * n_days,
        "time_idx": list(range(n_days)),
        "lag_1": [5.0] * n_days,
        "lag_7": [5.0] * n_days,
        "lag_14": [5.0] * n_days,
        "lag_28": [5.0] * n_days,
        "rolling_mean_7": [5.0] * n_days,
        "rolling_mean_28": [5.0] * n_days,
        "rolling_std_7": [0.1] * n_days,
    }
    df = pd.DataFrame(mock_data)
    current_inventory = {"item_1": 50.0}
    results = predictor.predict(df, current_inventory)
    logger.info("TFT forecast output:")
    print(results["item_1"].model_dump_json(indent=2))

def main():
    try:
        test_lgbm()
        print("\n" + "="*50 + "\n")
        test_lstm_ae()
        print("\n" + "="*50 + "\n")
        test_tft()
        logger.info("✅ All smoke tests passed successfully!")
    except Exception as e:
        logger.exception("❌ Smoke test failed:")
        sys.exit(1)

if __name__ == "__main__":
    main()
