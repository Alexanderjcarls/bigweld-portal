from types import SimpleNamespace

import pytest
from pydantic_ai.mcp import MCPServerStreamableHTTP

from backend.v2.agent.compactor import (
    MessageForCompaction,
    build_compactor_agent,
    compact_message_range,
)


class StubCompactorAgent:
    def __init__(self):
        self.prompt = ""

    async def run(self, user_prompt: str):
        self.prompt = user_prompt
        return SimpleNamespace(
            output=(
                "Topic: Case reopen workflow.\n"
                "Key entities: case-reopen.\n"
                "Decisions made: keep original turns immutable.\n"
                "Open questions: none."
            )
        )


@pytest.mark.asyncio
async def test_compactor_builds_with_fallback_model_without_mcp_toolsets():
    agent = build_compactor_agent()
    assert agent is not None
    assert len(agent.model.models) == 2
    assert not any(isinstance(toolset, MCPServerStreamableHTTP) for toolset in agent.toolsets)


@pytest.mark.asyncio
async def test_compact_message_range_uses_stubbed_agent():
    stub = StubCompactorAgent()
    messages = [
        MessageForCompaction(turn_idx=3, role="user", content="Compact case-reopen work."),
        MessageForCompaction(turn_idx=4, role="assistant", content="Decision: immutable turns."),
    ]

    summary = await compact_message_range(messages, agent=stub)

    assert summary.startswith("Topic: Case reopen workflow.")
    assert "[3] user: Compact case-reopen work." in stub.prompt
    assert "[4] assistant: Decision: immutable turns." in stub.prompt
