import asyncio
import logging

from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter

from app import cache
from app.db import search_similar
from app.models import RecommendRequest, RecommendResponse, WatchProvider
from app.services.embeddings import embed_text
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

CANDIDATE_LIMIT = 25


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
        raise HTTPException(status_code=400, detail=str(e))
    
    cache_key = f"{query}:{region}"
    
    cached = cache.get(cache_key)
    if cached is not None:
        # Cache hit logged at DEBUG level in cache.get()
        return RecommendResponse(results=cached)

    logger.debug(f"Cache miss for query={query!r}")
    
    embedding = await embed_text(query)
    candidates = await search_similar(embedding, limit=CANDIDATE_LIMIT)
    results = await rerank(query, candidates)
    
    # Enrich results with watch providers (async batch with concurrency control)
    semaphore = asyncio.Semaphore(WatchProviderService.MAX_CONCURRENT_REQUESTS)
    enriched_results = await _enrich_with_providers(results, region, semaphore)

    cache.store(cache_key, enriched_results)

    return RecommendResponse(results=enriched_results)
