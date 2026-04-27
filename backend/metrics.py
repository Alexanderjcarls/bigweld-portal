"""Prometheus metrics for the Bigweld portal."""

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

router = APIRouter()

# Keep labels bounded: per-conversation IDs are intentionally omitted.
turn_total = Counter(
    "bigweld_portal_turn_total",
    "Total turns processed",
    ["status"],
)
turn_duration_seconds = Histogram(
    "bigweld_portal_turn_duration_seconds",
    "Turn end-to-end duration",
)
subprocess_startup_seconds = Histogram(
    "bigweld_portal_subprocess_startup_seconds",
    "Time from spawn to first stream-json event (cold-start watch-item)",
)
resume_failure_total = Counter(
    "bigweld_portal_resume_failure_total",
    "Number of --resume invocations that fell back to fresh --session-id",
)
summarizer_total = Counter(
    "bigweld_portal_summarizer_total",
    "Summarizer invocations by status",
    ["status"],
)

turn_total.labels(status="ok")
turn_total.labels(status="error")
summarizer_total.labels(status="ok")
summarizer_total.labels(status="error")


@router.get("/metrics")
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
