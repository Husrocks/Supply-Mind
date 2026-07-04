"""
SupplyMind — Run Scheduler Script
Instantiates the scheduler, runs a mock cycle immediately, and tests the cron wiring.
"""

import asyncio
import logging
import sys

# Configure logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

from agent.scheduler import get_scheduler

async def main():
    scheduler = get_scheduler()
    print("Starting background scheduler...")
    scheduler.start()
    
    print("Triggering run_daily_audit() manually for validation...")
    await scheduler.run_daily_audit()
    
    print("Stopping scheduler...")
    scheduler.stop()

if __name__ == "__main__":
    asyncio.run(main())
