import pytest
from pydantic_ai.mcp import MCPServerStreamableHTTP

from backend.v2.agent.bigweld_agent import build_agent


@pytest.mark.asyncio
async def test_agent_builds_with_fallback_model():
    agent = build_agent()
    assert agent is not None
    assert len(agent.model.models) == 2
    assert any(isinstance(toolset, MCPServerStreamableHTTP) for toolset in agent.toolsets)
