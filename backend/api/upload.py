"""Input artifact upload endpoint (drop-in attachments from the chat surface)."""
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.auth import require_cf_access_email

router = APIRouter(prefix="/api/upload", dependencies=[Depends(require_cf_access_email)])


def _validate_path_component(value: str) -> None:
    if "/" in value or "\\" in value:
        raise HTTPException(status_code=400, detail="invalid path component")
    if value in ("..", "."):
        raise HTTPException(status_code=400, detail="invalid path component")


def _upload_path(conv_id: str, filename: str) -> Path:
    _validate_path_component(conv_id)
    _validate_path_component(filename)
    root = Path(os.environ.get("BIGWELD_PORTAL_ROOT", "/datapool/bigweld-portal"))
    return root / "uploads" / conv_id / filename


@router.put("/{conv_id}/{filename}")
async def upload_file(conv_id: str, filename: str, request: Request) -> dict:
    target = _upload_path(conv_id, filename)
    target.parent.mkdir(parents=True, exist_ok=True)
    body = await request.body()
    target.write_bytes(body)
    return {"ok": True, "path": str(target.resolve()), "bytes": len(body)}
