"""
SupplyMind — Async Thread Pool Offloader
Safely runs synchronous, CPU-bound machine learning inference and SHAP explainability
in worker threads so the FastAPI asyncio event loop is never blocked.
"""
from __future__ import annotations

import asyncio
import functools
from typing import Any, Callable, TypeVar

T = TypeVar("T")


async def run_in_thread(fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """
    Execute a synchronous, CPU-bound callable in Python's default ThreadPoolExecutor
    without blocking the asyncio event loop.

    Example:
        predictions = await run_in_thread(model.predict, df)
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, functools.partial(fn, *args, **kwargs))
