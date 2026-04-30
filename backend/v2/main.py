from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from backend.v2.api.artifacts import router as artifacts_router
from backend.v2.api.chat import router as chat_router
from backend.v2.api.compact import router as compact_router
from backend.v2.api.context_stats import router as context_stats_router
from backend.v2.api.conversations import router as conversations_router
from backend.v2.config import settings
from backend.v2.db.connection import close_pool, init_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool(settings.PG_URL)
    yield
    await close_pool()


app = FastAPI(title="Bigweld DA v2", version="v2", lifespan=lifespan)
app.include_router(artifacts_router)
app.include_router(chat_router)
app.include_router(compact_router)
app.include_router(context_stats_router)
app.include_router(conversations_router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "v2"}


# --- Static SPA serving ---------------------------------------------------
# Probes dist/<path> for real assets first (so /assets/*, /logos/*, /fonts/*,
# /favicon.svg, /icons.svg resolve to actual files); falls back to
# dist/v2/index.html for any unmatched path so the React Router SPA can
# handle client-side routes. Mirrors the v1 portal pattern from commit
# dc00069 (Bigweld Portal v1.1: FastAPI SPA fallback must probe dist/<path>
# for real files BEFORE falling through — otherwise /logos, /fonts,
# /favicon.svg are served as text/html and images break).
_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
_SPA_INDEX = _DIST / "v2" / "index.html"


@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    if not _DIST.exists() or not _SPA_INDEX.exists():
        raise HTTPException(status_code=404, detail="frontend bundle not built")

    # Probe dist/<path> for an actual file first.
    if full_path:
        candidate = (_DIST / full_path).resolve()
        if _DIST in candidate.parents and candidate.is_file():
            return FileResponse(candidate)

    # SPA fallback for client-side routes.
    return FileResponse(_SPA_INDEX)
