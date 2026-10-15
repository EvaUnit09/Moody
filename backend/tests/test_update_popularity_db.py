"""Runs update_popularity against a real Postgres. Set MOODY_TEST_DB_URL to a disposable database."""

import os

import asyncpg
import pytest

from app import db

TEST_DB_URL = os.environ.get("MOODY_TEST_DB_URL")

pytestmark = pytest.mark.skipif(not TEST_DB_URL, reason="MOODY_TEST_DB_URL not set")


async def _no_vector(conn):
    return None


def _tmdb_movie(tmdb_id: int, popularity: float) -> dict:
    return {
        "id": tmdb_id,
        "title": f"Movie {tmdb_id}",
        "popularity": popularity,
        "vote_average": 7.0,
        "vote_count": 500,
        "release_date": "2024-01-01",
        "genre_ids": [18],
    }


async def test_movies_missing_from_the_ingest_lose_their_popularity(monkeypatch):
    monkeypatch.setattr(db.settings, "supabase_db_url", TEST_DB_URL)
    monkeypatch.setattr(db, "register_vector", _no_vector)
    conn = await asyncpg.connect(TEST_DB_URL)
    await conn.execute(
        """
        drop table if exists movies;
        create table movies (
            tmdb_id bigint primary key, title text not null, poster_path text, backdrop_path text,
            release_date date, genre_ids integer[], popularity double precision,
            vote_average double precision, vote_count integer
        );
        insert into movies (tmdb_id, title, popularity, vote_average, vote_count)
        values (1, 'Old hit', 500, 7, 500), (2, 'Current hit', 50, 7, 500);
        """
    )

    try:
        await db.update_popularity([_tmdb_movie(2, 300)])
        rows = dict(await conn.fetch("select tmdb_id, popularity from movies"))
    finally:
        await db.close_pool()
        await conn.close()

    assert rows == {1: 0, 2: 300}
