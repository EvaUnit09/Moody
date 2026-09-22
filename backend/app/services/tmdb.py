import os
import re
from typing import Any

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
    """Service for fetching TMDB watch provider data with async batching and caching."""
    
    LOGO_BASE_URL = "https://image.tmdb.org/t/p/original"
    DEFAULT_REGION = "US"
    MAX_PROVIDERS = 3
    MAX_CONCURRENT_REQUESTS = 10
    
    # Class-level cache dict for successful fetches
    _cache: dict[str, tuple[tuple[tuple[str, Any], ...], ...]] = {}
    
    # Allowlist for watch provider links (TMDB and JustWatch only)
    ALLOWED_LINK_PATTERN = re.compile(
        r'^https://(www\.)?'
        r'(themoviedb\.org|justwatch\.com)/'
    )
    
    @classmethod
    def _validate_region(cls, region: str | None) -> str:
        """Validate and normalize region code to uppercase 2-letter format."""
        if not region:
            return cls.DEFAULT_REGION
        
        normalized = region.strip().upper()
        if not re.match(r'^[A-Z]{2}$', normalized):
            raise ValueError(f"Invalid region code: {region!r}. Must be 2-letter ISO code.")
        
        return normalized
    
    @classmethod
    def _is_link_allowed(cls, link: str) -> bool:
        """Check if link matches allowlist (TMDB or JustWatch HTTPS only)."""
        return bool(cls.ALLOWED_LINK_PATTERN.match(link))
    
    @classmethod
    def _build_cache_key(cls, tmdb_id: int, region: str) -> str:
        """Build unambiguous cache key with | delimiter."""
        return f"{tmdb_id}|{region}"
    
    @classmethod
    def _get_cached_providers(cls, cache_key: str) -> list[dict[str, Any]] | None:
        """Get cached providers if available. None means not cached."""
        if cache_key in cls._cache:
            cached_tuple = cls._cache[cache_key]
            return [dict(provider) for provider in cached_tuple]
        return None
    
    @classmethod
    def _store_cached_providers(cls, cache_key: str, providers: list[dict[str, Any]]) -> None:
        """Store successful provider fetch in cache. Converts to tuple for hashability."""
        try:
            if providers:
                tuple_data = tuple(tuple(sorted(p.items())) for p in providers)
                cls._cache[cache_key] = tuple_data
        except Exception as e:
            # Cache write failure should not affect the result returned to caller
            print(f"[watch_providers] Cache write failed for {cache_key}: {e}")
    
    @classmethod
    async def fetch_providers(cls, tmdb_id: int, region: str | None = None) -> list[dict[str, Any]]:
        """
        Async fetch watch providers for a movie.
        Returns list of {name, logo_url, link}. Empty list on failure (not cached).
        """
        normalized_region = cls._validate_region(region)
        cache_key = cls._build_cache_key(tmdb_id, normalized_region)
        
        # Check cache
        cached = cls._get_cached_providers(cache_key)
        if cached is not None:
            return cached
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{BASE_URL}/movie/{tmdb_id}/watch/providers",
                    headers=HEADERS,
                )
                response.raise_for_status()
                data = response.json()
                
                region_data = data.get("results", {}).get(normalized_region, {})
                if not region_data:
                    return []
                
                # Prefer flatrate (subscription streaming), fallback to buy/rent
                providers = (
                    region_data.get("flatrate", [])
                    or region_data.get("buy", [])
                    or region_data.get("rent", [])
                )
                
                link = region_data.get("link", f"https://www.themoviedb.org/movie/{tmdb_id}/watch")
                
                # Validate link against allowlist
                if not cls._is_link_allowed(link):
                    print(f"[watch_providers] Rejected non-allowlisted link for tmdb_id={tmdb_id}: {link}")
                    return []
                
                result = []
                for provider in providers[:cls.MAX_PROVIDERS]:
                    provider_data = {
                        "name": provider.get("provider_name", ""),
                        "logo_url": (
                            f"{cls.LOGO_BASE_URL}{provider['logo_path']}"
                            if provider.get("logo_path")
                            else None
                        ),
                        "link": link,
                    }
                    result.append(provider_data)
                
                # Cache successful result (but not failures)
                # Cache write failure must not affect the result returned to caller
                if result:
                    cls._store_cached_providers(cache_key, result)
                
                return result
                
        except Exception as e:
            # Network/API errors - return empty list (don't cache failures)
            print(f"[watch_providers] Failed to fetch for tmdb_id={tmdb_id}, region={normalized_region}: {e}")
            return []
