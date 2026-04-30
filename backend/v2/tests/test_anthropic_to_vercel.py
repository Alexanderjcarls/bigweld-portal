import pytest

from backend.v2.streaming.anthropic_to_vercel import (
    AnthropicToVercelTranslator,
    _map_stop_reason,
    stream_to_sse,
)


def test_message_start_emits_start_and_start_step():
    t = AnthropicToVercelTranslator(step_idx=0)
    parts = t.translate({"type": "message_start", "message": {"id": "msg_abc"}})
    assert parts == [
        {"type": "start", "messageId": "msg_abc"},
        {"type": "start-step"},
    ]


def test_text_block_lifecycle():
    t = AnthropicToVercelTranslator(step_idx=0)
    assert t.translate(
        {"type": "content_block_start", "index": 0, "content_block": {"type": "text"}}
    ) == [
        {"type": "text-start", "id": "0-0"},
    ]
    assert t.translate(
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": "hello "},
        }
    ) == [
        {"type": "text-delta", "id": "0-0", "delta": "hello "},
    ]
    assert t.translate(
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": "world"},
        }
    ) == [
        {"type": "text-delta", "id": "0-0", "delta": "world"},
    ]
    assert t.translate({"type": "content_block_stop", "index": 0}) == [
        {"type": "text-end", "id": "0-0"},
    ]


def test_tool_use_partial_json_accumulation():
    t = AnthropicToVercelTranslator(step_idx=0)
    t.translate(
        {
            "type": "content_block_start",
            "index": 1,
            "content_block": {
                "type": "tool_use",
                "id": "toolu_xyz",
                "name": "get_node",
            },
        }
    )
    t.translate(
        {
            "type": "content_block_delta",
            "index": 1,
            "delta": {"type": "input_json_delta", "partial_json": '{"sl'},
        }
    )
    t.translate(
        {
            "type": "content_block_delta",
            "index": 1,
            "delta": {"type": "input_json_delta", "partial_json": 'ug": "case-creation"}'},
        }
    )
    final = t.translate({"type": "content_block_stop", "index": 1})
    assert final == [
        {
            "type": "tool-input-available",
            "toolCallId": "toolu_xyz",
            "toolName": "get_node",
            "input": {"slug": "case-creation"},
        }
    ]


def test_thinking_block_signature_persisted_not_forwarded():
    t = AnthropicToVercelTranslator(step_idx=0)
    t.translate(
        {
            "type": "content_block_start",
            "index": 0,
            "content_block": {"type": "thinking"},
        }
    )
    forwarded = t.translate(
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "signature_delta", "signature": "sig_abc"},
        }
    )
    assert forwarded == []  # never sent to Vercel
    assert t.persisted_signatures[0] == "sig_abc"


def test_message_stop_emits_finish_with_usage():
    t = AnthropicToVercelTranslator(step_idx=0)
    t.translate(
        {
            "type": "message_delta",
            "delta": {"stop_reason": "end_turn"},
            "usage": {"input_tokens": 100, "output_tokens": 50},
        }
    )
    parts = t.translate({"type": "message_stop"})
    assert {"type": "finish-step"} in parts
    assert {"type": "finish"} in parts
    metadata = next(p for p in parts if p["type"] == "message-metadata")
    assert metadata["metadata"]["usage"] == {"input_tokens": 100, "output_tokens": 50}
    assert metadata["metadata"]["finishReason"] == "stop"


@pytest.mark.parametrize(
    ("anthropic", "vercel"),
    [
        ("end_turn", "stop"),
        ("tool_use", "tool-calls"),
        ("max_tokens", "length"),
        ("stop_sequence", "stop"),
        (None, "unknown"),
    ],
)
def test_map_stop_reason(anthropic, vercel):
    assert _map_stop_reason(anthropic) == vercel


def test_ping_and_unknown_return_empty():
    t = AnthropicToVercelTranslator()
    assert t.translate({"type": "ping"}) == []
    assert t.translate({"type": "weird_future_event"}) == []


def test_error_event_passthrough():
    t = AnthropicToVercelTranslator()
    parts = t.translate({"type": "error", "error": {"message": "overloaded"}})
    assert parts == [{"type": "error", "errorText": "overloaded"}]


@pytest.mark.asyncio
async def test_stream_to_sse_emits_done_terminator():
    async def fake_events():
        yield {"type": "message_start", "message": {"id": "m"}}
        yield {"type": "message_stop"}

    t = AnthropicToVercelTranslator()
    chunks = []
    async for chunk in stream_to_sse(fake_events(), t):
        chunks.append(chunk)

    full = b"".join(chunks)
    assert full.endswith(b"data: [DONE]\n\n")
    assert b'"type": "start"' in full
    assert b'"type": "finish"' in full
