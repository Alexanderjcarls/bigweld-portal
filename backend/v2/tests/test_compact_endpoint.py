import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from backend.v2.api import compact as compact_api
from backend.v2.main import app


async def _seed_messages(pg_pool, conv_id: uuid.UUID) -> None:
    async with pg_pool.acquire() as conn:
        await conn.execute("DELETE FROM bigweld_v2.conversations WHERE id = $1", conv_id)
        await conn.execute("INSERT INTO bigweld_v2.conversations (id) VALUES ($1)", conv_id)
        rows = [
            (0, "user", "We need a compact flow for case-reopen."),
            (1, "assistant", "Decision: propose first, persist only after user confirmation."),
        ]
        for turn_idx, role, content in rows:
            await conn.execute(
                "INSERT INTO bigweld_v2.messages "
                "(conv_id, turn_idx, role, content, raw_message, token_count) "
                "VALUES ($1, $2, $3, $4, $5::jsonb, $6)",
                conv_id,
                turn_idx,
                role,
                content,
                json.dumps({"role": role, "content": content}),
                8,
            )


async def _delete_conversation(pg_pool, conv_id: uuid.UUID) -> None:
    async with pg_pool.acquire() as conn:
        await conn.execute("DELETE FROM bigweld_v2.conversations WHERE id = $1", conv_id)


@pytest.mark.asyncio(loop_scope="session")
async def test_compact_endpoint_returns_proposed_summary_and_diff(pg_pool, monkeypatch):
    conv_id = uuid.uuid4()
    await _seed_messages(pg_pool, conv_id)

    async def fake_compact(messages):
        assert [message.turn_idx for message in messages] == [0, 1]
        return (
            "Topic: Compact flow.\n"
            "Key entities: case-reopen.\n"
            "Decisions made: persist only after confirmation.\n"
            "Open questions: none."
        )

    monkeypatch.setattr(compact_api, "get_pool", lambda: pg_pool)
    monkeypatch.setattr(compact_api, "compact_message_range", fake_compact)

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/compact",
                json={
                    "conv_id": str(conv_id),
                    "range_start_idx": 0,
                    "range_end_idx": 1,
                },
            )

        assert response.status_code == 200
        body = response.json()
        assert body["proposed_summary"].startswith("Topic: Compact flow.")
        assert "--- message_range" in body["diff_preview"]
        assert "+++ proposed_summary" in body["diff_preview"]
        assert "-[0] user: We need a compact flow for case-reopen." in body["diff_preview"]
        assert "+Topic: Compact flow." in body["diff_preview"]
    finally:
        await _delete_conversation(pg_pool, conv_id)


@pytest.mark.asyncio(loop_scope="session")
async def test_compact_confirm_embeds_and_persists_summary_without_modifying_messages(
    pg_pool,
    monkeypatch,
):
    conv_id = uuid.uuid4()
    await _seed_messages(pg_pool, conv_id)
    summary = (
        "Topic: Compact flow.\n"
        "Key entities: case-reopen.\n"
        "Decisions made: persist only after confirmation.\n"
        "Open questions: none."
    )

    async def fake_embed(text: str):
        assert text == summary
        return [0.125] * 2560

    monkeypatch.setattr(compact_api, "get_pool", lambda: pg_pool)
    monkeypatch.setattr(compact_api, "embed_query", fake_embed)

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/compact/confirm",
                json={
                    "conv_id": str(conv_id),
                    "range_start_idx": 0,
                    "range_end_idx": 1,
                    "summary": summary,
                },
            )

        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert isinstance(body["summary_id"], int)

        async with pg_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT conv_id, range_start_idx, range_end_idx, summary, "
                "embedding::text AS embedding "
                "FROM bigweld_v2.compacted_summaries WHERE id = $1",
                body["summary_id"],
            )
            message_count = await conn.fetchval(
                "SELECT COUNT(*) FROM bigweld_v2.messages WHERE conv_id = $1",
                conv_id,
            )

        assert row["conv_id"] == conv_id
        assert row["range_start_idx"] == 0
        assert row["range_end_idx"] == 1
        assert row["summary"] == summary
        assert row["embedding"].startswith("[0.125")
        assert message_count == 2
    finally:
        await _delete_conversation(pg_pool, conv_id)
