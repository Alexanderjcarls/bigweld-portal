"""Context usage stats endpoint for Bigweld DA v2."""

import uuid

from fastapi import APIRouter, HTTPException, Query

from backend.v2.db.connection import get_pool
from backend.v2.db.conversations import ConversationNotFound, get_conversation
from backend.v2.db.messages import total_token_count


DEFAULT_CONTEXT_BUDGET = 50_000

router = APIRouter(prefix="/api", tags=["context-stats"])


@router.get("/context-stats")
async def get_context_stats(
    conv_id: uuid.UUID,
    context_budget: int = Query(DEFAULT_CONTEXT_BUDGET, ge=1),
):
    try:
        await get_conversation(get_pool(), conv_id)
    except ConversationNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    token_count = await total_token_count(get_pool(), conv_id)
    percentage = min(100.0, round((token_count / context_budget) * 100.0, 2))
    return {
        "conv_id": str(conv_id),
        "token_count": token_count,
        "context_budget": context_budget,
        "percentage": percentage,
    }
