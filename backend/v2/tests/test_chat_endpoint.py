import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

from backend.v2.agent.bigweld_agent import BigweldDeps
from backend.v2.api import chat as chat_api
from backend.v2.main import app


@pytest.mark.asyncio(loop_scope="session")
async def test_chat_endpoint_returns_sse(pg_pool, monkeypatch):
    conv_id = uuid.uuid4()
    async with pg_pool.acquire() as conn:
        await conn.execute("DELETE FROM bigweld_v2.conversations WHERE id = $1", conv_id)
        await conn.execute(
            "INSERT INTO bigweld_v2.conversations (id) VALUES ($1)",
            conv_id,
        )

    fake_agent = Agent(TestModel(custom_output_text="hello back"), deps_type=BigweldDeps)
    monkeypatch.setattr(chat_api, "get_pool", lambda: pg_pool)
    monkeypatch.setattr(chat_api, "_agent", fake_agent)

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            async with client.stream(
                "POST",
                "/chat",
                json={
                    "conv_id": str(conv_id),
                    "user_msg": "hello",
                },
            ) as response:
                assert response.status_code == 200
                assert "text/event-stream" in response.headers["content-type"]
                chunks = []
                async for chunk in response.aiter_text():
                    chunks.append(chunk)

        assert any("data:" in c for c in chunks)

        async with pg_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT role, content, raw_message FROM bigweld_v2.messages "
                "WHERE conv_id = $1 ORDER BY turn_idx",
                conv_id,
            )

        assert [row["role"] for row in rows] == ["user", "assistant"]
        assert "hello" in rows[0]["content"]
        assert "hello back" in rows[1]["content"]
    finally:
        async with pg_pool.acquire() as conn:
            await conn.execute("DELETE FROM bigweld_v2.conversations WHERE id = $1", conv_id)
