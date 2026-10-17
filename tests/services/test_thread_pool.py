import threading
import pytest
from api.services.thread_pool import run_in_thread


def _get_thread_id() -> int:
    return threading.get_ident()


@pytest.mark.asyncio
async def test_executes_on_worker_thread():
    """Callable must run on a worker thread, not the main asyncio event loop thread."""
    loop_thread_id = threading.get_ident()
    worker_thread_id = await run_in_thread(_get_thread_id)
    assert worker_thread_id != loop_thread_id, "run_in_thread did not offload to a worker thread"


@pytest.mark.asyncio
async def test_returns_value():
    result = await run_in_thread(lambda a, b: a * b, 6, 7)
    assert result == 42


@pytest.mark.asyncio
async def test_propagates_exceptions():
    def failing_fn():
        raise ValueError("synthetic test failure")

    with pytest.raises(ValueError, match="synthetic test failure"):
        await run_in_thread(failing_fn)
