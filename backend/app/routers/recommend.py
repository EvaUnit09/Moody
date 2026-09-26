import asyncio
import logging

from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter

from app import cache
from app.db import search_similar
from app.models import RecommendRequest, RecommendResponse, WatchProvider
from app.services.embeddings import embed_text
from app.services.query_intent import expand_query
from app.services.rerank import rerank
from app.services.tmdb import WatchProviderService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_rate_limit_key(request: Request) -> str:
    """Extract rate limit key from request.
    
    For Railway deployments behind a proxy, attempts to use X-Forwarded-For header.
    
    LIMITATION: When using in-memory storage with multiple Railway replicas:
    - Each replica maintains its own rate limit state
    - Effective limit is N×10/min where N = number of replicas
    - Clients may be load-balanced across replicas, making the limit less predictable
    
    For production with strict rate limits, consider:
    - Single replica (prevents shared state issues)
    - Shared store like Redis (requires adding redis to stack)
    - Documenting the multiplied limit in API docs
    """
    # Check X-Forwarded-For header for Railway proxy
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Use the first (client) IP from the chain
        return forwarded_for.split(",")[0].strip()
    
    # Fallback to direct connection (local dev, direct access)
    return request.client.host if request.client else "unknown"


# Create rate limiter instance
# 10 requests per minute per IP for /recommend endpoint
# NOTE: Uses in-memory storage. With multiple Railway replicas, effective limit
# is multiplied (N replicas ≈ N×10/min). See get_rate_limit_key docstring.
limiter = Limiter(key_func=get_rate_limit_key)

CANDIDATE_LIMIT = 40


async def _enrich_with_providers(
    results: list[dict], 
    region: str,
    semaphore: asyncio.Semaphore
) -> list[dict]:
    """Enrich results with watch providers using async batch fetch with concurrency control."""
    
    async def fetch_for_movie(result: dict) -> dict:
        async with semaphore:
            providers_data = await WatchProviderService.fetch_providers(result["tmdb_id"], region)
            providers = [WatchProvider(**p) for p in providers_data]
            return {**result, "providers": providers}
    
    # Batch fetch all providers concurrently (with semaphore limiting concurrency)
    enriched_results = await asyncio.gather(
        *[fetch_for_movie(result) for result in results],
        return_exceptions=False
    )
    
    return enriched_results


@router.post("/recommend", response_model=RecommendResponse)
@limiter.limit("10/minute")
async def recommend(body: RecommendRequest, request: Request) -> RecommendResponse:
    query = body.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="query must not be empty")

    # Validate and normalize region
    try:
        region = WatchProviderService._validate_region(body.region)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    
    # Build cache key including exclude list
    exclude_ids = body.exclude_tmdb_ids or []
    cache_key = cache.build_cache_key(f"{query}:{region}", exclude_ids if exclude_ids else None)
    
    cached = cache.get(cache_key)
    if cached is not None:
        # Cache hit logged at DEBUG level in cache.get()
        return RecommendResponse(results=cached)

    logger.debug(f"Cache miss for query={query!r}")
    
    search_query = await expand_query(query)
    embedding = await embed_text(search_query)
    candidates = await search_similar(embedding, limit=CANDIDATE_LIMIT)
    
    # Filter out excluded tmdb_ids before reranking
    if exclude_ids:
        exclude_set = set(exclude_ids)
        candidates = [c for c in candidates if c["tmdb_id"] not in exclude_set]
        logger.debug(f"Filtered {len(exclude_ids)} excluded IDs, {len(candidates)} candidates remain")
    
    results = await rerank(query, candidates)
    
    # Enrich results with watch providers (async batch with concurrency control)
    semaphore = asyncio.Semaphore(WatchProviderService.MAX_CONCURRENT_REQUESTS)
    enriched_results = await _enrich_with_providers(results, region, semaphore)

    # Store with appropriate TTL (popular moods get longer cache)
    is_popular = cache._is_popular_mood(query)
    cache.store(cache_key, enriched_results, is_popular=is_popular)

    return RecommendResponse(results=enriched_results)
