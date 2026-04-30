"""Message DAO helpers for Bigweld DA v2."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

import asyncpg


async def persist_anthropic_message(
    conn: asyncpg.Connection,
    conversation_id: UUID,
    role: str,
    content: list[dict[str, Any]],
    *,
    turn_idx: int,
    token_count: int = 0,
    finish_reason: str | None = None,
    usage: dict | None = None,
) -> UUID:
    """
    Persist a single message turn (user or assistant) as Anthropic JSON shape.
    `content` is the full content-block list from Anthropic (text, tool_use,
    tool_result, thinking with signatures intact).
    """
    raw = {"role": role, "content": content}
    row = await conn.fetchrow(
        """
        INSERT INTO bigweld_v2.messages
            (conversation_id, role, raw_message, turn_idx, token_count, finish_reason, usage)
        VALUES ($1, $2, $3::jsonb, $4, $5, $6, $7::jsonb)
        RETURNING id
        """,
        conversation_id,
        role,
        json.dumps(raw),
        turn_idx,
        token_count,
        finish_reason,
        json.dumps(usage) if usage is not None else None,
    )
    return row["id"]


async def load_anthropic_messages(
    conn: asyncpg.Connection,
    conversation_id: UUID,
) -> list[dict[str, Any]]:
    """
    Load conversation history as a list of Anthropic message dicts ordered by turn_idx.
    Returns [] if no history.
    """
    rows = await conn.fetch(
        """
        SELECT raw_message FROM bigweld_v2.messages
        WHERE conversation_id = $1
        ORDER BY turn_idx ASC
        """,
        conversation_id,
    )
    return [_decode_jsonb(r["raw_message"]) for r in rows]


async def total_token_count(
    conn: asyncpg.Connection,
    conversation_id: UUID,
) -> int:
    """
    Anthropic message_delta.usage is cumulative within a single turn. Take MAX
    across messages -- the most-recent assistant message's usage already includes
    all prior context.
    """
    row = await conn.fetchrow(
        """
        SELECT COALESCE(MAX(token_count), 0) AS total
        FROM bigweld_v2.messages
        WHERE conversation_id = $1
        """,
        conversation_id,
    )
    return row["total"]


def _decode_jsonb(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        return json.loads(value)
    return value
