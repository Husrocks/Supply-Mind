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
    skus = await inventory_heatmap_service.build_heatmap(db)
    sku_info = None
    for s in skus:
        if s["sku_id"] == sku_id:
            sku_info = s
            break
            
    if not sku_info:
        raise HTTPException(status_code=404, detail=f"SKU {sku_id} not found")
        
    # Fetch actions for this SKU
    from api.models.db_models import ActionLog
    action_stmt = select(ActionLog).where(ActionLog.sku_id == sku_id).order_by(ActionLog.created_at.desc())
    action_res = await db.execute(action_stmt)
    actions = action_res.scalars().all()
    
    from api.routes.agent import _build_action_response
    formatted_actions = [_build_action_response(a) for a in actions]
    
    # Fetch supplier dependencies from network flows
    from api.services.network_service import network_dashboard_service
    dashboard = await network_dashboard_service.build_dashboard(db, agent_triggered=False)
    
    # Match dependency category or flows
    category = sku_id.split("_")[0]
    suppliers_dependent = []
    for f in dashboard.get("supply_flows", []):
        # If the category matches, this supplier delivers this SKU type
        if f.get("category") == category:
            suppliers_dependent.append(f)
            
    return {
        "sku_id": sku_info["sku_id"],
        "days_to_stockout": sku_info["days_to_stockout"],
        "uncertainty_spread": sku_info["uncertainty_spread"],
        "current_inventory": sku_info["current_inventory"],
        "status": sku_info["status"],
        "forecast_history": sku_info["forecast_history"],
        "actions": formatted_actions,
        "supplier_dependencies": suppliers_dependent,
    }

