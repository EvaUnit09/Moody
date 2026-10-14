import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from app import db
from app.config import Settings

_POOLER_URL = "postgresql://user:pass@pooler:5432/postgres"


@pytest.fixture
def reset_pool():
    db._pool = None
    db._pool_lock = None
    db._pool_loop_id = None
    yield
    db._pool = None
    db._pool_lock = None
    db._pool_loop_id = None


async def _contend_for_pool():
    create_calls = 0

    async def fake_create_pool(*args, **kwargs):
        nonlocal create_calls
        create_calls += 1
        await asyncio.sleep(0.05)
        return object()

    with patch.object(db.asyncpg, "create_pool", side_effect=fake_create_pool):
        pools = await asyncio.gather(*[db.get_pool() for _ in range(8)])
        again = await db.get_pool()

    assert create_calls == 1
    assert len({id(pool) for pool in pools}) == 1
    assert pools[0] is db._pool
    assert again is pools[0]
    return pools[0]


@pytest.mark.asyncio(loop_scope="function")
async def test_get_pool_contention_on_first_loop():
    await _contend_for_pool()


@pytest.mark.asyncio(loop_scope="function")
async def test_get_pool_contention_on_second_loop():
    await _contend_for_pool()


def test_get_pool_survives_two_asyncio_run_calls():
    asyncio.run(_contend_for_pool())
    asyncio.run(_contend_for_pool())


@pytest.mark.asyncio
async def test_get_pool_bounds_min_and_max_size(reset_pool):
    captured = {}

    async def fake_create_pool(*args, **kwargs):
        captured.update(kwargs)
        captured["_args"] = args
        return object()

    with patch.object(db.asyncpg, "create_pool", side_effect=fake_create_pool):
        await db.get_pool()

    assert captured["min_size"] == 1
    assert captured["max_size"] == 2
    assert captured["command_timeout"] == 30.0


@pytest.mark.asyncio
async def test_connection_raises_pool_acquire_timeout():
    class BusyPool:
        def acquire(self, *, timeout=None):
            raise TimeoutError("queue empty")

    with patch.object(db, "get_pool", new=AsyncMock(return_value=BusyPool())):
        with pytest.raises(db.PoolAcquireTimeout):
            async with db._connection():
                pass


@pytest.mark.asyncio
async def test_connection_propagates_query_timeout():
    class HeldPool:
        def acquire(self, **kwargs):
            class _Acquire:
                async def __aenter__(self):
                    return object()

                async def __aexit__(self, exc_type, exc, tb):
                    return False

            return _Acquire()

    with patch.object(db, "get_pool", new=AsyncMock(return_value=HeldPool())):
        with pytest.raises(TimeoutError, match="command timeout"):
            async with db._connection():
                raise TimeoutError("command timeout")


@pytest.mark.asyncio
async def test_update_popularity_releases_connection_on_error(reset_pool):
    class TrackingPool:
        def __init__(self):
            self.in_use = 0
            self.releases = 0

        def acquire(self, **kwargs):
            pool = self

            class _Acquire:
                async def __aenter__(self):
                    pool.in_use += 1
                    return BoomConnection()

                async def __aexit__(self, exc_type, exc, tb):
                    pool.in_use -= 1
                    pool.releases += 1
                    return False

            return _Acquire()

    class BoomConnection:
        async def executemany(self, *args, **kwargs):
            raise RuntimeError("executemany failed")

    pool = TrackingPool()

    with patch.object(db, "get_pool", new=AsyncMock(return_value=pool)):
        with pytest.raises(RuntimeError, match="executemany failed"):
            await db.update_popularity(
                [
                    {
                        "id": 1,
                        "title": "Heat",
                        "popularity": 10.0,
                        "vote_average": 8.2,
                        "vote_count": 100,
                        "poster_path": "/x.jpg",
                        "backdrop_path": "/y.jpg",
                        "release_date": "1995-12-15",
                        "genre_ids": [80],
                    }
                ]
            )

    assert pool.in_use == 0
    assert pool.releases == 1


@pytest.mark.asyncio
async def test_close_pool_closes_and_clears(reset_pool):
    closed = False

    class FakePool:
        async def close(self):
            nonlocal closed
            closed = True

    db._pool = FakePool()
    db._pool_loop_id = id(asyncio.get_running_loop())
    await db.close_pool()
    assert closed is True
    assert db._pool is None
    await db.close_pool()
    assert db._pool is None


def test_direct_url_falls_back_to_pooler_url():
    direct = "postgresql://user:pass@db:5432/postgres"
    fallback = Settings(supabase_db_url=_POOLER_URL)
    assert fallback.supabase_index_url == _POOLER_URL
    preferred = Settings(supabase_db_url=_POOLER_URL, supabase_db_direct_url=direct)
    assert preferred.supabase_index_url == direct


@pytest.mark.asyncio
async def test_loop_change_terminates_previous_pool(reset_pool):
    class FakePool:
        def __init__(self):
            self.terminated = False

        def terminate(self):
            self.terminated = True

    first = FakePool()
    db._pool = first
    db._pool_lock = asyncio.Lock()
    db._pool_loop_id = -1
    db._bind_to_running_loop()
    assert first.terminated is True
    assert db._pool is None


@pytest.mark.asyncio
async def test_loop_change_swallows_terminate_errors(reset_pool):
    class BoomPool:
        def terminate(self):
            raise RuntimeError("already closed")

    db._pool = BoomPool()
    db._pool_lock = asyncio.Lock()
    db._pool_loop_id = -1
    db._bind_to_running_loop()
    assert db._pool is None


@pytest.mark.asyncio
async def test_close_pool_terminates_when_loop_mismatches(reset_pool):
    class FakePool:
        def __init__(self):
            self.terminated = False

        def terminate(self):
            self.terminated = True

        async def close(self):
            raise AssertionError("close should not run on a dead loop")

    pool = FakePool()
    db._pool = pool
    db._pool_loop_id = -1
    await db.close_pool()
    assert pool.terminated is True
    assert db._pool is None


def test_settings_pool_defaults_and_test_min_zero():
    defaults = Settings(supabase_db_url=_POOLER_URL)
    assert defaults.db_pool_min_size == 1
    assert defaults.db_pool_max_size == 2
    assert defaults.db_command_timeout == 30.0
    assert defaults.db_pool_acquire_timeout == 5.0
    test_like = Settings(supabase_db_url=_POOLER_URL, db_pool_min_size=0)
    assert test_like.db_pool_min_size == 0
    assert test_like.db_pool_max_size == 2


@pytest.mark.parametrize(
    "overrides,match",
    [
        ({"db_pool_min_size": -1}, "greater than or equal to 0"),
        ({"db_pool_max_size": 0}, "greater than or equal to 1"),
        ({"db_command_timeout": 0}, "greater than 0"),
        ({"db_pool_acquire_timeout": -1}, "greater than 0"),
        ({"db_pool_min_size": 3, "db_pool_max_size": 2}, "must be <="),
    ],
)
def test_settings_reject_invalid_pool_bounds(overrides, match):
    with pytest.raises(ValidationError, match=match):
        Settings(supabase_db_url=_POOLER_URL, **overrides)
