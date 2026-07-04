"""
SupplyMind — Demand Time-Series Generator
Generates synthetic M5-style demand data for TFT training when Kaggle
credentials are unavailable. Produces SKU-level daily sales with trend,
seasonality, promotions, and stockout events.
"""

from __future__ import annotations

import logging
from datetime import date

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

STORES = ["STORE_01", "STORE_02", "STORE_03", "STORE_04", "STORE_05"]
CATEGORIES = ["FOODS", "HOUSEHOLD", "HOBBIES"]
DEPTS = {
    "FOODS":     ["FOODS_1", "FOODS_2", "FOODS_3"],
    "HOUSEHOLD": ["HOUSEHOLD_1", "HOUSEHOLD_2"],
    "HOBBIES":   ["HOBBIES_1", "HOBBIES_2"],
}


class DemandSeriesGenerator:
    """Generates synthetic daily demand time-series for TFT training."""

    def __init__(
        self,
        n_skus: int = 200,
        n_days: int = 1_000,
        start_date: date = date(2021, 1, 1),
        random_seed: int = 42,
    ):
        self.n_skus = n_skus
        self.n_days = n_days
        self.start_date = start_date
        self.rng = np.random.default_rng(random_seed)

    def generate(self) -> pd.DataFrame:
        logger.info("Generating %d SKU × %d day demand series", self.n_skus, self.n_days)
        dates = pd.date_range(self.start_date, periods=self.n_days, freq="D")
        records = []
        for sku_idx in range(self.n_skus):
            sku_id = f"SKU_{sku_idx:04d}"
            store   = self.rng.choice(STORES)
            cat     = self.rng.choice(CATEGORIES)
            dept    = self.rng.choice(DEPTS[cat])
            base_demand = float(self.rng.uniform(5, 120))
            trend_slope = float(self.rng.normal(0, 0.005))

            for t, d in enumerate(dates):
                day_of_week  = d.dayofweek            # 0=Mon
                month_of_year = d.month

                # Components
                trend     = base_demand * (1 + trend_slope * t)
                weekly    = base_demand * 0.15 * np.sin(2 * np.pi * day_of_week / 7)
                seasonal  = base_demand * 0.20 * np.sin(2 * np.pi * (month_of_year - 1) / 12)
                
                # New External Covariates: Weather and Holidays
                holiday_flag = 1 if (self.rng.random() < 0.03) else 0
                promo     = base_demand * 0.30 if (self.rng.random() < 0.06 or holiday_flag) else 0.0
                
                # Simulate weather: colder in winter, hotter in summer
                base_temp = 15.0 + 10.0 * np.sin(2 * np.pi * (d.dayofyear - 100) / 365)
                temperature_c = base_temp + self.rng.normal(0, 3.0)
                
                # Add weather and holiday effects to demand
                weather_effect = base_demand * 0.05 * (temperature_c - 15.0) / 10.0 if cat == "HOBBIES" else 0.0
                holiday_effect = base_demand * 0.40 * holiday_flag

                stockout  = 1 if (self.rng.random() < 0.02) else 0

                demand_raw = trend + weekly + seasonal + promo + weather_effect + holiday_effect
                demand_raw *= (1 + self.rng.normal(0, 0.10))   # noise
                demand = max(0.0, demand_raw) * (1 - stockout)
                sell_price = float(self.rng.uniform(1.5, 45.0))

                records.append({
                    "sku_id":        sku_id,
                    "store_id":      store,
                    "category":      cat,
                    "dept":          dept,
                    "date":          d.date(),
                    "demand":        round(max(0.0, demand)),
                    "sell_price":    round(sell_price, 2),
                    "is_promo":      int(promo > 0),
                    "stockout_flag": stockout,
                    "holiday_flag":  holiday_flag,
                    "temperature_c": round(temperature_c, 1),
                    "day_of_week":   day_of_week,
                    "month":         month_of_year,
                    "day_of_year":   d.dayofyear,
                    "week_of_year":  d.isocalendar().week,
                    "t":             t,
                })

        df = pd.DataFrame(records)
        logger.info("Generated demand dataframe: shape=%s", df.shape)
        return df
