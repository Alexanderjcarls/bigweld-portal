"""Conversation DAO helpers for Bigweld DA v2."""

import uuid

import asyncpg


async def get_or_create_conversation(pg_pool: asyncpg.Pool, conv_id: uuid.UUID) -> dict:
    async with pg_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, title, started_at, last_active_at "
            "FROM bigweld_v2.conversations WHERE id = $1",
            conv_id,
        )
        if row is None:
            row = await conn.fetchrow(
                "INSERT INTO bigweld_v2.conversations (id) VALUES ($1) "
                "RETURNING id, title, started_at, last_active_at",
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
            "SELECT id, title, started_at, last_active_at FROM bigweld_v2.conversations "
            "WHERE ($1 OR title IS NOT NULL) "
            "ORDER BY last_active_at DESC",
            archived,
        )
    return [dict(row) for row in rows]
