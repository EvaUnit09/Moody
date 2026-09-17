import logging

from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter

from app import cache
from app.db import search_similar
from app.models import RecommendRequest, RecommendResponse
from app.services.embeddings import embed_text
from app.services.rerank import rerank

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


@router.post("/recommend", response_model=RecommendResponse)
@limiter.limit("10/minute")
async def recommend(body: RecommendRequest, request: Request) -> RecommendResponse:
    query = body.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="query must not be empty")

    cached = cache.get(query)
    if cached is not None:
        # Cache hit logged at DEBUG level in cache.get()
        return RecommendResponse(results=cached)

    logger.debug(f"Cache miss for query={query!r}")
    
    embedding = await embed_text(query)
    candidates = await search_similar(embedding, limit=CANDIDATE_LIMIT)
    results = await rerank(query, candidates)

    cache.store(query, results)

    return RecommendResponse(results=results)
