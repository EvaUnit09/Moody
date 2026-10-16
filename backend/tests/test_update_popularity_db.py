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


_MOVIES_DDL = """
    drop table if exists movies;
    create table movies (
        tmdb_id bigint primary key, title text not null, poster_path text, backdrop_path text,
        release_date date, genre_ids integer[], popularity double precision,
        vote_average double precision, vote_count integer
    );
"""


async def test_movies_missing_from_the_ingest_lose_their_popularity(monkeypatch):
    monkeypatch.setattr(db.settings, "supabase_db_url", TEST_DB_URL)
    monkeypatch.setattr(db, "register_vector", _no_vector)
    monkeypatch.setattr(db, "POPULARITY_RESET_BATCH_SIZE", 1)
    conn = await asyncpg.connect(TEST_DB_URL)
    await conn.execute(
        _MOVIES_DDL
        + """
        insert into movies (tmdb_id, title, popularity, vote_average, vote_count)
        values (1, 'Old hit', 500, 7, 500), (2, 'Current hit', 50, 7, 500), (3, 'Other hit', 40, 7, 500);
        """
    )

    try:
        await db.update_popularity([_tmdb_movie(2, 300)])
        rows = dict(await conn.fetch("select tmdb_id, popularity from movies"))
    finally:
        await db.close_pool()
        await conn.close()

    assert rows == {1: 0, 2: 300, 3: 0}


async def test_real_reset_failure_keeps_committed_scores_and_finished_batches(monkeypatch):
    monkeypatch.setattr(db.settings, "supabase_db_url", TEST_DB_URL)
    monkeypatch.setattr(db, "register_vector", _no_vector)
    monkeypatch.setattr(db, "POPULARITY_RESET_BATCH_SIZE", 1)
    conn = await asyncpg.connect(TEST_DB_URL)
    await conn.execute(
        _MOVIES_DDL
        + """
        insert into movies (tmdb_id, title, popularity, vote_average, vote_count)
        values (1, 'Old hit', 500, 7, 500), (2, 'Current hit', 50, 7, 500), (3, 'Other hit', 40, 7, 500);

        drop table if exists reset_attempts;
        create table reset_attempts (n int);
        insert into reset_attempts values (0);

        create or replace function fail_after_first_stale_reset() returns trigger
        language plpgsql as $fn$
        declare
            seen int;
        begin
            if new.popularity = 0 and old.popularity > 0 then
                update reset_attempts set n = n + 1 returning n into seen;
                if seen > 1 then
                    raise exception 'second stale reset failed';
                end if;
            end if;
            return new;
        end;
        $fn$;

        create trigger fail_after_first_stale_reset
        before update on movies
        for each row execute function fail_after_first_stale_reset();
        """
    )

    try:
        with pytest.raises(asyncpg.PostgresError):
            await db.update_popularity([_tmdb_movie(2, 300)])
        rows = dict(await conn.fetch("select tmdb_id, popularity from movies"))
    finally:
        await db.close_pool()
        await conn.close()

    assert rows[2] == 300
    assert len([tmdb_id for tmdb_id in (1, 3) if rows[tmdb_id] == 0]) == 1
    assert rows[1] in (0, 500)
    assert rows[3] in (0, 40)
