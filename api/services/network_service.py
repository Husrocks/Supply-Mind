"""
SupplyMind — Network Dashboard Service
Builds the full Command Center payload from real parquet ML inference,
onboarding DB records, and risk context history.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent.context_builder import get_context_builder
from agent.orchestrator import get_orchestrator
from api.models.db_models import RiskContextLog, SupplierOnboarding

logger = logging.getLogger(__name__)

MAX_SUPPLIERS = 50
MAX_SKUS = 50
MAX_WAREHOUSES = 1

COUNTRY_TO_ALPHA3: dict[str, str] = {
    "USA": "USA",
    "United States": "USA",
    "Germany": "DEU",
    "China": "CHN",
    "Taiwan": "TWN",
    "Mexico": "MEX",
    "Vietnam": "VNM",
    "India": "IND",
    "Canada": "CAN",
    "Nigeria": "NGA",
    "South Korea": "KOR",
    "Korea": "KOR",
    "Japan": "JPN",
    "Brazil": "BRA",
    "UK": "GBR",
    "France": "FRA",
}


def _row_float(row: pd.Series, *keys: str, default: float = 0.0) -> float:
    for key in keys:
        if key in row.index and pd.notna(row[key]):
            return float(row[key])
    return default


def _country_code(raw: Any) -> str | None:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    name = str(raw)
    if hasattr(raw, "cat"):  # pandas categorical
        name = str(raw)
    return COUNTRY_TO_ALPHA3.get(name, name[:3].upper() if len(name) >= 3 else None)


def _concentration_ratio(supplier_id: str, supplier_df: pd.DataFrame) -> float:
    if supplier_df.empty:
        return 0.1
    latest_week = supplier_df["week_num"].max()
    latest = supplier_df[supplier_df["week_num"] == latest_week]
    total = len(latest)
    if total == 0:
        return 0.1
    share = len(latest[latest["supplier_id"] == supplier_id]) / total
    return float(min(0.95, max(0.05, share)))


def _risk_tier_label(level: str) -> str:
    return level.lower() if level else "unknown"


def _plain_english_risk(ctx, geopolitical: float, lead_var: float, quality: float) -> str:
    if ctx.shap_drivers:
        top = ctx.shap_drivers[0]
        return (
            f"Risk driven by {top.feature} ({top.direction.replace('_', ' ')}). "
            f"Score {ctx.risk_score:.0%} ({ctx.risk_level})."
        )
    parts = []
    if geopolitical >= 0.5:
        parts.append("elevated geopolitical exposure")
    if lead_var >= 0.5:
        parts.append("high lead-time variance")
    if quality >= 0.05:
        parts.append(f"quality failure rate {quality:.1%}")
    if ctx.is_anomaly:
        parts.append("LSTM-AE anomaly detected")
    if not parts:
        return f"Stable supplier profile at {ctx.risk_score:.0%} disruption probability."
    return "; ".join(parts).capitalize() + "."


class NetworkDashboardService:
    """Assembles real network-wide risk context for the Command Center."""

    async def build_dashboard(
        self,
        db: AsyncSession,
        agent_triggered: bool = True,
    ) -> dict[str, Any]:
        orchestrator = get_orchestrator()
        supplier_df = orchestrator._load_supplier_data()
        demand_df = orchestrator._load_demand_data()
        builder = get_context_builder()

        if supplier_df.empty:
            return self._empty_dashboard(agent_triggered)

        onboarding_map = await self._load_onboarding(db)

        # Latest row per supplier, pick representative set across countries for dashboard
        latest_rows = (
            supplier_df.sort_values("week_num")
            .groupby("supplier_id", as_index=False)
            .tail(1)
        )
        if "country" in latest_rows.columns:
            # Sort by country and regional_delay_factor descending
            latest_rows = latest_rows.sort_values(
                ["country", "regional_delay_factor"], ascending=[True, False]
            )
            # Group by country and take up to 3 from each to ensure all are represented
            sampled = latest_rows.groupby("country", as_index=False).head(3)
            remaining = latest_rows[~latest_rows["supplier_id"].isin(sampled["supplier_id"])]
            if len(sampled) < MAX_SUPPLIERS and not remaining.empty:
                extra_needed = MAX_SUPPLIERS - len(sampled)
                extra = remaining.sort_values("regional_delay_factor", ascending=False).head(extra_needed)
                sampled = pd.concat([sampled, extra])
            supplier_ids = sampled["supplier_id"].tolist()
        else:
            if "regional_delay_factor" in latest_rows.columns:
                latest_rows = latest_rows.sort_values(
                    "regional_delay_factor", ascending=False
                )
            supplier_ids = latest_rows["supplier_id"].head(MAX_SUPPLIERS).tolist()

        # Load precomputed risks from database
        from api.models.db_models import CachedSupplierRisk
        
        stmt = select(CachedSupplierRisk).where(CachedSupplierRisk.supplier_id.in_(supplier_ids))
        db_res = await db.execute(stmt)
        cached_risks = db_res.scalars().all()
        risk_map_db = {r.supplier_id: r for r in cached_risks}
        
        from models.lgbm.predict import SupplierRiskPrediction
        from models.lstm_ae.predict import AnomalyPrediction
        
        risk_map = {}
        anomaly_map = {}
        
        missing_sids = [sid for sid in supplier_ids if sid not in risk_map_db]
        fb_risks = {}
        fb_anoms = {}
        
        if missing_sids:
            fb_risks = builder._run_risk_predictions(missing_sids, supplier_df)
            fb_anoms = builder._run_anomaly_detection(missing_sids, supplier_df)

        for sid in supplier_ids:
            cached_r = risk_map_db.get(sid)
            if cached_r:
                risk_map[sid] = SupplierRiskPrediction(
                    supplier_id=sid,
                    risk_score=cached_r.risk_score,
                    risk_level=cached_r.risk_level,
                    shap_drivers=cached_r.shap_drivers_json
                )
                anomaly_map[sid] = AnomalyPrediction(
                    supplier_id=sid,
                    reconstruction_error=0.015,
                    is_anomaly=cached_r.is_anomaly,
                    threshold_used=0.0239
                )
            else:
                if fb_risks.get(sid):
                    risk_map[sid] = fb_risks[sid]
                if fb_anoms.get(sid):
                    anomaly_map[sid] = fb_anoms[sid]

        supplier_risks: list[dict[str, Any]] = []
        anomaly_count = 0

        for sid in supplier_ids:
            ctx = builder._build_supplier_context(
                sid, risk_map, anomaly_map, supplier_df
            )
            if ctx.is_anomaly:
                anomaly_count += 1

            sup_rows = supplier_df[supplier_df["supplier_id"] == sid]
            latest = (
                sup_rows.sort_values("week_num").iloc[-1]
                if not sup_rows.empty
                else None
            )
            onboarding = onboarding_map.get(sid, {})

            country_raw = latest["country"] if latest is not None and "country" in latest.index else None
            ob_cc = onboarding.get("country_code")
            country_code = ob_cc if ob_cc in COUNTRY_TO_ALPHA3.values() else _country_code(country_raw)
            geo_region = onboarding.get("geographic_risk_region")

            geopolitical = (
                _row_float(latest, "regional_delay_factor", default=0.15)
                if latest is not None
                else 0.15
            )
            lead_var = 0.1
            if latest is not None:
                mean_lt = _row_float(latest, "lead_time_mean_4w", "prev_lead_time", default=1.0)
                std_lt = _row_float(latest, "lead_time_std_4w", default=0.0)
                lead_var = min(1.0, std_lt / max(mean_lt, 1.0))

            quality = _row_float(latest, "defect_rate", "defect_rate_pct", default=0.02)
            concentration = _concentration_ratio(sid, supplier_df)

            supplier_name = onboarding.get("supplier_name") or (
                f"{country_raw} · {sid}" if country_raw is not None else sid
            )

            supplier_risks.append({
                "supplier_id": sid,
                "supplier_name": supplier_name,
                "risk_score": ctx.risk_score,
                "risk_tier": _risk_tier_label(ctx.risk_level),
                "geopolitical_factor": round(geopolitical, 4),
                "lead_time_variance": round(lead_var, 4),
                "quality_failure_rate": round(quality, 4),
                "concentration_ratio": round(concentration, 4),
                "reasoning": _plain_english_risk(ctx, geopolitical, lead_var, quality),
                "shap_drivers": [d.model_dump() for d in ctx.shap_drivers],
                "avg_lead_time_days": ctx.avg_lead_time_days,
                "on_time_delivery_pct": ctx.on_time_delivery_pct,
                "po_acceptance_rate": ctx.po_acceptance_rate,
                "lead_time_slope_6w": ctx.lead_time_slope_6w,
                "unit_cost_estimate": ctx.unit_cost_estimate,
                "country_code": country_code,
                "geographic_risk_region": geo_region,
                "is_anomaly": ctx.is_anomaly,
            })

        supplier_risks.sort(key=lambda s: s["risk_score"], reverse=True)

        demand_forecasts = await self._build_demand_forecasts(
            db, builder, demand_df, supplier_ids
        )
        supply_flows = self._build_supply_flows(
            supplier_risks, demand_forecasts, demand_df
        )
        warehouse_nodes = [
            {
                "id": "WH-001",
                "name": "Central Distribution Hub",
                "type": "warehouse",
            }
        ]
        network_links = [
            {
                "source": s["supplier_id"],
                "target": "WH-001",
                "volume": s["concentration_ratio"],
            }
            for s in supplier_risks
        ]
        risk_trends = await self._load_risk_trends(db, supplier_ids)

        overall = (
            max(s["risk_score"] for s in supplier_risks)
            if supplier_risks
            else 0.0
        )

        return {
            "context_id": f"ctx-net-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "overall_risk_score": round(overall, 4),
            "anomaly_count": anomaly_count,
            "agent_triggered": agent_triggered,
            "supplier_risks": supplier_risks,
            "demand_forecasts": demand_forecasts,
            "supply_flows": supply_flows,
            "warehouse_nodes": warehouse_nodes,
            "network_links": network_links,
            "risk_trends": risk_trends,
        }

    async def _build_demand_forecasts(
        self,
        db: AsyncSession,
        builder,
        demand_df: pd.DataFrame,
        supplier_ids: list[str],
    ) -> list[dict[str, Any]]:
        if demand_df.empty:
            return []

        sku_ids = demand_df["id"].unique()[:MAX_SKUS].tolist()
        forecasts: list[dict[str, Any]] = []

        from api.models.db_models import CachedSkuDemand
        
        stmt = select(CachedSkuDemand).where(CachedSkuDemand.sku_id.in_(sku_ids))
        db_res = await db.execute(stmt)
        cached_demands = db_res.scalars().all()
        demand_map = {d.sku_id: d for d in cached_demands}

        for sku_id in sku_ids:
            sku_rows = demand_df[demand_df["id"] == sku_id]
            cat_id = (
                str(sku_rows["cat_id"].iloc[-1])
                if not sku_rows.empty and "cat_id" in sku_rows.columns
                else sku_id.split("_")[0]
            )

            cached_d = demand_map.get(sku_id)
            if cached_d:
                forecasts.append({
                    "sku_id": sku_id,
                    "sku_name": f"SKU {cat_id} · {sku_id[-8:]}",
                    "forecast_units": round(cached_d.p50_total, 0),
                    "actual_units": None,
                    "forecast_horizon_days": 14,
                    "confidence_lower": round(cached_d.p05_total, 0),
                    "confidence_upper": round(cached_d.p95_total, 0),
                    "mape": None,
                    "model_used": "TFT",
                    "category": cat_id,
                })
            else:
                try:
                    signal = builder._run_demand_forecast(
                        sku_id, demand_df, current_inventory=5000
                    )
                    actual = None
                    mape = None
                    if not sku_rows.empty and "sales" in sku_rows.columns:
                        recent = sku_rows.sort_values("d").tail(14)
                        actual = float(recent["sales"].sum())
                        if signal.p50_14day_total > 0 and actual is not None:
                            mape = abs(actual - signal.p50_14day_total) / signal.p50_14day_total * 100

                    forecasts.append({
                        "sku_id": sku_id,
                        "sku_name": f"SKU {cat_id} · {sku_id[-8:]}",
                        "forecast_units": round(signal.p50_14day_total, 0),
                        "actual_units": round(actual, 0) if actual is not None else None,
                        "forecast_horizon_days": signal.forecast_horizon_days,
                        "confidence_lower": round(signal.p05_14day_total, 0),
                        "confidence_upper": round(signal.p95_14day_total, 0),
                        "mape": round(mape, 2) if mape is not None else None,
                        "model_used": "TFT",
                        "category": cat_id,
                    })
                except Exception as exc:
                    logger.warning("Demand forecast failed for %s: %s", sku_id, exc)
                    if sku_rows.empty or "sales" not in sku_rows.columns:
                        continue
                    recent = sku_rows.sort_values("d").tail(14)
                    prior = sku_rows.sort_values("d").tail(28).head(14)
                    p50 = float(recent["sales"].sum())
                    p_prior = float(prior["sales"].sum()) if not prior.empty else p50
                    spread = abs(p50 - p_prior) / max(p50, 1.0)
                    forecasts.append({
                        "sku_id": sku_id,
                        "sku_name": f"SKU {cat_id} · {sku_id[-8:]}",
                        "forecast_units": round(p50, 0),
                        "actual_units": round(p50, 0),
                        "forecast_horizon_days": 14,
                        "confidence_lower": round(p50 * (1 - spread), 0),
                        "confidence_upper": round(p50 * (1 + spread), 0),
                        "mape": None,
                        "model_used": "parquet_rolling",
                        "category": cat_id,
                    })

        return forecasts

    def _build_supply_flows(
        self,
        supplier_risks: list[dict[str, Any]],
        demand_forecasts: list[dict[str, Any]],
        demand_df: pd.DataFrame,
    ) -> list[dict[str, Any]]:
        if not supplier_risks or not demand_forecasts:
            return []

        warehouse = "Central Distribution Hub"
        flows: list[dict[str, Any]] = []

        for i, supplier in enumerate(supplier_risks):
            forecast = demand_forecasts[i % len(demand_forecasts)]
            category = forecast.get("category") or forecast["sku_id"].split("_")[0]
            vol = max(1, round(supplier["concentration_ratio"] * 100))

            flows.append({
                "supplier_id": supplier["supplier_id"],
                "supplier_name": supplier["supplier_name"],
                "category": str(category),
                "warehouse": warehouse,
                "volume": vol,
                "risk_score": supplier["risk_score"],
            })

        return flows

    async def _load_onboarding(self, db: AsyncSession) -> dict[str, dict[str, Any]]:
        result = await db.execute(select(SupplierOnboarding))
        records = result.scalars().all()
        out: dict[str, dict[str, Any]] = {}
        for rec in records:
            out[rec.supplier_id] = {
                "supplier_name": rec.supplier_name,
                "geographic_risk_region": rec.geographic_risk_region,
                "country_code": _country_code(rec.geographic_risk_region),
            }
        return out

    async def _load_risk_trends(
        self,
        db: AsyncSession,
        supplier_ids: list[str],
    ) -> dict[str, list[float]]:
        if not supplier_ids:
            return {}

        stmt = (
            select(RiskContextLog)
            .where(RiskContextLog.supplier_id.in_(supplier_ids))
            .order_by(RiskContextLog.created_at.desc())
            .limit(500)
        )
        result = await db.execute(stmt)
        logs = result.scalars().all()

        trends: dict[str, list[float]] = {sid: [] for sid in supplier_ids}
        seen: dict[str, int] = {sid: 0 for sid in supplier_ids}

        for log in logs:
            sid = log.supplier_id
            if sid not in trends or seen[sid] >= 12:
                continue
            trends[sid].append(log.risk_score)
            seen[sid] += 1

        # Oldest-first for sparklines
        for sid in trends:
            trends[sid] = list(reversed(trends[sid]))

        return trends

    def _empty_dashboard(self, agent_triggered: bool) -> dict[str, Any]:
        return {
            "context_id": "ctx-empty",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "overall_risk_score": 0.0,
            "anomaly_count": 0,
            "agent_triggered": agent_triggered,
            "supplier_risks": [],
            "demand_forecasts": [],
            "supply_flows": [],
            "warehouse_nodes": [{"id": "WH-001", "name": "Central Distribution Hub", "type": "warehouse"}],
            "network_links": [],
            "risk_trends": {},
        }


network_dashboard_service = NetworkDashboardService()
