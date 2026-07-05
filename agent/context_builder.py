"""
SupplyMind — Risk Context Frame Builder (Phase 5: Full Implementation)
Orchestrates ML inference across TFT, LightGBM, and LSTM-AE to build
a unified, structured RiskContextFrame that is the Agent's perception layer.

Data mapping (uses real processed parquet column names):
  - Supplier: supplier_id, week_num, prev_lead_time, prev_otd, prev_po_accept,
               otd_mean_4w, otd_mean_12w, lead_time_mean_4w, lead_time_std_4w,
               lead_time_mean_12w, po_accept_mean_4w, lead_time_slope_6w,
               country, contract_tier, tenure_years
  - Demand: id, item_id, dept_id, cat_id, event_name_1, snap_CA, sales,
            time_idx, lag_1, lag_7, lag_14, lag_28,
            rolling_mean_7, rolling_mean_28, rolling_std_7
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from config import settings
from models.lgbm.predict import get_predictor as get_risk_predictor, SupplierRiskPrediction
from models.tft.predict import get_predictor as get_demand_predictor, DemandForecast
from models.lstm_ae.predict import get_predictor as get_anomaly_predictor, AnomalyPrediction

logger = logging.getLogger(__name__)


def _row_float(row: pd.Series, *keys: str, default: float = 0.0) -> float:
    for key in keys:
        if key in row.index and pd.notna(row[key]):
            return float(row[key])
    return default


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


# ──────────────────────────────────────────────────────────────────────────────
# Pydantic Schemas — the structured perception frame
# ──────────────────────────────────────────────────────────────────────────────

class ShapDriver(BaseModel):
    """A single SHAP feature attribution for plain-language explanation."""
    feature: str
    value: float
    impact: float
    direction: str  # "increases_risk" | "decreases_risk"


class SupplierContext(BaseModel):
    """Complete risk profile for a single supplier in this context."""
    supplier_id: str
    risk_score: float = Field(0.0, ge=0.0, le=1.0)
    risk_level: str = "UNKNOWN"      # NORMAL | ELEVATED | HIGH | CRITICAL
    is_anomaly: bool = False
    reconstruction_error: float = 0.0
    shap_drivers: list[ShapDriver] = []
    # Operational fields (from processed data or derived estimates)
    avg_lead_time_days: float = 30.0
    on_time_delivery_pct: float = 0.0
    po_acceptance_rate: float = 0.0
    lead_time_slope_6w: float = 0.0   # positive = worsening, negative = improving
    unit_cost_estimate: float = 100.0

    @property
    def plain_english_risk(self) -> str:
        """Human-readable risk summary from SHAP drivers."""
        if not self.shap_drivers:
            return f"Risk score: {self.risk_score:.0%}"
        top = self.shap_drivers[0]
        direction_word = "declining" if top.direction == "increases_risk" else "improving"
        return (
            f"{self.risk_level} risk ({self.risk_score:.0%}). "
            f"Key driver: {top.feature.replace('_', ' ')} is {direction_word}."
        )


class DemandSignal(BaseModel):
    """Demand forecast summary for one SKU."""
    sku_id: str
    days_to_stockout_p50: float | None = None
    days_to_stockout_p95: float | None = None
    p05_14day_total: float = 0.0
    p50_14day_total: float = 0.0
    p95_14day_total: float = 0.0
    daily_forecasts: list[dict] = []
    forecast_horizon_days: int = 14

    @property
    def is_stockout_imminent(self) -> bool:
        return self.days_to_stockout_p95 is not None and self.days_to_stockout_p95 < 7

    @property
    def demand_uncertainty_pct(self) -> float:
        """P95 vs P50 spread as % of P50 — measures forecast uncertainty."""
        if self.p50_14day_total <= 0:
            return 0.0
        return (self.p95_14day_total - self.p50_14day_total) / self.p50_14day_total


class RiskContextFrame(BaseModel):
    """
    The complete perception frame for the Agent.
    This is the single source of truth passed to the PolicyEngine.
    """
    # Identity
    sku_id: str
    primary_supplier_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Risk classification
    criticality: str = "TIER_2"           # TIER_1 (critical) | TIER_2 (normal)
    overall_risk_level: str = "NORMAL"    # system-wide rollup

    # Demand intelligence
    demand: DemandSignal

    # Supplier intelligence
    primary_supplier: SupplierContext
    alternative_suppliers: list[SupplierContext] = []

    # Operational context
    current_inventory: int = 0
    budget_authority_usd: float = Field(default_factory=lambda: settings.autonomous_budget_usd)

    @property
    def requires_immediate_action(self) -> bool:
        """True if either stockout is imminent or primary supplier is CRITICAL."""
        return (
            self.demand.is_stockout_imminent
            or self.primary_supplier.risk_level == "CRITICAL"
            or (self.primary_supplier.is_anomaly and self.criticality == "TIER_1")
        )

    @property
    def best_alternative(self) -> SupplierContext | None:
        """Returns the safest, cheapest backup supplier (excluding HIGH/CRITICAL)."""
        valid = [
            s for s in self.alternative_suppliers
            if s.risk_level not in ("CRITICAL", "HIGH") and not s.is_anomaly
        ]
        if not valid:
            return None
        return min(valid, key=lambda s: (s.risk_score, s.unit_cost_estimate))

    def to_agent_prompt(self) -> str:
        """
        Generates a structured natural-language summary of the context frame.
        This can be passed to an LLM for richer reasoning (Phase 6 extension).
        """
        lines = [
            f"=== RISK CONTEXT: SKU {self.sku_id} ===",
            f"Criticality: {self.criticality} | Overall Risk: {self.overall_risk_level}",
            f"Current Inventory: {self.current_inventory:,} units",
            f"",
            f"[DEMAND FORECAST - 14 day horizon]",
            f"  P50 demand: {self.demand.p50_14day_total:.0f} units",
            f"  P95 demand: {self.demand.p95_14day_total:.0f} units",
            f"  Days to stockout (P50): {self.demand.days_to_stockout_p50 or 'N/A (>14 days)'}",
            f"  Days to stockout (P95): {self.demand.days_to_stockout_p95 or 'N/A (>14 days)'}",
            f"  Forecast uncertainty: {self.demand.demand_uncertainty_pct:.0%}",
            f"",
            f"[PRIMARY SUPPLIER: {self.primary_supplier_id}]",
            f"  {self.primary_supplier.plain_english_risk}",
            f"  Lead time: {self.primary_supplier.avg_lead_time_days:.0f} days",
            f"  OTD: {self.primary_supplier.on_time_delivery_pct:.0%}",
            f"  Anomaly detected: {self.primary_supplier.is_anomaly}",
            f"  Lead time trend (6w slope): {'↑ worsening' if self.primary_supplier.lead_time_slope_6w > 0 else '↓ improving'}",
        ]
        if self.alternative_suppliers:
            lines.append(f"\n[ALTERNATIVES ({len(self.alternative_suppliers)} available)]")
            for alt in self.alternative_suppliers[:3]:
                lines.append(f"  {alt.supplier_id}: {alt.risk_level} risk ({alt.risk_score:.0%})")
        best = self.best_alternative
        if best:
            est_cost = self.demand.p95_14day_total * best.unit_cost_estimate
            lines.append(f"\n  Best backup: {best.supplier_id} | Est. cost: ${est_cost:,.0f}")
        lines.append(f"\nBudget authority: ${self.budget_authority_usd:,.0f}")
        return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# Context Builder — the assembly engine
# ──────────────────────────────────────────────────────────────────────────────

class ContextBuilder:
    """
    Assembles a RiskContextFrame by calling all 3 ML models and merging results
    with operational data from the processed supplier dataframe.
    """

    def __init__(self):
        logger.info("Initialising ContextBuilder — loading ML predictors...")
        self.risk_predictor = get_risk_predictor()
        self.anomaly_predictor = get_anomaly_predictor()
        self.demand_predictor = get_demand_predictor()
        logger.info("ContextBuilder ready.")

    # ── Public API ────────────────────────────────────────────────────────────

    def build_frame(
        self,
        *,
        sku_id: str,
        primary_supplier_id: str,
        demand_history_df: pd.DataFrame,
        supplier_processed_df: pd.DataFrame,
        current_inventory: int,
        alternative_supplier_ids: list[str] | None = None,
    ) -> RiskContextFrame:
        """
        Build the complete RiskContextFrame.

        Args:
            sku_id: The SKU being evaluated (maps to 'id' in demand features).
            primary_supplier_id: The main supplier for this SKU.
            demand_history_df: Processed demand features (from demand_features.parquet).
            supplier_processed_df: Processed supplier features (from supplier_train.parquet).
            current_inventory: Current on-hand unit count from ERP/WMS.
            alternative_supplier_ids: Optional list of backup supplier IDs to evaluate.

        Returns:
            RiskContextFrame — complete perception frame for the agent.
        """
        logger.info("Building risk context frame for SKU=%s, Supplier=%s", sku_id, primary_supplier_id)

        alt_ids = alternative_supplier_ids or []
        all_supplier_ids = [primary_supplier_id] + alt_ids

        # ── 1. TFT Demand Forecast ─────────────────────────────────────────
        demand_signal = self._run_demand_forecast(sku_id, demand_history_df, current_inventory)

        # ── 2. LightGBM Risk Score + SHAP ────────────────────────────────
        risk_map = self._run_risk_predictions(all_supplier_ids, supplier_processed_df)

        # ── 3. LSTM-AE Anomaly Detection ─────────────────────────────────
        anomaly_map = self._run_anomaly_detection(all_supplier_ids, supplier_processed_df)

        # ── 4. Assemble supplier contexts ────────────────────────────────
        primary_ctx = self._build_supplier_context(
            primary_supplier_id, risk_map, anomaly_map, supplier_processed_df
        )
        alt_ctxs = [
            self._build_supplier_context(sid, risk_map, anomaly_map, supplier_processed_df)
            for sid in alt_ids
        ]

        # ── 5. Determine criticality ──────────────────────────────────────
        criticality = self._compute_criticality(demand_signal, primary_ctx)
        overall_risk = self._compute_overall_risk(primary_ctx, alt_ctxs, demand_signal)

        frame = RiskContextFrame(
            sku_id=sku_id,
            primary_supplier_id=primary_supplier_id,
            criticality=criticality,
            overall_risk_level=overall_risk,
            demand=demand_signal,
            primary_supplier=primary_ctx,
            alternative_suppliers=alt_ctxs,
            current_inventory=current_inventory,
        )

        logger.info(
            "Frame built | Criticality=%s | Risk=%s | Stockout P95=%s days",
            criticality, overall_risk,
            f"{demand_signal.days_to_stockout_p95:.1f}" if demand_signal.days_to_stockout_p95 else "N/A"
        )
        return frame

    # ── Private Helpers ───────────────────────────────────────────────────────

    def _run_demand_forecast(
        self,
        sku_id: str,
        demand_df: pd.DataFrame,
        current_inventory: int,
    ) -> DemandSignal:
        """Run TFT and return a DemandSignal."""
        # Filter for this SKU
        sku_df = demand_df[demand_df["id"] == sku_id].copy()
        if sku_df.empty:
            logger.warning("No demand history found for SKU=%s, using empty signal.", sku_id)
            return DemandSignal(sku_id=sku_id)

        inv_map = {sku_id: float(current_inventory)}
        try:
            forecasts = self.demand_predictor.predict(sku_df, inv_map)
            raw = forecasts.get(sku_id)
            if raw is None:
                return DemandSignal(sku_id=sku_id)
            return DemandSignal(
                sku_id=sku_id,
                days_to_stockout_p50=raw.days_to_stockout_p50,
                days_to_stockout_p95=raw.days_to_stockout_p95,
                p05_14day_total=raw.p05_14day_total,
                p50_14day_total=raw.p50_14day_total,
                p95_14day_total=raw.p95_14day_total,
                daily_forecasts=raw.daily_forecasts,
            )
        except Exception as exc:
            logger.error("TFT inference failed for SKU=%s: %s", sku_id, exc)
            return DemandSignal(sku_id=sku_id)

    def _run_risk_predictions(
        self,
        supplier_ids: list[str],
        supplier_df: pd.DataFrame,
    ) -> dict[str, SupplierRiskPrediction]:
        """Run LightGBM on the latest record per supplier."""
        # Take most recent record per supplier
        rel_df = supplier_df[supplier_df["supplier_id"].isin(supplier_ids)].copy()
        if rel_df.empty:
            logger.warning("No supplier records found for ids: %s", supplier_ids)
            return {}

        latest_df = (
            rel_df.sort_values("week_num")
            .groupby("supplier_id", as_index=False)
            .last()
        )

        try:
            preds = self.risk_predictor.predict(latest_df)
            return {p.supplier_id: p for p in preds}
        except Exception as exc:
            logger.error("LightGBM inference failed: %s", exc)
            return {}

    def _run_anomaly_detection(
        self,
        supplier_ids: list[str],
        supplier_df: pd.DataFrame,
    ) -> dict[str, AnomalyPrediction]:
        """Run LSTM-AE on the last 6 weeks of sequences per supplier."""
        rel_df = supplier_df[supplier_df["supplier_id"].isin(supplier_ids)].copy()
        if rel_df.empty:
            return {}

        try:
            preds = self.anomaly_predictor.predict(rel_df)
            return {p.supplier_id: p for p in preds}
        except Exception as exc:
            logger.error("LSTM-AE inference failed: %s", exc)
            return {}

    def _build_supplier_context(
        self,
        supplier_id: str,
        risk_map: dict[str, SupplierRiskPrediction],
        anomaly_map: dict[str, AnomalyPrediction],
        supplier_df: pd.DataFrame,
    ) -> SupplierContext:
        """Build a SupplierContext object from all available signals."""
        risk = risk_map.get(supplier_id)
        anomaly = anomaly_map.get(supplier_id)

        # Get latest row for operational fields (using pre-computed cache if available)
        latest_row = supplier_df.__dict__.get("_latest_rows_cache", {}).get(supplier_id)
        if latest_row is None:
            sup_rows = supplier_df[supplier_df["supplier_id"] == supplier_id]
            latest_row = sup_rows.sort_values("week_num").iloc[-1] if not sup_rows.empty else None

        # Extract SHAP drivers (convert from raw dict to ShapDriver)
        shap_drivers = []
        if risk and risk.shap_drivers:
            for d in risk.shap_drivers:
                shap_drivers.append(ShapDriver(
                    feature=d.get("feature", "unknown"),
                    value=_safe_float(d.get("value", 0.0)),
                    impact=_safe_float(d.get("impact", 0.0)),
                    direction=d.get("direction", "increases_risk"),
                ))

        return SupplierContext(
            supplier_id=supplier_id,
            risk_score=risk.risk_score if risk else 0.0,
            risk_level=risk.risk_level if risk else "UNKNOWN",
            is_anomaly=anomaly.is_anomaly if anomaly else False,
            reconstruction_error=anomaly.reconstruction_error if anomaly else 0.0,
            shap_drivers=shap_drivers,
            avg_lead_time_days=_row_float(latest_row, "avg_lead_time_days", "prev_lead_time", "lead_time_mean_4w", default=30.0) if latest_row is not None else 30.0,
            on_time_delivery_pct=_row_float(latest_row, "on_time_delivery_pct", "prev_otd", "otd_mean_4w", default=0.0) if latest_row is not None else 0.0,
            po_acceptance_rate=_row_float(latest_row, "po_acceptance_rate", "prev_po_accept", "po_accept_mean_4w", default=0.0) if latest_row is not None else 0.0,
            lead_time_slope_6w=_row_float(latest_row, "lead_time_slope_6w", default=0.0) if latest_row is not None else 0.0,
            unit_cost_estimate=_row_float(latest_row, "unit_cost", "raw_material_cost", default=100.0) if latest_row is not None else 100.0,
        )

    def _compute_criticality(
        self,
        demand: DemandSignal,
        primary: SupplierContext,
    ) -> str:
        """
        TIER_1 (Critical) if:
          - Stockout expected before next delivery (P95), OR
          - Primary supplier is CRITICAL risk + anomaly detected, OR
          - Less than 3 days of P50 stock remaining
        """
        if demand.days_to_stockout_p95 is not None:
            if demand.days_to_stockout_p95 < primary.avg_lead_time_days:
                return "TIER_1"
        if primary.risk_level == "CRITICAL" and primary.is_anomaly:
            return "TIER_1"
        if demand.days_to_stockout_p50 is not None and demand.days_to_stockout_p50 < 3:
            return "TIER_1"
        return "TIER_2"

    def _compute_overall_risk(
        self,
        primary: SupplierContext,
        alternatives: list[SupplierContext],
        demand: DemandSignal,
    ) -> str:
        """
        Roll up supplier risk + demand risk into a single classification.
        CRITICAL > HIGH > ELEVATED > NORMAL
        """
        # If we have no good alternatives and primary is risky → escalate
        no_safe_backup = not any(
            s.risk_level not in ("CRITICAL", "HIGH") for s in alternatives
        )
        if primary.risk_level == "CRITICAL" and no_safe_backup:
            return "CRITICAL"
        if primary.risk_level in ("CRITICAL", "HIGH"):
            return "HIGH"
        if primary.is_anomaly or demand.is_stockout_imminent:
            return "ELEVATED"
        return "NORMAL"


# Module-level singleton
_builder: ContextBuilder | None = None


def get_context_builder() -> ContextBuilder:
    global _builder
    if _builder is None:
        _builder = ContextBuilder()
    return _builder
