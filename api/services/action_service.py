"""
SupplyMind — ActionService (Category 3)
Handles action log generation, approvals, rejections, and audit trails.

Changes:
  - create_action() now accepts trigger_type and persists it on ActionLog
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.models.db_models import ActionLog, UserAuditTrail
from agent.actions import ActionStatus

logger = logging.getLogger(__name__)

class ActionService:
    """Manages the action log database tables and human approval overrides."""

    async def create_action(
        self,
        db: AsyncSession,
        action_plan_id: str,
        actions_list: list[dict[str, Any]],
        sku_id: str,
        supplier_id: str,
        trigger_type: str = "MANUAL",
        confidence_score: float | None = None,
    ) -> list[int]:
        """Creates ActionLog entries with PENDING status for authorization."""
        action_ids = []
        for act in actions_list:
            log = ActionLog(
                action_plan_id=action_plan_id,
                action_type=act.get("action_type"),
                status=act.get("status", "PENDING"),
                trigger_type=trigger_type,
                sku_id=sku_id,
                supplier_id=supplier_id,
                estimated_cost_usd=act.get("estimated_cost_usd", 0.0),
                reasoning=act.get("reasoning", ""),
                confidence_score=confidence_score,
            )
            db.add(log)
            await db.flush()
            action_ids.append(log.id)
        
        logger.info(
            "Registered %d action logs for plan: %s (trigger=%s)",
            len(action_ids), action_plan_id, trigger_type
        )
        return action_ids

    async def approve_action(
        self,
        db: AsyncSession,
        action_id: int,
        approved_by_user_id: str,
        justification: str,
        mark_executed: bool = False,
    ) -> ActionLog | None:
        """Approves a pending action and stores validation logs in audit trail."""
        action = await db.get(ActionLog, action_id)
        if not action:
            return None

        action.status = "EXECUTED" if mark_executed else "APPROVED"
        action.updated_at = datetime.now(timezone.utc)

        # Log to User Audit Trail
        trail = UserAuditTrail(
            user_id=approved_by_user_id,
            action_id=action_id,
            decision_type="APPROVED",
            justification=justification
        )
        db.add(trail)
        await db.commit()

        logger.info("Action %d APPROVED by user: %s", action_id, approved_by_user_id)
        return action

    async def reject_action(
        self,
        db: AsyncSession,
        action_id: int,
        rejected_by_user_id: str,
        rejection_reason: str
    ) -> ActionLog | None:
        """Rejects a pending action and stores validation logs in audit trail."""
        action = await db.get(ActionLog, action_id)
        if not action:
            return None

        # Transition status
        action.status = "REJECTED"
        action.updated_at = datetime.now(timezone.utc)

        # Log to User Audit Trail
        trail = UserAuditTrail(
            user_id=rejected_by_user_id,
            action_id=action_id,
            decision_type="REJECTED",
            justification=rejection_reason
        )
        db.add(trail)
        await db.commit()

        logger.info("Action %d REJECTED by user: %s", action_id, rejected_by_user_id)
        return action


# Singleton
action_service = ActionService()
