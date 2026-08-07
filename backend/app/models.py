from pydantic import BaseModel


class RecommendRequest(BaseModel):
    query: str


class MovieBase(BaseModel):
    tmdb_id: int
    title: str
    poster_path: str | None
    year: int | None
    vote_average: float | None
    genres: list[str]


class MovieRecommendation(MovieBase):
    reason: str


class RecommendResponse(BaseModel):
    results: list[MovieRecommendation]


class PopularMovie(MovieBase):
    pass


class PopularResponse(BaseModel):
    results: list[PopularMovie]
