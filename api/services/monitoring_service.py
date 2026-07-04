"""
SupplyMind — Audit and Monitoring Services (Category 3)
Queries reasoning logs, aggregates performance metrics, and caches outcomes.
"""

from __future__ import annotations

from datetime import datetime
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from api.models.db_models import ActionLog, UserAuditTrail, ModelPerformanceMetric
from api.services.cache import cache_result

logger = logging.getLogger(__name__)

class AuditService:
    """Retrieves decision histories, paginated audits, and tracking tables."""

    async def query_reasoning_log(
        self,
        db: AsyncSession,
        start_date: datetime,
        end_date: datetime,
        sku_id: str | None = None,
        limit: int = 50,
        offset: int = 0
    ) -> dict[str, Any]:
        """Queries ActionLogs joined with UserAuditTrails between date constraints."""
        stmt = (
            select(ActionLog)
            .where(
                and_(
                    ActionLog.created_at >= start_date,
                    ActionLog.created_at <= end_date
                )
            )
        )

        if sku_id:
            stmt = stmt.where(ActionLog.sku_id == sku_id)

        # Count query
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await db.scalar(count_stmt) or 0

        # Pagination & Execution
        stmt = stmt.limit(limit).offset(offset)
        result = await db.execute(stmt)
        actions = result.scalars().all()

        logs_list = []
        for act in actions:
            logs_list.append({
                "action_id": act.id,
                "action_plan_id": act.action_plan_id,
                "action_type": act.action_type,
                "status": act.status,
                "sku_id": act.sku_id,
                "supplier_id": act.supplier_id,
                "estimated_cost_usd": act.estimated_cost_usd,
                "reasoning": act.reasoning,
                "timestamp": act.created_at.isoformat()
            })

        return {
            "logs": logs_list,
            "total": total
        }


class ModelMonitoringService:
    """Manages tracking model performance metrics for the observatory dashboard."""

    @cache_result(ttl_seconds=14400) # 4 hours TTL cache
    async def compute_performance_metrics(
        self,
        db: AsyncSession,
        model_names: list[str] | None = None,
        lookback_days: int = 30
    ) -> dict[str, dict[str, float]]:
        """Averages metrics grouped by model across a lookback window."""
        stmt = select(ModelPerformanceMetric)
        if model_names:
            stmt = stmt.where(ModelPerformanceMetric.model_name.in_(model_names))

        result = await db.execute(stmt)
        metrics = result.scalars().all()

        # Group and calculate average values
        aggregated: dict[str, dict[str, list[float]]] = {}
        for m in metrics:
            aggregated.setdefault(m.model_name, {}).setdefault(m.metric_name, []).append(m.metric_value)

        output = {}
        for model, metrics_map in aggregated.items():
            output[model] = {
                metric: sum(vals) / len(vals) for metric, vals in metrics_map.items() if vals
            }

        return output


# Singletons
audit_service = AuditService()
model_monitoring_service = ModelMonitoringService()
