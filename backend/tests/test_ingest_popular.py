"""Drives ingest_popular end to end against a fake TMDB, with the DB write stubbed."""

from unittest.mock import AsyncMock

import httpx
import pytest

from app.scripts import ingest_popular as ingest


def _movie(tmdb_id: int) -> dict:
    return {"id": tmdb_id, "title": f"Movie {tmdb_id}", "vote_average": 7.0, "release_date": "2024-01-01"}


@pytest.fixture
def tmdb(monkeypatch):
    requests: list[str] = []
    failing_paths: set[str] = set()

    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        requests.append(f"{request.url.path}?page={page}")
        if request.url.path in failing_paths:
            return httpx.Response(500)
        return httpx.Response(200, json={"results": [_movie(page)]})

    real_client = httpx.AsyncClient
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(ingest.httpx, "AsyncClient", lambda **kwargs: real_client(transport=transport, **kwargs))
    update = AsyncMock(side_effect=lambda movies: len(movies))
    monkeypatch.setattr(ingest, "update_popularity", update)
    monkeypatch.setattr(ingest, "close_pool", AsyncMock())
    return requests, failing_paths, update


async def test_fetches_every_page_and_writes_deduplicated_movies(tmdb):
    requests, _, update = tmdb

    assert await ingest.ingest_popular() == 0

    assert sorted(requests) == [
        "/3/movie/popular?page=1",
        "/3/movie/popular?page=2",
        "/3/movie/popular?page=3",
        "/3/trending/movie/week?page=1",
        "/3/trending/movie/week?page=2",
    ]
    assert [m["id"] for m in update.await_args.args[0]] == [1, 2, 3]


async def test_tmdb_error_exits_1_without_writing(tmdb):
    _, failing_paths, update = tmdb
    failing_paths.add("/3/trending/movie/week")

    assert await ingest.ingest_popular() == 1

    update.assert_not_awaited()
