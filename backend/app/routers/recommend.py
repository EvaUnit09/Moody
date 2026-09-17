import logging

from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app import cache
from app.db import search_similar
from app.models import RecommendRequest, RecommendResponse
from app.services.embeddings import embed_text
from app.services.rerank import rerank

logger = logging.getLogger(__name__)

router = APIRouter()

# Create rate limiter instance
# 10 requests per minute per IP for /recommend endpoint
limiter = Limiter(key_func=get_remote_address)

CANDIDATE_LIMIT = 25


@router.post("/recommend", response_model=RecommendResponse)
@limiter.limit("10/minute")
async def recommend(body: RecommendRequest, request: Request) -> RecommendResponse:
    query = body.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="query must not be empty")

    cached = cache.get(query)
    if cached is not None:
        logger.info(f"Cache hit for query={query!r}")
        return RecommendResponse(results=cached)

    logger.debug(f"Cache miss for query={query!r}")
    
    embedding = await embed_text(query)
    candidates = await search_similar(embedding, limit=CANDIDATE_LIMIT)
    results = await rerank(query, candidates)

    cache.store(query, results)

    return RecommendResponse(results=results)
