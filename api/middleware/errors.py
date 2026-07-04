"""
SupplyMind — Error Handler & Logging Middleware (Category 7)
Implements RFC 7807 details mapping and unique correlation ID tracking.
"""

from __future__ import annotations

import logging
import uuid
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Generates and propagates a trace correlation ID across every request-response cycle."""
    async def dispatch(self, request: Request, call_next):
        corr_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        request.state.correlation_id = corr_id

        # Execute request downstream
        response: Response = await call_next(request)
        response.headers["X-Correlation-ID"] = corr_id
        return response


async def rfc7807_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all exception handler converting server exceptions into standard
    RFC 7807 Problem Details JSON structures.
    """
    corr_id = getattr(request.state, "correlation_id", "N/A")
    
    if isinstance(exc, HTTPException):
        status_code = exc.status_code
        detail = exc.detail
        title = "Client request validation failed" if status_code < 500 else "Internal execution error"
    elif exc.__class__.__name__ == "RequestValidationError":
        status_code = 422
        detail = str(exc)
        title = "Request payload validation failed"
    else:
        status_code = 500
        detail = str(exc)
        title = "Internal Server Error"

    logger.error("Error encountered [Correlation-ID: %s]: %s (Status: %d)", corr_id, detail, status_code)

    payload = {
        "type": f"https://supplymind.local/errors/{status_code}",
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": request.url.path,
        "correlation_id": corr_id
    }

    return JSONResponse(status_code=status_code, content=payload)
