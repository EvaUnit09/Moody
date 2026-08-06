from pydantic import BaseModel


class RecommendRequest(BaseModel):
    query: str


class MovieRecommendation(BaseModel):
    tmdb_id: int
    title: str
    poster_path: str | None
    reason: str


class RecommendResponse(BaseModel):
    results: list[MovieRecommendation]
