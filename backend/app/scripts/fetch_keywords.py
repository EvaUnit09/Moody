import asyncio
import json
from pathlib import Path

import httpx

from app.services.tmdb import BASE_URL, HEADERS

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

PROGRESS_INTERVAL = 1000


async def get_keywords_for_movie(
    client: httpx.AsyncClient,
    movie_id: int,
    semaphore: asyncio.Semaphore,
    progress: list[int],
) -> tuple[int, list[str]]:
    async with semaphore:
        try:
            resp = await client.get(
                f"{BASE_URL}/movie/{movie_id}/keywords",
                headers=HEADERS,
            )
            resp.raise_for_status()
            data = resp.json()
            keywords = [kw["name"] for kw in data.get("keywords", [])]
        except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.RequestError) as e:
            print(f"Failed to fetch keywords for movie {movie_id}: {e}")
            keywords = []

        progress[0] += 1
        if progress[0] % PROGRESS_INTERVAL == 0:
            print(f"Fetched keywords for {progress[0]} movies")

        return movie_id, keywords


async def enrich_movies_with_keywords(movies: list[dict]) -> list[dict]:
    semaphore = asyncio.Semaphore(15)
    progress = [0]
    async with httpx.AsyncClient(timeout=30.0) as client:
        results = await asyncio.gather(
            *[
                get_keywords_for_movie(client, movie["id"], semaphore, progress)
                for movie in movies
            ]
        )

    keywords_by_id = {movie_id: keywords for movie_id, keywords in results}
    return [
        {**movie, "keywords": keywords_by_id.get(movie["id"], [])} for movie in movies
    ]


if __name__ == "__main__":
    with open(DATA_DIR / "raw_movies.json") as f:
        movies = json.load(f)

    enriched = asyncio.run(enrich_movies_with_keywords(movies))

    with open(DATA_DIR / "movies_with_keywords.json", "w") as f:
        json.dump(enriched, f, indent=2)

    print(f"Saved {len(enriched)} movies with keywords")
