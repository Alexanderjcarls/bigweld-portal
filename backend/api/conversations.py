"""Conversation create, list, replay, and turn endpoints."""
import json
import logging
import os
import uuid as uuid_lib
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.auth import require_cf_access_email
from backend.core.conversation_store import ConversationStore
from backend.core.subprocess_mgr import SubprocessManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", dependencies=[Depends(require_cf_access_email)])
_subprocess_mgr = SubprocessManager()


def _portal_root() -> Path:
    return Path(os.environ.get("BIGWELD_PORTAL_ROOT", "/datapool/bigweld-portal"))


def _store() -> ConversationStore:
    return ConversationStore(root=_portal_root() / "conversations")


class CreateResponse(BaseModel):
    conv_id: str


class ListResponse(BaseModel):
    conversations: list[dict]


class EventsResponse(BaseModel):
    events: list[dict]


class TurnRequest(BaseModel):
    message: str
    attachments: list[dict] | None = None


@router.post("/conversations", response_model=CreateResponse)
async def create_conversation() -> CreateResponse:
    return CreateResponse(conv_id=_store().create())


@router.get("/conversations", response_model=ListResponse)
async def list_conversations() -> ListResponse:
    return ListResponse(conversations=_store().list_all())


@router.get("/conversations/{conv_id}", response_model=EventsResponse)
async def get_conversation(conv_id: str) -> EventsResponse:
    store = _store()
    if not store.path_for(conv_id).exists():
        raise HTTPException(status_code=404, detail="conversation not found")
    return EventsResponse(events=store.read_events(conv_id))


@router.post("/conversations/{conv_id}/turn")
async def take_turn(conv_id: str, body: TurnRequest) -> StreamingResponse:
    store = _store()
    path = store.path_for(conv_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="conversation not found")

    existing_uuid = store.read_session_uuid(conv_id)
    is_resume = existing_uuid is not None
    session_uuid = existing_uuid or str(uuid_lib.uuid4())

    async def stream() -> AsyncIterator[bytes]:
        try:
            result = await _subprocess_mgr.spawn_turn_with_fallback(
                prompt=body.message,
                session_uuid=session_uuid,
                is_resume=is_resume,
                conversation_id=conv_id,
                conversation_file=path,
            )
            if result.fallback_used or not is_resume:
                store.set_session_uuid(conv_id, result.new_session_uuid)

            async for ev in _subprocess_mgr.stream_events(result.proc):
                yield (json.dumps(ev) + "\n").encode("utf-8")
            await result.proc.wait_closed()
        except Exception as exc:
            logger.exception("turn stream failed")
            err = {
                "type": "system",
                "subtype": "error",
                "error": str(exc),
                "is_error": True,
            }
            yield (json.dumps(err) + "\n").encode("utf-8")

    return StreamingResponse(stream(), media_type="application/x-ndjson")
