"""Claude Agent SDK conversation compactor for Bigweld DA v2."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions, query

from backend.v2.config import settings


COMPACTOR_PROMPT = """You compact a conversation into a faithful summary preserving:
- Decisions and their reasons
- Open questions
- Concrete facts learned (entity names, slugs, URLs, numbers)
- The user's preferences expressed during the conversation

Output a single coherent paragraph. No bullet lists. No headers. Under 500 words."""


@dataclass(frozen=True)
class MessageForCompaction:
    turn_idx: int
    role: str
    content: str | None


async def compact_conversation(messages: list[dict]) -> str:
    options = ClaudeAgentOptions(
        model=settings.MODEL,
        system_prompt=COMPACTOR_PROMPT,
        tools=[],
        setting_sources=[],
        permission_mode="bypassPermissions",
    )
    transcript = "\n\n".join(_format_message(m) for m in messages)
    full = ""
    async for event in query(prompt=f"Compact this conversation:\n\n{transcript}", options=options):
        content = getattr(event, "content", None)
        if isinstance(content, list):
            for block in content:
                text = _block_text(block)
                if text:
                    full += text
    return full.strip()


def _format_message(m: dict) -> str:
    role = m.get("role", "?").upper()
    content = m.get("content", "")
    if isinstance(content, list):
        text = " ".join(
            _block_text(block)
            for block in content
            if _is_text_block(block) and _block_text(block)
        )
        return f"{role}: {text}"
    return f"{role}: {content}"


def format_message_range(messages: Sequence[MessageForCompaction]) -> str:
    lines: list[str] = []
    for message in messages:
        content = (message.content or "").strip()
        lines.append(f"[{message.turn_idx}] {message.role}: {content}")
    return "\n".join(lines)


async def compact_message_range(messages: Sequence[MessageForCompaction]) -> str:
    if not messages:
        raise ValueError("cannot compact an empty message range")

    return await compact_conversation(
        [
            {
                "role": message.role,
                "content": f"[{message.turn_idx}] {(message.content or '').strip()}",
            }
            for message in messages
        ]
    )


def _is_text_block(block: Any) -> bool:
    if isinstance(block, dict):
        return block.get("type") == "text" or "text" in block
    return hasattr(block, "text")


def _block_text(block: Any) -> str:
    if isinstance(block, dict):
        return str(block.get("text", ""))
    return str(getattr(block, "text", ""))
