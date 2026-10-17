import asyncio
import datetime
import logging
from contextlib import asynccontextmanager

import asyncpg
from pgvector.asyncpg import register_vector

from app.config import settings
from app.services.observability import DatadogObservability
from app.services.tmdb import MIN_VOTE_AVERAGE, genre_names

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None
_pool_lock: asyncio.Lock | None = None
_pool_loop: asyncio.AbstractEventLoop | None = None


class PoolAcquireTimeout(Exception):
    pass


def _terminate_pool(pool: asyncpg.Pool | None) -> None:
    if pool is None:
        return
    try:
        pool.terminate()
    except Exception:
        logger.exception("failed to terminate stale asyncpg pool")


def _bind_to_running_loop() -> asyncio.Lock:
    global _pool, _pool_lock, _pool_loop
    loop = asyncio.get_running_loop()
    if _pool_loop is not loop:
        old_pool = _pool
        _pool = None
        _pool_lock = asyncio.Lock()
        _pool_loop = loop
        _terminate_pool(old_pool)
    lock = _pool_lock
    if lock is None:
        lock = asyncio.Lock()
        _pool_lock = lock
    return lock


async def get_pool() -> asyncpg.Pool:
    global _pool
    lock = _bind_to_running_loop()
    if _pool is not None:
        return _pool
    async with lock:
        if _pool is not None:
            return _pool
        _pool = await asyncpg.create_pool(
            settings.supabase_db_url,
            init=register_vector,
            min_size=settings.db_pool_min_size,
            max_size=settings.db_pool_max_size,
            command_timeout=settings.db_command_timeout,
            server_settings={"application_name": settings.db_application_name},
        )
        return _pool


async def close_pool() -> None:
    global _pool
    pool = _pool
    if pool is None:
        return
    if _pool_loop is not None and _pool_loop is not asyncio.get_running_loop():
        _bind_to_running_loop()
        return
    await pool.close()
    if _pool is pool:
        _pool = None


@asynccontextmanager
async def _connection():
    pool = await get_pool()
    acquired = False
    try:
        async with pool.acquire(timeout=settings.db_pool_acquire_timeout) as conn:
            acquired = True
            yield conn
    except TimeoutError as exc:
        if not acquired:
            raise PoolAcquireTimeout from exc
        raise


def _with_genres(rows: list[asyncpg.Record]) -> list[dict]:
    movies = []
    for row in rows:
        movie = dict(row)
        movie["genres"] = genre_names(movie.pop("genre_ids", []))
        movies.append(movie)
    return movies


@DatadogObservability.trace_vector_search
async def search_similar(embedding: list[float], limit: int = 25) -> list[dict]:
    async with _connection() as conn:
        rows = await conn.fetch(
            """
            select tmdb_id, title, overview, genre_ids, keywords, poster_path,
                   extract(year from release_date)::int as year, vote_average,
                   embedding_half <=> $1 as distance
            from movies
            where vote_average >= $3
            order by embedding_half <=> $1
            limit $2
            """,
            embedding,
            limit,
            MIN_VOTE_AVERAGE,
        )
    return _with_genres(rows)


async def get_popular_movies(limit: int = 15) -> list[dict]:
    async with _connection() as conn:
        rows = await conn.fetch(
            """
            select tmdb_id, title, poster_path, genre_ids,
                   extract(year from release_date)::int as year, vote_average
            from movies
            where vote_count >= 100 and vote_average >= $2
            order by popularity desc
            limit $1
            """,
            limit,
            MIN_VOTE_AVERAGE,
        )
    return _with_genres(rows)


UPSERT_BATCH_SIZE = 1000

