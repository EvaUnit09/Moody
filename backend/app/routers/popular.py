from fastapi import APIRouter

from app import cache
from app.db import get_popular_movies
from app.models import PopularResponse

router = APIRouter()

POPULAR_LIMIT = 15
POPULAR_CACHE_KEY = "__popular__"


async def warm_popular_cache() -> list[dict]:
    movies = await get_popular_movies(POPULAR_LIMIT)
    cache.store(POPULAR_CACHE_KEY, movies)
    return movies


@router.get("/popular", response_model=PopularResponse)
async def popular() -> PopularResponse:
    cached = cache.get(POPULAR_CACHE_KEY)
    if cached is not None:
        return PopularResponse(results=cached)

    movies = await warm_popular_cache()
    return PopularResponse(results=movies)
