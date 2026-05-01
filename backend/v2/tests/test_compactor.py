from types import SimpleNamespace
from unittest.mock import patch

import pytest

from backend.v2.agent.compactor import compact_conversation
from backend.v2.config import settings


@pytest.mark.asyncio
async def test_compact_conversation_returns_concatenated_text_from_sdk_stream():
    first = SimpleNamespace(content=[SimpleNamespace(text="Case reopen workflow ")])
    second = SimpleNamespace(content=[SimpleNamespace(text="keeps turns immutable.")])

    with patch("backend.v2.agent.compactor.query", return_value=_async_iter([first, second])) as mock_query:
        summary = await compact_conversation(
            [
                {"role": "user", "content": "Compact case-reopen work."},
                {"role": "assistant", "content": "Decision: immutable turns."},
            ]
        )

    assert summary == "Case reopen workflow keeps turns immutable."
    kwargs = mock_query.call_args.kwargs
    assert "Compact this conversation:" in kwargs["prompt"]
    assert "USER: Compact case-reopen work." in kwargs["prompt"]
    assert "ASSISTANT: Decision: immutable turns." in kwargs["prompt"]
    assert kwargs["options"].model == settings.MODEL
    assert kwargs["options"].tools == []
    assert kwargs["options"].setting_sources == []
    assert kwargs["options"].permission_mode == "bypassPermissions"


async def _async_iter(items):
    for item in items:
        yield item
