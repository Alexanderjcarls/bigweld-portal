"""Render endpoints: proxy to Kroki for fallback diagram rendering."""
import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from backend.auth import require_cf_access_email
from backend.core.config import KROKI_URL

router = APIRouter(prefix="/api/render", dependencies=[Depends(require_cf_access_email)])

SUPPORTED_DIAGRAM_TYPES = {"mermaid", "d2", "plantuml", "graphviz", "structurizr", "bpmn"}


class RenderBody(BaseModel):
    diagram_type: str
    source: str


@router.post("/kroki")
async def render_via_kroki(body: RenderBody) -> Response:
    if body.diagram_type not in SUPPORTED_DIAGRAM_TYPES:
        raise HTTPException(status_code=400, detail=f"unsupported: {body.diagram_type}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{KROKI_URL}/{body.diagram_type}/svg",
                content=body.source.encode("utf-8"),
                headers={"Content-Type": "text/plain"},
            )
            response.raise_for_status()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"kroki: {exc}") from exc

    return Response(content=response.content, media_type="image/svg+xml")
