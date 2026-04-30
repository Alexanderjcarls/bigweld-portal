"""Streaming chat endpoint for Bigweld DA v2."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
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

    messages = body.get("messages", [])
    if not messages:
        raise HTTPException(400, "no messages")

    last_user = messages[-1]
    user_text = _flatten_text_parts(last_user.get("parts", []) or last_user.get("content", []))
    if not user_text:
        raise HTTPException(400, "empty user message")

    body_data = body.get("data", {})
    conversation_id = UUID(body_data["conversationId"]) if body_data.get("conversationId") else None
    if not conversation_id:
        raise HTTPException(400, "conversationId required")

    async with pool.acquire() as conn:
        turn_count = await conn.fetchval(
            "SELECT COUNT(*) FROM bigweld_v2.messages WHERE conversation_id = $1",
            conversation_id,
        )
        turn_idx = turn_count

        await persist_anthropic_message(
            conn,
            conversation_id,
            "user",
            [{"type": "text", "text": user_text}],
            turn_idx=turn_idx,
        )

        prior_history = await load_anthropic_messages(conn, conversation_id)
        prior_history = prior_history[:-1] if prior_history else []

    deps = BigweldDeps(conversation_id=str(conversation_id))
    translator = AnthropicToVercelTranslator(step_idx=turn_idx)

    assistant_blocks: list[dict | None] = []
    final_usage: dict | None = None
    final_finish: str | None = None

    async def event_stream() -> AsyncIterator[dict]:
        nonlocal assistant_blocks, final_usage, final_finish
        async for ev in stream_agent_response(deps, user_text, prior_history):
            _accumulate_into_blocks(ev, assistant_blocks, translator)
            yield ev
            if ev.get("type") == "message_delta":
                if ev.get("usage"):
                    final_usage = ev["usage"]
                if ev.get("delta", {}).get("stop_reason"):
                    final_finish = ev["delta"]["stop_reason"]

    async def sse_stream() -> AsyncIterator[bytes]:
        async for chunk in stream_to_sse(event_stream(), translator):
            yield chunk

        async with pool.acquire() as conn:
            await persist_anthropic_message(
                conn,
                conversation_id,
                "assistant",
                [block for block in assistant_blocks if block is not None],
                turn_idx=turn_idx + 1,
                token_count=(final_usage or {}).get("output_tokens", 0)
                + (final_usage or {}).get("input_tokens", 0),
                finish_reason=final_finish,
                usage=final_usage,
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


def _accumulate_into_blocks(
    event: dict,
    blocks: list[dict | None],
    translator: AnthropicToVercelTranslator,
):
    """Mirror Anthropic events into content blocks for persistence."""
    _ = translator
    et = event.get("type")
    if et == "content_block_start":
        idx = event["index"]
        cb = event["content_block"]
        while len(blocks) <= idx:
            blocks.append(None)
        blocks[idx] = dict(cb)
        if cb.get("type") == "text":
            blocks[idx]["text"] = ""
        elif cb.get("type") == "thinking":
            blocks[idx]["thinking"] = ""
        elif cb.get("type") == "tool_use":
            blocks[idx]["_partial_input"] = ""
    elif et == "content_block_delta":
        idx = event["index"]
        delta = event["delta"]
        if idx >= len(blocks) or blocks[idx] is None:
            return
        block = blocks[idx]
        dt = delta.get("type")
        if dt == "text_delta":
            block["text"] = (block.get("text") or "") + delta["text"]
        elif dt == "thinking_delta":
            block["thinking"] = (block.get("thinking") or "") + delta["thinking"]
        elif dt == "input_json_delta":
            block["_partial_input"] = (block.get("_partial_input") or "") + delta["partial_json"]
        elif dt == "signature_delta":
            block["signature"] = delta["signature"]
    elif et == "content_block_stop":
        idx = event["index"]
        if idx >= len(blocks) or blocks[idx] is None:
            return
        block = blocks[idx]
        if block.get("type") == "tool_use" and "_partial_input" in block:
            try:
                block["input"] = json.loads(block["_partial_input"]) if block["_partial_input"] else {}
            except json.JSONDecodeError:
                block["input"] = {}
            del block["_partial_input"]
