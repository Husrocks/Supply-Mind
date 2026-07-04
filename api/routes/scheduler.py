"""
SupplyMind — Scheduler Status Router
Exposes real scheduler state for the Agent Status widget.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Request, Depends

from api.middleware.auth import require_role

router = APIRouter(prefix="/scheduler", tags=["Scheduler"])


@router.get(
    "/status",
    summary="Get agent scheduler running state and last run metadata",
)
async def get_scheduler_status(
    request: Request,
    user: dict[str, str] = Depends(require_role(["viewer", "approver", "admin"])),
):
    scheduler = getattr(request.app.state, "scheduler", None)
    if scheduler is None:
        return {
            "running": False,
            "scheduler_running": False,
            "last_run_at": None,
            "next_run_at": None,
            "last_trigger_type": None,
        }

    jobs = scheduler.scheduler.get_jobs() if scheduler.scheduler.running else []
    next_run = jobs[0].next_run_time if jobs else None

    last_run = getattr(scheduler, "last_run_at", None)
    if last_run and last_run.tzinfo is None:
        last_run = last_run.replace(tzinfo=timezone.utc)

    return {
        "running": bool(getattr(scheduler, "is_running", False)),
        "scheduler_running": scheduler.scheduler.running,
        "last_run_at": last_run.isoformat() if last_run else None,
        "next_run_at": next_run.isoformat() if next_run else None,
        "last_trigger_type": getattr(scheduler, "last_trigger_type", None),
    }
