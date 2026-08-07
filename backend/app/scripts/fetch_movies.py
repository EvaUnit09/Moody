import asyncio
import json
import math
from datetime import date
from pathlib import Path

import httpx

from app.services.tmdb import BASE_URL, HEADERS

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

CURRENT_YEAR = date.today().year
PAGE_SIZE = 20
VOTE_COUNT_MIN = 20
CONCURRENCY = 15

# Recent-weighted: TMDB's popularity signal and vote coverage are both
# stronger in recent decades, so recent years get a bigger per-year quota
# and older years taper off. Targets ~30k movies total.
YEAR_BUCKETS = [
    (2015, CURRENT_YEAR, 800),
    (2000, 2014, 600),
    (1980, 1999, 400),
    (1950, 1979, 150),
]


def year_quotas() -> list[tuple[int, int]]:
    return [
        (year, quota)
        for start, end, quota in YEAR_BUCKETS
        for year in range(start, end + 1)
    ]


async def fetch_year_page(
    client: httpx.AsyncClient, year: int, page: int, semaphore: asyncio.Semaphore
) -> list[dict]:
    async with semaphore:
        params = {
            "sort_by": "popularity.desc",
            "primary_release_year": year,
            "vote_count.gte": VOTE_COUNT_MIN,
            "include_adult": "false",
            "page": page,
        }
        try:
            resp = await client.get(
                f"{BASE_URL}/discover/movie", headers=HEADERS, params=params
            )
            resp.raise_for_status()
            return resp.json().get("results", [])
        except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.RequestError) as e:
            print(f"Failed to fetch year={year} page={page}: {e}")
            return []


async def fetch_all_movies() -> list[dict]:
    semaphore = asyncio.Semaphore(CONCURRENCY)
    movies_by_id: dict[int, dict] = {}

    async with httpx.AsyncClient(timeout=30.0) as client:
        for year, quota in year_quotas():
            pages_needed = math.ceil(quota / PAGE_SIZE)
            pages = await asyncio.gather(
                *[
                    fetch_year_page(client, year, page, semaphore)
                    for page in range(1, pages_needed + 1)
                ]
            )
            year_new_count = 0
            for page_results in pages:
                for movie in page_results:
                    if movie["id"] not in movies_by_id:
                        movies_by_id[movie["id"]] = movie
                        year_new_count += 1
            print(f"{year}: +{year_new_count} movies (running total {len(movies_by_id)})")

    return list(movies_by_id.values())


def get_all_movies() -> None:
    movies = asyncio.run(fetch_all_movies())

    with open(DATA_DIR / "raw_movies.json", "w") as f:
        json.dump(movies, f, indent=2)

    print(f"Saved {len(movies)} movies")


if __name__ == "__main__":
    get_all_movies()
