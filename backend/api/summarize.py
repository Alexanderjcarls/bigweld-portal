"""Manual conversation summarization endpoint."""
from fastapi import APIRouter, Depends, HTTPException

from backend.api.conversations import _store
from backend.auth import require_cf_access_email
from backend.core.summarizer import summarize_conversation

router = APIRouter(prefix="/api", dependencies=[Depends(require_cf_access_email)])


@router.post("/conversations/{conv_id}/summarize")
async def summarize_now(conv_id: str):
    store = _store()
    if not store.path_for(conv_id).exists():
        raise HTTPException(status_code=404, detail="conversation not found")

    summary = await summarize_conversation(store, conv_id)
    if summary is None:
        raise HTTPException(status_code=500, detail="summarizer failed; see logs")
    return {"summary_md": summary}
