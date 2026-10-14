import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app import cache
from app.db import PoolAcquireTimeout
from app.main import _refresh_popular_cache_periodically
from app.routers.popular import POPULAR_CACHE_KEY, popular


@pytest.mark.asyncio
async def test_popular_returns_503_on_pool_acquire_timeout():
    cache._cache.pop(POPULAR_CACHE_KEY, None)

    with patch(
        "app.routers.popular.get_popular_movies",
        new_callable=AsyncMock,
        side_effect=PoolAcquireTimeout,
    ):
        with pytest.raises(HTTPException) as exc_info:
            await popular()

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Database busy, try again shortly"


@pytest.mark.asyncio
async def test_refresh_popular_cache_continues_after_timeout():
    sleeps = 0

    async def fake_sleep(_seconds):
        nonlocal sleeps
        sleeps += 1
        if sleeps >= 3:
            raise asyncio.CancelledError()

    with (
        patch("app.main.asyncio.sleep", side_effect=fake_sleep),
        patch(
            "app.main.warm_popular_cache",
            new_callable=AsyncMock,
            side_effect=PoolAcquireTimeout,
        ),
        patch("app.main.logger.exception") as log_exc,
    ):
        with pytest.raises(asyncio.CancelledError):
            await _refresh_popular_cache_periodically()

    assert sleeps == 3
    assert log_exc.call_count == 2


@pytest.mark.asyncio
async def test_refresh_popular_cache_propagates_cancelled_error():
    async def once(_seconds):
        return None

    with (
        patch("app.main.asyncio.sleep", side_effect=once),
        patch(
            "app.main.warm_popular_cache",
            new_callable=AsyncMock,
            side_effect=asyncio.CancelledError,
        ),
        patch("app.main.logger.exception") as log_exc,
    ):
        with pytest.raises(asyncio.CancelledError):
            await _refresh_popular_cache_periodically()

    log_exc.assert_not_called()
