"""
SupplyMind — Database Models (Category 1)
Contains all relational schemas matching specifications.

Changes:
  - Added trigger_type column to ActionLog (MANUAL/SCHEDULED/EVENT/THRESHOLD)
  - Added SupplierOnboarding model with 90-day probation logic
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from typing import Any
from sqlalchemy import String, Float, DateTime, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

# UTC Helper function
def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class RiskContextLog(Base):
    """Stores a snapshot of the agent's risk perception at execution time."""
    __tablename__ = "risk_context_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sku_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    supplier_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    context_frame_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ActionLog(Base):
    """Tracks the lifecycle of actions computed and executed by the policy engine."""
    __tablename__ = "action_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    action_plan_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True) # PENDING | APPROVED | REJECTED | EXECUTED
    trigger_type: Mapped[str] = mapped_column(String(50), nullable=False, default="MANUAL")  # MANUAL | SCHEDULED | EVENT | THRESHOLD
    sku_id: Mapped[str] = mapped_column(String(255), nullable=False)
    supplier_id: Mapped[str] = mapped_column(String(255), nullable=False)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    audit_trails: Mapped[list[UserAuditTrail]] = relationship(back_populates="action", cascade="all, delete-orphan")


class ModelPerformanceMetric(Base):
    """Logs historic model health metrics for the Observatory."""
    __tablename__ = "model_performance_metrics"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    model_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True) # tft | lgbm | lstm
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)           # wrmsse | pr_auc | f1
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    lookback_days: Mapped[int] = mapped_column(default=30)


class UserAuditTrail(Base):
    """Persists human validation decisions (Approve/Reject) on Tier 2 pending actions."""
    __tablename__ = "user_audit_trails"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    action_id: Mapped[int] = mapped_column(ForeignKey("action_logs.id", ondelete="CASCADE"), nullable=False)
    decision_type: Mapped[str] = mapped_column(String(50), nullable=False) # APPROVED | REJECTED
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    # Back relation
    action: Mapped[ActionLog] = relationship(back_populates="audit_trails")


class SupplierOnboarding(Base):
    """
    Tracks new supplier onboarding through a mandatory 90-day probationary period.

    Status transitions:
      PENDING_REVIEW → IN_PROBATION (manual review + reference check)
      IN_PROBATION   → APPROVED  (auto: on_time_rate >= 85% AND rejection_rate < 3%)
      IN_PROBATION   → REJECTED  (auto: on_time_rate < 70% OR rejection_rate > 8%)
      IN_PROBATION   → APPROVED  (manual override at end of probation if thresholds not triggered)

    Tier promotion: APPROVED suppliers graduate from Tier 2 → Tier 1 via a separate
    manual review (not handled here — this table tracks probation only).
    """
    __tablename__ = "supplier_onboardings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    supplier_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    supplier_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Dates
    application_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    probation_start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    probation_end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Status: PENDING_REVIEW | IN_PROBATION | APPROVED | REJECTED
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING_REVIEW", index=True)

    # Onboarding assessment fields
    credentials_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    reference_check_status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING")  # PENDING | PASSED | FAILED
    geographic_risk_region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    capacity_info: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    # Live probation metrics (updated by evaluation job)
    probation_on_time_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    probation_rejection_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    probation_po_count: Mapped[int] = mapped_column(default=0)

    # Audit
    reviewed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    # ── Threshold constants ─────────────────────────────────────────────────
    AUTO_APPROVE_OTD_MIN: float = 0.85       # on-time delivery ≥ 85%
    AUTO_APPROVE_REJECTION_MAX: float = 0.03 # rejection rate < 3%
    AUTO_REJECT_OTD_MAX: float = 0.70        # on-time delivery < 70%
    AUTO_REJECT_REJECTION_MIN: float = 0.08  # rejection rate > 8%

    @property
    def days_remaining(self) -> int | None:
        """Days until probation ends. Negative if overdue."""
        if self.probation_end_date is None:
            return None
        now = datetime.now(timezone.utc)
        end = self.probation_end_date
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        return (end - now).days

    @property
    def probation_progress_pct(self) -> float:
        """0–100% of the 90-day period elapsed."""
        if self.probation_start_date is None or self.probation_end_date is None:
            return 0.0
        now = datetime.now(timezone.utc)
        start = self.probation_start_date
        end = self.probation_end_date
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        total = (end - start).total_seconds()
        elapsed = (now - start).total_seconds()
        if total <= 0:
            return 100.0
        return min(100.0, max(0.0, (elapsed / total) * 100.0))

    def evaluate_auto_thresholds(self) -> str | None:
        """
        Check whether probation metrics trigger auto-approve or auto-reject.
        Returns new status string if a transition should occur, else None.
        Only meaningful when status == 'IN_PROBATION'.
        """
        if self.status != "IN_PROBATION":
            return None
        # Auto-reject takes priority
        if (self.probation_on_time_rate < self.AUTO_REJECT_OTD_MAX
                or self.probation_rejection_rate > self.AUTO_REJECT_REJECTION_MIN):
            return "REJECTED"
        # Auto-approve
        if (self.probation_on_time_rate >= self.AUTO_APPROVE_OTD_MIN
                and self.probation_rejection_rate < self.AUTO_APPROVE_REJECTION_MAX):
            return "APPROVED"
        return None


class CachedSupplierRisk(Base):
    """Caches pre-computed supplier risk and anomaly prediction outputs."""
    __tablename__ = "cached_supplier_risks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    supplier_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(50), nullable=False)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, default=False)
    shap_drivers_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class CachedSkuDemand(Base):
    """Caches pre-computed SKU demand forecast quantiles and stockout timelines."""
    __tablename__ = "cached_sku_demands"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sku_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    p05_total: Mapped[float] = mapped_column(Float, nullable=False)
    p50_total: Mapped[float] = mapped_column(Float, nullable=False)
    p95_total: Mapped[float] = mapped_column(Float, nullable=False)
    days_to_stockout: Mapped[float | None] = mapped_column(Float, nullable=True)
    daily_forecasts_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class ModelTrainingJob(Base):
    """Tracks background model retraining jobs and log outputs."""
    __tablename__ = "model_training_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    model_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING", index=True)
    log_file: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class InventoryLevel(Base):
    """Relational table tracking live SKU units on hand and reorder triggers."""
    __tablename__ = "inventory_levels"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sku_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    units_on_hand: Mapped[int] = mapped_column(nullable=False, default=0)
    units_in_transit: Mapped[int] = mapped_column(nullable=False, default=0)
    reorder_point: Mapped[int] = mapped_column(nullable=False, default=1000)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

