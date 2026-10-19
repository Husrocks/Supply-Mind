"""
SupplyMind — Smart Reorder Routes
Endpoints for querying replenishment recommendations, updating review status, and CSV export.
"""

from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.db import get_db_session
from api.middleware.auth import require_role
from api.schemas.interactive_schemas import (
    ReorderSummaryResponse,
    ReorderStatusUpdateRequest,
)
from api.services.reorder_service import reorder_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reorder", tags=["Smart Reorders"])


@router.get(
    "/recommendations",
    response_model=ReorderSummaryResponse,
    summary="Get data-grounded replenishment recommendations for all eligible SKUs",
)
async def get_reorder_recommendations(
    status: str | None = Query(None, description="Filter by status: PENDING | REVIEWED | DISMISSED"),
    criticality: str | None = Query(None, description="Filter by criticality: CRITICAL | ELEVATED | NORMAL"),
    supplier_id: str | None = Query(None, description="Filter by preferred supplier ID"),
    search: str | None = Query(None, description="Search by SKU or supplier name"),
    db: AsyncSession = Depends(get_db_session),
    user: dict[str, str] = Depends(require_role(["viewer", "approver", "admin"])),
):
    try:
        return await reorder_service.get_recommendations(
            db=db,
            status_filter=status,
            criticality_filter=criticality,
            supplier_id_filter=supplier_id,
            search_query=search,
        )
    except Exception as exc:
        logger.exception("Failed to compute reorder recommendations: %s", exc)
        raise HTTPException(status_code=500, detail=f"Reorder computation error: {exc}")


@router.post(
    "/{sku_id}/status",
    summary="Update review status of a reorder recommendation (Reviewed / Dismissed)",
)
async def update_reorder_status(
    sku_id: str,
    request: ReorderStatusUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
    user: dict[str, str] = Depends(require_role(["approver", "admin"])),
):
    try:
        return await reorder_service.update_status(
            sku_id=sku_id,
            status=request.status,
            notes=request.notes,
            updated_by=request.updated_by or user.get("sub", "User"),
            db=db,
        )
    except Exception as exc:
        logger.exception("Failed to update reorder status: %s", exc)
        raise HTTPException(status_code=500, detail=f"Status update error: {exc}")


@router.get(
    "/export",
    summary="Export smart reorder recommendations to downloadable CSV with calculation formulas",
)
async def export_reorder_csv(
    db: AsyncSession = Depends(get_db_session),
    user: dict[str, str] = Depends(require_role(["viewer", "approver", "admin"])),
):
    try:
        csv_buffer = await reorder_service.export_csv(db)
        return StreamingResponse(
            iter([csv_buffer.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=supplymind_reorders.csv"},
        )
    except Exception as exc:
        logger.exception("Failed to export reorders CSV: %s", exc)
        raise HTTPException(status_code=500, detail=f"Export error: {exc}")
