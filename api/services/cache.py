"""
SupplyMind — Cache & Redis Layer (Category 2)
Provides connection pooling, cache decorators, invalidation, and circuit breaker fallbacks.
"""

from __future__ import annotations

import functools
import json
import logging
from typing import Any, Callable
import redis.asyncio as aioredis

from config import settings

logger = logging.getLogger(__name__)

# Redis Client connection details
# Defaults to localhost or config url
class RedisCacheManager:
    """Manages Redis connection pooling and client requests."""
    _instance: RedisCacheManager | None = None

    def __new__(cls) -> RedisCacheManager:
        if cls._instance is None:
            cls._instance = super(RedisCacheManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.client: aioredis.Redis | None = None
        self.is_healthy = False
        self._initialized = True

    async def connect(self) -> None:
        """Initialize connections using pool parameters."""
        try:
            logger.info("Initializing Redis connection pool to: %s", settings.redis_url)
            self.client = aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20,
                socket_timeout=2.0,
                socket_connect_timeout=2.0,
            )
            await self.ping()
        except Exception as exc:
            logger.warning("Redis initialization failed: %s. Circuit breaker active.", exc)
            self.client = None
            self.is_healthy = False

    async def ping(self) -> bool:
        """Health check endpoint to test connection status."""
        if not self.client:
            self.is_healthy = False
            return False
        try:
            await self.client.ping()
            self.is_healthy = True
            return True
        except Exception:
            self.is_healthy = False
            return False

    async def get(self, key: str) -> str | None:
        """Retrieves raw string keys with fallback breaker."""
        if not self.is_healthy or not self.client:
            return None
        try:
            return await self.client.get(key)
        except Exception as exc:
            logger.warning("Redis GET failed for %s, circuit breaker tripped: %s", key, exc)
            self.is_healthy = False
            return None

    async def set(self, key: str, value: str, ttl_seconds: int = 3600) -> bool:
        """Stores a serialized payload in Redis with TTL validation."""
        if not self.is_healthy or not self.client:
            return False
        try:
            await self.client.set(key, value, ex=ttl_seconds)
            return True
        except Exception as exc:
            logger.warning("Redis SET failed for %s, circuit breaker tripped: %s", key, exc)
            self.is_healthy = False
            return False

    async def delete(self, key: str) -> bool:
        """Removes a key from cache registry."""
        if not self.is_healthy or not self.client:
            return False
        try:
            await self.client.delete(key)
            return True
        except Exception as exc:
            logger.warning("Redis DELETE failed for %s: %s", key, exc)
            return False

# Global singleton cache instance
cache_manager = RedisCacheManager()


def cache_result(ttl_seconds: int = 3600, prefix: str = "supplymind:") -> Callable:
    """
    Decorator to cache async service method return structures.
    Uses method arguments to construct unique keys.
    Falls back to normal compute execution if Redis connection fails.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Construct distinct keys from function name and parameter strings
            # Exclude self or cls instances
            func_args = [str(arg) for arg in args[1:]] if args else []
            func_kwargs = [f"{k}={v}" for k, v in sorted(kwargs.items())]
            key_body = ":".join(func_args + func_kwargs)
            cache_key = f"{prefix}{func.__name__}:{key_body}"

            # Step 1: Query cache if manager claims to be healthy
            if cache_manager.is_healthy:
                cached_val = await cache_manager.get(cache_key)
                if cached_val:
                    try:
                        logger.debug("Cache hit for: %s", cache_key)
                        return json.loads(cached_val)
                    except json.JSONDecodeError:
                        logger.error("JSON decode error reading cache key %s", cache_key)

            # Step 2: Fallback execution on miss/break
            logger.debug("Cache miss/breaker active for: %s", cache_key)
            result = await func(*args, **kwargs)

            # Step 3: Write computed payload back to cache
            if cache_manager.is_healthy:
                try:
                    serialized = json.dumps(result)
                    await cache_manager.set(cache_key, serialized, ttl_seconds)
                except Exception as exc:
                    logger.warning("Failed to serialize and write cache key %s: %s", cache_key, exc)

            return result
        return wrapper
    return decorator
