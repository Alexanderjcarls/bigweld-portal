"""Diff-then-nod compaction endpoints."""

import difflib
import uuid
from typing import Sequence

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

from backend.v2.agent.compactor import (
    MessageForCompaction,
    compact_message_range,
    format_message_range,
)
from backend.v2.db.connection import get_pool
from backend.v2.db.messages import fetch_message_range
from backend.v2.db.summaries import insert_compacted_summary
from backend.v2.retrieval.embed import embed_query


router = APIRouter(prefix="/api", tags=["compact"])


class CompactRequest(BaseModel):
    conv_id: uuid.UUID
    range_start_idx: int = Field(ge=0)
    range_end_idx: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_range(self):
        if self.range_end_idx < self.range_start_idx:
            raise ValueError("range_end_idx must be greater than or equal to range_start_idx")
        return self


class CompactConfirmRequest(CompactRequest):
    summary: str = Field(min_length=1)


def build_diff_preview(messages: Sequence[MessageForCompaction], proposed_summary: str) -> str:
    original = format_message_range(messages).splitlines()
    summary = proposed_summary.strip().splitlines()
    return "\n".join(
        difflib.unified_diff(
            original,
            summary,
            fromfile="message_range",
            tofile="proposed_summary",
            lineterm="",
        )
    )


async def _load_nonempty_range(request: CompactRequest) -> list[MessageForCompaction]:
    messages = await fetch_message_range(
        get_pool(),
        request.conv_id,
        request.range_start_idx,
        request.range_end_idx,
    )
    if (
        not messages
        or messages[0].turn_idx != request.range_start_idx
        or messages[-1].turn_idx != request.range_end_idx
    ):
        raise HTTPException(status_code=404, detail="message range not found")
    return messages


@router.post("/compact")
async def propose_compaction(request: CompactRequest):
    messages = await _load_nonempty_range(request)
    proposed_summary = await compact_message_range(messages)
    return {
        "proposed_summary": proposed_summary,
        "diff_preview": build_diff_preview(messages, proposed_summary),
    }


@router.post("/compact/confirm")
async def confirm_compaction(request: CompactConfirmRequest):
    await _load_nonempty_range(request)
    summary = request.summary.strip()
    if not summary:
        raise HTTPException(status_code=422, detail="summary cannot be blank")

    embedding = await embed_query(summary)
    summary_id = await insert_compacted_summary(
        get_pool(),
        request.conv_id,
        request.range_start_idx,
        request.range_end_idx,
        summary,
        embedding,
    )
    return {"ok": True, "summary_id": summary_id}
