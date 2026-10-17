import pytest
from unittest.mock import patch
from api.services.cache import cache_result

call_count = 0


@cache_result(ttl_seconds=60, prefix="test:")
async def expensive_fn(name: str, session=None):
    global call_count
    call_count += 1
    return {"name": name, "count": call_count}


class DummySession:
    pass


@pytest.mark.asyncio
async def test_session_arg_excluded_from_cache_key():
    """Two calls with the same scalar argument but different session objects must share cache."""
    global call_count
    call_count = 0

    in_memory: dict = {}

    async def fake_get(key: str):
        import json
        val = in_memory.get(key)
        return json.dumps(val) if val is not None else None

    async def fake_set(key: str, value: str, ttl_seconds: int = 60):
        import json
        in_memory[key] = json.loads(value)
        return True

    with patch("api.services.cache.cache_manager.is_healthy", True), \
         patch("api.services.cache.cache_manager.get", side_effect=fake_get), \
         patch("api.services.cache.cache_manager.set", side_effect=fake_set):
        result1 = await expensive_fn("alice", session=DummySession())
        result2 = await expensive_fn("alice", session=DummySession())

    assert call_count == 1, f"Expected 1 call (cache hit on 2nd), got {call_count}"
    assert result1 == result2


@pytest.mark.asyncio
async def test_different_names_produce_different_cache_entries():
    global call_count
    call_count = 0
    in_memory: dict = {}

    async def fake_get(key: str):
        import json
        val = in_memory.get(key)
        return json.dumps(val) if val is not None else None

    async def fake_set(key: str, value: str, ttl_seconds: int = 60):
        import json
        in_memory[key] = json.loads(value)
        return True

    with patch("api.services.cache.cache_manager.is_healthy", True), \
         patch("api.services.cache.cache_manager.get", side_effect=fake_get), \
         patch("api.services.cache.cache_manager.set", side_effect=fake_set):
        await expensive_fn("alice")
        await expensive_fn("bob")

    assert call_count == 2
