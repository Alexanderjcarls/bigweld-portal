"""Streaming chat endpoint for Bigweld DA v2."""

import uuid

from fastapi import APIRouter
from pydantic import BaseModel, Field
from pydantic_ai.mcp import MCPServerStreamableHTTP
from pydantic_ai.ui import SSE_CONTENT_TYPE
from pydantic_ai.ui.vercel_ai import VercelAIAdapter
from pydantic_ai.ui.vercel_ai.request_types import SubmitMessage, TextUIPart, UIMessage

from backend.v2.agent.bigweld_agent import BigweldDeps, build_agent, load_persona_text
from backend.v2.config import settings
from backend.v2.db.connection import get_pool
from backend.v2.db.conversations import get_or_create_conversation, touch_conversation
from backend.v2.db.messages import append_messages, load_active_history, model_messages_from_raw


router = APIRouter(tags=["chat"])
_agent = build_agent()
PERSONA_TEXT = load_persona_text()


class ChatRequest(BaseModel):
    conv_id: uuid.UUID
    user_msg: str = Field(min_length=1)


@router.post("/chat")
async def chat(request: ChatRequest):
    pg_pool = get_pool()
    await get_or_create_conversation(pg_pool, request.conv_id)

    history_rows = await load_active_history(pg_pool, request.conv_id)
    message_history = model_messages_from_raw([row["raw_message"] for row in history_rows])
    last_assistant = next(
        (row for row in reversed(history_rows) if row["role"] == "assistant"),
        None,
    )

    deps = BigweldDeps(
        mcp_client=MCPServerStreamableHTTP(settings.MCP_URL),
        pg_pool=pg_pool,
        user_msg=request.user_msg,
        last_assistant_msg=last_assistant["content"] if last_assistant else None,
        persona_text=PERSONA_TEXT,
    )
    adapter = VercelAIAdapter(
        agent=_agent,
        run_input=_run_input_from_chat_request(request),
        accept=SSE_CONTENT_TYPE,
    )

    async def on_complete(result):
        await append_messages(pg_pool, request.conv_id, [*adapter.messages, *result.new_messages()])
        await touch_conversation(pg_pool, request.conv_id)

    return adapter.streaming_response(
        adapter.run_stream(
            message_history=message_history,
            deps=deps,
            on_complete=on_complete,
        )
    )


def _run_input_from_chat_request(request: ChatRequest) -> SubmitMessage:
    return SubmitMessage(
        id=str(request.conv_id),
        messages=[
            UIMessage(
                id=str(uuid.uuid4()),
                role="user",
                parts=[TextUIPart(text=request.user_msg)],
            )
        ],
    )
