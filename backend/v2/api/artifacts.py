"""Artifact storage endpoints for Bigweld DA v2."""

from __future__ import annotations

import base64
import uuid
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Path, Query, Request
from pydantic import BaseModel, Field, ValidationError, model_validator
from starlette.datastructures import FormData, UploadFile

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
from backend.v2.db.messages import append_messages


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
TEXT_ARTIFACT_TYPES = {"markdown", "spreadsheet", "mermaid", "d2"}


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
async def post_artifact(request: Request):
    artifact_request = await _artifact_create_request_from_http(request)
    pg_pool = get_pool()

    try:
        artifact = await create_artifact(
            pg_pool,
            conv_id=artifact_request.conv_id,
            artifact_type=artifact_request.type,
            title=artifact_request.title,
            source=artifact_request.source,
            body=artifact_request.body,
            files=artifact_request.files,
        )
    except ConversationNotFound as exc:
        raise _not_found(exc) from exc

    if artifact_request.source == "user_dropped":
        await append_messages(
            pg_pool,
            artifact_request.conv_id,
            [{
                "role": "system",
                "content": f"user dropped: {artifact_request.title}",
            }],
        )

    return artifact


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


async def _artifact_create_request_from_http(request: Request) -> ArtifactCreateRequest:
    try:
        content_type = request.headers.get("content-type", "")
        if content_type.startswith("multipart/form-data"):
            return await _artifact_create_request_from_form(await request.form())
        return ArtifactCreateRequest.model_validate(await request.json())
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors(include_context=False)) from exc


async def _artifact_create_request_from_form(form: FormData) -> ArtifactCreateRequest:
    artifact_type = str(_required_form_value(form, "type"))
    body = _optional_form_text(form, "body")
    files_payload: list[dict[str, Any]] | None = None

    uploads = [
        value
        for value in [*form.getlist("file"), *form.getlist("files")]
        if isinstance(value, UploadFile)
    ]

    if body is None and uploads:
        files_payload = []
        for upload in uploads:
            content = await upload.read()
            files_payload.append(_upload_to_payload(upload, content))

        if len(files_payload) == 1 and artifact_type in TEXT_ARTIFACT_TYPES:
            body = _decode_text_upload(uploads[0], files_payload[0])
            files_payload = None

    return ArtifactCreateRequest.model_validate({
        "conv_id": _required_form_value(form, "conv_id"),
        "type": artifact_type,
        "title": _required_form_value(form, "title"),
        "source": _required_form_value(form, "source"),
        "body": body,
        "files": files_payload,
    })


def _required_form_value(form: FormData, key: str) -> str:
    value = form.get(key)
    if value is None or isinstance(value, UploadFile):
        raise ValidationError.from_exception_data(
            "ArtifactCreateRequest",
            [{
                "type": "missing",
                "loc": (key,),
                "msg": f"{key} is required",
                "input": None,
            }],
        )
    return str(value)


def _optional_form_text(form: FormData, key: str) -> str | None:
    value = form.get(key)
    if value is None or isinstance(value, UploadFile):
        return None
    text = str(value)
    return text if text.strip() else None


def _upload_to_payload(upload: UploadFile, content: bytes) -> dict[str, Any]:
    content_type = upload.content_type or "application/octet-stream"
    encoded = base64.b64encode(content).decode("ascii")
    payload: dict[str, Any] = {
        "filename": upload.filename,
        "mime_type": content_type,
        "size": len(content),
        "body_base64": encoded,
    }
    if content_type.startswith("image/"):
        payload["data_url"] = f"data:{content_type};base64,{encoded}"
    return payload


def _decode_text_upload(upload: UploadFile, payload: dict[str, Any]) -> str:
    encoded = payload.get("body_base64")
    if not isinstance(encoded, str):
        return ""
    content = base64.b64decode(encoded)
    charset = "utf-8"
    content_type = upload.content_type or ""
    if "charset=" in content_type:
        charset = content_type.rsplit("charset=", 1)[-1].split(";", 1)[0].strip()
    return content.decode(charset or "utf-8", errors="replace")
