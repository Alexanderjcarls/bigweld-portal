from math import sqrt
from uuid import UUID

import pytest

from backend.v2.retrieval.cross_conv import nearest_summaries


def _vector(first: float, second: float = 0.0) -> str:
    values = [0.0] * 2560
    values[0] = first
    values[1] = second
    return "[" + ",".join(str(v) for v in values) + "]"


@pytest.mark.asyncio(loop_scope="session")
async def test_nearest_summaries_returns_top_k_above_floor(pg_pool):
    conv_ids = [
        UUID("11111111-1111-4111-8111-111111111111"),
        UUID("22222222-2222-4222-8222-222222222222"),
        UUID("33333333-3333-4333-8333-333333333333"),
        UUID("44444444-4444-4444-8444-444444444444"),
    ]
    query_embedding = [0.0] * 2560
    query_embedding[0] = 1.0

    async with pg_pool.acquire() as conn:
        for conv_id in conv_ids:
            await conn.execute("DELETE FROM bigweld_v2.conversations WHERE id = $1", conv_id)

        try:
            for i, conv_id in enumerate(conv_ids):
                await conn.execute(
                    "INSERT INTO bigweld_v2.conversations (id, title) VALUES ($1, $2)",
                    conv_id,
                    f"Fixture conversation {i}",
                )

            rows = [
                (conv_ids[0], "Exact case-reopen summary", _vector(1.0)),
                (conv_ids[1], "Related entitlement summary", _vector(0.8, 0.6)),
                (conv_ids[2], "Below floor summary", _vector(0.74, sqrt(1 - 0.74**2))),
                (conv_ids[3], "Opposite direction summary", _vector(-1.0)),
            ]
            for idx, (conv_id, summary, embedding) in enumerate(rows):
                await conn.execute(
                    """
                    INSERT INTO bigweld_v2.compacted_summaries
                      (conv_id, range_start_idx, range_end_idx, summary, embedding)
                    VALUES ($1, $2, $3, $4, $5::vector)
                    """,
                    conv_id,
                    idx,
                    idx,
                    summary,
                    embedding,
                )

            results = await nearest_summaries(
                pg_pool,
                query_embedding,
                top_k=3,
                cosine_floor=0.75,
            )
        finally:
            for conv_id in conv_ids:
                await conn.execute("DELETE FROM bigweld_v2.conversations WHERE id = $1", conv_id)

    assert [r["summary"] for r in results] == [
        "Exact case-reopen summary",
        "Related entitlement summary",
    ]
    assert all(r["score"] >= 0.75 for r in results)
