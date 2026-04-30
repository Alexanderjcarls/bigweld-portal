import pytest
from pydantic_ai.mcp import MCPServerStreamableHTTP
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.openai import OpenAIChatModel

from backend.v2.agent.bigweld_agent import BigweldDeps, build_agent, load_persona_text
from backend.v2 import config as v2_config


@pytest.mark.asyncio
async def test_agent_builds_with_fallback_model_when_nas_url_set(monkeypatch):
    monkeypatch.setattr(v2_config.settings, "NAS_VLLM_URL", "http://192.168.0.25:8005/v1")
    agent = build_agent()
    assert agent is not None
    assert isinstance(agent.model, FallbackModel)
    assert len(agent.model.models) == 2
    assert any(isinstance(toolset, MCPServerStreamableHTTP) for toolset in agent.toolsets)
    assert agent.deps_type is BigweldDeps
    # Single merged dynamic system_prompt — DeepInfra Qwen requires merged systems.
    assert len(agent._system_prompt_dynamic_functions) == 1


@pytest.mark.asyncio
async def test_agent_builds_cloud_only_when_nas_url_unset(monkeypatch):
    monkeypatch.setattr(v2_config.settings, "NAS_VLLM_URL", "")
    agent = build_agent()
    assert agent is not None
    assert isinstance(agent.model, OpenAIChatModel)
    assert any(isinstance(toolset, MCPServerStreamableHTTP) for toolset in agent.toolsets)


@pytest.mark.asyncio
@pytest.mark.parametrize("disabled_value", ["none", "skip", "disabled", "  none  "])
async def test_agent_builds_cloud_only_when_nas_url_disabled(monkeypatch, disabled_value):
    monkeypatch.setattr(v2_config.settings, "NAS_VLLM_URL", disabled_value)
    agent = build_agent()
    assert isinstance(agent.model, OpenAIChatModel)


def test_load_persona_text_expands_memory_includes():
    text = load_persona_text()

    assert "# Bigweld DA" in text
    assert "# Working with Alex" in text
    assert "# World Model" in text
    assert "# Never-list" in text
    assert "@memory/" not in text
