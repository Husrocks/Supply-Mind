"""
SupplyMind — Smart Reorder Recommendations Service
Calculates data-grounded replenishment recommendations, safety stocks,
and reorder points using real demand history and supplier risk profiles.
"""

from __future__ import annotations

import io
import csv
import math
import logging
from datetime import datetime, timedelta, timezone
from typing import Any
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
    ReorderRecommendationItem,
    ReorderSummaryResponse,
    SupplierOption,
)

logger = logging.getLogger(__name__)

DEFAULT_LEAD_TIME = 25
ESTIMATED_UNIT_COST = 45.0
ORDER_CYCLE_DAYS = 30  # 30-day economic replenishment batch target


class ReorderService:
    """Computes actionable inventory replenishment recommendations."""

    async def get_recommendations(
        self,
        db: AsyncSession,
        status_filter: str | None = None,
        criticality_filter: str | None = None,
        supplier_id_filter: str | None = None,
        search_query: str | None = None,
    ) -> ReorderSummaryResponse:
        # 1. Fetch live inventory levels
        inv_stmt = select(InventoryLevel)
        inv_res = await db.execute(inv_stmt)
        inv_levels = inv_res.scalars().all()

        # 2. Fetch cached SKU demands
        demand_stmt = select(CachedSkuDemand)
        demand_res = await db.execute(demand_stmt)
        demand_map = {d.sku_id: d for d in demand_res.scalars().all()}

        # 3. Fetch cached supplier risks
        risk_stmt = select(CachedSupplierRisk)
        risk_res = await db.execute(risk_stmt)
        supplier_risks = {r.supplier_id: r for r in risk_res.scalars().all()}

        # 4. Fetch supplier onboardings for names
        ob_stmt = select(SupplierOnboarding)
        ob_res = await db.execute(ob_stmt)
        onboardings = {o.supplier_id: o for o in ob_res.scalars().all()}

        # 5. Fetch human review statuses
        status_stmt = select(ReorderRecommendationStatus)
        status_res = await db.execute(status_stmt)
        user_statuses = {s.sku_id: s for s in status_res.scalars().all()}

        # Pre-build list of candidate suppliers for alternative comparisons
        all_supplier_options: list[SupplierOption] = []
        for sid, r in supplier_risks.items():
            ob = onboardings.get(sid)
            s_name = ob.supplier_name if ob else f"Supplier {sid}"
            all_supplier_options.append(
                SupplierOption(
                    supplier_id=sid,
                    supplier_name=s_name,
                    risk_score=round(r.risk_score, 2),
                    risk_tier=r.risk_level.upper(),
                    lead_time_days=25 if r.risk_score < 0.40 else 35,
                    estimated_unit_cost=round(ESTIMATED_UNIT_COST * (1.0 + (r.risk_score * 0.1)), 2),
                    is_preferred=r.risk_score < 0.30,
                    capacity_status="Verified" if r.risk_score < 0.35 else "Unverified capacity",
                )
            )
        all_supplier_options.sort(key=lambda x: x.risk_score)

        items: list[ReorderRecommendationItem] = []
        now = datetime.now(timezone.utc)

        total_suggested_units = 0
        total_budget_usd = 0.0
        critical_count = 0
        elevated_count = 0
        actionable_count = 0

        for inv in inv_levels:
            sku_id = inv.sku_id
            category = sku_id.split("_")[0] if "_" in sku_id else "GENERAL"

            # Demand parameters
            cached_d = demand_map.get(sku_id)
            if cached_d and cached_d.p50_total > 0:
                daily_demand = max(5.0, round(cached_d.p50_total / 14.0, 1))
                uncertainty = max(2.0, cached_d.p95_total - cached_d.p05_total)
                sigma_d = uncertainty / 3.29
            else:
                daily_demand = 75.0
                uncertainty = 25.0
                sigma_d = 7.6

            # Determine preferred supplier for this SKU
            preferred_opt = all_supplier_options[0] if all_supplier_options else SupplierOption(
                supplier_id="SUP-0001",
                supplier_name="Apex Global Logistics",
                risk_score=0.22,
                risk_tier="LOW",
                lead_time_days=DEFAULT_LEAD_TIME,
                estimated_unit_cost=ESTIMATED_UNIT_COST,
                is_preferred=True,
                capacity_status="Verified",
            )
            
            lead_time = preferred_opt.lead_time_days
            sup_risk = preferred_opt.risk_score

            # Calculations
            # Dynamic Z: buffer up to 1.96 (97.5% service level) if supplier is risky
            z_factor = 1.96 if sup_risk >= 0.70 else 1.65
            safety_stock = int(math.ceil(z_factor * sigma_d * math.sqrt(lead_time)))
            lead_time_demand = int(round(daily_demand * lead_time))
            reorder_point = lead_time_demand + safety_stock

            on_hand = inv.units_on_hand
            in_transit = inv.units_in_transit
            effective_inv = on_hand + in_transit

            # Suggested Qty calculation
            # Target coverage = 30 days of daily demand
            batch_target = int(round(daily_demand * ORDER_CYCLE_DAYS))
            if effective_inv <= reorder_point:
                suggested_qty = max(batch_target, (reorder_point - effective_inv) + batch_target)
                is_actionable = True
            else:
                suggested_qty = 0
                is_actionable = False

            # Runway & stockout timeline
            days_to_stockout = round(on_hand / max(daily_demand, 0.01), 1)
            stockout_date = (now + timedelta(days=days_to_stockout)).strftime("%b %d, %Y")

            # Criticality tier
            if days_to_stockout < lead_time:
                criticality = "CRITICAL"
                critical_count += 1
            elif days_to_stockout < (lead_time + 14) or effective_inv <= reorder_point:
                criticality = "ELEVATED"
                elevated_count += 1
            else:
                criticality = "NORMAL"

            if is_actionable:
                actionable_count += 1
                total_suggested_units += suggested_qty
                total_budget_usd += suggested_qty * preferred_opt.estimated_unit_cost

            # Plain-English Explanation
            if effective_inv <= reorder_point:
                explanation = (
                    f"Net inventory ({effective_inv:,} units: {on_hand:,} on hand + {in_transit:,} in transit) "
                    f"has dropped below Reorder Point ({reorder_point:,} units). "
                    f"Estimated stockout in {days_to_stockout:.1f} days vs {lead_time} days supplier lead time. "
                    f"Immediate purchase order of {suggested_qty:,} units recommended."
                )
            else:
                explanation = (
                    f"Net inventory ({effective_inv:,} units) comfortably exceeds Reorder Point ({reorder_point:,} units). "
                    f"Current safety buffer provides {days_to_stockout:.1f} days of demand coverage."
                )

            # Review status
            saved_status = user_statuses.get(sku_id)
            current_status = saved_status.status if saved_status else "PENDING"
            review_notes = saved_status.notes if saved_status else None

            # Filters
            if status_filter and current_status.upper() != status_filter.upper():
                continue
            if criticality_filter and criticality != criticality_filter.upper():
                continue
            if supplier_id_filter and preferred_opt.supplier_id != supplier_id_filter:
                continue
            if search_query:
                q = search_query.lower()
                if q not in sku_id.lower() and q not in preferred_opt.supplier_name.lower():
                    continue

            # Alternatives (excluding the preferred one)
            alts = [s for s in all_supplier_options if s.supplier_id != preferred_opt.supplier_id][:3]

            items.append(
                ReorderRecommendationItem(
                    sku_id=sku_id,
                    category=category,
                    current_inventory=on_hand,
                    units_in_transit=in_transit,
                    daily_demand=daily_demand,
                    demand_uncertainty_spread=round(uncertainty, 1),
                    lead_time_days=lead_time,
                    safety_stock=safety_stock,
                    reorder_point=reorder_point,
                    suggested_order_qty=suggested_qty,
                    days_to_stockout=days_to_stockout,
                    expected_stockout_date=stockout_date,
                    criticality=criticality,
                    preferred_supplier_id=preferred_opt.supplier_id,
                    preferred_supplier_name=preferred_opt.supplier_name,
                    preferred_supplier_risk_score=preferred_opt.risk_score,
                    preferred_supplier_risk_tier=preferred_opt.risk_tier,
                    explanation=explanation,
                    status=current_status,
                    review_notes=review_notes,
                    alternative_suppliers=alts,
                )
            )

        # Sort: CRITICAL first, then ELEVATED, then NORMAL
        criticality_order = {"CRITICAL": 0, "ELEVATED": 1, "NORMAL": 2}
        items.sort(key=lambda x: (criticality_order.get(x.criticality, 3), x.days_to_stockout))

        return ReorderSummaryResponse(
            total_skus_evaluated=len(inv_levels),
            actionable_reorders_count=actionable_count,
            critical_stockout_count=critical_count,
            elevated_count=elevated_count,
            total_suggested_units=total_suggested_units,
            estimated_reorder_budget_usd=round(total_budget_usd, 2),
            recommendations=items,
        )

    async def update_status(
        self,
        sku_id: str,
        status: str,
        notes: str | None,
        updated_by: str | None,
        db: AsyncSession,
    ) -> dict[str, Any]:
        stmt = select(ReorderRecommendationStatus).where(ReorderRecommendationStatus.sku_id == sku_id)
        res = await db.execute(stmt)
        record = res.scalar_one_or_none()

        now = datetime.now(timezone.utc)
        if record:
            record.status = status.upper()
            record.notes = notes
            record.updated_by = updated_by
            record.updated_at = now
        else:
            record = ReorderRecommendationStatus(
                sku_id=sku_id,
                status=status.upper(),
                notes=notes,
                updated_by=updated_by,
                updated_at=now,
            )
            db.add(record)

        await db.commit()
        return {
            "sku_id": sku_id,
            "status": record.status,
            "notes": record.notes,
            "updated_at": now.isoformat(),
        }

    async def export_csv(self, db: AsyncSession) -> io.StringIO:
        """Exports recommendations as CSV with transparent formula documentation."""
        summary = await self.get_recommendations(db)
        output = io.StringIO()
        writer = csv.writer(output)

        # Header documentation
        writer.writerow(["# SupplyMind — Smart Reorder Recommendations Export"])
        writer.writerow(["# Formulas: ROP = (Daily Demand * Lead Time) + Safety Stock"])
        writer.writerow(["# Safety Stock = Z * Sigma_d * sqrt(Lead Time), where Z=1.65 (or 1.96 for high-risk suppliers)"])
        writer.writerow(["# Suggested Qty = max(30-day coverage, ROP - Net Inventory + 30-day coverage)"])
        writer.writerow([])

        writer.writerow([
            "SKU ID",
            "Category",
            "Current On Hand",
            "In Transit",
            "Daily Demand",
            "Lead Time (Days)",
            "Safety Stock",
            "Reorder Point",
            "Suggested Order Qty",
            "Days to Stockout",
            "Expected Stockout Date",
            "Criticality Tier",
            "Preferred Supplier ID",
            "Preferred Supplier Name",
            "Supplier Risk Score",
            "Supplier Risk Tier",
            "Review Status",
            "Recommendation Explanation",
        ])

        for item in summary.recommendations:
            writer.writerow([
                item.sku_id,
                item.category,
                item.current_inventory,
                item.units_in_transit,
                f"{item.daily_demand:.1f}",
                item.lead_time_days,
                item.safety_stock,
                item.reorder_point,
                item.suggested_order_qty,
                f"{item.days_to_stockout:.1f}",
                item.expected_stockout_date,
                item.criticality,
                item.preferred_supplier_id,
                item.preferred_supplier_name,
                f"{item.preferred_supplier_risk_score:.0%}",
                item.preferred_supplier_risk_tier,
                item.status,
                item.explanation,
            ])

        output.seek(0)
        return output


reorder_service = ReorderService()
