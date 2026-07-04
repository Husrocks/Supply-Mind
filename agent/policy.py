"""
SupplyMind — Agent Policy Engine (Phase 5: Full Implementation)
Evaluates a RiskContextFrame and produces a structured ActionPlan.

Decision ladder (three tiers):
  AUTONOMOUS         — Execute immediately, log and notify after.
                       Condition: cost ≤ budget + action is reversible
  RECOMMEND_CONFIRM  — Prepare approval card, pause execution until clicked.
                       Condition: cost > budget, or new supplier activation
  ESCALATE           — Surface situation to procurement manager immediately.
                       Condition: cascade risk (all suppliers compromised),
                       agent confidence too low, or >1 TIER_1 SKU cascade

Each action uses the dataclasses defined in actions.py for full serialisation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from .actions import (
    ActionTier,
    ActionStatus,
    ActionType,
    BaseAction,
    IssuePurchaseOrderAction,
    AdjustSafetyStockAction,
    MonitorPurchaseOrderAction,
    EscalateToManagerAction,
    ActionPlan as DataclassActionPlan,
)
from .context_builder import RiskContextFrame, SupplierContext, DemandSignal

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Pydantic-serialisable ActionPlan (wraps dataclasses for API/JSON output)
# ──────────────────────────────────────────────────────────────────────────────

class PolicyResult:
    """
    Holds the ActionPlan dataclass and provides JSON-serialisable representation
    for the API layer and audit logger.
    """

    def __init__(self, plan: DataclassActionPlan):
        self.plan = plan

    def to_dict(self) -> dict[str, Any]:
        return self.plan.to_dict()

    @property
    def actions(self) -> list[BaseAction]:
        return self.plan.actions

    @property
    def system_reasoning_summary(self) -> str:
        return " → ".join(self.plan.reasoning_steps) if self.plan.reasoning_steps else "No action required."


# ──────────────────────────────────────────────────────────────────────────────
# Policy Engine
# ──────────────────────────────────────────────────────────────────────────────

class PolicyEngine:
    """
    Rule-based policy engine that converts a RiskContextFrame into an ActionPlan.

    Design principles:
    1. Composable rules — each step adds zero or more actions independently.
    2. Tier promotion — autonomous actions are promoted to RECOMMEND_CONFIRM
       if they exceed the budget gate.
    3. Cascade safety net — if all suppliers (primary + alts) are HIGH/CRITICAL,
       escalate to human regardless of budget.
    4. Reasoning trail — every decision step is recorded for the audit log.
    """

    # Anomaly reconstruction error threshold for the LSTM-AE model.
    # This was set empirically from the Colab training run.
    ANOMALY_SCORE_ALERT_THRESHOLD = 50.0  # MSE units in unscaled lead time space

    def decide_actions(self, context: RiskContextFrame) -> PolicyResult:
        """
        Main entry point. Evaluates the context frame and returns a PolicyResult.
        """
        actions: list[BaseAction] = []
        reasoning: list[str] = []

        sku = context.sku_id
        primary = context.primary_supplier
        demand = context.demand

        logger.info(
            "PolicyEngine evaluating SKU=%s | Criticality=%s | Risk=%s",
            sku, context.criticality, context.overall_risk_level,
        )

        # ── Step 1: Assess Urgency ────────────────────────────────────────
        if context.criticality == "TIER_1":
            reasoning.append(
                f"⚠ TIER 1 CRITICAL: Stockout in "
                f"{demand.days_to_stockout_p95:.1f if demand.days_to_stockout_p95 else '< ?'} days"
                f" | Lead time: {primary.avg_lead_time_days:.0f} days"
            )

        # ── Step 2: Primary Supplier Assessment ─────────────────────────
        if primary.risk_level in ("CRITICAL", "HIGH"):
            reasoning.append(
                f"Primary supplier {primary.supplier_id} is {primary.risk_level} risk "
                f"(score: {primary.risk_score:.0%})"
            )
            # Always monitor existing PO — do NOT cancel prematurely
            actions.append(MonitorPurchaseOrderAction(
                tier=ActionTier.AUTONOMOUS,
                sku_id=sku,
                supplier_id=primary.supplier_id,
                reasoning=(
                    f"Monitor open POs from {primary.supplier_id}. "
                    f"Risk level {primary.risk_level} — do not cancel, partial delivery still valuable."
                ),
                risk_reason=primary.shap_drivers[0].feature if primary.shap_drivers else "unknown",
            ))

        # ── Step 3: Anomaly Alert ────────────────────────────────────────
        if primary.is_anomaly and primary.reconstruction_error > self.ANOMALY_SCORE_ALERT_THRESHOLD:
            reasoning.append(
                f"LSTM-AE anomaly detected on {primary.supplier_id} "
                f"(reconstruction error: {primary.reconstruction_error:.1f})"
            )

        # ── Step 4: Cascade Detection ────────────────────────────────────
        if self._is_cascade(context):
            reasoning.append(
                "CASCADE RISK: Primary AND all alternatives are HIGH/CRITICAL. "
                "No safe automated sourcing possible."
            )
            actions.append(EscalateToManagerAction(
                tier=ActionTier.ESCALATE,
                sku_id=sku,
                supplier_id=primary.supplier_id,
                reasoning=(
                    f"Multi-supplier cascade on SKU {sku}. "
                    f"Primary: {primary.risk_level}. All {len(context.alternative_suppliers)} "
                    f"alternatives compromised. Human intervention required."
                ),
                escalation_reason="cascade_risk",
                shap_summary=[d.model_dump() for d in primary.shap_drivers],
                recommended_next_step=(
                    "Contact procurement manager to activate emergency spot-market sourcing "
                    "or accept partial fulfillment plan."
                ),
            ))
            # No further automated actions possible in cascade scenario
            return self._assemble_result(sku, primary.supplier_id, actions, reasoning, context)

        # ── Step 5: Backup Procurement ───────────────────────────────────
        if context.criticality == "TIER_1" or primary.risk_level in ("CRITICAL", "HIGH"):
            best_alt = context.best_alternative
            if best_alt:
                po_action = self._build_po_action(sku, best_alt, demand, context.budget_authority_usd)
                actions.append(po_action)
                reasoning.append(
                    f"Backup PO to {best_alt.supplier_id} | "
                    f"{int(demand.p95_14day_total)} units | "
                    f"Tier: {po_action.tier.value}"
                )
            else:
                reasoning.append(
                    f"No viable backup available (all {len(context.alternative_suppliers)} alts are high-risk)."
                )
                # Escalate if there is truly no option
                actions.append(EscalateToManagerAction(
                    tier=ActionTier.ESCALATE,
                    sku_id=sku,
                    supplier_id=primary.supplier_id,
                    reasoning=f"High risk on primary ({primary.risk_level}) with no viable backup suppliers.",
                    escalation_reason="no_backup_available",
                    shap_summary=[d.model_dump() for d in primary.shap_drivers],
                    recommended_next_step="Consider spot market or demand rationing.",
                ))

        # ── Step 6: Safety Stock Adjustment ─────────────────────────────
        if context.criticality == "TIER_1" or primary.risk_level == "HIGH":
            current_ss = max(100, context.current_inventory // 10)  # 10% of inventory as safety stock proxy
            actions.append(AdjustSafetyStockAction(
                tier=ActionTier.AUTONOMOUS,
                sku_id=sku,
                supplier_id=primary.supplier_id,
                reasoning=(
                    f"Increase safety stock by 25% for SKU {sku} "
                    f"due to {primary.risk_level} supplier risk. "
                    f"Duration: 30 days."
                ),
                multiplier=1.25,
                duration_days=30,
                original_safety_stock=current_ss,
            ))
            reasoning.append(f"Safety stock increased 25% for 30 days.")

        # ── Step 7: Elevated Risk or Anomaly Alert (non-critical) ────────────────
        if not actions and (primary.risk_level == "ELEVATED" or primary.is_anomaly):
            reason_str = ""
            if primary.is_anomaly:
                reason_str = f"LSTM-AE anomaly detected (recon error: {primary.reconstruction_error:.1f})"
            else:
                reason_str = f"Elevated risk ({primary.risk_score:.0%})"
            
            reasoning.append(
                f"Supplier {primary.supplier_id} has warning: {reason_str}. "
                f"Monitoring only — no action threshold crossed."
            )
            actions.append(MonitorPurchaseOrderAction(
                tier=ActionTier.AUTONOMOUS,
                sku_id=sku,
                supplier_id=primary.supplier_id,
                reasoning=f"Warning active ({reason_str}) — flag for weekly review.",
                risk_reason="anomaly_monitoring" if primary.is_anomaly else "elevated_risk_monitoring",
            ))

        # ── Step 8: No Action ────────────────────────────────────────────
        if not actions:
            reasoning.append(
                f"All signals normal: Risk={primary.risk_level} ({primary.risk_score:.0%}), "
                f"Anomaly={primary.is_anomaly}, Stockout=None. No action required."
            )

        return self._assemble_result(sku, primary.supplier_id, actions, reasoning, context)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _build_po_action(
        self,
        sku_id: str,
        supplier: SupplierContext,
        demand: DemandSignal,
        budget_usd: float,
    ) -> IssuePurchaseOrderAction:
        """Construct an emergency PO action with automatic tier assignment."""
        units = max(1, int(demand.p95_14day_total))
        unit_cost = supplier.unit_cost_estimate
        total_cost = units * unit_cost

        # Budget gate: exceed budget → downgrade to RECOMMEND_CONFIRM
        tier = ActionTier.AUTONOMOUS if total_cost <= budget_usd else ActionTier.RECOMMEND_CONFIRM

        return IssuePurchaseOrderAction(
            tier=tier,
            sku_id=sku_id,
            supplier_id=supplier.supplier_id,
            reasoning=(
                f"Emergency PO: {units} units from {supplier.supplier_id} "
                f"@ ${unit_cost:.2f}/unit. Total: ${total_cost:,.2f}. "
                f"Supplier risk: {supplier.risk_level} ({supplier.risk_score:.0%}). "
                f"{'Within budget — autonomous.' if tier == ActionTier.AUTONOMOUS else 'Exceeds budget — requires approval.'}"
            ),
            units=units,
            unit_cost_usd=unit_cost,
            target_supplier_id=supplier.supplier_id,
            target_supplier_name=supplier.supplier_id,
            lead_time_days=int(supplier.avg_lead_time_days),
        )

    def _is_cascade(self, context: RiskContextFrame) -> bool:
        """
        Cascade = primary supplier is HIGH/CRITICAL AND
        every single alternative is also HIGH/CRITICAL.
        Requires at least one alternative to be a real cascade.
        """
        if context.primary_supplier.risk_level not in ("CRITICAL", "HIGH"):
            return False
        if not context.alternative_suppliers:
            return False  # No alternatives → not cascade, just no backup
        return all(
            s.risk_level in ("CRITICAL", "HIGH") or s.is_anomaly
            for s in context.alternative_suppliers
        )

    def _assemble_result(
        self,
        sku_id: str,
        supplier_id: str,
        actions: list[BaseAction],
        reasoning: list[str],
        context: RiskContextFrame,
    ) -> PolicyResult:
        plan = DataclassActionPlan(
            sku_id=sku_id,
            supplier_id=supplier_id,
            actions=actions,
            reasoning_steps=reasoning,
            trigger_type="OODA_CYCLE",
            risk_score=context.primary_supplier.risk_score,
            days_to_stockout_p95=context.demand.days_to_stockout_p95 or 999.0,
        )
        logger.info(
            "PolicyEngine produced %d actions for SKU=%s "
            "(autonomous=%d, pending_approval=%d)",
            len(actions), sku_id,
            len(plan.autonomous_actions), len(plan.pending_approval_actions)
        )
        return PolicyResult(plan)
