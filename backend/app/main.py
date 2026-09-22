import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.db import close_pool, get_pool
from app.routers.popular import router as popular_router
from app.routers.popular import warm_popular_cache
from app.routers.recommend import limiter
from app.routers.recommend import router as recommend_router
from app.services.observability import DatadogObservability

POPULAR_CACHE_REFRESH_SECONDS = 3300  # keep the cache warm ahead of its 3600s TTL


async def _refresh_popular_cache_periodically() -> None:
    while True:
        await asyncio.sleep(POPULAR_CACHE_REFRESH_SECONDS)
        await warm_popular_cache()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Datadog observability
    DatadogObservability.initialize()
    
    await get_pool()
    await warm_popular_cache()
    refresh_task = asyncio.create_task(_refresh_popular_cache_periodically())
    yield
    refresh_task.cancel()
    await close_pool()


app = FastAPI(lifespan=lifespan)

# Add rate limiter state to app
app.state.limiter = limiter

# Custom rate limit exceeded handler with friendly message
@app.exception_handler(RateLimitExceeded)
async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "message": "You've made too many requests. Please try again in a minute.",
        },
        headers={"Retry-After": "60"},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(recommend_router)
app.include_router(popular_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
