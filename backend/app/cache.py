import time

CACHE_TTL_SECONDS = 3600

_cache: dict[str, tuple[float, list[dict]]] = {}


def normalize_query(query: str) -> str:
    return query.strip().lower()


def get(query: str) -> list[dict] | None:
    key = normalize_query(query)
    entry = _cache.get(key)
    if entry is None:
        return None

    expires_at, results = entry
    if time.monotonic() > expires_at:
        del _cache[key]
        return None

    return results


def store(query: str, results: list[dict]) -> None:
    key = normalize_query(query)
    _cache[key] = (time.monotonic() + CACHE_TTL_SECONDS, results)
