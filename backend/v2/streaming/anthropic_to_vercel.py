"""
Translates Anthropic streaming events to Vercel AI Data Stream Protocol v1.

Stateful per-turn -- instantiate one AnthropicToVercelTranslator per
ClaudeSDKClient turn, feed it events, get back Vercel parts.
"""

import json
from dataclasses import dataclass, field
from typing import AsyncIterator


VERCEL_HEADER = ("x-vercel-ai-ui-message-stream", "v1")


@dataclass
class _BlockState:
    block_type: str  # "text" | "tool_use" | "thinking"
    block_id: str  # deterministic part id e.g. f"{step}-{block_idx}"
    tool_call_id: str | None = None
    tool_name: str | None = None
    partial_json: str = ""


@dataclass
class AnthropicToVercelTranslator:
    step_idx: int = 0
    blocks: dict[int, _BlockState] = field(default_factory=dict)
    last_usage: dict | None = None
    last_stop_reason: str | None = None
    persisted_signatures: dict[int, str] = field(default_factory=dict)

    def translate(self, event: dict) -> list[dict]:
        """Returns zero or more Vercel parts for a single Anthropic event."""
        et = event.get("type")

        if et == "message_start":
            msg_id = event.get("message", {}).get("id", "msg_unknown")
            return [
                {"type": "start", "messageId": msg_id},
                {"type": "start-step"},
            ]

        if et == "content_block_start":
            idx = event["index"]
            cb = event["content_block"]
            block_id = f"{self.step_idx}-{idx}"
            cb_type = cb.get("type")
            if cb_type == "text":
                self.blocks[idx] = _BlockState(block_type="text", block_id=block_id)
                return [{"type": "text-start", "id": block_id}]
            if cb_type == "tool_use":
                self.blocks[idx] = _BlockState(
                    block_type="tool_use",
                    block_id=block_id,
                    tool_call_id=cb["id"],
                    tool_name=cb["name"],
                )
                return [
                    {
                        "type": "tool-input-start",
                        "toolCallId": cb["id"],
                        "toolName": cb["name"],
                    }
                ]
            if cb_type == "thinking":
                self.blocks[idx] = _BlockState(block_type="thinking", block_id=block_id)
                return [{"type": "reasoning-start", "id": block_id}]
            return []  # server_tool_use, web_search_tool_result -- not used yet

        if et == "content_block_delta":
            idx = event["index"]
            delta = event["delta"]
            dt = delta.get("type")
            block = self.blocks.get(idx)
            if block is None:
                return []
            if dt == "text_delta":
                return [
                    {
                        "type": "text-delta",
                        "id": block.block_id,
                        "delta": delta["text"],
                    }
                ]
            if dt == "input_json_delta":
                block.partial_json += delta["partial_json"]
                return [
                    {
                        "type": "tool-input-delta",
                        "toolCallId": block.tool_call_id,
                        "inputTextDelta": delta["partial_json"],
                    }
                ]
            if dt == "thinking_delta":
                return [
                    {
                        "type": "reasoning-delta",
                        "id": block.block_id,
                        "delta": delta["thinking"],
                    }
                ]
            if dt == "signature_delta":
                # Persist server-side; do not forward to Vercel.
                self.persisted_signatures[idx] = delta["signature"]
                return []
            return []

        if et == "content_block_stop":
            idx = event["index"]
            block = self.blocks.get(idx)
            if block is None:
                return []
            if block.block_type == "text":
                return [{"type": "text-end", "id": block.block_id}]
            if block.block_type == "tool_use":
                try:
                    parsed = json.loads(block.partial_json) if block.partial_json else {}
                except json.JSONDecodeError:
                    parsed = {}
                return [
                    {
                        "type": "tool-input-available",
                        "toolCallId": block.tool_call_id,
                        "toolName": block.tool_name,
                        "input": parsed,
                    }
                ]
            if block.block_type == "thinking":
                return [{"type": "reasoning-end", "id": block.block_id}]
            return []

        if et == "message_delta":
            usage = event.get("usage")
            if usage:
                self.last_usage = usage
            stop = event.get("delta", {}).get("stop_reason")
            if stop:
                self.last_stop_reason = stop
            return []  # accumulate but don't emit until message_stop

        if et == "message_stop":
            finish_reason = _map_stop_reason(self.last_stop_reason)
            return [
                {"type": "finish-step"},
                {"type": "finish"},
                {
                    "type": "message-metadata",
                    "metadata": {
                        "usage": self.last_usage,
                        "finishReason": finish_reason,
                    },
                },
            ]

        if et == "ping":
            return []

        if et == "error":
            err = event.get("error", {})
            return [{"type": "error", "errorText": err.get("message", "unknown")}]

        return []


def _map_stop_reason(anthropic_stop: str | None) -> str:
    if anthropic_stop == "end_turn":
        return "stop"
    if anthropic_stop == "tool_use":
        return "tool-calls"
    if anthropic_stop == "max_tokens":
        return "length"
    if anthropic_stop == "stop_sequence":
        return "stop"
    return "unknown"


async def stream_to_sse(
    events: AsyncIterator[dict],
    translator: AnthropicToVercelTranslator,
) -> AsyncIterator[bytes]:
    """Convert an async iterator of Anthropic events to an SSE byte stream of Vercel parts."""
    async for ev in events:
        for part in translator.translate(ev):
            yield f"data: {json.dumps(part)}\n\n".encode()
    yield b"data: [DONE]\n\n"
