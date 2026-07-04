"""
SupplyMind — JWT Authentication & Authorization (Category 5)
Extracts tokens, validates signatures, and enforces role permission rules.

Fix 8: JWT debug bypass now requires BOTH debug=True AND allow_auth_bypass=True.
A single forgotten `debug=True` env var can no longer open the API.
Bypass activation always emits a WARNING-level log for auditability.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Callable
import jwt
from fastapi import Request, HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from config import settings

logger = logging.getLogger(__name__)

# Bearer parser helper
security_agent = HTTPBearer()


def _auth_bypass_active() -> bool:
    """
    Returns True only when BOTH debug=True AND allow_auth_bypass=True are set.
    This double-gating prevents a single misconfigured flag from bypassing auth.
    """
    return settings.debug and settings.allow_auth_bypass


def create_jwt_token(user_id: str, role: str) -> str:
    """Helper utility to sign test JWT payloads."""
    payload = {
        "sub": user_id,
        "role": role,
        "exp": int(datetime.now(timezone.utc).timestamp()) + (settings.access_token_expire_minutes * 60)
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


async def get_current_user(request: Request) -> dict[str, str]:
    """
    FastAPI dependency that parses and validates incoming Bearer JWT tokens.

    Auth bypass behaviour (Fix 8):
      - Bypass is ONLY active when BOTH `debug=True` AND `allow_auth_bypass=True`
        are set in settings. A WARNING is logged every time bypass is used.
      - In production (debug=False), missing or invalid tokens always raise 401.
    """
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        if _auth_bypass_active():
            logger.warning(
                "⚠️  JWT AUTH BYPASS ACTIVE (debug=%s, allow_auth_bypass=%s). "
                "Missing Authorization header \u2014 returning mock admin user. "
                "DO NOT run with these settings in staging or production.",
                settings.debug, settings.allow_auth_bypass,
            )
            return {"user_id": "admin_carlos", "role": "admin"}
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        user_id = payload.get("sub")
        role = payload.get("role")

        if not user_id or not role:
            raise HTTPException(status_code=401, detail="Invalid token claims: missing sub or role")

        return {
            "user_id": str(user_id),
            "role": str(role),
        }

    except jwt.ExpiredSignatureError:
        if _auth_bypass_active():
            logger.warning(
                "⚠️  JWT AUTH BYPASS ACTIVE: expired token accepted for user=admin_carlos "
                "(debug=%s, allow_auth_bypass=%s). DO NOT use in production.",
                settings.debug, settings.allow_auth_bypass,
            )
            return {"user_id": "admin_carlos", "role": "admin"}
        raise HTTPException(status_code=401, detail="Token signature expired")

    except jwt.InvalidTokenError:
        if _auth_bypass_active():
            logger.warning(
                "⚠️  JWT AUTH BYPASS ACTIVE: invalid token accepted for user=admin_carlos "
                "(debug=%s, allow_auth_bypass=%s). DO NOT use in production.",
                settings.debug, settings.allow_auth_bypass,
            )
            return {"user_id": "admin_carlos", "role": "admin"}
        raise HTTPException(status_code=401, detail="Invalid token signature")


def require_role(allowed_roles: list[str]) -> Callable:
    """
    Dependency generator validating that the authenticated user possesses
    one of the allowed permission roles (viewer | approver | admin).
    """
    def dependency(user: dict[str, str] = Depends(get_current_user)) -> dict[str, str]:
        user_role = user.get("role")
        if user_role not in allowed_roles:
            logger.warning("Access denied: role %s not in authorized list %s", user_role, allowed_roles)
            raise HTTPException(status_code=403, detail="Operation not permitted for this user role")
        return user
    return dependency
