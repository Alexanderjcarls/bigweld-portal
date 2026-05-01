"""Claude Agent SDK client for Bigweld DA v2."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, StreamEvent

from backend.v2.config import settings
from backend.v2.retrieval.mcp_client import MCPStreamableHTTPClient
from backend.v2.retrieval.pipeline import run_pre_retrieval


@dataclass
class BigweldDeps:
    conversation_id: str
    persona_text: str | None = None
    pg_pool: Any | None = None


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
        include_partial_messages=True,  # emit raw Anthropic SSE event dicts as StreamEvent
        tools=[],  # disable Bash/Read/Write/etc. — agent is graph-only via MCP
        setting_sources=[],  # don't inherit ~/.claude/settings.json (matrix_admin's interactive CC config)
        permission_mode="bypassPermissions",  # no gate; conversational confirmation is the gate
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
    last_assistant_text = _extract_last_assistant_text(message_history)
    retrieved = ""
    if deps.pg_pool is not None:
        try:
            mcp_client = MCPStreamableHTTPClient(settings.MCP_URL)
            retrieved = await run_pre_retrieval(
                user_msg=user_message,
                last_assistant_msg=last_assistant_text,
                mcp_client=mcp_client,
                pg_pool=deps.pg_pool,
            )
        except Exception as exc:  # pre-retrieval is best-effort — never block the turn
            import logging
            logging.getLogger(__name__).warning(
                "pre-retrieval failed, continuing without retrieved_context: %s", exc
            )
    options = _build_options(deps, retrieved)

    async with ClaudeSDKClient(options=options) as client:
        if message_history:
            await client.query(_sdk_message_stream(message_history, user_message))
        else:
            await client.query(user_message)

        # With include_partial_messages=True the SDK emits StreamEvent objects
        # carrying raw Anthropic SSE event dicts in `.event`. Skip the aggregated
        # typed messages (SystemMessage / AssistantMessage / ResultMessage /
        # UserMessage) — the Vercel adapter consumes the raw deltas.
        async for sdk_msg in client.receive_response():
            if isinstance(sdk_msg, StreamEvent):
                yield sdk_msg.event


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


def _extract_last_assistant_text(message_history: list[dict]) -> str | None:
    """Walk history backwards; return the most recent assistant turn's text content."""
    for turn in reversed(message_history or []):
        if turn.get("role") != "assistant":
            continue
        content = turn.get("content")
        if isinstance(content, str):
            return content if content.strip() else None
        if isinstance(content, list):
            text_parts = [
                b.get("text", "")
                for b in content
                if isinstance(b, dict) and b.get("type") == "text"
            ]
            joined = " ".join(p for p in text_parts if p).strip()
            if joined:
                return joined
    return None
