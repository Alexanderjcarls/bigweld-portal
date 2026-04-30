from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.v2.api.chat import router as chat_router
from backend.v2.api.compact import router as compact_router
from backend.v2.config import settings
from backend.v2.db.connection import close_pool, init_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool(settings.PG_URL)
    yield
    await close_pool()


app = FastAPI(title="Bigweld DA v2", version="v2", lifespan=lifespan)
app.include_router(chat_router)
app.include_router(compact_router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "v2"}
