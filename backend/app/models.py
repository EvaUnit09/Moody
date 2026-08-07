from pydantic import BaseModel


class RecommendRequest(BaseModel):
    query: str


class MovieRecommendation(BaseModel):
    tmdb_id: int
    title: str
    poster_path: str | None
    year: int | None
    vote_average: float | None
    reason: str


class RecommendResponse(BaseModel):
    results: list[MovieRecommendation]
