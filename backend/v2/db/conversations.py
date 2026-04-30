"""Conversation DAO helpers for Bigweld DA v2."""

from __future__ import annotations

import uuid
from typing import Any

import asyncpg


class ConversationNotFound(ValueError):
    pass


_CONVERSATION_COLUMNS = "id, title, started_at, last_active_at, archived"


async def get_or_create_conversation(pg_pool: asyncpg.Pool, conv_id: uuid.UUID) -> dict:
    async with pg_pool.acquire() as conn:
        row = await conn.fetchrow(
            f"SELECT {_CONVERSATION_COLUMNS} FROM bigweld_v2.conversations WHERE id = $1",
            conv_id,
        )
        if row is None:
            row = await conn.fetchrow(
                "INSERT INTO bigweld_v2.conversations (id) VALUES ($1) "
                f"RETURNING {_CONVERSATION_COLUMNS}",
                conv_id,
            )
        return dict(row)


async def touch_conversation(pg_pool: asyncpg.Pool, conv_id: uuid.UUID) -> None:
    async with pg_pool.acquire() as conn:
        await conn.execute(
            "UPDATE bigweld_v2.conversations SET last_active_at = now() WHERE id = $1",
            conv_id,
        )


async def list_conversations(pg_pool: asyncpg.Pool, archived: bool = False) -> list[dict]:
    async with pg_pool.acquire() as conn:
        rows = await conn.fetch(
            f"SELECT {_CONVERSATION_COLUMNS} FROM bigweld_v2.conversations "
            "WHERE ($1::boolean OR archived = false) "
            "ORDER BY last_active_at DESC",
            archived,
        )
    return [dict(row) for row in rows]


async def get_conversation(pg_pool: asyncpg.Pool, conv_id: uuid.UUID) -> dict[str, Any]:
    async with pg_pool.acquire() as conn:
        row = await conn.fetchrow(
            f"SELECT {_CONVERSATION_COLUMNS} FROM bigweld_v2.conversations WHERE id = $1",
            conv_id,
        )
    if row is None:
        raise ConversationNotFound(f"conversation not found: {conv_id}")
    return dict(row)


async def update_conversation(
    pg_pool: asyncpg.Pool,
    conv_id: uuid.UUID,
    *,
    title: str | None = None,
    archived: bool | None = None,
) -> dict[str, Any]:
    updates: list[str] = []
    args: list[Any] = []

    if title is not None:
        args.append(title)
        updates.append(f"title = ${len(args)}")
    if archived is not None:
        args.append(archived)
        updates.append(f"archived = ${len(args)}")

    if not updates:
        return await get_conversation(pg_pool, conv_id)

    args.append(conv_id)
    async with pg_pool.acquire() as conn:
        row = await conn.fetchrow(
            f"""
            UPDATE bigweld_v2.conversations
            SET {", ".join(updates)}
            WHERE id = ${len(args)}
            RETURNING {_CONVERSATION_COLUMNS}
            """,
            *args,
        )

    if row is None:
        raise ConversationNotFound(f"conversation not found: {conv_id}")
    return dict(row)
