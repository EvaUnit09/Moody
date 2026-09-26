import datetime

import asyncpg
from pgvector.asyncpg import register_vector

from app.config import settings
from app.services.observability import DatadogObservability
from app.services.tmdb import MIN_VOTE_AVERAGE, genre_names

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            settings.supabase_db_url, init=register_vector
        )
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def _with_genres(rows: list[asyncpg.Record]) -> list[dict]:
    movies = []
    for row in rows:
        movie = dict(row)
        movie["genres"] = genre_names(movie.pop("genre_ids", []))
        movies.append(movie)
    return movies


@DatadogObservability.trace_vector_search
async def search_similar(embedding: list[float], limit: int = 25) -> list[dict]:
    pool = await get_pool()
    rows = await pool.fetch(
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
    pool = await get_pool()
    rows = await pool.fetch(
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
    pool = await get_pool()
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
    async with pool.acquire() as conn:
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


async def update_popularity(movies: list[dict]) -> int:
    """
    Update popularity metrics only, preserving keywords and embeddings.
    
    Used by scheduled ingest to refresh popularity rankings without
    overwriting enriched keywords or regenerating embeddings.
    
    Returns count of movies updated.
    """
    pool = await get_pool()
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
    async with pool.acquire() as conn:
        for i in range(0, len(rows), UPSERT_BATCH_SIZE):
            batch = rows[i : i + UPSERT_BATCH_SIZE]
            await conn.executemany(_UPDATE_POPULARITY_SQL, batch)
            updated += len(batch)
            print(f"Updated popularity for {min(i + UPSERT_BATCH_SIZE, len(rows))}/{len(rows)} movies")
    
    return updated
