import pytest
from pydantic_ai.mcp import MCPServerStreamableHTTP

from backend.v2.agent.bigweld_agent import BigweldDeps, build_agent, load_persona_text


@pytest.mark.asyncio
async def test_agent_builds_with_fallback_model():
    agent = build_agent()
    assert agent is not None
    assert len(agent.model.models) == 2
    assert any(isinstance(toolset, MCPServerStreamableHTTP) for toolset in agent.toolsets)
    assert agent.deps_type is BigweldDeps
    assert len(agent._system_prompt_dynamic_functions) == 2


def test_load_persona_text_expands_memory_includes():
    text = load_persona_text()

    assert "# Bigweld DA" in text
    assert "# Working with Alex" in text
    assert "# World Model" in text
    assert "# Never-list" in text
    assert "@memory/" not in text
