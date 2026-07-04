"""
SupplyMind — Predictions Router (Category 6)
Exposes endpoints for forecasting model outputs.
"""

from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.db import get_db_session
from api.middleware.auth import require_role
from api.schemas.validation import RiskContextResponse
from api.services.risk_service import risk_context_service
from api.services.network_service import network_dashboard_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/predictions", tags=["Predictions"])


def _scheduler_agent_active(request: Request) -> bool:
    scheduler = getattr(request.app.state, "scheduler", None)
    if scheduler is None:
        return False
    return bool(getattr(scheduler, "is_running", False) or scheduler.scheduler.running)


@router.get(
    "/risk-context",
    response_model=dict,
    summary="Fetch structured overall Risk Context Frame for Command Center",
)
async def get_overall_risk_context(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    user: dict[str, str] = Depends(require_role(["viewer", "approver", "admin"])),
):
    """Build network-wide dashboard payload from real ML inference — no mock fallback."""
    try:
        return await network_dashboard_service.build_dashboard(
            db=db,
            agent_triggered=_scheduler_agent_active(request),
        )
    except Exception as exc:
        logger.exception("Network dashboard build failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Network risk context build failed: {exc}",
        )


@router.get(
    "/risk-context/{sku_id}",
    response_model=RiskContextResponse,
    summary="Compute and fetch Risk Context Frame for SKU",
)
async def get_risk_context_by_sku(
    sku_id: str,
    supplier_id: str = Query(..., description="ID of primary supplier to evaluate"),
    current_inventory: int = Query(5000, ge=0),
    alternative_supplier_ids: list[str] = Query(default_factory=list),
    db: AsyncSession = Depends(get_db_session),
    user: dict[str, str] = Depends(require_role(["viewer", "approver", "admin"])),
):
    """Computes a fresh context frame through the model layer for a specific SKU."""
    try:
        frame_dict = await risk_context_service.compute_risk_context(
            sku_id=sku_id,
            supplier_id=supplier_id,
            db=db,
            current_inventory=current_inventory,
            alternative_supplier_ids=alternative_supplier_ids,
        )
        return RiskContextResponse(
            sku_id=sku_id,
            supplier_id=supplier_id,
            risk_score=frame_dict["primary_supplier"]["risk_score"],
            context_frame=frame_dict,
        )
    except Exception as exc:
        logger.exception("Failed to fetch risk context predictions")
        raise HTTPException(
            status_code=500, detail=f"Inference pipeline execution error: {exc}"
        )
