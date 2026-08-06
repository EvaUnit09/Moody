from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import close_pool, get_pool
from app.routers.recommend import router as recommend_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()
    yield
    await close_pool()


app = FastAPI(lifespan=lifespan)
app.include_router(recommend_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
