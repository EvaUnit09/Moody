#!/usr/bin/env python3
"""
Ingest TMDB popular and trending movies into Supabase.

Fetches current popular and trending movies from TMDB and updates their
popularity metrics in the movies table. Preserves enriched keywords and
embeddings.

Usage:
    python -m app.scripts.ingest_popular

Environment variables (from .env):
    - API_READ_ACCESS_TOKEN: TMDB API read access token
    - SUPABASE_DB_URL: Postgres connection string

Exit codes:
    0: Success (popularity updated)
    1: TMDB API error (keep existing shelf, no DB changes)
    2: Database error (partial failure)

Note:
    This script runs in GitHub Actions and cannot bust Railway's in-memory cache.
    Railway's __popular__ entry uses a 1-hour TTL and a warm loop every
    3300 seconds. The 2-hour TTL is only for popular-mood /recommend queries.
"""

import asyncio
import sys

import httpx

from app.db import get_pool, update_popularity
from app.services.tmdb import BASE_URL, HEADERS, MIN_VOTE_AVERAGE

# Fetch top N pages from each endpoint to capture ~100-200 movies total
POPULAR_PAGES = 3
TRENDING_PAGES = 2
REQUEST_TIMEOUT = 15.0


async def fetch_popular_movies() -> list[dict]:
    """Fetch current popular movies from TMDB."""
    movies = []
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        for page in range(1, POPULAR_PAGES + 1):
            try:
                resp = await client.get(
                    f"{BASE_URL}/movie/popular",
                    headers=HEADERS,
                    params={"page": page},
                )
                resp.raise_for_status()
                results = resp.json().get("results", [])
                movies.extend(results)
                print(f"Fetched popular page {page}: {len(results)} movies")
            except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.RequestError) as e:
                print(f"Failed to fetch popular page {page}: {e}")
                raise
    return movies


async def fetch_trending_movies() -> list[dict]:
    """Fetch current trending movies from TMDB (weekly window)."""
    movies = []
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        for page in range(1, TRENDING_PAGES + 1):
            try:
                resp = await client.get(
                    f"{BASE_URL}/trending/movie/week",
                    headers=HEADERS,
                    params={"page": page},
                )
                resp.raise_for_status()
                results = resp.json().get("results", [])
                movies.extend(results)
                print(f"Fetched trending page {page}: {len(results)} movies")
            except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.RequestError) as e:
                print(f"Failed to fetch trending page {page}: {e}")
                raise
    return movies


def _filter_and_deduplicate(movies: list[dict]) -> list[dict]:
    """Filter by quality thresholds and deduplicate by TMDB ID."""
    seen_ids = set()
    filtered = []
    
    for movie in movies:
        tmdb_id = movie.get("id")
        vote_avg = movie.get("vote_average", 0.0)
        release_date_str = movie.get("release_date")
        
        # Skip if missing required fields
        if not tmdb_id or not release_date_str:
            continue
            
        # Skip if below quality threshold
        if vote_avg < MIN_VOTE_AVERAGE:
            continue
            
        # Deduplicate by ID
        if tmdb_id in seen_ids:
            continue
            
        seen_ids.add(tmdb_id)
        filtered.append(movie)
    
    return filtered


async def ingest_popular() -> int:
    """
    Main ingest routine.
    
    Returns:
        0 on success, 1 on TMDB error, 2 on DB error
    """
    print("=== Starting popular/trending ingest ===")
    
    # Step 1: Fetch from TMDB
    try:
        popular, trending = await asyncio.gather(
            fetch_popular_movies(),
            fetch_trending_movies(),
        )
    except Exception as e:
        print(f"TMDB fetch failed: {e}")
        print("Keeping existing shelf (no DB changes)")
        return 1
    
    # Step 2: Filter and deduplicate
    all_movies = popular + trending
    movies = _filter_and_deduplicate(all_movies)
    print(f"After filtering and dedup: {len(movies)} movies")
    
    if not movies:
        print("No movies to ingest after filtering")
        return 0
    
    # Step 3: Update popularity in database (preserves keywords and embeddings)
    try:
        await get_pool()  # Ensure pool is initialized
        updated = await update_popularity(movies)
        print(f"Successfully updated popularity for {updated} movies")
    except Exception as e:
        print(f"Database update failed: {e}")
        return 2
    
    print("=== Ingest complete ===")
    print("Note: GitHub Actions cannot bust Railway's cache (process-local).")
    print("Railway __popular__ cache refreshes on its 55min warm loop or after the 1h TTL.")
    return 0


def main() -> None:
    """CLI entrypoint."""
    exit_code = asyncio.run(ingest_popular())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
