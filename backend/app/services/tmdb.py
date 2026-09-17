import os
from typing import Any
from functools import lru_cache

import httpx
from dotenv import load_dotenv

load_dotenv()

API_READ_TOKEN = os.getenv("API_READ_ACCESS_TOKEN")
BASE_URL = "https://api.themoviedb.org/3"

HEADERS = {
    "accept": "application/json",
    "Authorization": f"Bearer {API_READ_TOKEN}",
}

MIN_VOTE_AVERAGE = 5.0

GENRE_MAP: dict[int, str] = {
    28: "Action",
    12: "Adventure",
    16: "Animation",
    35: "Comedy",
    80: "Crime",
    99: "Documentary",
    18: "Drama",
    10751: "Family",
    14: "Fantasy",
    36: "History",
    27: "Horror",
    10402: "Music",
    9648: "Mystery",
    10749: "Romance",
    878: "Science Fiction",
    10770: "TV Movie",
    53: "Thriller",
    10752: "War",
    37: "Western",
}


def genre_names(genre_ids: list[int]) -> list[str]:
    return [GENRE_MAP[gid] for gid in genre_ids if gid in GENRE_MAP]


class WatchProviderService:
    """Service for fetching TMDB watch provider data with caching."""
    
    LOGO_BASE_URL = "https://image.tmdb.org/t/p/original"
    DEFAULT_REGION = "US"
    MAX_PROVIDERS = 3
    
    @classmethod
    @lru_cache(maxsize=1024)
    def _fetch_providers_sync(cls, tmdb_id: int, region: str) -> tuple[dict[str, Any], ...]:
        """Synchronous cached provider fetch. Returns tuple for hashability."""
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(
                    f"{BASE_URL}/movie/{tmdb_id}/watch/providers",
                    headers=HEADERS,
                )
                response.raise_for_status()
                data = response.json()
                
                region_data = data.get("results", {}).get(region, {})
                if not region_data:
                    return tuple()
                
                # Prefer flatrate (subscription streaming), fallback to buy/rent
                providers = (
                    region_data.get("flatrate", [])
                    or region_data.get("buy", [])
                    or region_data.get("rent", [])
                )
                
                link = region_data.get("link", f"https://www.themoviedb.org/movie/{tmdb_id}/watch")
                
                result = []
                for provider in providers[:cls.MAX_PROVIDERS]:
                    result.append({
                        "name": provider.get("provider_name", ""),
                        "logo_url": f"{cls.LOGO_BASE_URL}{provider['logo_path']}" if provider.get("logo_path") else None,
                        "link": link,
                    })
                
                return tuple(tuple(sorted(p.items())) for p in result)
                
        except Exception as e:
            print(f"[watch_providers] Failed to fetch for tmdb_id={tmdb_id}, region={region}: {e}")
            return tuple()
    
    @classmethod
    def fetch_providers(cls, tmdb_id: int, region: str = DEFAULT_REGION) -> list[dict[str, Any]]:
        """Fetch watch providers for a movie. Returns list of {name, logo_url, link}."""
        cached_tuple = cls._fetch_providers_sync(tmdb_id, region)
        return [dict(provider) for provider in cached_tuple] if cached_tuple else []
