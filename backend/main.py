"""Bigweld DA Portal — FastAPI entrypoint.

This file scaffolds the app surface. Subsequent phases wire in:
- Phase 5: API routers (conversations, render, output, budget, summarize)
- Phase 5.4: lifespan startup sweep for stale conversation summaries
- Phase 12: Prometheus /metrics endpoint + structlog
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    """App lifespan — startup/shutdown hooks land here in later phases."""
    yield


app = FastAPI(title="Bigweld DA Portal", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
