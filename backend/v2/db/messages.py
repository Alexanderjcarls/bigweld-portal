"""Message DAO helpers for Bigweld DA v2."""

import uuid

import asyncpg

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
