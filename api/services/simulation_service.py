"""
SupplyMind — Simulation Service (What-If & Supplier Disruption)
Implements transparent, lightweight, data-grounded scenario calculations
without expensive repeated neural network retraining.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.db_models import (
    InventoryLevel,
    CachedSkuDemand,
    CachedSupplierRisk,
    SupplierOnboarding,
    ReorderRecommendationStatus,
)
from api.schemas.interactive_schemas import (
    WhatIfRequest,
    WhatIfResponse,
    DailyTrajectoryPoint,
    DriverAttribution,
    DisruptionRequest,
    DisruptionResponse,
    AffectedSkuItem,
    SupplierOption,
    MitigationRecommendation,
)

logger = logging.getLogger(__name__)

DEFAULT_LEAD_TIME_DAYS = 25
ESTIMATED_UNIT_COST_USD = 45.0


class SimulationService:
    """Provides what-if scenario forecasting and supplier disruption analysis."""

    async def simulate_what_if(
        self,
        request: WhatIfRequest,
        db: AsyncSession,
    ) -> WhatIfResponse:
        sku_id = request.sku_id
        now_str = datetime.now(timezone.utc).isoformat()

        # 1. Fetch current inventory from DB
        inv_stmt = select(InventoryLevel).where(InventoryLevel.sku_id == sku_id)
        inv_res = await db.execute(inv_stmt)
        inv_record = inv_res.scalar_one_or_none()
        base_inventory = float(inv_record.units_on_hand) if inv_record else 4800.0

        # 2. Fetch baseline demand quantiles
        demand_stmt = select(CachedSkuDemand).where(CachedSkuDemand.sku_id == sku_id)
        demand_res = await db.execute(demand_stmt)
        cached_demand = demand_res.scalar_one_or_none()

        if cached_demand and cached_demand.p50_total > 0:
            base_daily_demand = max(5.0, round(cached_demand.p50_total / 14.0, 2))
            uncertainty_spread = max(2.0, cached_demand.p95_total - cached_demand.p05_total)
            demand_std = uncertainty_spread / (2.0 * 1.645)
        else:
            base_daily_demand = 85.0
            demand_std = 18.0

        # 3. Determine Supplier details
        supplier_id = request.supplier_id or "SUP-0001"
        sup_risk_stmt = select(CachedSupplierRisk).where(CachedSupplierRisk.supplier_id == supplier_id)
        sup_risk_res = await db.execute(sup_risk_stmt)
        cached_risk = sup_risk_res.scalar_one_or_none()
        
        ob_stmt = select(SupplierOnboarding).where(SupplierOnboarding.supplier_id == supplier_id)
        ob_res = await db.execute(ob_stmt)
        ob_record = ob_res.scalar_one_or_none()

        supplier_name = ob_record.supplier_name if ob_record else f"Supplier {supplier_id}"
        base_risk_score = cached_risk.risk_score if cached_risk else 0.22
        base_risk_tier = (cached_risk.risk_level if cached_risk else "LOW").upper()
        base_lead_time = DEFAULT_LEAD_TIME_DAYS

        # Baseline ROP & coverage
        base_safety_stock = int(1.65 * demand_std * math.sqrt(base_lead_time))
        base_rop = int((base_daily_demand * base_lead_time) + base_safety_stock)
        base_days_coverage = round(base_inventory / max(base_daily_demand, 0.01), 1)

        # 4. Calculate Simulated Values
        demand_multiplier = 1.0 + (request.demand_change_pct / 100.0)
        sim_daily_demand = max(1.0, round(base_daily_demand * demand_multiplier, 2))

        sim_inventory = (
            float(request.inventory_override)
            if request.inventory_override is not None
            else base_inventory
        )

        # Disruption capacity factor extends the effective replenishment delay
        disrupt_severity = max(0.0, min(100.0, request.supplier_disruption_pct)) / 100.0
        disruption_lead_delay = int(round(disrupt_severity * 20.0))
        sim_effective_lead_time = base_lead_time + request.lead_time_increase_days + disruption_lead_delay

        sim_safety_stock = int(1.65 * (demand_std * demand_multiplier) * math.sqrt(max(1, sim_effective_lead_time)))
        sim_rop = int((sim_daily_demand * sim_effective_lead_time) + sim_safety_stock)
        sim_days_coverage = round(sim_inventory / max(sim_daily_demand, 0.01), 1)

        # Deltas
        delta_coverage = round(sim_days_coverage - base_days_coverage, 1)
        coverage_gap = round(sim_effective_lead_time - sim_days_coverage, 1)
        is_stockout_within_replenishment = sim_days_coverage < sim_effective_lead_time

        # Simulated Risk Tier
        if sim_days_coverage < sim_effective_lead_time or sim_days_coverage < 10.0:
            sim_risk_tier = "CRITICAL"
        elif sim_days_coverage < (sim_effective_lead_time * 1.35) or sim_days_coverage < 21.0:
            sim_risk_tier = "ELEVATED"
        else:
            sim_risk_tier = "NORMAL"

        # 5. Build 30-day projection trajectory
        trajectory: list[DailyTrajectoryPoint] = []
        stockout_day: int | None = None

        for day in range(0, 31):
            base_inv_day = max(0.0, round(base_inventory - (base_daily_demand * day), 1))
            sim_inv_day = max(0.0, round(sim_inventory - (sim_daily_demand * day), 1))
            if sim_inv_day <= 0.0 and stockout_day is None and day > 0:
                stockout_day = day

            trajectory.append(
                DailyTrajectoryPoint(
                    day=day,
                    baseline_inventory=base_inv_day,
                    simulated_inventory=sim_inv_day,
                )
            )

        # 6. Driver Impact Attribution
        drivers: list[DriverAttribution] = []

        # Demand impact
        demand_coverage_only = base_inventory / max(sim_daily_demand, 0.01)
        demand_days_delta = round(demand_coverage_only - base_days_coverage, 1)
        if abs(request.demand_change_pct) > 0.01:
            drivers.append(
                DriverAttribution(
                    factor="Demand Shift",
                    impact_days=demand_days_delta,
                    direction="reduces_runway" if demand_days_delta < 0 else "increases_runway",
                    description=f"{request.demand_change_pct:+.1f}% change in daily demand shifts runway by {demand_days_delta:+.1f} days.",
                )
            )

        # Lead time increase impact
        if request.lead_time_increase_days > 0:
            drivers.append(
                DriverAttribution(
                    factor="Supplier Lead Time Delay",
                    impact_days=-float(request.lead_time_increase_days),
                    direction="reduces_runway",
                    description=f"+{request.lead_time_increase_days} days added to supplier transit extends replenishment exposure window.",
                )
            )

        # Inventory override impact
        if request.inventory_override is not None:
            inv_delta_days = round((request.inventory_override - base_inventory) / max(base_daily_demand, 0.01), 1)
            drivers.append(
                DriverAttribution(
                    factor="Inventory Override",
                    impact_days=inv_delta_days,
                    direction="increases_runway" if inv_delta_days > 0 else "reduces_runway",
                    description=f"Inventory level set to {request.inventory_override:,} units ({inv_delta_days:+.1f} days equivalent runway).",
                )
            )

        # Supplier disruption impact
        if request.supplier_disruption_pct > 0:
            drivers.append(
                DriverAttribution(
                    factor="Supplier Disruption",
                    impact_days=-float(disruption_lead_delay),
                    direction="reduces_runway",
                    description=f"{request.supplier_disruption_pct:.0f}% capacity reduction introduces approx +{disruption_lead_delay} days delivery lag.",
                )
            )

        # Formulate primary explanation
        if not drivers:
            primary_driver_explanation = "Inputs match baseline conditions. Operational trajectory remains stable."
        else:
            most_negative = min(drivers, key=lambda d: d.impact_days)
            if is_stockout_within_replenishment:
                primary_driver_explanation = (
                    f"CRITICAL WARNING: Simulated stockout occurs in ~{sim_days_coverage:.1f} days, "
                    f"which is {coverage_gap:.1f} days BEFORE replenishment can arrive ({sim_effective_lead_time} days lead time). "
                    f"The primary driver is {most_negative.factor.lower()} ({most_negative.impact_days:+.1f} days runway)."
                )
            else:
                primary_driver_explanation = (
                    f"Under simulated conditions, inventory coverage stands at {sim_days_coverage:.1f} days. "
                    f"The dominant driver is {most_negative.factor.lower()}, impacting runway by {most_negative.impact_days:+.1f} days."
                )

        assumptions_summary = (
            f"Daily Demand: {base_daily_demand:.1f} → {sim_daily_demand:.1f} units/day | "
            f"Lead Time: {base_lead_time}d → {sim_effective_lead_time}d | "
            f"Starting Stock: {int(sim_inventory):,} units | "
            f"Supplier Disruption: {request.supplier_disruption_pct:.0f}%"
        )

        return WhatIfResponse(
            sku_id=sku_id,
            supplier_id=supplier_id,
            supplier_name=supplier_name,
            assumptions_summary=assumptions_summary,
            baseline_inventory=base_inventory,
            baseline_daily_demand=base_daily_demand,
            baseline_lead_time_days=base_lead_time,
            baseline_days_to_stockout=base_days_coverage,
            baseline_risk_tier=base_risk_tier,
            baseline_reorder_point=base_rop,
            simulated_inventory=sim_inventory,
            simulated_daily_demand=sim_daily_demand,
            simulated_effective_lead_time_days=sim_effective_lead_time,
            simulated_days_to_stockout=sim_days_coverage,
            simulated_risk_tier=sim_risk_tier,
            simulated_reorder_point=sim_rop,
            delta_days_to_stockout=delta_coverage,
            coverage_gap_days=coverage_gap,
            stockout_day=stockout_day,
            is_stockout_within_replenishment=is_stockout_within_replenishment,
            drivers=drivers,
            primary_driver_explanation=primary_driver_explanation,
            trajectory=trajectory,
            timestamp=now_str,
            is_simulated_estimate=True,
        )

    async def simulate_supplier_disruption(
        self,
        request: DisruptionRequest,
        db: AsyncSession,
    ) -> DisruptionResponse:
        supplier_id = request.supplier_id
        duration_days = request.duration_days
        severity_pct = request.severity_pct
        now_str = datetime.now(timezone.utc).isoformat()

        # 1. Fetch supplier baseline profile
        sup_risk_stmt = select(CachedSupplierRisk).where(CachedSupplierRisk.supplier_id == supplier_id)
        sup_risk_res = await db.execute(sup_risk_stmt)
        cached_risk = sup_risk_res.scalar_one_or_none()

        ob_stmt = select(SupplierOnboarding).where(SupplierOnboarding.supplier_id == supplier_id)
        ob_res = await db.execute(ob_stmt)
        ob_record = ob_res.scalar_one_or_none()

        supplier_name = ob_record.supplier_name if ob_record else f"Supplier {supplier_id}"
        baseline_score = cached_risk.risk_score if cached_risk else 0.25
        baseline_tier = (cached_risk.risk_level if cached_risk else "LOW").upper()

        # Disrupted risk calculation
        severity_factor = severity_pct / 100.0
        disrupted_score = min(0.99, round(baseline_score + (0.50 * severity_factor), 2))
        disrupted_tier = "CRITICAL" if disrupted_score >= 0.75 else "ELEVATED"

        # 2. Identify SKUs associated with or impacted in network
        # We query the inventory levels and demand features
        inv_stmt = select(InventoryLevel).limit(15)
        inv_res = await db.execute(inv_stmt)
        inv_records = inv_res.scalars().all()

        demand_stmt = select(CachedSkuDemand)
        demand_res = await db.execute(demand_stmt)
        demand_map = {d.sku_id: d for d in demand_res.scalars().all()}

        affected_skus: list[AffectedSkuItem] = []
        total_shortfall = 0
        total_exposure_val = 0.0
        critical_count = 0

        for inv in inv_records:
            d_cached = demand_map.get(inv.sku_id)
            daily_burn = (d_cached.p50_total / 14.0) if (d_cached and d_cached.p50_total > 0) else 65.0
            daily_burn = max(1.0, round(daily_burn, 1))

            stock_left = inv.units_on_hand
            runway_days = round(stock_left / daily_burn, 1)

            stockout_during_disruption = runway_days < duration_days
            stockout_day = int(math.floor(runway_days)) if stockout_during_disruption else None

            if stockout_during_disruption:
                deficit_days = duration_days - runway_days
                shortfall_units = int(round(deficit_days * daily_burn * severity_factor))
                critical_count += 1
            else:
                shortfall_units = 0

            sku_exposure_val = round(shortfall_units * ESTIMATED_UNIT_COST_USD, 2)
            total_shortfall += shortfall_units
            total_exposure_val += sku_exposure_val

            affected_skus.append(
                AffectedSkuItem(
                    sku_id=inv.sku_id,
                    current_units_on_hand=stock_left,
                    daily_consumption=daily_burn,
                    days_of_stock_remaining=runway_days,
                    stockout_expected_within_disruption=stockout_during_disruption,
                    stockout_day=stockout_day,
                    projected_shortfall_units=shortfall_units,
                    estimated_value_exposure_usd=sku_exposure_val,
                )
            )

        # Sort affected SKUs by shortest runway first
        affected_skus.sort(key=lambda s: s.days_of_stock_remaining)

        # 3. Alternative Supplier Candidates
        # Query active suppliers other than the disrupted one
        alt_stmt = (
            select(CachedSupplierRisk)
            .where(CachedSupplierRisk.supplier_id != supplier_id)
            .order_by(CachedSupplierRisk.risk_score.asc())
            .limit(5)
        )
        alt_res = await db.execute(alt_stmt)
        alt_risks = alt_res.scalars().all()

        ob_all_stmt = select(SupplierOnboarding)
        ob_all_res = await db.execute(ob_all_stmt)
        ob_all_map = {o.supplier_id: o for o in ob_all_res.scalars().all()}

        alternative_candidates: list[SupplierOption] = []
        for alt in alt_risks:
            ob = ob_all_map.get(alt.supplier_id)
            alt_name = ob.supplier_name if ob else f"Supplier {alt.supplier_id}"
            
            # Label capacity realistically without hallucinating unverified throughput
            has_ob_capacity = bool(ob and ob.capacity_info and len(ob.capacity_info) > 0)
            capacity_label = (
                "Verified throughput available"
                if (has_ob_capacity and alt.risk_score < 0.35)
                else "Capacity unverified — confirmation required before order placement"
            )

            alternative_candidates.append(
                SupplierOption(
                    supplier_id=alt.supplier_id,
                    supplier_name=alt_name,
                    risk_score=round(alt.risk_score, 2),
                    risk_tier=alt.risk_level.upper(),
                    lead_time_days=28 if alt.risk_score < 0.40 else 35,
                    estimated_unit_cost=round(ESTIMATED_UNIT_COST_USD * (1.0 + (alt.risk_score * 0.1)), 2),
                    is_preferred=alt.risk_score < 0.30,
                    capacity_status=capacity_label,
                )
            )

        # 4. Tailored Mitigation Recommendations
        recommended_mitigations: list[MitigationRecommendation] = []

        if alternative_candidates:
            best_alt = alternative_candidates[0]
            recommended_mitigations.append(
                MitigationRecommendation(
                    title=f"Re-route Replenishment POs to {best_alt.supplier_name}",
                    priority="HIGH" if critical_count > 0 else "MEDIUM",
                    action_type="SPLIT_PURCHASE_ORDER",
                    description=(
                        f"Divert incoming purchase orders from {supplier_name} to qualified secondary supplier "
                        f"{best_alt.supplier_name} ({best_alt.supplier_id}, risk: {best_alt.risk_score:.0%}). "
                        f"Est. lead time {best_alt.lead_time_days} days. Note: {best_alt.capacity_status}."
                    ),
                    estimated_risk_mitigation=f"Covers up to {int(total_shortfall * 0.75):,} units of projected shortfall.",
                    trade_off=f"+{round((best_alt.estimated_unit_cost - ESTIMATED_UNIT_COST_USD), 2):.2f} USD/unit price premium.",
                )
            )

        recommended_mitigations.append(
            MitigationRecommendation(
                title="Emergency Safety Buffer Adjustment",
                priority="HIGH" if critical_count > 2 else "MEDIUM",
                action_type="ADJUST_SAFETY_STOCK",
                description=(
                    f"Adjust safety stock targets in the Policy Engine for the {critical_count} critical SKUs. "
                    f"Prevents automatic de-stocking and preserves available units for high-priority fulfillments."
                ),
                estimated_risk_mitigation="Extends buffer runway by 7–12 days across affected distribution centers.",
                trade_off="Temporarily ties up operational working capital.",
            )
        )

        recommended_mitigations.append(
            MitigationRecommendation(
                title="Active Expedited Transit / Air Freight",
                priority="MEDIUM",
                action_type="EXPEDITE_TRANSIT",
                description=(
                    "For shipments already in transit from secondary locations, authorize expedited logistics "
                    "to shave 6–8 days off standard ocean transport."
                ),
                estimated_risk_mitigation="Prevents stockout on top 2 critical SKUs.",
                trade_off="Est. $4,500 logistics surcharge.",
            )
        )

        return DisruptionResponse(
            supplier_id=supplier_id,
            supplier_name=supplier_name,
            disruption_type=request.disruption_type,
            duration_days=duration_days,
            severity_pct=severity_pct,
            baseline_risk_score=baseline_score,
            baseline_risk_tier=baseline_tier,
            disrupted_risk_score=disrupted_score,
            disrupted_risk_tier=disrupted_tier,
            total_affected_skus=len(affected_skus),
            critical_skus_count=critical_count,
            total_inventory_exposure_usd=round(total_exposure_val, 2),
            total_shortfall_units=total_shortfall,
            affected_skus=affected_skus,
            alternative_candidates=alternative_candidates,
            recommended_mitigations=recommended_mitigations,
            timestamp=now_str,
        )

    async def reset_demo_state(self, db: AsyncSession) -> dict[str, Any]:
        """Resets simulated overrides, dismissals, and seeds baseline inventories."""
        logger.info("Resetting demo state to clean baseline...")
        
        # Reset Reorder statuses back to PENDING
        reorder_stmt = select(ReorderRecommendationStatus)
        reorder_res = await db.execute(reorder_stmt)
        for row in reorder_res.scalars().all():
            await db.delete(row)

        # Baseline standard units
        inv_stmt = select(InventoryLevel)
        inv_res = await db.execute(inv_stmt)
        levels = inv_res.scalars().all()
        
        for idx, lvl in enumerate(levels):
            # Deterministic, realistic inventory spread
            lvl.units_on_hand = 3500 + ((idx * 850) % 4000)
            lvl.units_in_transit = 1200 + ((idx * 300) % 1500)
            lvl.reorder_point = 2500

        await db.commit()
        return {
            "status": "SUCCESS",
            "message": "Demo state reset to verified baseline. All simulations and filters restored.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


simulation_service = SimulationService()
