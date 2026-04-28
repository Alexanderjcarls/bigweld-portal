"""Output artifact upload and download endpoints."""
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse

from backend.auth import require_cf_access_email

router = APIRouter(prefix="/api/output", dependencies=[Depends(require_cf_access_email)])


def _validate_path_component(value: str) -> None:
    if "/" in value or "\\" in value:
        raise HTTPException(status_code=400, detail="invalid path component")
    if value in ("..", "."):
        raise HTTPException(status_code=400, detail="invalid path component")


def _output_path(conv_id: str, filename: str) -> Path:
    _validate_path_component(conv_id)
    _validate_path_component(filename)
    root = Path(os.environ.get("BIGWELD_PORTAL_ROOT", "/datapool/bigweld-portal"))
    return root / "output" / conv_id / filename


@router.put("/{conv_id}/{filename}")
async def upload_output(conv_id: str, filename: str, request: Request):
    target = _output_path(conv_id, filename)
    target.parent.mkdir(parents=True, exist_ok=True)
    content = await request.body()
    target.write_bytes(content)
    return {"ok": True, "path": str(target.resolve()), "bytes": len(content)}


@router.get("/{conv_id}/{filename}")
async def download_output(conv_id: str, filename: str):
    target = _output_path(conv_id, filename)
    if not target.exists():
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(target, filename=filename)
