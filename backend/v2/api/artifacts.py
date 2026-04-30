"""Artifact storage endpoints for Bigweld DA v2."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel, Field, model_validator

from backend.v2.db.artifacts import (
    ArtifactArchived,
    ArtifactNotFound,
    ConversationNotFound,
    SectionNotFound,
    archive_artifact,
    create_artifact,
    get_artifact,
    get_artifact_version,
    list_artifacts,
    patch_artifact_section,
)
from backend.v2.db.connection import get_pool


ArtifactType = Literal[
    "markdown",
    "spreadsheet",
    "image",
    "mermaid",
    "d2",
    "pdf",
    "powerpoint",
]
ArtifactSource = Literal["bigweld", "user_dropped", "user_pasted", "cross_conv_pulled"]

router = APIRouter(prefix="/api", tags=["artifacts"])


class ArtifactCreateRequest(BaseModel):
    conv_id: uuid.UUID
    type: ArtifactType
    title: str = Field(min_length=1)
    body: str | None = None
    files: list[dict[str, Any]] | dict[str, Any] | None = None
    source: ArtifactSource

    @model_validator(mode="after")
    def validate_content(self):
        has_body = self.body is not None
        has_files = self.files is not None
        if has_body == has_files:
            raise ValueError("provide exactly one of body or files")
        if self.body is not None and not self.body.strip():
            raise ValueError("body cannot be blank")
        if self.files is not None and not self.files:
            raise ValueError("files cannot be empty")
        return self


class ArtifactPatchRequest(BaseModel):
    section_id: str = Field(min_length=1)
    new_content: str


def _not_found(exc: Exception) -> HTTPException:
    return HTTPException(status_code=404, detail=str(exc))


@router.post("/artifacts", status_code=201)
async def post_artifact(request: ArtifactCreateRequest):
    try:
        return await create_artifact(
            get_pool(),
            conv_id=request.conv_id,
            artifact_type=request.type,
            title=request.title,
            source=request.source,
            body=request.body,
            files=request.files,
        )
    except ConversationNotFound as exc:
        raise _not_found(exc) from exc


@router.get("/artifacts")
async def get_artifacts(
    conv_id: uuid.UUID | None = None,
    global_library: bool = Query(False, alias="global"),
):
    if not global_library and conv_id is None:
        raise HTTPException(
            status_code=422,
            detail="conv_id is required unless global=true",
        )
    artifacts = await list_artifacts(
        get_pool(),
        conv_id=conv_id,
        global_library=global_library,
    )
    return {"artifacts": artifacts}


@router.get("/artifacts/{artifact_id}")
async def get_current_artifact(artifact_id: uuid.UUID):
    try:
        return await get_artifact(get_pool(), artifact_id)
    except ArtifactNotFound as exc:
        raise _not_found(exc) from exc


@router.get("/artifacts/{artifact_id}/versions/{version}")
async def get_versioned_artifact(artifact_id: uuid.UUID, version: int = Path(ge=1)):
    try:
        return await get_artifact_version(get_pool(), artifact_id, version)
    except ArtifactNotFound as exc:
        raise _not_found(exc) from exc


@router.patch("/artifacts/{artifact_id}")
async def patch_artifact(artifact_id: uuid.UUID, request: ArtifactPatchRequest):
    try:
        return await patch_artifact_section(
            get_pool(),
            artifact_id=artifact_id,
            section_id=request.section_id,
            new_content=request.new_content,
        )
    except ArtifactArchived as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (ArtifactNotFound, SectionNotFound) as exc:
        raise _not_found(exc) from exc


@router.delete("/artifacts/{artifact_id}")
async def delete_artifact(artifact_id: uuid.UUID):
    try:
        archived_id = await archive_artifact(get_pool(), artifact_id)
    except ArtifactNotFound as exc:
        raise _not_found(exc) from exc
    return {"ok": True, "id": str(archived_id)}
