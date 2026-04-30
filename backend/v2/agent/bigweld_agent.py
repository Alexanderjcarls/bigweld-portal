"""Pydantic AI Agent for Bigweld DA v2."""

from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from backend.v2.config import settings


def build_agent() -> Agent:
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

    return Agent(
        model=fallback,
        toolsets=[mcp_server],
        system_prompt=(
            "You are Bigweld, Alex's work-augmentation Domain Agent. "
            "(Full persona loaded dynamically.)"
        ),
    )
