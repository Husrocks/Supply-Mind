"""
SupplyMind — RiskContextService (Category 3)
Calculates and caches the RiskContextFrame by calling model predictors.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.models.db_models import RiskContextLog
from api.services.cache import cache_result, cache_manager
from agent.context_builder import get_context_builder, RiskContextFrame
from agent.orchestrator import get_orchestrator

logger = logging.getLogger(__name__)

class RiskContextService:
    """Manages risk context generation, persistence, and caching."""

    @cache_result(ttl_seconds=3600)
    async def compute_risk_context(
        self,
        sku_id: str,
        supplier_id: str,
        db: AsyncSession,
        current_inventory: int = 5000,
        alternative_supplier_ids: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Assembles the RiskContextFrame using the ML models.
        Persists the result to the PostgreSQL database.
        """
        logger.info("Computing fresh risk context for SKU=%s, Supplier=%s", sku_id, supplier_id)

        # Retrieve Orchestrator & ContextBuilder instances
        orchestrator = get_orchestrator()
        
        # Load parquet dataframes
        supplier_df = orchestrator._load_supplier_data()
        demand_df = orchestrator._load_demand_data()

        # Build context frame from model inference
        frame: RiskContextFrame = get_context_builder().build_frame(
            sku_id=sku_id,
            primary_supplier_id=supplier_id,
            demand_history_df=demand_df,
            supplier_processed_df=supplier_df,
            current_inventory=current_inventory,
            alternative_supplier_ids=alternative_supplier_ids
        )

        frame_dict = frame.model_dump()

        # Persist log to relational DB
        db_log = RiskContextLog(
            sku_id=sku_id,
            supplier_id=supplier_id,
            risk_score=frame.primary_supplier.risk_score,
            context_frame_json=frame_dict
        )
        db.add(db_log)
        await db.flush()

        return frame_dict

    async def invalidate_cache(self, sku_id: str) -> None:
        """Removes the cached risk context for all services matching this SKU ID."""
        # Find and delete matching cached keys in Redis
        if not cache_manager.client or not cache_manager.is_healthy:
            return
        
        pattern = f"supplymind:compute_risk_context:{sku_id}:*"
        try:
            keys = await cache_manager.client.keys(pattern)
            if keys:
                await cache_manager.client.delete(*keys)
                logger.info("Invalidated %d cache keys matching pattern: %s", len(keys), pattern)
        except Exception as exc:
            logger.warning("Failed to invalidate cache keys for SKU %s: %s", sku_id, exc)


# Singleton
risk_context_service = RiskContextService()
