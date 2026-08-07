import datetime

import asyncpg
from pgvector.asyncpg import register_vector

from app.config import settings

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


async def search_similar(embedding: list[float], limit: int = 25) -> list[dict]:
    pool = await get_pool()
    rows = await pool.fetch(
        """
        select tmdb_id, title, overview, genre_ids, keywords, poster_path,
               extract(year from release_date)::int as year, vote_average,
               embedding <=> $1 as distance
        from movies
        order by embedding <=> $1
        limit $2
        """,
        embedding,
        limit,
    )
    return [dict(row) for row in rows]


UPSERT_BATCH_SIZE = 1000

_UPSERT_SQL = """
    insert into movies (
        tmdb_id, title, original_title, original_language, overview,
        genre_ids, keywords, poster_path, backdrop_path, release_date,
        popularity, vote_average, vote_count, embedding
    )
    values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
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
        embedding = excluded.embedding
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
        for movie, embedding in zip(movies, embeddings)
    ]
    async with pool.acquire() as conn:
        for i in range(0, len(rows), UPSERT_BATCH_SIZE):
            batch = rows[i : i + UPSERT_BATCH_SIZE]
            await conn.executemany(_UPSERT_SQL, batch)
            print(f"Upserted {min(i + UPSERT_BATCH_SIZE, len(rows))}/{len(rows)} movies")
