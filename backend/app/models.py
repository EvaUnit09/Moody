from pydantic import BaseModel


class RecommendRequest(BaseModel):
    query: str
    region: str | None = None


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
