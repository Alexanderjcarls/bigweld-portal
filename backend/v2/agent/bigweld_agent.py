"""Claude Agent SDK client for Bigweld DA v2."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

from backend.v2.config import settings
from backend.v2.retrieval.pipeline import run_pre_retrieval


@dataclass
class BigweldDeps:
    conversation_id: str
    persona_text: str | None = None


def load_persona_text(persona_dir: Path | None = None) -> str:
    persona_dir = persona_dir or Path(__file__).resolve().parents[1] / "persona"
    claude_md = persona_dir / "CLAUDE.md"
    return _expand_persona_includes(claude_md, persona_dir)


def _expand_persona_includes(path: Path, persona_dir: Path) -> str:
    sections: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("@") and len(stripped) > 1:
            include_path = persona_dir / stripped[1:]
            sections.append(_expand_persona_includes(include_path, persona_dir))
        else:
            sections.append(line)
    return "\n".join(sections).strip() + "\n"


PERSONA_TEXT = load_persona_text()


def _build_options(deps: BigweldDeps, retrieved_context: str | None) -> ClaudeAgentOptions:
    persona = deps.persona_text or PERSONA_TEXT
    system_prompt = persona if not retrieved_context else f"{persona}\n\n{retrieved_context}"
    return ClaudeAgentOptions(
        model=settings.MODEL,
        system_prompt=system_prompt,
        mcp_servers={
            "bigweld": {
                "type": "http",
                "url": settings.MCP_URL,
            }
        },
        env={"ENABLE_TOOL_SEARCH": "true"},
    )


async def stream_agent_response(
    deps: BigweldDeps,
    user_message: str,
    message_history: list[dict],
) -> AsyncIterator[dict]:
    """
    Yields raw Anthropic SDK message events as dicts.
    Caller (chat.py) is responsible for translating to Vercel AI Data Stream Protocol.
    """
    retrieved = await run_pre_retrieval(user_message, deps.conversation_id)
    options = _build_options(deps, retrieved)

    async with ClaudeSDKClient(options=options) as client:
        if message_history:
            await client.query(_sdk_message_stream(message_history, user_message))
        else:
            await client.query(user_message)

        async for event in client.receive_response():
            yield event


async def _sdk_message_stream(
    message_history: list[dict],
    user_message: str,
) -> AsyncIterator[dict[str, Any]]:
    for turn in message_history:
        yield _sdk_input_message(turn)
    yield _sdk_input_message({"role": "user", "content": user_message})


def _sdk_input_message(turn: dict[str, Any]) -> dict[str, Any]:
    role = turn.get("role") or "user"
    content = turn.get("content", "")
    return {
        "type": role,
        "message": {
            "role": role,
            "content": content,
        },
        "parent_tool_use_id": None,
    }
