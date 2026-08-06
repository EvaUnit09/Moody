from fastapi import APIRouter, HTTPException

from app import cache
from app.db import search_similar
from app.models import RecommendRequest, RecommendResponse
from app.services.embeddings import embed_text
from app.services.rerank import rerank

router = APIRouter()

CANDIDATE_LIMIT = 25


@router.post("/recommend", response_model=RecommendResponse)
async def recommend(request: RecommendRequest) -> RecommendResponse:
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="query must not be empty")

    cached = cache.get(query)
    if cached is not None:
        print(f"[cache] hit for query={query!r}")
        return RecommendResponse(results=cached)

    embedding = await embed_text(query)
    candidates = await search_similar(embedding, limit=CANDIDATE_LIMIT)
    results = await rerank(query, candidates)

    cache.store(query, results)

    return RecommendResponse(results=results)
