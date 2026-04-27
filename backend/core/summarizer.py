"""Per-conversation LLM summarizer."""
import logging
from datetime import datetime, timezone
from typing import Any

from backend.core.config import SUMMARIZE_IDLE_THRESHOLD_S
from backend.core.conversation_store import ConversationStore
from backend.core.llm_router import chat
from backend.metrics import summarizer_total

logger = logging.getLogger(__name__)

SUMMARY_PROMPT = """Summarize this conversation. Surface:
- Key decisions made (with the agreed answer, not just the question)
- Open questions still unresolved
- References to Bigweld articles/scopes/tags consulted
- Key insights or breakthroughs

Keep it tight (200-500 words). Use ## section headers."""


def _event_content(event: dict[str, Any]) -> str:
    content = event.get("content")
    if isinstance(content, str):
        return content

    message = event.get("message")
    if not isinstance(message, dict):
        return ""

    message_content = message.get("content")
    if isinstance(message_content, str):
        return message_content
    if isinstance(message_content, list):
        chunks: list[str] = []
        for item in message_content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                chunks.append(item["text"])
        return "\n".join(chunks)
    return ""


def _build_transcript(events: list[dict[str, Any]]) -> str:
    transcript_lines: list[str] = []
    for event in events:
        event_type = event.get("type")
        if event_type == "user":
            transcript_lines.append(f"USER: {_event_content(event)}")
        elif event_type == "assistant":
            transcript_lines.append(f"BIGWELD: {_event_content(event)}")
        elif event_type in {"tool_use_result", "tool_result"}:
            tool = event.get("tool") or event.get("name") or "?"
            output = event.get("output") or _event_content(event)
            transcript_lines.append(f"[TOOL {tool}]: {str(output)[:500]}")
    return "\n".join(line for line in transcript_lines if line.strip())


async def summarize_conversation(store: ConversationStore, conv_id: str) -> str | None:
    events = store.read_events(conv_id)
    transcript = _build_transcript(events)
    if not transcript:
        logger.info("conversation %s is empty; skipping summarize", conv_id)
        summarizer_total.labels(status="ok").inc()
        return None

    try:
        summary_md = await chat(
            messages=[
                {"role": "system", "content": SUMMARY_PROMPT},
                {"role": "user", "content": transcript},
            ],
            temperature=0.3,
        )
    except Exception as exc:
        logger.exception("summarizer LLM call failed: %s", exc)
        summarizer_total.labels(status="error").inc()
        return None

    try:
        store.write_summary(conv_id, summary_md)
    except Exception:
        summarizer_total.labels(status="error").inc()
        raise

    summarizer_total.labels(status="ok").inc()
    return summary_md


async def sweep_idle_conversations(
    store: ConversationStore,
    now: datetime | None = None,
) -> int:
    now = now or datetime.now(timezone.utc)
    count = 0
    for item in store.list_all():
        if item.get("has_summary"):
            continue
        idle = store.idle_seconds_since_last_event(item["id"], now=now)
        if idle is None or idle < SUMMARIZE_IDLE_THRESHOLD_S:
            continue
        if await summarize_conversation(store, item["id"]):
            count += 1
    return count
