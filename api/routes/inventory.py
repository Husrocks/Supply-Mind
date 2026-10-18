from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.services.inventory_service import inventory_heatmap_service
from api.models.db import get_db_session
from api.middleware.auth import require_role

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.get("/risk-heatmap", summary="Get inventory risk heatmap for all SKUs")
async def get_inventory_risk_heatmap(
    db: AsyncSession = Depends(get_db_session),
    user: dict[str, str] = Depends(require_role(["viewer", "approver", "admin"]))
):
    """Returns inventory state derived from real demand parquet features."""
    return await inventory_heatmap_service.build_heatmap(db)


@router.get("/{sku_id}", summary="Get detailed forecast and dependencies for a single SKU")
async def get_sku_detail(
    sku_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: dict[str, str] = Depends(require_role(["viewer", "approver", "admin"])),
):
    from api.models.db_models import InventoryLevel, CachedSkuDemand, ActionLog
    from api.routes.agent import _build_action_response

    inv_stmt = select(InventoryLevel).where(InventoryLevel.sku_id == sku_id)
    inv_res = await db.execute(inv_stmt)
    inv_level = inv_res.scalar_one_or_none()

    demand_stmt = select(CachedSkuDemand).where(CachedSkuDemand.sku_id == sku_id)
    demand_res = await db.execute(demand_stmt)
    cached_demand = demand_res.scalar_one_or_none()

    if not inv_level and not cached_demand:
        raise HTTPException(status_code=404, detail=f"SKU {sku_id} not found")

    current_inv = float(inv_level.units_on_hand) if inv_level else 5000.0
    daily_demand = (cached_demand.p50_total / 14.0) if cached_demand else 50.0
    days_to_stockout = current_inv / max(daily_demand, 0.01)

    # Fetch actions for this SKU
    action_stmt = select(ActionLog).where(ActionLog.sku_id == sku_id).order_by(ActionLog.created_at.desc())
    action_res = await db.execute(action_stmt)
    formatted_actions = [_build_action_response(a) for a in action_res.scalars().all()]

    status = (
        "CRITICAL" if days_to_stockout < 14
        else ("ELEVATED" if days_to_stockout < 21 else "NORMAL")
    )

    return {
        "sku_id": sku_id,
        "days_to_stockout": round(days_to_stockout, 1),
        "uncertainty_spread": round(cached_demand.p95_total - cached_demand.p05_total, 1) if cached_demand else 14.0,
        "current_inventory": round(current_inv, 0),
        "status": status,
        "forecast_history": cached_demand.daily_forecasts_json if cached_demand else [],
        "actions": formatted_actions,
        "supplier_dependencies": [],
    }

