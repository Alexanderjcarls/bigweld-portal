from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.v2.agent.bigweld_agent import BigweldDeps, _build_options, stream_agent_response
from backend.v2.config import settings


def test_build_options_sets_model_from_config():
    deps = BigweldDeps(conversation_id="c1")
    opts = _build_options(deps, retrieved_context=None)
    assert opts.model == settings.MODEL


def test_build_options_merges_retrieved_context():
    deps = BigweldDeps(conversation_id="c1", persona_text="PERSONA")
    opts = _build_options(deps, retrieved_context="RETRIEVED")
    assert "PERSONA" in opts.system_prompt
    assert "RETRIEVED" in opts.system_prompt
    assert opts.system_prompt.index("PERSONA") < opts.system_prompt.index("RETRIEVED")


def test_build_options_no_retrieved_context_omits_separator():
    deps = BigweldDeps(conversation_id="c1", persona_text="PERSONA")
    opts = _build_options(deps, retrieved_context=None)
    assert opts.system_prompt == "PERSONA"


def test_build_options_includes_mcp_server():
    deps = BigweldDeps(conversation_id="c1")
    opts = _build_options(deps, retrieved_context=None)
    assert "bigweld" in opts.mcp_servers
    assert opts.mcp_servers["bigweld"]["type"] == "http"
    assert opts.mcp_servers["bigweld"]["url"] == settings.MCP_URL


def test_build_options_enables_tool_search():
    deps = BigweldDeps(conversation_id="c1")
    opts = _build_options(deps, retrieved_context=None)
    assert opts.env.get("ENABLE_TOOL_SEARCH") == "true"


@pytest.mark.asyncio
async def test_stream_agent_response_yields_events_from_sdk():
    deps = BigweldDeps(conversation_id="c1")
    mock_event = MagicMock()

    with (
        patch("backend.v2.agent.bigweld_agent.ClaudeSDKClient") as MockClient,
        patch(
            "backend.v2.agent.bigweld_agent.run_pre_retrieval",
            new=AsyncMock(return_value=""),
        ),
    ):
        instance = MockClient.return_value.__aenter__.return_value
        instance.receive_response = MagicMock(return_value=_async_iter([mock_event]))
        instance.query = AsyncMock()

        events = []
        async for ev in stream_agent_response(deps, "hello", []):
            events.append(ev)

        assert events == [mock_event]
        instance.query.assert_awaited_once_with("hello")


async def _async_iter(items):
    for item in items:
        yield item