_UPSERT_SQL = """
    insert into movies (
        tmdb_id, title, original_title, original_language, overview,
        genre_ids, keywords, poster_path, backdrop_path, release_date,
        popularity, vote_average, vote_count, embedding_half
    )
    values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14::vector(1536)::halfvec(1536))
    on conflict (tmdb_id) do update set
        title = excluded.title,
        original_title = excluded.original_title,
        original_language = excluded.original_language,
        overview = excluded.overview,
        genre_ids = excluded.genre_ids,
        keywords = excluded.keywords,
        poster_path = excluded.poster_path,
        backdrop_path = excluded.backdrop_path,
        release_date = excluded.release_date,
        popularity = excluded.popularity,
        vote_average = excluded.vote_average,
        vote_count = excluded.vote_count,
        embedding_half = excluded.embedding_half
"""


async def upsert_movies(movies: list[dict], embeddings: list[list[float]]) -> None:
    rows = [
        (
            movie["id"],
            movie["title"],
            movie.get("original_title"),
            movie.get("original_language"),
            movie.get("overview"),
            movie.get("genre_ids", []),
            movie.get("keywords", []),
            movie.get("poster_path"),
            movie.get("backdrop_path"),
            datetime.date.fromisoformat(movie["release_date"]),
            movie.get("popularity"),
            movie.get("vote_average"),
            movie.get("vote_count"),
            embedding,
        )
        for movie, embedding in zip(movies, embeddings, strict=True)
    ]
    async with _connection() as conn:
        for i in range(0, len(rows), UPSERT_BATCH_SIZE):
            batch = rows[i : i + UPSERT_BATCH_SIZE]
            await conn.executemany(_UPSERT_SQL, batch)
            print(f"Upserted {min(i + UPSERT_BATCH_SIZE, len(rows))}/{len(rows)} movies")


_UPDATE_POPULARITY_SQL = """
    update movies set
        popularity = $2,
        vote_average = $3,
        vote_count = $4,
        title = $5,
        poster_path = $6,
        backdrop_path = $7,
        release_date = $8,
        genre_ids = $9
    where tmdb_id = $1
"""

# Titles that fell off TMDB's popular lists would otherwise keep their last high score forever.
# One statement over every stale row exceeds the 30s command timeout. popularity is not indexed.
POPULARITY_RESET_BATCH_SIZE = 500
_RESET_STALE_POPULARITY_SQL = """
    with stale as (
        select tmdb_id from movies
        where popularity > 0 and tmdb_id <> all($1::bigint[])
        limit $2
    )
    update movies set popularity = 0
    from stale
    where movies.tmdb_id = stale.tmdb_id
"""


async def update_popularity(movies: list[dict]) -> int:
    """
    Update popularity metrics only, preserving keywords and embeddings.
    Every other movie's popularity is reset to 0 after those updates commit.

    Used by scheduled ingest to refresh popularity rankings without
    overwriting enriched keywords or regenerating embeddings.

    Returns count of movies updated.
    """
    if not movies:
        raise ValueError("update_popularity got an empty batch; it would reset every movie's popularity")
    rows = [
        (
            movie["id"],
            movie.get("popularity"),
            movie.get("vote_average"),
            movie.get("vote_count"),
            movie["title"],
            movie.get("poster_path"),
            movie.get("backdrop_path"),
            datetime.date.fromisoformat(movie["release_date"]),
            movie.get("genre_ids", []),
        )
        for movie in movies
    ]

    updated = 0
    # Commit the new scores first. A reset timeout must not roll them back.
    async with _connection() as conn:
        async with conn.transaction():
            for i in range(0, len(rows), UPSERT_BATCH_SIZE):
                batch = rows[i : i + UPSERT_BATCH_SIZE]
                await conn.executemany(_UPDATE_POPULARITY_SQL, batch)
                updated += len(batch)
        print(f"Updated popularity for {updated}/{len(rows)} movies")

        keep_ids = [row[0] for row in rows]
        while True:
            async with conn.transaction():
                status = await conn.execute(
                    _RESET_STALE_POPULARITY_SQL,
                    keep_ids,
                    POPULARITY_RESET_BATCH_SIZE,
                )
            if int(status.split()[-1]) == 0:
                break

    return updated
