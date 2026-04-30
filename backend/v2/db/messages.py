"""Message DAO helpers for Bigweld DA v2."""

from __future__ import annotations

import json
import uuid
from collections.abc import Mapping, Sequence
from typing import Any

import asyncpg
from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter,
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    ToolReturnPart,
    UserPromptPart,
)

from backend.v2.agent.compactor import MessageForCompaction


async def fetch_message_range(
    pg_pool: asyncpg.Pool,
    conv_id: uuid.UUID,
    range_start_idx: int,
    range_end_idx: int,
) -> list[MessageForCompaction]:
    async with pg_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT turn_idx, role, content FROM bigweld_v2.messages "
            "WHERE conv_id = $1 AND turn_idx >= $2 AND turn_idx <= $3 "
            "ORDER BY turn_idx ASC",
            conv_id,
            range_start_idx,
            range_end_idx,
        )
    return [
        MessageForCompaction(
            turn_idx=row["turn_idx"],
            role=row["role"],
            content=row["content"],
        )
        for row in rows
    ]


async def load_active_history(pg_pool: asyncpg.Pool, conv_id: uuid.UUID) -> list[dict[str, Any]]:
    """Return message rows in turn order, post-most-recent-Compact range."""

    async with pg_pool.acquire() as conn:
        latest_compact = await conn.fetchrow(
            "SELECT range_end_idx FROM bigweld_v2.compacted_summaries "
            "WHERE conv_id = $1 ORDER BY range_end_idx DESC LIMIT 1",
            conv_id,
        )
        cutoff = latest_compact["range_end_idx"] if latest_compact else -1
        rows = await conn.fetch(
            "SELECT turn_idx, role, content, raw_message FROM bigweld_v2.messages "
            "WHERE conv_id = $1 AND turn_idx > $2 ORDER BY turn_idx ASC",
            conv_id,
            cutoff,
        )

    history: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["raw_message"] = _decode_raw_message(item["raw_message"])
        history.append(item)
    return history


async def fetch_conversation_messages(
    pg_pool: asyncpg.Pool,
    conv_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """Return every persisted message row for portal hydration."""

    async with pg_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, turn_idx, role, content, raw_message, token_count, ts "
            "FROM bigweld_v2.messages WHERE conv_id = $1 ORDER BY turn_idx ASC",
            conv_id,
        )

    messages: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["raw_message"] = _decode_raw_message(item["raw_message"])
        messages.append(item)
    return messages


async def append_messages(
    pg_pool: asyncpg.Pool,
    conv_id: uuid.UUID,
    messages: Sequence[ModelMessage | Mapping[str, Any]],
) -> None:
    """Append Pydantic AI ModelMessage records to bigweld_v2.messages."""

    if not messages:
        return

    records = [_message_record(message) for message in messages]
    async with pg_pool.acquire() as conn:
        max_turn = await conn.fetchval(
            "SELECT COALESCE(MAX(turn_idx), -1) FROM bigweld_v2.messages WHERE conv_id = $1",
            conv_id,
        )
        for i, record in enumerate(records):
            await conn.execute(
                "INSERT INTO bigweld_v2.messages "
                "(conv_id, turn_idx, role, content, raw_message, token_count) "
                "VALUES ($1, $2, $3, $4, $5::jsonb, $6)",
                conv_id,
                max_turn + 1 + i,
                record["role"],
                record.get("content"),
                json.dumps(record["raw_message"]),
                record.get("token_count"),
            )


