"""
SupplyMind — Assistant Routes
Endpoints for conversational, data-grounded AI assistant interactions.
"""

from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.db import get_db_session
from api.middleware.auth import require_role
from api.schemas.interactive_schemas import (
    AssistantChatRequest,
    AssistantChatResponse,
)
from api.services.assistant_service import assistant_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assistant", tags=["AI Assistant"])


@router.post(
    "/chat",
    response_model=AssistantChatResponse,
    summary="Ask supply chain questions grounded in real live DB records, forecasts, and scenario calculations",
)
async def ask_assistant(
    request: AssistantChatRequest,
    db: AsyncSession = Depends(get_db_session),
    user: dict[str, str] = Depends(require_role(["viewer", "approver", "admin"])),
):
    try:
        return await assistant_service.chat(request, db)
    except Exception as exc:
        logger.exception("Assistant chat processing error: %s", exc)
        raise HTTPException(status_code=500, detail=f"Assistant processing error: {exc}")


@router.get(
    "/suggestions",
    summary="Get popular quick-prompt starter questions for the supply chain assistant",
)
async def get_suggestions(
    user: dict[str, str] = Depends(require_role(["viewer", "approver", "admin"])),
):
    return {
        "suggestions": [
            "Which suppliers currently have the highest risk?",
            "Which products may experience stockouts soon?",
            "What happens if demand increases by 20%?",
            "Which reorder recommendations should be reviewed first?",
            "Why is supplier SUP-0001 considered high risk?",
        ]
    }
