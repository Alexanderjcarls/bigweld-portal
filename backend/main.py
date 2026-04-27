"""Bigweld DA Portal — FastAPI entrypoint.

This file scaffolds the app surface. Subsequent phases wire in:
- Phase 5: API routers (conversations, render, output, budget, summarize)
- Phase 5.4: lifespan startup sweep for stale conversation summaries
- Phase 12: Prometheus /metrics endpoint + structlog
"""
import asyncio
import logging
import sys
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from backend.api.budget import router as budget_router
from backend.api.conversations import _store, router as conversations_router
from backend.api.output import router as output_router
from backend.api.render import router as render_router
from backend.api.summarize import router as summarize_router
from backend.core.summarizer import sweep_idle_conversations
from backend.metrics import router as metrics_router

logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.INFO)
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
)

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
app.include_router(budget_router)
app.include_router(conversations_router)
app.include_router(output_router)
app.include_router(render_router)
app.include_router(summarize_router)
app.include_router(metrics_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _DIST.exists():
    app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str) -> FileResponse:
        return FileResponse(_DIST / "index.html")
