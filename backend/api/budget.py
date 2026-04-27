"""Stub budget endpoint for v1 context bars."""
from fastapi import APIRouter, Depends

from backend.auth import require_cf_access_email

router = APIRouter(prefix="/api", dependencies=[Depends(require_cf_access_email)])


@router.get("/budget")
async def get_budget():
    return {
        "conversation_context_pct": 0.0,
        "max_5h_pct": 0.0,
        "max_7d_pct": 0.0,
    }
