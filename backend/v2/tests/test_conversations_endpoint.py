import json
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.v2.api import conversations as conversations_api
from backend.v2.main import app


@pytest_asyncio.fixture(loop_scope="session")
async def seeded_conversations(pg_pool):
    conv_recent = uuid.uuid4()
    conv_older = uuid.uuid4()
    conv_archived = uuid.uuid4()
    ids = [conv_recent, conv_older, conv_archived]

    async with pg_pool.acquire() as conn:
        for conv_id in ids:
            await conn.execute("DELETE FROM bigweld_v2.conversations WHERE id = $1", conv_id)

        await conn.execute(
            """
            INSERT INTO bigweld_v2.conversations
                (id, title, started_at, last_active_at, archived)
            VALUES
                ($1, 'Recent compacted', '2026-04-30T08:00:00Z',
                    '2026-04-30T12:00:00Z', false),
                ($2, 'Older active', '2026-04-29T08:00:00Z',
                    '2026-04-29T12:00:00Z', false),
                ($3, 'Archived newest', '2026-04-28T08:00:00Z',
                    '2026-04-30T13:00:00Z', true)
            """,
            conv_recent,
            conv_older,
            conv_archived,
        )

        messages = [
            (conv_recent, 0, "user", "Scope the context stats endpoint.", 30),
            (conv_recent, 1, "assistant", "Compact can summarize these first turns.", 40),
            (conv_recent, 2, "user", "Continue after compact.", 12),
            (conv_older, 0, "user", "Older conversation message.", 5),
            (conv_archived, 0, "user", "Archived conversation message.", 7),
        ]
        for conv_id, turn_idx, role, content, token_count in messages:
            await conn.execute(
                """
                INSERT INTO bigweld_v2.messages
                    (conv_id, turn_idx, role, content, raw_message, token_count)
                VALUES ($1, $2, $3, $4, $5::jsonb, $6)
                """,
                conv_id,
                turn_idx,
                role,
                content,
                json.dumps({"role": role, "content": content}),
                token_count,
            )

        await conn.execute(
            """
            INSERT INTO bigweld_v2.compacted_summaries
                (conv_id, range_start_idx, range_end_idx, summary)
            VALUES ($1, 0, 1, 'Summary: context stats endpoint scoped and compacted.')
            """,
            conv_recent,
        )

    try:
        yield {
            "recent": conv_recent,
            "older": conv_older,
            "archived": conv_archived,
        }
    finally:
        async with pg_pool.acquire() as conn:
            for conv_id in ids:
                await conn.execute("DELETE FROM bigweld_v2.conversations WHERE id = $1", conv_id)


@pytest.mark.asyncio(loop_scope="session")
async def test_list_conversations_defaults_to_non_archived_sorted_by_last_active(
    pg_pool,
    monkeypatch,
    seeded_conversations,
):
    monkeypatch.setattr(conversations_api, "get_pool", lambda: pg_pool)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/conversations")

    assert response.status_code == 200
    seeded_ids = {str(value) for value in seeded_conversations.values()}
    conversations = [
        item for item in response.json()["conversations"] if item["id"] in seeded_ids
    ]

    assert [item["id"] for item in conversations] == [
        str(seeded_conversations["recent"]),
        str(seeded_conversations["older"]),
    ]
    assert all(item["archived"] is False for item in conversations)


@pytest.mark.asyncio(loop_scope="session")
async def test_list_conversations_can_include_archived(
    pg_pool,
    monkeypatch,
    seeded_conversations,
):
    monkeypatch.setattr(conversations_api, "get_pool", lambda: pg_pool)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/conversations?archived=true")

    assert response.status_code == 200
    seeded_ids = {str(value) for value in seeded_conversations.values()}
    conversations = [
        item for item in response.json()["conversations"] if item["id"] in seeded_ids
    ]

    assert [item["id"] for item in conversations] == [
        str(seeded_conversations["archived"]),
        str(seeded_conversations["recent"]),
        str(seeded_conversations["older"]),
    ]
    assert conversations[0]["archived"] is True


@pytest.mark.asyncio(loop_scope="session")
async def test_get_conversation_returns_messages_and_compacted_summaries(
    pg_pool,
    monkeypatch,
    seeded_conversations,
):
    monkeypatch.setattr(conversations_api, "get_pool", lambda: pg_pool)
    conv_id = seeded_conversations["recent"]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/conversations/{conv_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(conv_id)
    assert body["title"] == "Recent compacted"
    assert body["archived"] is False
    assert [message["turn_idx"] for message in body["messages"]] == [0, 1, 2]
    assert body["messages"][0]["raw_message"] == {
        "role": "user",
        "content": "Scope the context stats endpoint.",
    }
    assert len(body["compacted_summaries"]) == 1
    assert body["compacted_summaries"][0]["range_start_idx"] == 0
    assert body["compacted_summaries"][0]["range_end_idx"] == 1
    assert body["compacted_summaries"][0]["summary"].startswith("Summary:")


@pytest.mark.asyncio(loop_scope="session")
async def test_patch_conversation_renames_and_archives(
    pg_pool,
    monkeypatch,
    seeded_conversations,
):
    monkeypatch.setattr(conversations_api, "get_pool", lambda: pg_pool)
    conv_id = seeded_conversations["older"]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(
            f"/api/conversations/{conv_id}",
            json={"title": "Renamed active", "archived": True},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(conv_id)
    assert body["title"] == "Renamed active"
    assert body["archived"] is True

    async with pg_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT title, archived FROM bigweld_v2.conversations WHERE id = $1",
            conv_id,
        )
    assert row["title"] == "Renamed active"
    assert row["archived"] is True


@pytest.mark.asyncio(loop_scope="session")
async def test_get_missing_conversation_returns_404(pg_pool, monkeypatch):
    monkeypatch.setattr(conversations_api, "get_pool", lambda: pg_pool)
    missing = uuid.uuid4()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/conversations/{missing}")

    assert response.status_code == 404
