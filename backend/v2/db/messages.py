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


async def append_messages(
    pg_pool: asyncpg.Pool,
    conversation_id: UUID,
    messages: list[Any],
) -> None:
    """Append message-like dicts using the current Anthropic raw_message schema."""
    if not messages:
        return

    async with pg_pool.acquire() as conn:
        next_turn = await conn.fetchval(
            """
            SELECT COALESCE(MAX(turn_idx) + 1, 0)
            FROM bigweld_v2.messages
            WHERE conversation_id = $1
            """,
            conversation_id,
        )
        for offset, message in enumerate(messages):
            raw = _normalise_message(message)
            await persist_anthropic_message(
                conn,
                conversation_id,
                raw["role"],
                raw["content"],
                turn_idx=next_turn + offset,
                token_count=_message_token_count(message),
                finish_reason=_message_finish_reason(message),
                usage=_message_usage(message),
            )


async def fetch_conversation_messages(
    pg_pool: asyncpg.Pool,
    conversation_id: UUID,
) -> list[dict[str, Any]]:
    async with pg_pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, conversation_id, turn_idx, role, raw_message, token_count,
                   finish_reason, usage, created_at
            FROM bigweld_v2.messages
            WHERE conversation_id = $1
            ORDER BY turn_idx ASC
            """,
            conversation_id,
        )

    messages = []
    for row in rows:
        raw_message = _decode_jsonb(row["raw_message"])
        usage = _decode_jsonb(row["usage"]) if row["usage"] is not None else None
        messages.append(
            {
                "id": str(row["id"]),
                "conversation_id": str(row["conversation_id"]),
                "conv_id": str(row["conversation_id"]),
                "turn_idx": row["turn_idx"],
                "role": row["role"],
                "content": _message_text(raw_message),
                "raw_message": raw_message,
                "token_count": row["token_count"],
                "finish_reason": row["finish_reason"],
                "usage": usage,
                "created_at": row["created_at"],
                "ts": row["created_at"],
            }
        )
    return messages


async def fetch_message_range(
    pg_pool: asyncpg.Pool,
    conversation_id: UUID,
    range_start_idx: int,
    range_end_idx: int,
):
    from backend.v2.agent.compactor import MessageForCompaction

    async with pg_pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT turn_idx, role, raw_message
            FROM bigweld_v2.messages
            WHERE conversation_id = $1
              AND turn_idx BETWEEN $2 AND $3
            ORDER BY turn_idx ASC
            """,
            conversation_id,
            range_start_idx,
            range_end_idx,
        )

    return [
        MessageForCompaction(
            turn_idx=row["turn_idx"],
            role=row["role"],
            content=_message_text(_decode_jsonb(row["raw_message"])),
        )
        for row in rows
    ]


def _decode_jsonb(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        return json.loads(value)
    return value


def _normalise_message(message: Any) -> dict[str, Any]:
    if isinstance(message, dict):
        raw = message.get("raw_message")
        if raw is not None:
            decoded = _decode_jsonb(raw)
            return {
                "role": decoded.get("role", message.get("role", "user")),
                "content": _normalise_content(decoded.get("content", "")),
            }
        return {
            "role": message.get("role", "user"),
            "content": _normalise_content(message.get("content", "")),
        }

    role = getattr(message, "role", None) or "user"
    content = getattr(message, "content", "")
    return {"role": role, "content": _normalise_content(content)}


def _normalise_content(content: Any) -> list[dict[str, Any]]:
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    if isinstance(content, list):
        normalised: list[dict[str, Any]] = []
        for item in content:
            if isinstance(item, dict):
                normalised.append(dict(item))
            elif isinstance(item, str):
                normalised.append({"type": "text", "text": item})
        return normalised
    if isinstance(content, dict):
        return [dict(content)]
    return [{"type": "text", "text": str(content)}]


def _message_text(raw_message: dict[str, Any]) -> str:
    content = raw_message.get("content", "")
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return str(content) if content is not None else ""

    parts: list[str] = []
    for block in content:
        if isinstance(block, dict):
            if "text" in block:
                parts.append(str(block["text"]))
            elif block.get("type") == "thinking" and "thinking" in block:
                parts.append(str(block["thinking"]))
    return "".join(parts)


def _message_token_count(message: Any) -> int:
    if isinstance(message, dict):
        return int(message.get("token_count", 0) or 0)
    return int(getattr(message, "token_count", 0) or 0)


def _message_finish_reason(message: Any) -> str | None:
    if isinstance(message, dict):
        return message.get("finish_reason")
    return getattr(message, "finish_reason", None)


def _message_usage(message: Any) -> dict | None:
    usage = message.get("usage") if isinstance(message, dict) else getattr(message, "usage", None)
    return usage if isinstance(usage, dict) else None
