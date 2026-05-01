"""Streaming chat endpoint for Bigweld DA v2."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from backend.v2.agent.bigweld_agent import BigweldDeps, stream_agent_response
from backend.v2.db.connection import get_pool
from backend.v2.db.messages import load_anthropic_messages, persist_anthropic_message
from backend.v2.streaming.anthropic_to_vercel import (
    VERCEL_HEADER,
    AnthropicToVercelTranslator,
    stream_to_sse,
)


router = APIRouter(tags=["chat"])


@router.post("/chat")
async def chat(request: Request, pool: asyncpg.Pool = Depends(get_pool)):
    body = await request.json()

    # Frontend (frontend/src/v2/lib/api.ts buildChatRequestBody) sends:
    #   { id, messages, trigger, messageId, conv_id, user_msg }
    # Prefer the pre-extracted user_msg + conv_id fields from the frontend.
    conv_raw = body.get("conv_id") or body.get("conversationId")
    if not conv_raw:
        # Fallback for any legacy callers that nest under data.conversationId
        conv_raw = (body.get("data") or {}).get("conversationId")
    if not conv_raw:
        raise HTTPException(400, "conv_id required")
    try:
        conversation_id = UUID(conv_raw)
    except (TypeError, ValueError):
        raise HTTPException(400, f"conv_id is not a valid UUID: {conv_raw}")

    user_text = (body.get("user_msg") or "").strip()
    if not user_text:
        # Fallback: extract from the messages array
        messages = body.get("messages", [])
        if messages:
            last_user = messages[-1]
            user_text = _flatten_text_parts(
                last_user.get("parts", []) or last_user.get("content", [])
            )
    if not user_text:
        raise HTTPException(400, "empty user message")

    async with pool.acquire() as conn:
        # Upsert the conversation row — frontend generates conv_id client-side
        # and submits messages without a separate "create conversation" call.
        await conn.execute(
            """
            INSERT INTO bigweld_v2.conversations (id, title)
            VALUES ($1, $2)
            ON CONFLICT (id) DO NOTHING
            """,
            conversation_id,
            user_text[:80] if user_text else "untitled",
        )

        turn_idx = await conn.fetchval(
            """
            SELECT COALESCE(MAX(turn_idx) + 1, 0)
            FROM bigweld_v2.messages
            WHERE conversation_id = $1
            """,
            conversation_id,
        )

        await persist_anthropic_message(
            conn,
            conversation_id,
            "user",
            [{"type": "text", "text": user_text}],
            turn_idx=turn_idx,
        )

        prior_history = await load_anthropic_messages(conn, conversation_id)
        prior_history = prior_history[:-1] if prior_history else []

    deps = BigweldDeps(conversation_id=str(conversation_id), pg_pool=pool)
    translator = AnthropicToVercelTranslator(step_idx=turn_idx)
    accumulator = _AnthropicMessageAccumulator()

    async def event_stream() -> AsyncIterator[dict]:
        async for ev in stream_agent_response(deps, user_text, prior_history):
            _accumulate_into_blocks(ev, accumulator)
            yield ev

    async def sse_stream() -> AsyncIterator[bytes]:
        async for chunk in stream_to_sse(event_stream(), translator):
            yield chunk

        async with pool.acquire() as conn:
            for offset, message in enumerate(accumulator.completed_messages, start=1):
                await persist_anthropic_message(
                    conn,
                    conversation_id,
                    message.role,
                    message.content,
                    turn_idx=turn_idx + offset,
                    token_count=message.token_count,
                    finish_reason=message.finish_reason,
                    usage=message.usage,
                )

    return StreamingResponse(
        sse_stream(),
        media_type="text/event-stream",
        headers={VERCEL_HEADER[0]: VERCEL_HEADER[1]},
    )


def _flatten_text_parts(parts) -> str:
    """Vercel UI parts list or content list -> concatenated text."""
    if isinstance(parts, str):
        return parts
    out = []
    for part in parts:
        if isinstance(part, dict):
            if part.get("type") == "text":
                out.append(part.get("text", ""))
            elif "text" in part:
                out.append(part["text"])
    return "".join(out)


@dataclass
class _PersistableMessage:
    role: str
    content: list[dict]
    token_count: int = 0
    finish_reason: str | None = None
    usage: dict | None = None


@dataclass
class _AnthropicMessageAccumulator:
    """Mirror raw Anthropic stream events into replayable message rows."""

    current_role: str | None = None
    blocks: list[dict | None] = field(default_factory=list)
    usage: dict | None = None
    finish_reason: str | None = None
    completed_messages: list[_PersistableMessage] = field(default_factory=list)

    def handle(self, event: dict) -> None:
        et = event.get("type")
        if et == "message_start":
            self._start_message(event)
        elif et == "content_block_start":
            self._start_block(event)
        elif et == "content_block_delta":
            self._apply_delta(event)
        elif et == "content_block_stop":
            self._stop_block(event)
        elif et == "message_delta":
            self._apply_message_delta(event)
        elif et == "message_stop":
            self._stop_message()

    def _start_message(self, event: dict) -> None:
        self.current_role = event.get("message", {}).get("role") or "assistant"
        self.blocks = []
        self.usage = None
        self.finish_reason = None

    def _start_block(self, event: dict) -> None:
        if self.current_role not in {"assistant", "user"}:
            return
        idx = event["index"]
        cb = event["content_block"]
        while len(self.blocks) <= idx:
            self.blocks.append(None)
        self.blocks[idx] = dict(cb)
        block = self.blocks[idx]
        if cb.get("type") == "text":
            block["text"] = cb.get("text", "")
        elif cb.get("type") == "thinking":
            block["thinking"] = cb.get("thinking", "")
        elif cb.get("type") == "tool_use":
            block["_partial_input"] = ""
        elif cb.get("type") == "tool_result":
            block["content"] = cb.get("content", [])

    def _apply_delta(self, event: dict) -> None:
        idx = event["index"]
        delta = event["delta"]
        if idx >= len(self.blocks) or self.blocks[idx] is None:
            return
        block = self.blocks[idx]
        dt = delta.get("type")
        if dt == "text_delta":
            block["text"] = (block.get("text") or "") + delta["text"]
        elif dt == "thinking_delta":
            block["thinking"] = (block.get("thinking") or "") + delta["thinking"]
        elif dt == "input_json_delta":
            block["_partial_input"] = (block.get("_partial_input") or "") + delta["partial_json"]
        elif dt == "signature_delta":
            block["signature"] = delta["signature"]

    def _stop_block(self, event: dict) -> None:
        idx = event["index"]
        if idx >= len(self.blocks) or self.blocks[idx] is None:
            return
        block = self.blocks[idx]
        if block.get("type") == "tool_use" and "_partial_input" in block:
            try:
                block["input"] = json.loads(block["_partial_input"]) if block["_partial_input"] else {}
            except json.JSONDecodeError:
                block["input"] = {}
            del block["_partial_input"]

    def _apply_message_delta(self, event: dict) -> None:
        if event.get("usage"):
            self.usage = event["usage"]
        stop_reason = event.get("delta", {}).get("stop_reason")
        if stop_reason:
            self.finish_reason = stop_reason

    def _stop_message(self) -> None:
        if self.current_role not in {"assistant", "user"}:
            return
        content = [block for block in self.blocks if block is not None]
        if not content:
            self._clear_current()
            return

        usage = None
        finish_reason = None
        token_count = 0
        if self.current_role == "assistant" and self.finish_reason != "tool_use":
            usage = self.usage
            finish_reason = self.finish_reason
            token_count = (usage or {}).get("output_tokens", 0) + (usage or {}).get(
                "input_tokens",
                0,
            )

        self.completed_messages.append(
            _PersistableMessage(
                role=self.current_role,
                content=content,
                token_count=token_count,
                finish_reason=finish_reason,
                usage=usage,
            )
        )
        self._clear_current()

    def _clear_current(self) -> None:
        self.current_role = None
        self.blocks = []
        self.usage = None
        self.finish_reason = None


def _accumulate_into_blocks(event: dict, accumulator: _AnthropicMessageAccumulator):
    accumulator.handle(event)
