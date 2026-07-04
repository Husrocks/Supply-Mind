"""
SupplyMind — Agent Scheduler
Runs the agent periodically using APScheduler. Triggers the Orchestrator
to run OODA loops across all critical SKUs.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import settings
from .orchestrator import get_orchestrator

logger = logging.getLogger(__name__)

class AgentScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.orchestrator = get_orchestrator()
        self.is_running: bool = False
        self.last_run_at: datetime | None = None
        self.last_trigger_type: str | None = None

    def start(self):
        """Starts the scheduler in the background."""
        logger.info(
            "Starting Agent Scheduler. Scheduled for %02d:%02d daily.",
            settings.agent_schedule_hour,
            settings.agent_schedule_minute
        )
        
        # Schedule daily run
        self.scheduler.add_job(
            self.run_daily_audit,
            trigger=CronTrigger(
                hour=settings.agent_schedule_hour,
                minute=settings.agent_schedule_minute
            ),
            id="daily_agent_audit",
            name="Daily Autonomous Agent Audit",
            replace_existing=True,
        )
        
        self.scheduler.start()

    def stop(self):
        """Stops the scheduler."""
        logger.info("Stopping Agent Scheduler.")
        self.scheduler.shutdown()

    async def run_daily_audit(self):
        """
        The main job triggered daily. Scans all active SKUs and runs the agent cycle.
        """
        logger.info("--- TRIGGERED: Daily Agent Audit ---")
        self.is_running = True
        self.last_trigger_type = "SCHEDULED"

        try:
            await self._execute_daily_audit()
        finally:
            self.last_run_at = datetime.now(timezone.utc)
            self.is_running = False
            logger.info("--- COMPLETED: Daily Agent Audit ---")

    async def _execute_daily_audit(self):
        # Load unique active SKUs and primary suppliers from the parquet dataset
        supplier_df = self.orchestrator._load_supplier_data()
        demand_df = self.orchestrator._load_demand_data()
        
        if supplier_df.empty or demand_df.empty:
            logger.error("Failed to load supplier/demand data. Skipping daily audit.")
            return

        # Map active SKU to primary supplier (mock relationships using dataset samples)
        # Select first 5 unique SKUs from demand data for simulation
        sample_skus = demand_df["id"].unique()[:5].tolist()
        # Pair each with a supplier from the supplier pool
        suppliers = supplier_df["supplier_id"].unique()[:5].tolist()
        
        batch_pairs = []
        for i, sku in enumerate(sample_skus):
            primary_sup = suppliers[i % len(suppliers)]
            # Get other suppliers as alternatives
            alternatives = [s for s in suppliers if s != primary_sup][:3]
            batch_pairs.append({
                "sku_id": sku,
                "primary_supplier_id": primary_sup,
                "current_inventory": 5000,
                "alternative_supplier_ids": alternatives
            })
            
        logger.info("Running OODA cycles for %d batch SKU-supplier pairs.", len(batch_pairs))
        results = self.orchestrator.run_batch(batch_pairs, trigger_type="SCHEDULED")
        
        successes = sum(1 for r in results if r.get("status") == "SUCCESS")
        logger.info("Daily audit finished. Successes: %d/%d", successes, len(results))

# Singleton
_scheduler = None

def get_scheduler() -> AgentScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AgentScheduler()
    return _scheduler
