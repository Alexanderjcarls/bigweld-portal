"""Conversation list and hydration endpoints for Bigweld DA v2."""

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, model_validator

from backend.v2.db.connection import get_pool
from backend.v2.db.conversations import (
    ConversationNotFound,
    get_conversation,
    list_conversations,
    update_conversation,
)
from backend.v2.db.messages import fetch_conversation_messages
from backend.v2.db.summaries import list_active_compacted_summaries


router = APIRouter(prefix="/api", tags=["conversations"])


class ConversationPatchRequest(BaseModel):
    title: str | None = None
    archived: bool | None = None

    @model_validator(mode="after")
    def validate_patch(self):
        if self.title is None and self.archived is None:
            raise ValueError("provide title or archived")
        if self.title is not None:
            title = self.title.strip()
            if not title:
                raise ValueError("title cannot be blank")
            self.title = title
        return self


def _not_found(exc: Exception) -> HTTPException:
    return HTTPException(status_code=404, detail=str(exc))


@router.get("/conversations")
async def get_conversations(archived: bool = False):
    conversations = await list_conversations(get_pool(), archived=archived)
    return {"conversations": conversations}


@router.get("/conversations/{conv_id}")
async def get_conversation_detail(conv_id: uuid.UUID):
    try:
        conversation = await get_conversation(get_pool(), conv_id)
    except ConversationNotFound as exc:
        raise _not_found(exc) from exc

    messages = await fetch_conversation_messages(get_pool(), conv_id)
    summaries = await list_active_compacted_summaries(get_pool(), conv_id)
    return {
        **conversation,
        "messages": messages,
        "compacted_summaries": summaries,
    }


@router.patch("/conversations/{conv_id}")
async def patch_conversation(conv_id: uuid.UUID, request: ConversationPatchRequest):
    try:
        return await update_conversation(
            get_pool(),
            conv_id,
            title=request.title,
            archived=request.archived,
        )
    except ConversationNotFound as exc:
        raise _not_found(exc) from exc
