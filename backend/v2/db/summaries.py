"""DAO helpers for compacted conversation summaries."""

import uuid
from collections.abc import Sequence

import asyncpg


def _vector_literal(embedding: Sequence[float]) -> str:
    return "[" + ",".join(str(float(value)) for value in embedding) + "]"


async def insert_compacted_summary(
    pg_pool: asyncpg.Pool,
    conv_id: uuid.UUID,
    range_start_idx: int,
    range_end_idx: int,
    summary: str,
    embedding: Sequence[float],
) -> int:
    async with pg_pool.acquire() as conn:
        summary_id = await conn.fetchval(
            "INSERT INTO bigweld_v2.compacted_summaries "
            "(conv_id, range_start_idx, range_end_idx, summary, embedding) "
            "VALUES ($1, $2, $3, $4, $5::vector) "
            "RETURNING id",
            conv_id,
            range_start_idx,
            range_end_idx,
            summary,
            _vector_literal(embedding),
        )
    return int(summary_id)
