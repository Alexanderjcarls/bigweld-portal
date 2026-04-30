"""Context usage stats endpoint for Bigweld DA v2."""

import uuid

import asyncpg
from fastapi import APIRouter, HTTPException

from backend.v2.db.connection import get_pool
from backend.v2.db.conversations import ConversationNotFound, get_conversation
from backend.v2.db.messages import total_token_count


CONTEXT_BUDGET = 1_000_000

router = APIRouter(prefix="/api", tags=["context-stats"])


async def get_context_stats(conn: asyncpg.Connection, conversation_id: uuid.UUID):
    used = await total_token_count(conn, conversation_id)
    pct = round((used / CONTEXT_BUDGET) * 100, 2) if CONTEXT_BUDGET else 0.0
    return {
        "tokens_used": used,
        "token_limit": CONTEXT_BUDGET,
        "percent_used": pct,
        "token_count": used,
        "context_budget": CONTEXT_BUDGET,
        "percentage": pct,
    }


@router.get("/context-stats")
async def get_context_stats_endpoint(conv_id: uuid.UUID):
    pool = get_pool()
    try:
        await get_conversation(pool, conv_id)
    except ConversationNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    async with pool.acquire() as conn:
        stats = await get_context_stats(conn, conv_id)
    return {"conv_id": str(conv_id), **stats}
