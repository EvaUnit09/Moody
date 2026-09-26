from pydantic import BaseModel, Field


class RecommendRequest(BaseModel):
    query: str = Field(min_length=1, max_length=200)
    region: str | None = None
    exclude_tmdb_ids: list[int] | None = Field(
        default=None,
        description="TMDB IDs to exclude from recommendations (e.g., previously passed/hidden titles)"
    )


class WatchProvider(BaseModel):
    name: str
    logo_url: str | None
    link: str


class MovieBase(BaseModel):
    tmdb_id: int
    title: str
    poster_path: str | None
    year: int | None
    vote_average: float | None
    genres: list[str]


class MovieRecommendation(MovieBase):
    reason: str
    providers: list[WatchProvider] = []


class RecommendResponse(BaseModel):
    results: list[MovieRecommendation]


class PopularMovie(MovieBase):
    pass


class PopularResponse(BaseModel):
    results: list[PopularMovie]
