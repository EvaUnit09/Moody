import logging
import re
import time

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 3600
POPULAR_CACHE_TTL_SECONDS = 7200  # 2 hours for popular moods

# Popular mood keywords that get longer TTL
# These are common mood/scenario queries that tend to repeat
# Note: word-boundary matching prevents false positives (e.g., "sad" won't match "crusade")
POPULAR_MOOD_KEYWORDS = {
    "comedy",
    "romantic",
    "romance",
    "horror",
    "action",
    "thriller",
    "drama",
    "sci fi",  # normalized form (hyphens → spaces)
    "science fiction",
    "fantasy",
    "feel good",
    "sad",
    "happy",
    "scary",
    "funny",
    "heartwarming",
    "emotional",
    "lighthearted",
    "dark",
    "intense",
    "inspiring",
    "relaxing",
    "friday night",
    "date night",
    "family movie",
}

_cache: dict[str, tuple[float, list[dict]]] = {}
_cache_stats = {"hits": 0, "misses": 0}


def normalize_query(query: str) -> str:
    """Normalize query to maximize cache hits.
    
    - Convert to lowercase
    - Strip leading/trailing whitespace
    - Normalize hyphens to spaces (sci-fi → sci fi for collision)
    - Remove other punctuation
    - Collapse multiple spaces
    """
    # Lowercase and strip
    normalized = query.strip().lower()
    
    # Normalize hyphens to spaces first (sci-fi → sci fi)
    normalized = normalized.replace("-", " ")
    
    # Remove other punctuation
    normalized = re.sub(r"[^\w\s]", "", normalized)
    
    # Collapse multiple spaces
    normalized = re.sub(r"\s+", " ", normalized)
    
    return normalized


def _is_popular_mood(query: str) -> bool:
    """Check if query contains popular mood keywords with word boundaries.
    
    Uses word boundaries to avoid false positives like "sad" matching in "crusade".
    """
    normalized = normalize_query(query)
    
    for keyword in POPULAR_MOOD_KEYWORDS:
        # Use word boundaries for single-word keywords, exact phrase match for multi-word
        if " " in keyword:
            # Multi-word: exact substring match (already safe)
            if keyword in normalized:
                return True
        else:
            # Single-word: use word boundaries to prevent partial matches
            pattern = rf"\b{re.escape(keyword)}\b"
            if re.search(pattern, normalized):
                return True
    
    return False


def build_cache_key(query: str, exclude_tmdb_ids: list[int] | None = None) -> str:
    """Build cache key from query and optional exclude list.
    
    Normalizes query and includes sorted exclude_tmdb_ids to ensure
    cache hits only when both query and excludes match.
    """
    key = normalize_query(query)
    if exclude_tmdb_ids:
        # Sort to ensure [1,2,3] and [3,2,1] produce same key
        exclude_str = ",".join(str(id) for id in sorted(exclude_tmdb_ids))
        key = f"{key}:exclude:{exclude_str}"
    return key


def get(cache_key: str) -> list[dict] | None:
    """Get cached results by cache key.
    
    Args:
        cache_key: Pre-built cache key from build_cache_key() or normalize_query()
    """
    entry = _cache.get(cache_key)
    if entry is None:
        _cache_stats["misses"] += 1
        _log_cache_stats()
        return None

    expires_at, results = entry
    if time.monotonic() > expires_at:
        del _cache[cache_key]
        _cache_stats["misses"] += 1
        _log_cache_stats()
        return None

    _cache_stats["hits"] += 1
    _log_cache_stats()
    logger.debug(f"Cache hit for key={cache_key!r}")
    return results


def store(cache_key: str, results: list[dict], is_popular: bool = False) -> None:
    """Store results in cache by cache key.
    
    Args:
        cache_key: Pre-built cache key from build_cache_key() or normalize_query()
        results: Results to cache
        is_popular: Whether this is a popular mood query (longer TTL)
    """
    # Use longer TTL for popular mood queries
    ttl = POPULAR_CACHE_TTL_SECONDS if is_popular else CACHE_TTL_SECONDS
    
    _cache[cache_key] = (time.monotonic() + ttl, results)
    logger.debug(f"Cache store: key={cache_key!r} ttl={ttl}s popular={is_popular}")


def _log_cache_stats() -> None:
    """Log cache hit rate periodically at DEBUG level."""
    total = _cache_stats["hits"] + _cache_stats["misses"]
    
    # Log stats every 10 requests at DEBUG level (not INFO)
    if total > 0 and total % 10 == 0:
        hit_rate = (_cache_stats["hits"] / total) * 100
        logger.debug(
            f"Cache stats: hits={_cache_stats['hits']} "
            f"misses={_cache_stats['misses']} "
            f"hit_rate={hit_rate:.1f}% "
            f"size={len(_cache)}"
        )


def get_stats() -> dict:
    """Get current cache statistics."""
    total = _cache_stats["hits"] + _cache_stats["misses"]
    hit_rate = (_cache_stats["hits"] / total * 100) if total > 0 else 0.0
    
    return {
        "hits": _cache_stats["hits"],
        "misses": _cache_stats["misses"],
        "total_requests": total,
        "hit_rate_percent": round(hit_rate, 1),
        "cache_size": len(_cache),
    }
