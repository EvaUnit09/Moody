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


def get(query: str) -> list[dict] | None:
    key = normalize_query(query)
    entry = _cache.get(key)
    if entry is None:
        _cache_stats["misses"] += 1
        _log_cache_stats()
        return None

    expires_at, results = entry
    if time.monotonic() > expires_at:
        del _cache[key]
        _cache_stats["misses"] += 1
        _log_cache_stats()
        return None

    _cache_stats["hits"] += 1
    _log_cache_stats()
    logger.debug(f"Cache hit for query={query!r}")
    return results


def store(query: str, results: list[dict]) -> None:
    key = normalize_query(query)
    
    # Use longer TTL for popular mood queries
    ttl = POPULAR_CACHE_TTL_SECONDS if _is_popular_mood(query) else CACHE_TTL_SECONDS
    
    _cache[key] = (time.monotonic() + ttl, results)
    logger.debug(f"Cache store: query={query!r} (normalized={key!r}) ttl={ttl}s popular={_is_popular_mood(query)}")


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
