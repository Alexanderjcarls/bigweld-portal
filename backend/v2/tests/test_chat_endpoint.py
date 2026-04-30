import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from backend.v2.api import chat as chat_api
from backend.v2.main import app
from backend.v2.streaming.anthropic_to_vercel import VERCEL_HEADER


def _decode_raw(value):
    return json.loads(value) if isinstance(value, str) else value


@pytest.mark.asyncio(loop_scope="session")
async def test_chat_endpoint_streams_vercel_sse_and_persists_turns(pg_pool, monkeypatch):
    conv_id = uuid.uuid4()
    async with pg_pool.acquire() as conn:
        await conn.execute("DELETE FROM bigweld_v2.conversations WHERE id = $1", conv_id)
        await conn.execute(
            "INSERT INTO bigweld_v2.conversations (id) VALUES ($1)",
            conv_id,
        )

    async def fake_stream_agent_response(deps, user_text, prior_history):
        assert deps.conversation_id == str(conv_id)
        assert user_text == "hello"
        assert prior_history == []

        yield {"type": "message_start", "message": {"id": "msg_test"}}
        yield {
            "type": "content_block_start",
            "index": 0,
            "content_block": {"type": "text"},
        }
        yield {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": "hello back"},
        }
        yield {"type": "content_block_stop", "index": 0}
        yield {
            "type": "message_delta",
            "delta": {"stop_reason": "end_turn"},
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }
        yield {"type": "message_stop"}

    monkeypatch.setattr(chat_api, "stream_agent_response", fake_stream_agent_response)
    app.dependency_overrides[chat_api.get_pool] = lambda: pg_pool

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            async with client.stream(
                "POST",
                "/chat",
                json={
                    "messages": [
                        {
                            "id": "user-msg",
                            "role": "user",
                            "parts": [{"type": "text", "text": "hello"}],
                        }
                    ],
                    "data": {"conversationId": str(conv_id)},
                },
            ) as response:
                assert response.status_code == 200
                assert "text/event-stream" in response.headers["content-type"]
                assert response.headers[VERCEL_HEADER[0]] == VERCEL_HEADER[1]
                body = "".join([chunk async for chunk in response.aiter_text()])

        assert '"type": "text-delta"' in body
        assert '"delta": "hello back"' in body
        assert '"type": "finish"' in body
        assert body.endswith("data: [DONE]\n\n")

        async with pg_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT role, raw_message, token_count, finish_reason, usage
                FROM bigweld_v2.messages
                WHERE conversation_id = $1
                ORDER BY turn_idx
                """,
                conv_id,
            )

        assert [row["role"] for row in rows] == ["user", "assistant"]
        assert _decode_raw(rows[0]["raw_message"]) == {
            "role": "user",
            "content": [{"type": "text", "text": "hello"}],
        }
        assert _decode_raw(rows[1]["raw_message"]) == {
            "role": "assistant",
            "content": [{"type": "text", "text": "hello back"}],
        }
        assert rows[1]["token_count"] == 15
        assert rows[1]["finish_reason"] == "end_turn"
        assert _decode_raw(rows[1]["usage"]) == {"input_tokens": 10, "output_tokens": 5}
    finally:
        app.dependency_overrides.pop(chat_api.get_pool, None)
        async with pg_pool.acquire() as conn:
            await conn.execute("DELETE FROM bigweld_v2.conversations WHERE id = $1", conv_id)
