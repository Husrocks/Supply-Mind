"""
SupplyMind — Central Configuration
All settings loaded from environment variables via pydantic-settings.
Access anywhere: from config import settings
"""

from functools import lru_cache
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ────────────────────────────────────────────
    app_name: str = "SupplyMind"
    app_env: Literal["development", "staging", "production"] = "development"
    app_version: str = "0.1.0"
    debug: bool = False   # Fix 8: default to False; do NOT set True in staging/production
    # Fix 8: BOTH debug=True AND allow_auth_bypass=True must be set to bypass JWT.
    # This requires two deliberate opt-ins so a forgotten flag cannot open the API.
    allow_auth_bypass: bool = False
    log_level: str = "INFO"

    # ── API Server ────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"
    secret_key: str = "CHANGE_ME_IN_PRODUCTION"
    access_token_expire_minutes: int = 60

    # ── Database ──────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://supplymind_user:password@localhost:5432/supplymind"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "supplymind"
    postgres_user: str = "supplymind_user"
    postgres_password: str = "password"

    # ── Redis ─────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    # ── MLflow ────────────────────────────────────────────────
    mlflow_tracking_uri: str = "./mlruns"
    mlflow_experiment_name: str = "supplymind"

    # ── Kafka ─────────────────────────────────────────────────
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_supplier_topic: str = "supplier.events"
    kafka_inventory_topic: str = "inventory.alerts"
    kafka_consumer_group: str = "supplymind-agent"

    # ── Agent Scheduling ──────────────────────────────────────
    agent_schedule_hour: int = 3
    agent_schedule_minute: int = 0
    inventory_poll_interval_seconds: int = 7200   # 2 hours
    event_trigger_otd_drop_threshold: float = 0.15
    event_trigger_demand_revision: float = 0.40

    # ── Risk Thresholds ───────────────────────────────────────
    risk_high_threshold: float = 0.75
    risk_critical_threshold: float = 0.85
    stockout_warning_days: int = 14
    autonomous_budget_usd: float = 85_000.0
    anomaly_reconstruction_percentile: int = 95

    # ── External APIs ─────────────────────────────────────────
    kaggle_username: str = ""
    kaggle_key: str = ""
    fred_api_key: str = ""

    # ── Notifications ─────────────────────────────────────────
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    manager_email: str = "manager@supplymind.local"

    # ── Simulated ERP / WMS ───────────────────────────────────
    erp_api_url: str = "http://localhost:8001"
    erp_api_key: str = "mock_erp_key_dev"
    wms_api_url: str = "http://localhost:8002"
    wms_api_key: str = "mock_wms_key_dev"

    # ── Model Paths ───────────────────────────────────────────
    tft_model_path: str = "models/tft/checkpoints/best.ckpt"
    lgbm_model_path: str = "models/lgbm/checkpoints/best.joblib"
    lstm_ae_model_path: str = "models/lstm_ae/checkpoints/best.pt"
    calibrator_path: str = "models/calibration/isotonic_calibrator.joblib"

    # ── Data Paths ────────────────────────────────────────────
    data_raw_dir: str = "data/raw"
    data_processed_dir: str = "data/processed"
    data_synthetic_dir: str = "data/synthetic"
    synthetic_supplier_path: str = "data/synthetic/supplier_dataset.parquet"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache()
def get_settings() -> Settings:
    """Return cached Settings instance. Use this everywhere."""
    import os
    import json
    s = Settings()
    json_path = os.path.join("data", "settings.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in data.items():
                if hasattr(s, k):
                    setattr(s, k, v)
        except Exception:
            pass
    return s


# Module-level singleton for convenience
settings = get_settings()

