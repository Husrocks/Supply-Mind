"""
SupplyMind — Simulation Routes
Endpoints for What-If scenario simulations, supplier disruption analyses, and demo reset.
"""

from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.db import get_db_session
from api.middleware.auth import require_role
from api.schemas.interactive_schemas import (
    WhatIfRequest,
    WhatIfResponse,
    DisruptionRequest,
    DisruptionResponse,
)
from api.services.simulation_service import simulation_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/simulation", tags=["Simulation"])


@router.post(
    "/what-if",
    response_model=WhatIfResponse,
    summary="Simulate hypothetical demand, lead time, inventory, and capacity shocks",
)
async def simulate_what_if(
    request: WhatIfRequest,
    db: AsyncSession = Depends(get_db_session),
    user: dict[str, str] = Depends(require_role(["viewer", "approver", "admin"])),
):
    try:
        return await simulation_service.simulate_what_if(request, db)
    except Exception as exc:
        logger.exception("What-if simulation failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Simulation error: {exc}")


@router.post(
    "/supplier-disruption",
    response_model=DisruptionResponse,
    summary="Simulate temporary supplier shutdown or delivery delays",
)
async def simulate_supplier_disruption(
    request: DisruptionRequest,
    db: AsyncSession = Depends(get_db_session),
    user: dict[str, str] = Depends(require_role(["viewer", "approver", "admin"])),
):
    try:
        return await simulation_service.simulate_supplier_disruption(request, db)
    except Exception as exc:
        logger.exception("Supplier disruption simulation failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Disruption analysis error: {exc}")


@router.post(
    "/reset",
    summary="Reset demo overrides and restore verified baseline operational state",
)
async def reset_demo(
    db: AsyncSession = Depends(get_db_session),
    user: dict[str, str] = Depends(require_role(["approver", "admin"])),
):
    try:
        return await simulation_service.reset_demo_state(db)
    except Exception as exc:
        logger.exception("Demo reset failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Reset error: {exc}")
