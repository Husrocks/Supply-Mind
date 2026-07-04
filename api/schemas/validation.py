"""
SupplyMind — Schemas & Validation (Category 4)
Pydantic schemas aligned with frontend request/response payloads.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field

# ── Response Schemas ──────────────────────────────────────────────────────────

class RiskContextResponse(BaseModel):
    sku_id: str
    supplier_id: str
    risk_score: float
    context_frame: dict[str, Any]


class ActionResponse(BaseModel):
    action_id: str
    action_plan_id: str
    action_type: str
    status: str
    trigger_type: str = "MANUAL"  # MANUAL | SCHEDULED | EVENT | THRESHOLD
    sku_id: str
    supplier_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
    reasoning: str
    confidence_score: float = 0.85
    estimated_impact: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class AuditLogItem(BaseModel):
    action_id: int
    action_plan_id: str
    action_type: str
    status: str
    sku_id: str
    supplier_id: str
    estimated_cost_usd: float
    reasoning: str
    timestamp: str


class AuditLogResponse(BaseModel):
    logs: list[AuditLogItem]
    total: int


class MetricsResponse(BaseModel):
    performance_metrics: dict[str, dict[str, float]]


# ── Request Validation Schemas ────────────────────────────────────────────────

class ApproveActionRequest(BaseModel):
    approved_by: str = Field(..., min_length=1, description="Approver user name")
    notes: str | None = Field(None, description="Optional justification/notes")


class RejectActionRequest(BaseModel):
    rejected_by: str = Field(..., min_length=1, description="Rejector user name")
    reason: str = Field(..., min_length=1, description="Rejection reason required")


class TriggerAgentRequest(BaseModel):
    trigger_type: Literal["MANUAL", "SCHEDULED", "EVENT", "THRESHOLD"] = "MANUAL"
    sku_id: str | None = Field(default="FOODS_1_001_CA_1_evaluation")
    primary_supplier_id: str | None = Field(default="SUP-0001")
    current_inventory: int = Field(5000, ge=0)
    alternative_supplier_ids: list[str] = Field(default_factory=list)