async def total_token_count(pg_pool: asyncpg.Pool, conv_id: uuid.UUID) -> int:
    """Return the size of the LATEST request context (not the cumulative sum).

    Pydantic AI's ModelResponse stores total_tokens (= prompt + completion) in
    `usage.total_tokens` for each LLM call. Summing across calls double-counts:
    the prompt of call N includes the entire history up through call N-1, so
    a sum of three N=15K calls overstates the "current context size" 3×.

    The right metric for the context bar is: how big was the LAST prompt sent
    to the model, plus the completion that came back? That's the size that
    will fill the context window for the NEXT turn.

    We approximate this with `MAX(token_count)` over the active range — for a
    well-formed conversation, the last assistant turn's row carries the
    largest total_tokens (most prompt context + its own response).
    """

    async with pg_pool.acquire() as conn:
        latest_compact = await conn.fetchrow(
            "SELECT range_end_idx FROM bigweld_v2.compacted_summaries "
            "WHERE conv_id = $1 ORDER BY range_end_idx DESC LIMIT 1",
            conv_id,
        )
        cutoff = latest_compact["range_end_idx"] if latest_compact else -1
        result = await conn.fetchval(
            "SELECT COALESCE(MAX(token_count), 0) FROM bigweld_v2.messages "
            "WHERE conv_id = $1 AND turn_idx > $2",
            conv_id,
            cutoff,
        )
    return result or 0


def model_messages_from_raw(raw_messages: Sequence[Any]) -> list[ModelMessage]:
    """Reconstruct Pydantic AI message history from JSONB raw_message values.

    Defensive: strip SystemPromptPart entries from persisted ModelRequests on
    the load path too. Pre-fix rows (persisted before the persistence-shape
    fix in commit 9b95816) may have system-prompt-tagged-as-user content
    that, on reconstruction, produces malformed message_history that the
    Pydantic AI validator rejects with "Processed history must end with a
    ModelRequest."

    The system-prompt is re-rendered fresh per turn by the dynamic
    @agent.system_prompt decorator, so dropping it from history is safe and
    avoids the duplicate-system case (DeepInfra Qwen rejects multi-system).
    """
    normalized = [_normalize_raw_message(raw) for raw in raw_messages]
    cleaned = [_strip_system_parts_from_raw(raw) for raw in normalized]
    # Also drop ModelRequests that had ONLY system parts — after stripping
    # they'd have empty parts list, which the validator also rejects.
    cleaned = [
        raw for raw in cleaned
        if not (
            isinstance(raw, Mapping)
            and raw.get("kind") == "request"
            and not raw.get("parts")
        )
    ]
    return ModelMessagesTypeAdapter.validate_python(cleaned)


def _decode_raw_message(raw_message: Any) -> Any:
    if isinstance(raw_message, str):
        return json.loads(raw_message)
    return raw_message


def _normalize_raw_message(raw_message: Any) -> Any:
    raw = _decode_raw_message(raw_message)
    if not isinstance(raw, Mapping):
        return raw
    if raw.get("kind") in {"request", "response"}:
        return dict(raw)

    role = raw.get("role")
    content = raw.get("content") or ""
    if role == "assistant":
        return {
            "kind": "response",
            "parts": [{"part_kind": "text", "content": content}],
        }
    if role == "system":
        return {
            "kind": "request",
            "parts": [{"part_kind": "system-prompt", "content": content}],
        }
    return {
        "kind": "request",
        "parts": [{"part_kind": "user-prompt", "content": content}],
    }


