"""
SupplyMind — Main REST API Lifespan Configuration (Category 7)
Integrates routers, lifespan database triggers, and exception decorators.
"""

from __future__ import annotations

import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from api.models.db import engine, Base
from api.services.cache import cache_manager
from api.middleware.errors import CorrelationIdMiddleware, rfc7807_exception_handler
from api.routes import agent, predictions
from agent.scheduler import get_scheduler

logger = logging.getLogger(__name__)

async def health_check_daemon(app: FastAPI):
    """Background loop to periodically cache health status and keep /health sub-30ms."""
    logger.info("Starting health check background caching daemon...")
    while True:
        try:
            redis_alive = await cache_manager.ping()
            scheduler = getattr(app.state, "scheduler", None)
            scheduler_running = scheduler.scheduler.running if scheduler else False
            jobs = []
            if scheduler_running:
                jobs = [
                    {"id": j.id, "name": j.name, "next_run": str(j.next_run_time)}
                    for j in scheduler.scheduler.get_jobs()
                ]
            app.state.health_cache = {
                "status": "ok",
                "app": settings.app_name,
                "version": settings.app_version,
                "redis_connected": redis_alive,
                "scheduler_running": scheduler_running,
                "scheduler_jobs": jobs,
            }
        except Exception as e:
            logger.warning("Error in health check background caching daemon: %s", e)
            app.state.health_cache = {
                "status": "error",
                "detail": str(e)
            }
        await asyncio.sleep(10)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup Context
    logger.info("Initializing SupplyMind FastAPI connection wrappers...")

    # Seed initial health check cache immediately
    app.state.health_cache = {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "redis_connected": False,
        "scheduler_running": False,
        "scheduler_jobs": [],
    }

    # ── Database Model Setup ─────────────────────────────────────
    # Database schema is now managed externally via Alembic migrations.
    # To run migrations: `alembic upgrade head`
    logger.info("Database schemas are managed by Alembic.")

    # ── Cache Layer Setup ─────────────────────────────────────────
    await cache_manager.connect()

    # ── Agent Scheduler ──────────────────────────────────────────
    # Guard against double-start on uvicorn --reload (which forks the process)
    scheduler = get_scheduler()
    if not scheduler.scheduler.running:
        scheduler.start()
        logger.info(
            "Agent scheduler started. Daily audit cron: %02d:%02d UTC.",
            settings.agent_schedule_hour,
            settings.agent_schedule_minute,
        )
    else:
        logger.info("Agent scheduler already running — skipping duplicate start.")

    app.state.scheduler = scheduler

    # Start health check caching daemon
    app.state.health_daemon_task = asyncio.create_task(health_check_daemon(app))

    yield

    # Shutdown Context
    logger.info("Terminating API wrappers and engine connections...")

    # Stop health check caching daemon
    if hasattr(app.state, "health_daemon_task"):
        app.state.health_daemon_task.cancel()
        try:
            await app.state.health_daemon_task
        except asyncio.CancelledError:
            pass
        logger.info("Health check daemon stopped.")

    # ── Stop Scheduler ────────────────────────────────────────────
    if scheduler.scheduler.running:
        scheduler.stop()
        logger.info("Agent scheduler stopped.")

    await engine.dispose()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="SupplyMind Supply Chain Risk & Decision Orchestration API",
    lifespan=lifespan,
    docs_url="/docs",
)

# Registrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(CorrelationIdMiddleware)

# Exceptions
from fastapi.exceptions import RequestValidationError
app.add_exception_handler(RequestValidationError, rfc7807_exception_handler)
app.add_exception_handler(Exception, rfc7807_exception_handler)

from api.routes import agent, predictions, inventory, models, auth, suppliers, scheduler, settings as settings_router, reports

# API Routers
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(predictions.router, prefix=settings.api_prefix)
app.include_router(agent.router, prefix=settings.api_prefix)
app.include_router(inventory.router, prefix=settings.api_prefix)
app.include_router(models.router, prefix=settings.api_prefix)
app.include_router(suppliers.router, prefix=settings.api_prefix)
app.include_router(scheduler.router, prefix=settings.api_prefix)
app.include_router(settings_router.router, prefix=settings.api_prefix)
app.include_router(reports.router, prefix=settings.api_prefix)


@app.get("/health", tags=["System"])
async def health(request: Request):
    return request.app.state.health_cache
