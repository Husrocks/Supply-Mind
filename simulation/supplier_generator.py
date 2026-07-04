"""
SupplyMind — Synthetic Supplier Dataset Generator
Generates a realistic multi-dimensional supplier risk dataset with:
- 500 suppliers × 36 months of monthly snapshots
- Features: OTD, quality defect rate, financial stress, geo-political exposure,
  lead time variability, capacity utilization, ESG score, etc.
- Target: binary disruption flag (≥ 1 stockout event in next 4 weeks)
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# Supplier archetypes (probabilities over risk profile)
# ──────────────────────────────────────────────────────────────
ARCHETYPES = {
    "reliable":      dict(weight=0.40, base_otd=0.95, base_defect=0.01, base_fin_stress=0.10),
    "volatile":      dict(weight=0.20, base_otd=0.78, base_defect=0.05, base_fin_stress=0.35),
    "improving":     dict(weight=0.15, base_otd=0.82, base_defect=0.03, base_fin_stress=0.20),
    "declining":     dict(weight=0.15, base_otd=0.88, base_defect=0.02, base_fin_stress=0.15),
    "high_risk":     dict(weight=0.10, base_otd=0.65, base_defect=0.09, base_fin_stress=0.55),
}

GEOPOLITICAL_REGIONS = [
    ("North America", 0.05),
    ("Western Europe", 0.08),
    ("Eastern Europe", 0.20),
    ("East Asia", 0.15),
    ("Southeast Asia", 0.25),
    ("South Asia", 0.22),
    ("Latin America", 0.18),
    ("Middle East", 0.30),
    ("Africa", 0.28),
]

CATEGORIES = [
    "Electronics", "Mechanical", "Raw Materials", "Chemicals",
    "Packaging", "Textiles", "Food Grade", "Pharma", "Automotive",
]

# ──────────────────────────────────────────────────────────────
# Helper utilities
# ──────────────────────────────────────────────────────────────

def _stable_rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


def _supplier_id(idx: int) -> str:
    digest = hashlib.md5(str(idx).encode()).hexdigest()[:6].upper()
    return f"SUP-{digest}"


def _archetype_sample(rng: np.random.Generator) -> tuple[str, dict]:
    names = list(ARCHETYPES.keys())
    weights = [ARCHETYPES[n]["weight"] for n in names]
    chosen = rng.choice(names, p=weights)
    return chosen, ARCHETYPES[chosen]


def _region_sample(rng: np.random.Generator) -> tuple[str, float]:
    regions = [r[0] for r in GEOPOLITICAL_REGIONS]
    risk    = np.array([r[1] for r in GEOPOLITICAL_REGIONS])
    risk    = risk / risk.sum()
    idx = rng.choice(len(regions), p=risk)
    return regions[idx], GEOPOLITICAL_REGIONS[idx][1]


# ──────────────────────────────────────────────────────────────
# Core generator
# ──────────────────────────────────────────────────────────────

@dataclass
class SupplierGeneratorConfig:
    n_suppliers: int = 500
    n_months: int = 36
    start_date: date = date(2021, 1, 1)
    disruption_base_rate: float = 0.08     # ~8% base monthly disruption probability
    random_seed: int = 42
    noise_scale: float = 0.04


class SupplierDataGenerator:
    """Generates synthetic supplier risk time-series data."""

    def __init__(self, cfg: SupplierGeneratorConfig | None = None):
        self.cfg = cfg or SupplierGeneratorConfig()
        self._rng = _stable_rng(self.cfg.random_seed)

    # ── Public ──────────────────────────────────────────────

    def generate(self) -> pd.DataFrame:
        """Return a tidy DataFrame with one row per (supplier, month)."""
        logger.info("Generating synthetic supplier data: %d suppliers × %d months",
                    self.cfg.n_suppliers, self.cfg.n_months)
        records: list[dict] = []
        for sup_idx in range(self.cfg.n_suppliers):
            records.extend(self._simulate_supplier(sup_idx))
        df = pd.DataFrame(records)
        df = self._add_lag_features(df)
        df = self._add_disruption_label(df)
        logger.info("Generated %d rows, disruption rate=%.2f%%",
                    len(df), df["disrupted"].mean() * 100)
        return df

    # ── Private ─────────────────────────────────────────────

    def _simulate_supplier(self, idx: int) -> list[dict]:
        rng = _stable_rng(self.cfg.random_seed + idx * 1000)
        sup_id = _supplier_id(idx)
        archetype, arch_params = _archetype_sample(rng)
        region, geo_risk = _region_sample(rng)
        category = rng.choice(CATEGORIES)
        annual_revenue_m = float(rng.uniform(5, 2000))     # $5M–$2B
        years_relationship = int(rng.integers(1, 20))
        single_source = bool(rng.random() < 0.25)

        # Trend direction for "improving" / "declining" archetypes
        trend = 0.0
        if archetype == "improving":
            trend = 0.005
        elif archetype == "declining":
            trend = -0.004

        # Seasonal pattern
        months = pd.date_range(self.cfg.start_date, periods=self.cfg.n_months, freq="MS")
        rows = []
        for t, month_date in enumerate(months):
            season_factor = 0.03 * np.sin(2 * np.pi * t / 12)
            noise = self.cfg.noise_scale

            otd = float(np.clip(
                arch_params["base_otd"] + trend * t + season_factor
                + rng.normal(0, noise),
                0.40, 1.0
            ))
            defect_rate = float(np.clip(
                arch_params["base_defect"] - trend * t * 0.5
                + rng.normal(0, noise / 4),
                0.0, 0.30
            ))
            fin_stress = float(np.clip(
                arch_params["base_fin_stress"] - trend * t * 0.3
                + rng.normal(0, noise),
                0.0, 1.0
            ))
            lead_time_days = float(np.clip(
                rng.normal(30, 8) + (1 - otd) * 20,
                5, 120
            ))
            lead_time_cv = float(np.clip(rng.exponential(0.15), 0.0, 0.80))
            capacity_util = float(np.clip(rng.normal(0.72, 0.12), 0.20, 1.0))
            esg_score = float(np.clip(rng.normal(65, 15), 10, 100))
            invoice_disputes = int(rng.poisson(0.8 * (1 + fin_stress)))
            open_pos = int(rng.poisson(5 + capacity_util * 10))
            backorder_rate = float(np.clip(
                (1 - otd) * 0.5 + rng.normal(0, 0.03), 0.0, 0.60
            ))
            price_index = float(np.clip(rng.normal(100, 5) + fin_stress * 10, 70, 150))
            natural_disaster_flag = int(rng.random() < 0.04)
            political_stability = float(np.clip(1 - geo_risk + rng.normal(0, 0.05), 0.0, 1.0))

            rows.append({
                "supplier_id": sup_id,
                "month": month_date.date(),
                "archetype": archetype,
                "region": region,
                "category": category,
                "annual_revenue_m": annual_revenue_m,
                "years_relationship": years_relationship,
                "single_source": single_source,
                "otd_rate": otd,
                "defect_rate": defect_rate,
                "financial_stress_score": fin_stress,
                "lead_time_days": lead_time_days,
                "lead_time_cv": lead_time_cv,
                "capacity_utilization": capacity_util,
                "esg_score": esg_score,
                "invoice_disputes": invoice_disputes,
                "open_purchase_orders": open_pos,
                "backorder_rate": backorder_rate,
                "price_index": price_index,
                "natural_disaster_flag": natural_disaster_flag,
                "political_stability": political_stability,
                "geo_risk_base": geo_risk,
                "t": t,
            })
        return rows

    @staticmethod
    def _add_lag_features(df: pd.DataFrame) -> pd.DataFrame:
        """Add 1-month and 3-month lag features per supplier."""
        df = df.sort_values(["supplier_id", "month"]).reset_index(drop=True)
        lag_cols = ["otd_rate", "defect_rate", "financial_stress_score",
                    "capacity_utilization", "backorder_rate"]
        for col in lag_cols:
            df[f"{col}_lag1"] = df.groupby("supplier_id")[col].shift(1)
            df[f"{col}_lag3"] = df.groupby("supplier_id")[col].shift(3)
            df[f"{col}_rolling3"] = (
                df.groupby("supplier_id")[col]
                  .transform(lambda x: x.rolling(3, min_periods=1).mean())
            )
        return df

    def _add_disruption_label(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Stochastic disruption label.
        P(disruption) is driven by OTD drop, financial stress, geo risk,
        capacity, and a random shock component.
        """
        rng = _stable_rng(self.cfg.random_seed + 99999)

        p_disruption = (
            self.cfg.disruption_base_rate
            + 0.30 * (1 - df["otd_rate"])
            + 0.25 * df["financial_stress_score"]
            + 0.15 * df["geo_risk_base"]
            + 0.10 * (df["capacity_utilization"] - 0.70).clip(0)
            + 0.10 * df["defect_rate"] * 5
            + 0.08 * df["single_source"].astype(float)
            + 0.05 * df["natural_disaster_flag"].astype(float)
        ).clip(0.02, 0.90)

        u = rng.random(len(df))
        df["disrupted"] = (u < p_disruption).astype(int)

        # Lead-time disruption severity (0.0–1.0)
        df["disruption_severity"] = np.where(
            df["disrupted"] == 1,
            np.clip(rng.exponential(0.4, len(df)), 0.1, 1.0),
            0.0,
        )
        return df
