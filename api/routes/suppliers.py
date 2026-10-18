"""
SupplyMind — Supplier Onboarding Router (Phase 0)
Implements 90-day probationary onboarding with auto-evaluate thresholds.

Endpoints:
  POST /api/v1/suppliers/onboard          — create onboarding record
  GET  /api/v1/suppliers/onboarding       — list all records (filterable by status)
  POST /api/v1/suppliers/onboarding/{id}/start-probation  — transition to IN_PROBATION
  POST /api/v1/suppliers/onboarding/{id}/evaluate         — run threshold check
  PATCH /api/v1/suppliers/onboarding/{id}/metrics         — update live probation metrics
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.db import get_db_session
from api.models.db_models import SupplierOnboarding
from api.middleware.auth import require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/suppliers", tags=["Supplier Onboarding"])

PROBATION_DAYS = 90


# ── Request / Response schemas ──────────────────────────────────────────────────

class OnboardRequest(BaseModel):
    supplier_id: str = Field(..., description="Unique supplier identifier")
    supplier_name: str = Field(..., description="Human-readable supplier name")
    credentials_data: dict[str, Any] = Field(default_factory=dict, description="Business credentials JSON")
    geographic_risk_region: str | None = Field(None, description="e.g. 'APAC', 'EMEA', 'AMER'")
    capacity_info: dict[str, Any] = Field(default_factory=dict, description="Capacity / throughput info JSON")
    reference_check_status: str = Field("PENDING", description="PENDING | PASSED | FAILED")


class MetricsUpdateRequest(BaseModel):
    probation_on_time_rate: float = Field(..., ge=0.0, le=1.0, description="0.0–1.0")
    probation_rejection_rate: float = Field(..., ge=0.0, le=1.0, description="0.0–1.0")
    probation_po_count: int = Field(..., ge=0)


class OnboardingResponse(BaseModel):
    id: int
    supplier_id: str
    supplier_name: str
    status: str
    application_date: str
    probation_start_date: str | None
    probation_end_date: str | None
    days_remaining: int | None
    probation_progress_pct: float
    probation_on_time_rate: float
    probation_rejection_rate: float
    probation_po_count: int
    reference_check_status: str
    geographic_risk_region: str | None
    credentials_data: dict[str, Any]
    capacity_info: dict[str, Any]
    reviewed_by: str | None
    review_notes: str | None
    # Threshold indicators for UI
    auto_approve_threshold_met: bool
    auto_reject_threshold_triggered: bool


def _to_response(rec: SupplierOnboarding) -> OnboardingResponse:
    """Convert ORM record to response dict."""
    auto_status = rec.evaluate_auto_thresholds()
    return OnboardingResponse(
        id=rec.id,
        supplier_id=rec.supplier_id,
        supplier_name=rec.supplier_name,
        status=rec.status,
        application_date=rec.application_date.isoformat() if rec.application_date else "",
        probation_start_date=rec.probation_start_date.isoformat() if rec.probation_start_date else None,
        probation_end_date=rec.probation_end_date.isoformat() if rec.probation_end_date else None,
        days_remaining=rec.days_remaining,
        probation_progress_pct=round(rec.probation_progress_pct, 1),
        probation_on_time_rate=rec.probation_on_time_rate,
        probation_rejection_rate=rec.probation_rejection_rate,
        probation_po_count=rec.probation_po_count,
        reference_check_status=rec.reference_check_status,
        geographic_risk_region=rec.geographic_risk_region,
        credentials_data=rec.credentials_data,
        capacity_info=rec.capacity_info,
        reviewed_by=rec.reviewed_by,
        review_notes=rec.review_notes,
        auto_approve_threshold_met=(auto_status == "APPROVED"),
        auto_reject_threshold_triggered=(auto_status == "REJECTED"),
    )


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post(
    "/onboard",
    response_model=OnboardingResponse,
    status_code=201,
    summary="Create a new supplier onboarding application (starts as PENDING_REVIEW)",
)
async def onboard_supplier(
    request: OnboardRequest,
    db: AsyncSession = Depends(get_db_session),
    user: dict[str, str] = Depends(require_role(["approver", "admin"])),
):
    """
    Creates a SupplierOnboarding record in PENDING_REVIEW state.
    A reviewer must manually call /start-probation to begin the 90-day clock.
    """
    # Guard: prevent duplicate applications
    existing = await db.execute(
        select(SupplierOnboarding).where(SupplierOnboarding.supplier_id == request.supplier_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Supplier {request.supplier_id} already has an onboarding record")

    rec = SupplierOnboarding(
        supplier_id=request.supplier_id,
        supplier_name=request.supplier_name,
        credentials_data=request.credentials_data,
        geographic_risk_region=request.geographic_risk_region,
        capacity_info=request.capacity_info,
        reference_check_status=request.reference_check_status,
        status="PENDING_REVIEW",
    )
    db.add(rec)
    await db.commit()
    await db.refresh(rec)

    logger.info("Supplier onboarding application created: supplier_id=%s", request.supplier_id)
    return _to_response(rec)


@router.get(
    "/onboarding",
    response_model=list[OnboardingResponse],
    summary="List supplier onboarding records (filterable by status)",
)
async def list_onboarding(
    status: str | None = Query(None, description="Filter: PENDING_REVIEW | IN_PROBATION | APPROVED | REJECTED"),
    db: AsyncSession = Depends(get_db_session),
    user: dict[str, str] = Depends(require_role(["viewer", "approver", "admin"])),
):
    """Returns all onboarding records. Live metrics and days_remaining are computed on the fly."""
    stmt = select(SupplierOnboarding)
    if status:
        stmt = stmt.where(SupplierOnboarding.status == status.upper())
    result = await db.execute(stmt)
    records = result.scalars().all()
    return [_to_response(r) for r in records]


@router.post(
    "/onboarding/{onboarding_id}/start-probation",
    response_model=OnboardingResponse,
    summary="Start the 90-day probationary clock for a PENDING_REVIEW supplier",
)
async def start_probation(
    onboarding_id: int,
    db: AsyncSession = Depends(get_db_session),
    user: dict[str, str] = Depends(require_role(["approver", "admin"])),
):
    rec = await db.get(SupplierOnboarding, onboarding_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Onboarding record not found")
    if rec.status != "PENDING_REVIEW":
        raise HTTPException(status_code=409, detail=f"Cannot start probation from status={rec.status}")

    now = datetime.now(timezone.utc)
    rec.status = "IN_PROBATION"
    rec.probation_start_date = now
    rec.probation_end_date = now + timedelta(days=PROBATION_DAYS)
    rec.reviewed_by = user.get("user_id", "unknown")
    rec.updated_at = now

    await db.commit()
    await db.refresh(rec)
    logger.info("Probation started for supplier_id=%s, ends=%s", rec.supplier_id, rec.probation_end_date)
    return _to_response(rec)


@router.patch(
    "/onboarding/{onboarding_id}/metrics",
    response_model=OnboardingResponse,
    summary="Update live probation performance metrics for a supplier",
)
async def update_probation_metrics(
    onboarding_id: int,
    request: MetricsUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
    user: dict[str, str] = Depends(require_role(["approver", "admin"])),
):
    """Update on-time rate and rejection rate. Automatically evaluates thresholds after update."""
    rec = await db.get(SupplierOnboarding, onboarding_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Onboarding record not found")

    rec.probation_on_time_rate = request.probation_on_time_rate
    rec.probation_rejection_rate = request.probation_rejection_rate
    rec.probation_po_count = request.probation_po_count
    rec.updated_at = datetime.now(timezone.utc)

    # Auto-evaluate thresholds on every metric update
    new_status = rec.evaluate_auto_thresholds()
    if new_status:
        rec.status = new_status
        logger.info(
            "Auto-transition supplier_id=%s → %s (otd=%.0f%%, rejection=%.0f%%)",
            rec.supplier_id, new_status,
            rec.probation_on_time_rate * 100,
            rec.probation_rejection_rate * 100,
        )

    await db.commit()
    await db.refresh(rec)
    return _to_response(rec)


@router.post(
    "/onboarding/{onboarding_id}/evaluate",
    response_model=OnboardingResponse,
    summary="On-demand: evaluate current metrics against auto-approve/auto-reject thresholds",
)
async def evaluate_onboarding(
    onboarding_id: int,
    db: AsyncSession = Depends(get_db_session),
    user: dict[str, str] = Depends(require_role(["approver", "admin"])),
):
    """
    Runs the threshold check against current metrics:
      - on-time ≥ 85% AND rejection < 3%  → APPROVED
      - on-time < 70% OR rejection > 8%   → REJECTED
      - otherwise no change
    """
    rec = await db.get(SupplierOnboarding, onboarding_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Onboarding record not found")

    new_status = rec.evaluate_auto_thresholds()
    if new_status:
        rec.status = new_status
        rec.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(rec)
        logger.info("Evaluated onboarding id=%d: new status=%s", onboarding_id, new_status)
    else:
        logger.info("Evaluated onboarding id=%d: no threshold triggered (status unchanged=%s)", onboarding_id, rec.status)

    return _to_response(rec)


@router.get("/{supplier_id}", summary="Get detailed profile of a single supplier")
async def get_supplier_detail(
    supplier_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: dict[str, str] = Depends(require_role(["viewer", "approver", "admin"])),
):
    from api.models.db_models import CachedSupplierRisk, ActionLog
    from api.routes.agent import _build_action_response

    # Fast path: Direct DB query for this supplier's risk record
    stmt = select(CachedSupplierRisk).where(CachedSupplierRisk.supplier_id == supplier_id)
    cached_res = await db.execute(stmt)
    cached = cached_res.scalar_one_or_none()

    # Query onboarding details
    ob_stmt = select(SupplierOnboarding).where(SupplierOnboarding.supplier_id == supplier_id)
    ob_res = await db.execute(ob_stmt)
    onboarding = ob_res.scalar_one_or_none()
    onboarding_info = _to_response(onboarding) if onboarding else None

    # Query actions
    action_stmt = select(ActionLog).where(ActionLog.supplier_id == supplier_id).order_by(ActionLog.created_at.desc())
    action_res = await db.execute(action_stmt)
    actions = action_res.scalars().all()
    formatted_actions = [_build_action_response(a) for a in actions]

    if not cached and not onboarding:
        raise HTTPException(status_code=404, detail="Supplier not found")

    supplier_name = onboarding.supplier_name if onboarding else supplier_id
    risk_score = cached.risk_score if cached else 0.15
    risk_level = cached.risk_level if cached else "LOW"
    is_anomaly = cached.is_anomaly if cached else False
    shap_drivers = cached.shap_drivers_json if cached else []

    return {
        "supplier_id": supplier_id,
        "supplier_name": supplier_name,
        "risk_score": risk_score,
        "risk_tier": risk_level.lower(),
        "geopolitical_factor": 0.15,
        "lead_time_variance": 0.1,
        "quality_failure_rate": 0.02,
        "concentration_ratio": 0.1,
        "reasoning": f"Supplier {supplier_name} risk score: {risk_score:.0%}.",
        "shap_drivers": shap_drivers,
        "avg_lead_time_days": 30.0,
        "on_time_delivery_pct": onboarding.probation_on_time_rate if onboarding else 0.95,
        "po_acceptance_rate": 0.98,
        "lead_time_slope_6w": 0.0,
        "unit_cost_estimate": 100.0,
        "country_code": onboarding.country_code if onboarding else None,
        "geographic_risk_region": onboarding.geographic_risk_region if onboarding else None,
        "is_anomaly": is_anomaly,
        "risk_trend": [],
        "onboarding": onboarding_info,
        "actions": formatted_actions,
    }