def _message_record(message: ModelMessage | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(message, Mapping):
        raw_message = _normalize_raw_message(message.get("raw_message", message))
        raw_message = _strip_system_parts_from_raw(raw_message)
        return {
            "role": message.get("role") or _role_from_raw(raw_message),
            "content": message.get("content") or _content_from_raw(raw_message),
            "raw_message": raw_message,
            "token_count": message.get("token_count"),
        }

    # Strip SystemPromptPart before persistence: dynamic @agent.system_prompt
    # decorators re-inject the system message per turn. Persisting it would
    # duplicate it into next turn's message_history → DeepInfra Qwen would
    # reject the resulting multi-system request with HTTP 400.
    persisted_message = _strip_system_parts(message)
    raw_message = ModelMessagesTypeAdapter.dump_python([persisted_message], mode="json")[0]
    return {
        "role": _message_role(persisted_message),
        "content": _message_content(persisted_message),
        "raw_message": raw_message,
        "token_count": _message_token_count(persisted_message),
    }


def _strip_system_parts(message: ModelMessage) -> ModelMessage:
    """Return a copy of `message` with SystemPromptPart entries removed.

    Used before persistence so the durable conversation log doesn't contain
    dynamic system prompts that get re-rendered on reconstruction.
    """
    import dataclasses

    if not isinstance(message, ModelRequest):
        return message
    filtered_parts = [p for p in message.parts if not isinstance(p, SystemPromptPart)]
    if len(filtered_parts) == len(message.parts):
        return message  # no system parts to strip; cheap fast-path
    return dataclasses.replace(message, parts=filtered_parts)


def _strip_system_parts_from_raw(raw_message: Any) -> Any:
    """Mirror of `_strip_system_parts` for raw JSON dicts loaded from DB."""
    if not isinstance(raw_message, Mapping):
        return raw_message
    if raw_message.get("kind") != "request":
        return raw_message
    parts = raw_message.get("parts")
    if not isinstance(parts, list):
        return raw_message
    filtered = [p for p in parts if not _raw_part_is_system(p)]
    if len(filtered) == len(parts):
        return raw_message
    cleaned = dict(raw_message)
    cleaned["parts"] = filtered
    return cleaned


def _raw_part_is_system(part: Any) -> bool:
    if not isinstance(part, Mapping):
        return False
    return part.get("part_kind") == "system-prompt"


def _message_role(message: ModelMessage) -> str:
    if isinstance(message, ModelResponse):
        return "assistant"

    if isinstance(message, ModelRequest):
        if any(isinstance(part, UserPromptPart) for part in message.parts):
            return "user"
        if any(isinstance(part, ToolReturnPart) for part in message.parts):
            return "tool"
        if any(isinstance(part, SystemPromptPart) for part in message.parts):
            return "system"

    return "unknown"


def _message_content(message: ModelMessage) -> str | None:
    if isinstance(message, ModelRequest):
        # Defense in depth: even if a SystemPromptPart sneaks past the strip
        # at _message_record (e.g. for legacy rows), don't include it in the
        # human-readable `content` column.
        return _join_content(
            _stringify_part_content(part.content)
            for part in message.parts
            if isinstance(part, (UserPromptPart, ToolReturnPart))
        )

    if isinstance(message, ModelResponse):
        return _join_content(
            part.content for part in message.parts if isinstance(part, TextPart)
        )

    return None


def _message_token_count(message: ModelMessage) -> int | None:
    if isinstance(message, ModelResponse):
        return message.usage.total_tokens
    return None


def _role_from_raw(raw_message: Any) -> str:
    if not isinstance(raw_message, Mapping):
        return "unknown"
    kind = raw_message.get("kind")
    if kind == "response":
        return "assistant"
    if kind != "request":
        return "unknown"

    part_kinds = {
        part.get("part_kind")
        for part in raw_message.get("parts", [])
        if isinstance(part, Mapping)
    }
    if "user-prompt" in part_kinds:
        return "user"
    if "tool-return" in part_kinds:
        return "tool"
    if "system-prompt" in part_kinds:
        return "system"
    return "unknown"


def _content_from_raw(raw_message: Any) -> str | None:
    if not isinstance(raw_message, Mapping):
        return None
    return _join_content(
        _stringify_part_content(part.get("content"))
        for part in raw_message.get("parts", [])
        if isinstance(part, Mapping) and "content" in part
    )


def _join_content(values: Any) -> str | None:
    parts = [value for value in values if value]
    return "\n".join(parts) if parts else None


def _stringify_part_content(content: Any) -> str | None:
    if content is None:
        return None
    if isinstance(content, str):
        return content
    return json.dumps(content)
