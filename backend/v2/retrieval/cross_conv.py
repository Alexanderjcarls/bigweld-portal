"""Cross-conversation summary search via pgvector cosine similarity."""

from __future__ import annotations

from typing import Any


DEFAULT_TOP_K = 3
DEFAULT_COSINE_FLOOR = 0.75


async def nearest_summaries(
    pg_pool: Any,
    embedding: list[float],
    top_k: int = DEFAULT_TOP_K,
    cosine_floor: float = DEFAULT_COSINE_FLOOR,
) -> list[dict[str, Any]]:
    """Return top-K compacted summaries above cosine_floor."""

    threshold = 1.0 - cosine_floor
    query = """
        SELECT cs.id, cs.conv_id, cs.summary, c.title AS conv_title,
               1 - (cs.embedding <=> $1::vector) AS score
        FROM bigweld_v2.compacted_summaries cs
        JOIN bigweld_v2.conversations c ON c.id = cs.conv_id
        WHERE cs.embedding IS NOT NULL
          AND (cs.embedding <=> $1::vector) <= $2
        ORDER BY cs.embedding <=> $1::vector ASC
        LIMIT $3
    """
    async with pg_pool.acquire() as conn:
        rows = await conn.fetch(query, _vector_literal(embedding), threshold, top_k)
    return [dict(row) for row in rows]


def _vector_literal(embedding: list[float]) -> str:
    return "[" + ",".join(str(float(value)) for value in embedding) + "]"
