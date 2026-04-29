"""Context-window budget endpoint."""
import os

from fastapi import APIRouter, Depends

from backend.api.conversations import _store
from backend.auth import require_cf_access_email

router = APIRouter(prefix="/api", dependencies=[Depends(require_cf_access_email)])


@router.get("/budget")
async def get_budget(conv_id: str | None = None) -> dict:
    context_window = _context_window()
    pct = 0.0
    if conv_id:
        total = _store().get_max_usage_total(conv_id)
        if total > 0:
            pct = min(100.0, (total / context_window) * 100.0)
    return {"context_window_pct": pct, "context_window_total": context_window}


def _context_window() -> int:
    raw = os.environ.get("BIGWELD_PORTAL_CONTEXT_WINDOW", "1000000")
    try:
        value = int(raw)
    except ValueError:
        return 1000000
    return value if value > 0 else 1000000
