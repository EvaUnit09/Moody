"""Regression tests for the process-wide asyncpg pool budget."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app import db


@pytest.fixture
def reset_pool():
    db._pool = None
    yield
    db._pool = None


@pytest.mark.asyncio
async def test_get_pool_is_a_singleton_under_concurrency(reset_pool):
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


@pytest.mark.asyncio
async def test_update_popularity_releases_connection_on_error(reset_pool):
    class TrackingPool:
        def __init__(self):
            self.in_use = 0
            self.releases = 0

        def acquire(self):
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
    await db.close_pool()
    assert closed is True
    assert db._pool is None
    await db.close_pool()
    assert db._pool is None
