"""
SupplyMind — Action Types (Phase 5: Fixed dataclass inheritance)
Defines all possible actions the agent can take.
Each action knows its tier (Autonomous / Recommend / Escalate),
its cost, and how to serialize itself for the audit log.

Python dataclass inheritance: to avoid "non-default after default" errors,
all BaseAction fields have defaults, and subclasses use field(default=...).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ActionTier(str, Enum):
    """Human oversight tier for an action."""
    AUTONOMOUS = "AUTONOMOUS"               # Execute immediately, notify after
    RECOMMEND_CONFIRM = "RECOMMEND_CONFIRM" # Prepare card, wait for approval
    ESCALATE = "ESCALATE"                   # Defer entirely to human


class ActionStatus(str, Enum):
    """Lifecycle status of an action."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"


class ActionType(str, Enum):
    """Enumeration of all action categories."""
    ISSUE_PURCHASE_ORDER = "ISSUE_PURCHASE_ORDER"
    CANCEL_PURCHASE_ORDER = "CANCEL_PURCHASE_ORDER"
    MONITOR_PURCHASE_ORDER = "MONITOR_PURCHASE_ORDER"
    ADJUST_SAFETY_STOCK = "ADJUST_SAFETY_STOCK"
    ESCALATE_TO_MANAGER = "ESCALATE_TO_MANAGER"
    SEND_SUPPLIER_ALERT = "SEND_SUPPLIER_ALERT"
    FLAG_FOR_CONTRACT_REVIEW = "FLAG_FOR_CONTRACT_REVIEW"
    UPDATE_DEMAND_FORECAST = "UPDATE_DEMAND_FORECAST"


@dataclass
class BaseAction:
    """
    Base class for all agent actions.
    All fields have defaults so that subclasses can override specific ones
    without triggering the 'non-default after default' dataclass error.
    """
    action_type: ActionType = ActionType.MONITOR_PURCHASE_ORDER
    tier: ActionTier = ActionTier.AUTONOMOUS
    sku_id: str = ""
    supplier_id: str = ""
    reasoning: str = ""
    estimated_cost_usd: float = 0.0
    confidence: float = 1.0
    status: ActionStatus = ActionStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    executed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type.value,
            "tier": self.tier.value,
            "sku_id": self.sku_id,
            "supplier_id": self.supplier_id,
            "reasoning": self.reasoning,
            "estimated_cost_usd": self.estimated_cost_usd,
            "confidence": self.confidence,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class IssuePurchaseOrderAction(BaseAction):
    """
    Issue an emergency purchase order to an alternative supplier.
    Tier AUTONOMOUS if cost <= budget authority.
    Tier RECOMMEND_CONFIRM if cost exceeds budget or new supplier.
    """
    action_type: ActionType = field(default=ActionType.ISSUE_PURCHASE_ORDER)
    units: int = 0
    unit_cost_usd: float = 0.0
    target_supplier_id: str = ""
    target_supplier_name: str = ""
    lead_time_days: int = 0
    is_new_supplier: bool = False

    def __post_init__(self):
        self.estimated_cost_usd = self.units * self.unit_cost_usd
        self.metadata.update({
            "units": self.units,
            "unit_cost_usd": self.unit_cost_usd,
            "target_supplier_id": self.target_supplier_id,
            "lead_time_days": self.lead_time_days,
            "is_new_supplier": self.is_new_supplier,
        })


@dataclass
class AdjustSafetyStockAction(BaseAction):
    """
    Adjust safety stock multiplier for a SKU.
    Always Autonomous — fully reversible, no direct cost.
    """
    action_type: ActionType = field(default=ActionType.ADJUST_SAFETY_STOCK)
    tier: ActionTier = field(default=ActionTier.AUTONOMOUS)
    multiplier: float = 1.2          # e.g. 1.2 = increase by 20%
    duration_days: int = 30
    original_safety_stock: int = 0
    new_safety_stock: int = 0

    def __post_init__(self):
        self.new_safety_stock = int(self.original_safety_stock * self.multiplier)
        self.metadata.update({
            "multiplier": self.multiplier,
            "duration_days": self.duration_days,
            "original_safety_stock": self.original_safety_stock,
            "new_safety_stock": self.new_safety_stock,
        })


@dataclass
class MonitorPurchaseOrderAction(BaseAction):
    """
    Flag an open PO for active monitoring without cancellation.
    Partial recovery still valuable — don't cancel prematurely.
    """
    action_type: ActionType = field(default=ActionType.MONITOR_PURCHASE_ORDER)
    tier: ActionTier = field(default=ActionTier.AUTONOMOUS)
    po_id: str = ""
    committed_delivery_day: int = 0
    risk_reason: str = ""

    def __post_init__(self):
        self.metadata.update({
            "po_id": self.po_id,
            "committed_delivery_day": self.committed_delivery_day,
            "risk_reason": self.risk_reason,
        })


@dataclass
class EscalateToManagerAction(BaseAction):
    """
    Escalate a supplier situation to the procurement manager
    with a SHAP-based plain-language explanation.
    """
    action_type: ActionType = field(default=ActionType.ESCALATE_TO_MANAGER)
    tier: ActionTier = field(default=ActionTier.ESCALATE)
    escalation_reason: str = ""
    shap_summary: list[dict] = field(default_factory=list)
    recommended_next_step: str = ""

    def __post_init__(self):
        self.metadata.update({
            "escalation_reason": self.escalation_reason,
            "shap_summary": self.shap_summary,
            "recommended_next_step": self.recommended_next_step,
        })


@dataclass
class ActionPlan:
    """
    Complete set of actions the agent decided to take for one risk context.
    Includes the full reasoning chain for the audit log.
    """
    sku_id: str
    supplier_id: str
    actions: list[BaseAction] = field(default_factory=list)
    reasoning_steps: list[str] = field(default_factory=list)
    trigger_type: str = "SCHEDULED"
    risk_score: float = 0.0
    days_to_stockout_p95: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def autonomous_actions(self) -> list[BaseAction]:
        return [a for a in self.actions if a.tier == ActionTier.AUTONOMOUS]

    @property
    def pending_approval_actions(self) -> list[BaseAction]:
        return [a for a in self.actions if a.tier == ActionTier.RECOMMEND_CONFIRM]

    @property
    def total_estimated_cost(self) -> float:
        return sum(a.estimated_cost_usd for a in self.actions)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sku_id": self.sku_id,
            "supplier_id": self.supplier_id,
            "trigger_type": self.trigger_type,
            "risk_score": self.risk_score,
            "days_to_stockout_p95": self.days_to_stockout_p95,
            "reasoning_steps": self.reasoning_steps,
            "actions": [a.to_dict() for a in self.actions],
            "total_estimated_cost_usd": self.total_estimated_cost,
            "created_at": self.created_at.isoformat(),
        }
