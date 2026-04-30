import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from backend.v2.api import context_stats as context_stats_api
from backend.v2.main import app


async def _seed_context_stats_conversation(pg_pool, conv_id: uuid.UUID) -> None:
    async with pg_pool.acquire() as conn:
        await conn.execute("DELETE FROM bigweld_v2.conversations WHERE id = $1", conv_id)
        await conn.execute(
            "INSERT INTO bigweld_v2.conversations (id, title) VALUES ($1, $2)",
            conv_id,
            "Token stats fixture",
        )
        rows = [
            (0, "user", "Pre-compact user turn.", 0),
            (1, "assistant", "Pre-compact assistant turn.", 3000),
            (2, "user", "Active user turn.", 0),
            (3, "assistant", "Active assistant turn.", 12000),
        ]
        for turn_idx, role, content, token_count in rows:
            await conn.execute(
                """
                INSERT INTO bigweld_v2.messages
                    (conversation_id, turn_idx, role, raw_message, token_count)
                VALUES ($1, $2, $3, $4::jsonb, $5)
                """,
                conv_id,
                turn_idx,
                role,
                json.dumps({"role": role, "content": [{"type": "text", "text": content}]}),
                token_count,
            )
        await conn.execute(
            """
            INSERT INTO bigweld_v2.compacted_summaries
                (conv_id, range_start_idx, range_end_idx, summary)
            VALUES ($1, 0, 1, 'Summary: first two turns.')
            """,
            conv_id,
        )


async def _delete_conversation(pg_pool, conv_id: uuid.UUID) -> None:
    async with pg_pool.acquire() as conn:
        await conn.execute("DELETE FROM bigweld_v2.conversations WHERE id = $1", conv_id)


@pytest.mark.asyncio(loop_scope="session")
async def test_context_stats_returns_one_million_budget_and_both_name_shapes(
    pg_pool,
    monkeypatch,
):
    conv_id = uuid.uuid4()
    await _seed_context_stats_conversation(pg_pool, conv_id)
    monkeypatch.setattr(context_stats_api, "get_pool", lambda: pg_pool)

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/api/context-stats?conv_id={conv_id}")

        assert response.status_code == 200
        assert response.json() == {
            "conv_id": str(conv_id),
            "tokens_used": 12000,
            "token_limit": 1_000_000,
            "percent_used": 1.2,
            "token_count": 12000,
            "context_budget": 1_000_000,
            "percentage": 1.2,
        }
    finally:
        await _delete_conversation(pg_pool, conv_id)
