"""
SupplyMind — Agent Audit Logger
Writes every agent cycle to a persistent JSONL file for compliance, debugging,
and dashboard display.

Format: One JSON object per line (JSONL), each representing one agent cycle.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

LOG_PATH = Path("logs/agent_audit.jsonl")


class AuditLogger:
    """
    Thread-safe append-only audit log writer.
    Each record is a complete snapshot of one agent OODA cycle:
    - What triggered it
    - What the ML models saw
    - What actions were decided
    - The full reasoning chain
    """

    def __init__(self, log_path: str | Path = LOG_PATH):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def log_cycle(
        self,
        *,
        trigger_type: str,
        sku_id: str,
        primary_supplier_id: str,
        risk_context: dict[str, Any],
        action_plan: dict[str, Any],
        dispatch_results: list[dict[str, Any]],
        status: str,
        error_message: str | None = None,
    ) -> None:
        """
        Append one complete agent cycle record to the audit log.
        """
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trigger_type": trigger_type,
            "sku_id": sku_id,
            "primary_supplier_id": primary_supplier_id,
            "status": status,
            # ── ML Snapshot ──────────────────────────────────────────
            "risk_score": risk_context.get("primary_supplier", {}).get("risk_score"),
            "risk_level": risk_context.get("primary_supplier", {}).get("risk_level"),
            "is_anomaly": risk_context.get("primary_supplier", {}).get("is_anomaly"),
            "criticality": risk_context.get("criticality"),
            "days_to_stockout_p50": risk_context.get("demand", {}).get("days_to_stockout_p50"),
            "days_to_stockout_p95": risk_context.get("demand", {}).get("days_to_stockout_p95"),
            "p50_14day_total": risk_context.get("demand", {}).get("p50_14day_total"),
            "p95_14day_total": risk_context.get("demand", {}).get("p95_14day_total"),
            "current_inventory": risk_context.get("current_inventory"),
            "shap_drivers": risk_context.get("primary_supplier", {}).get("shap_drivers", []),
            # ── Decisions ─────────────────────────────────────────────
            "actions_count": len(action_plan.get("actions", [])),
            "actions": action_plan.get("actions", []),
            "system_reasoning_summary": action_plan.get("system_reasoning_summary", ""),
            "total_estimated_cost_usd": sum(
                a.get("estimated_cost_usd", 0) for a in action_plan.get("actions", [])
            ),
            # ── Dispatch ──────────────────────────────────────────────
            "dispatch_results": dispatch_results,
            # ── Error (if any) ────────────────────────────────────────
            "error_message": error_message,
        }

        line = json.dumps(record, default=str)
        with self._lock:
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")

        logger.debug("Audit record written for SKU=%s | Status=%s", sku_id, status)

    def get_recent(self, n: int = 50) -> list[dict[str, Any]]:
        """
        Return the last N audit records (most recent last).
        """
        if not self.log_path.exists():
            return []
        try:
            with self.log_path.open("r", encoding="utf-8") as f:
                lines = f.readlines()
            records = []
            for line in lines[-n:]:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
            return records
        except Exception as e:
            logger.error("Failed to read audit log: %s", e)
            return []

    def get_all(self) -> list[dict[str, Any]]:
        """Return all audit records."""
        return self.get_recent(n=999_999)

    def get_stats(self) -> dict[str, Any]:
        """
        Returns aggregate statistics from the audit log:
        total cycles, success rate, average risk score, action breakdown.
        """
        records = self.get_all()
        if not records:
            return {"total_cycles": 0}

        total = len(records)
        successes = sum(1 for r in records if r.get("status") == "SUCCESS")
        errors = total - successes
        risk_scores = [r.get("risk_score") for r in records if r.get("risk_score") is not None]
        avg_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0.0

        action_types: dict[str, int] = {}
        tier_counts: dict[str, int] = {}
        for rec in records:
            for action in rec.get("actions", []):
                a_type = action.get("action_type", "UNKNOWN")
                tier = action.get("tier", "UNKNOWN")
                action_types[a_type] = action_types.get(a_type, 0) + 1
                tier_counts[tier] = tier_counts.get(tier, 0) + 1

        return {
            "total_cycles": total,
            "successful_cycles": successes,
            "error_cycles": errors,
            "success_rate_pct": round(100 * successes / total, 1),
            "avg_risk_score": round(avg_risk, 4),
            "action_type_breakdown": action_types,
            "tier_breakdown": tier_counts,
        }


# Module-level singleton
_audit_logger: AuditLogger | None = None


def get_audit_logger() -> AuditLogger:
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
