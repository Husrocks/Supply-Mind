"""
SupplyMind — Explainability Routes
Endpoints for retrieving detailed SHAP drivers, TFT forecast intervals, and LSTM-AE anomaly evidence.
"""

from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.db import get_db_session
from api.middleware.auth import require_role
from api.schemas.interactive_schemas import (
    SupplierExplainabilityResponse,
    SkuExplainabilityResponse,
)
from api.services.explainability_service import explainability_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/explainability", tags=["Explainability"])


@router.get(
    "/supplier/{supplier_id}",
    response_model=SupplierExplainabilityResponse,
    summary="Get SHAP feature importance, plain-language risk breakdown, and anomaly metrics for a supplier",
)
async def get_supplier_explainability(
    supplier_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: dict[str, str] = Depends(require_role(["viewer", "approver", "admin"])),
):
    try:
        return await explainability_service.get_supplier_explanation(supplier_id, db)
    except Exception as exc:
        logger.exception("Failed to fetch supplier explainability: %s", exc)
        raise HTTPException(status_code=500, detail=f"Explainability error: {exc}")


@router.get(
    "/sku/{sku_id}",
    response_model=SkuExplainabilityResponse,
    summary="Get TFT demand quantile uncertainty intervals (P05/P50/P95) and interpretation for a SKU",
)
async def get_sku_explainability(
    sku_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: dict[str, str] = Depends(require_role(["viewer", "approver", "admin"])),
):
    try:
        return await explainability_service.get_sku_explanation(sku_id, db)
    except Exception as exc:
        logger.exception("Failed to fetch SKU explainability: %s", exc)
        raise HTTPException(status_code=500, detail=f"Explainability error: {exc}")
