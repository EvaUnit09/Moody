from fastapi import APIRouter

from app.db import get_popular_movies
from app.models import PopularResponse

router = APIRouter()

POPULAR_LIMIT = 15


@router.get("/popular", response_model=PopularResponse)
async def popular() -> PopularResponse:
    movies = await get_popular_movies(POPULAR_LIMIT)
    return PopularResponse(results=movies)
