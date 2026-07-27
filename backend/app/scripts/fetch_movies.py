import json
from pathlib import Path

import httpx

from app.services.tmdb import BASE_URL, HEADERS

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def get_all_movies():
    all_movies = []
    for page in range(1, 11):
        params = {"sort_by": "popularity.desc", "page": page}
        resp = httpx.get(f"{BASE_URL}/discover/movie", headers=HEADERS, params=params)
        all_movies.extend(resp.json()["results"])

    with open(DATA_DIR / "raw_movies.json", "w") as f:
        json.dump(all_movies, f, indent=2)

    print(f"Saved {len(all_movies)} movies")


if __name__ == "__main__":
    get_all_movies()

