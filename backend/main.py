"""Bigweld DA Portal — FastAPI entrypoint.

This file scaffolds the app surface. Subsequent phases wire in:
- Phase 5: API routers (conversations, render, output, budget, summarize)
- Phase 5.4: lifespan startup sweep for stale conversation summaries
- Phase 12: Prometheus /metrics endpoint + structlog
"""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.api.conversations import _store, router as conversations_router
from backend.api.render import router as render_router
from backend.api.summarize import router as summarize_router
from backend.core.summarizer import sweep_idle_conversations

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """App lifespan with non-blocking startup summary sweep."""

    async def _sweep() -> None:
        try:
            summarized = await sweep_idle_conversations(_store())
            if summarized:
                logger.info("startup sweep summarized %d stale conversations", summarized)
        except Exception:
            logger.exception("startup sweep failed")

    asyncio.create_task(_sweep())
    yield


app = FastAPI(title="Bigweld DA Portal", lifespan=lifespan)
app.include_router(conversations_router)
app.include_router(render_router)
app.include_router(summarize_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
