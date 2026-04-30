"""Dedicated Pydantic AI compactor agent for Bigweld DA v2."""

from dataclasses import dataclass
from typing import Protocol, Sequence

from pydantic_ai import Agent
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from backend.v2.config import settings


COMPACTOR_SYSTEM_PROMPT = (
    "You are Bigweld's conversation compactor. Summarize only the supplied "
    "message range into roughly 200-500 tokens. Cover: topic, key entities "
    "with graph slugs when present, decisions made, and open questions. "
    "Do not invent facts, do not use tools, and return only the summary text."
)


@dataclass(frozen=True)
class MessageForCompaction:
    turn_idx: int
    role: str
    content: str | None


class _CompactorAgent(Protocol):
    async def run(self, user_prompt: str):
        """Run the agent and return an object with an ``output`` attribute."""


def build_compactor_agent() -> Agent:
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

    return Agent(
        model=fallback,
        system_prompt=COMPACTOR_SYSTEM_PROMPT,
    )


def format_message_range(messages: Sequence[MessageForCompaction]) -> str:
    lines: list[str] = []
    for message in messages:
        content = (message.content or "").strip()
        lines.append(f"[{message.turn_idx}] {message.role}: {content}")
    return "\n".join(lines)


async def compact_message_range(
    messages: Sequence[MessageForCompaction],
    agent: _CompactorAgent | None = None,
) -> str:
    if not messages:
        raise ValueError("cannot compact an empty message range")

    compactor = agent or build_compactor_agent()
    transcript = format_message_range(messages)
    prompt = (
        "Summarize this Bigweld conversation message range for later history "
        "reconstruction.\n\n"
        "<message_range>\n"
        f"{transcript}\n"
        "</message_range>"
    )
    result = await compactor.run(prompt)
    return str(result.output).strip()
