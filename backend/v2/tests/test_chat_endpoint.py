import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from backend.v2.api import chat as chat_api
from backend.v2.main import app
from backend.v2.streaming.anthropic_to_vercel import VERCEL_HEADER


def _decode_raw(value):
    return json.loads(value) if isinstance(value, str) else value


def _decode_sse_parts(body: str) -> list[dict]:
    parts = []
    for line in body.splitlines():
        if not line.startswith("data: ") or line == "data: [DONE]":
            continue
        parts.append(json.loads(line.removeprefix("data: ")))
    return parts


@pytest.mark.asyncio(loop_scope="session")
async def test_chat_endpoint_streams_vercel_sse_and_persists_turns(pg_pool, monkeypatch):
    conv_id = uuid.uuid4()
    async with pg_pool.acquire() as conn:
        await conn.execute("DELETE FROM bigweld_v2.conversations WHERE id = $1", conv_id)
        await conn.execute(
            """
            INSERT INTO bigweld_v2.conversations (id, last_active_at)
            VALUES ($1, '2020-01-01T00:00:00Z')
            """,
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
            last_active_at = await conn.fetchval(
                "SELECT last_active_at FROM bigweld_v2.conversations WHERE id = $1",
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
        assert last_active_at.isoformat() > "2020-01-01T00:00:00+00:00"
    finally:
        app.dependency_overrides.pop(chat_api.get_pool, None)
        async with pg_pool.acquire() as conn:
            await conn.execute("DELETE FROM bigweld_v2.conversations WHERE id = $1", conv_id)


@pytest.mark.asyncio(loop_scope="session")
async def test_chat_endpoint_persists_multistep_tool_turns(pg_pool, monkeypatch):
    conv_id = uuid.uuid4()
    async with pg_pool.acquire() as conn:
        await conn.execute("DELETE FROM bigweld_v2.conversations WHERE id = $1", conv_id)
        await conn.execute(
            "INSERT INTO bigweld_v2.conversations (id) VALUES ($1)",
            conv_id,
        )

    async def fake_stream_agent_response(deps, user_text, prior_history):
        assert deps.conversation_id == str(conv_id)
        assert user_text == "find x"
        assert prior_history == []

        yield {"type": "message_start", "message": {"id": "msg_step_1", "role": "assistant"}}
        yield {
            "type": "content_block_start",
            "index": 0,
            "content_block": {"type": "text"},
        }
        yield {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": "I will check."},
        }
        yield {"type": "content_block_stop", "index": 0}
        yield {
            "type": "content_block_start",
            "index": 1,
            "content_block": {
                "type": "tool_use",
                "id": "toolu_1",
                "name": "entity_search",
            },
        }
        yield {
            "type": "content_block_delta",
            "index": 1,
            "delta": {"type": "input_json_delta", "partial_json": '{"query":"x"}'},
        }
        yield {"type": "content_block_stop", "index": 1}
        yield {
            "type": "message_delta",
            "delta": {"stop_reason": "tool_use"},
            "usage": {"input_tokens": 10, "output_tokens": 3},
        }
        yield {"type": "message_stop"}
        yield {"type": "message_start", "message": {"id": "msg_tool_1", "role": "user"}}
        yield {
            "type": "content_block_start",
            "index": 0,
            "content_block": {
                "type": "tool_result",
                "tool_use_id": "toolu_1",
                "content": [{"type": "text", "text": "result x"}],
            },
        }
        yield {"type": "content_block_stop", "index": 0}
        yield {"type": "message_stop"}
        yield {"type": "message_start", "message": {"id": "msg_step_2", "role": "assistant"}}
        yield {
            "type": "content_block_start",
            "index": 0,
            "content_block": {"type": "text"},
        }
        yield {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": "Found x."},
        }
        yield {"type": "content_block_stop", "index": 0}
        yield {
            "type": "message_delta",
            "delta": {"stop_reason": "end_turn"},
            "usage": {"input_tokens": 20, "output_tokens": 4},
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
                            "parts": [{"type": "text", "text": "find x"}],
                        }
                    ],
                    "conv_id": str(conv_id),
                    "user_msg": "find x",
                },
            ) as response:
                assert response.status_code == 200
                body = "".join([chunk async for chunk in response.aiter_text()])

        parts = _decode_sse_parts(body)
        assert [part["type"] for part in parts].count("start") == 1
        assert [part["type"] for part in parts].count("start-step") == 2
        assert {"type": "tool-output-available", "toolCallId": "toolu_1", "output": [
            {"type": "text", "text": "result x"}
        ]} in parts
        assert [part["type"] for part in parts].count("finish") == 1

        async with pg_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT turn_idx, role, raw_message, token_count, finish_reason, usage
                FROM bigweld_v2.messages
                WHERE conversation_id = $1
                ORDER BY turn_idx
                """,
                conv_id,
            )

        assert [row["turn_idx"] for row in rows] == [0, 1, 2, 3]
        assert [row["role"] for row in rows] == ["user", "assistant", "user", "assistant"]
        assert _decode_raw(rows[1]["raw_message"]) == {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "I will check."},
                {
                    "type": "tool_use",
                    "id": "toolu_1",
                    "name": "entity_search",
                    "input": {"query": "x"},
                },
            ],
        }
        assert _decode_raw(rows[2]["raw_message"]) == {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "toolu_1",
                    "content": [{"type": "text", "text": "result x"}],
                }
            ],
        }
        assert _decode_raw(rows[3]["raw_message"]) == {
            "role": "assistant",
            "content": [{"type": "text", "text": "Found x."}],
        }
        assert rows[1]["token_count"] == 0
        assert rows[1]["finish_reason"] is None
        assert rows[3]["token_count"] == 24
        assert rows[3]["finish_reason"] == "end_turn"
        assert _decode_raw(rows[3]["usage"]) == {"input_tokens": 20, "output_tokens": 4}
    finally:
        app.dependency_overrides.pop(chat_api.get_pool, None)
        async with pg_pool.acquire() as conn:
            await conn.execute("DELETE FROM bigweld_v2.conversations WHERE id = $1", conv_id)
