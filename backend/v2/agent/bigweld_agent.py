"""Pydantic AI Agent for Bigweld DA v2."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic_ai import Agent, RunContext
from pydantic_ai.mcp import MCPServerStreamableHTTP
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from backend.v2.config import settings
from backend.v2.retrieval.pipeline import run_pre_retrieval


@dataclass
class BigweldDeps:
    mcp_client: Any
    pg_pool: Any
    user_msg: str
    last_assistant_msg: str | None
    persona_text: str


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


def build_agent() -> Agent[BigweldDeps]:
    nas_provider = OpenAIProvider(
        base_url=settings.NAS_VLLM_URL,
        api_key="not-used",
    )
    nas_model = OpenAIChatModel(settings.MODEL_NAME, provider=nas_provider)

    deepinfra_provider = OpenAIProvider(
        base_url=settings.DEEPINFRA_BASE_URL,
        api_key=settings.DEEPINFRA_API_KEY,
    )
    deepinfra_model = OpenAIChatModel(settings.MODEL_NAME, provider=deepinfra_provider)

    fallback = FallbackModel(nas_model, deepinfra_model)
    mcp_server = MCPServerStreamableHTTP(settings.MCP_URL)

    agent = Agent(
        model=fallback,
        toolsets=[mcp_server],
        deps_type=BigweldDeps,
    )

    @agent.system_prompt(dynamic=True)
    async def base_persona(ctx: RunContext[BigweldDeps]) -> str:
        return ctx.deps.persona_text or PERSONA_TEXT

    @agent.system_prompt(dynamic=True)
    async def retrieved_context(ctx: RunContext[BigweldDeps]) -> str:
        return await run_pre_retrieval(
            ctx.deps.user_msg,
            ctx.deps.last_assistant_msg,
            ctx.deps.mcp_client,
            ctx.deps.pg_pool,
        )

    return agent
