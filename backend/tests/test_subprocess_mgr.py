"""SubprocessManager tests - env hygiene, cleanup, fallback."""

import asyncio
import sys
from pathlib import Path

import pytest

from backend.core.subprocess_mgr import SpawnResult, SubprocessManager

MOCK_CLAUDE = Path(__file__).parent / "fixtures" / "mock_claude.py"


@pytest.fixture
def mgr() -> SubprocessManager:
    """Subprocess manager pointed at the mock claude binary."""
    return SubprocessManager(
        claude_command=[sys.executable, str(MOCK_CLAUDE)],
        per_turn_timeout_s=10,
        resume_retry_backoff_s=0,
    )


async def test_spawn_unsets_anthropic_api_key(mgr, monkeypatch):
    """ANTHROPIC_API_KEY must be empty so claude falls through to Max OAuth."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "should-not-leak")
    monkeypatch.setenv("AEGIS_V2_TOGETHER_API_KEY", "must-not-leak")

    proc = await mgr.spawn_turn(
        prompt="hi",
        session_uuid="s1",
        is_resume=False,
        conversation_id="c1",
        conversation_file=Path("/tmp/c1.json"),
    )
    events = []
    async for ev in mgr.stream_events(proc):
        events.append(ev)

    assert any(e.get("type") == "system" for e in events)
    assert proc.env_seen.get("ANTHROPIC_API_KEY") == ""
    assert proc.env_seen.get("BIGWELD_CONVERSATION_ID") == "c1"
    assert proc.env_seen.get("BIGWELD_CONVERSATION_FILE") == "/tmp/c1.json"
    assert "AEGIS_V2_TOGETHER_API_KEY" not in proc.env_seen


async def test_terminate_then_kill_on_cancel(mgr, monkeypatch):
    """If client disconnects mid-stream, subprocess must terminate->kill."""
    monkeypatch.setenv("MOCK_CLAUDE_MODE", "hang")
    proc = await mgr.spawn_turn(
        prompt="will hang",
        session_uuid="s2",
        is_resume=False,
        conversation_id="c2",
        conversation_file=Path("/tmp/c2.json"),
    )

    async def consume_with_cancel():
        count = 0
        async for _ in mgr.stream_events(proc):
            count += 1
            if count >= 1:
                raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        await consume_with_cancel()

    await asyncio.wait_for(proc.wait_closed(), timeout=15)
    assert proc.returncode is not None


async def test_resume_failure_falls_back_to_fresh_session(mgr, monkeypatch, tmp_path):
    """When --resume errors, retry with a fresh --session-id and embedded transcript."""
    monkeypatch.setenv("MOCK_CLAUDE_MODE", "resume_fail")
    transcript_file = tmp_path / "c3.json"
    transcript_file.write_text(
        '{"type":"meta","session_uuid":"original-uuid"}\n'
        '{"type":"user","content":"prior turn 1"}\n'
        '{"type":"assistant","content":"prior response 1"}\n'
    )
    result = await mgr.spawn_turn_with_fallback(
        prompt="continue",
        session_uuid="original-uuid",
        is_resume=True,
        conversation_id="c3",
        conversation_file=transcript_file,
    )
    assert isinstance(result, SpawnResult)
    assert result.fallback_used is True
    assert result.new_session_uuid != "original-uuid"
    events = []
    async for ev in mgr.stream_events(result.proc):
        events.append(ev)

    assert any(ev.get("type") == "result" for ev in events)
    assistant = [ev for ev in events if ev.get("type") == "assistant"]
    assert "prior turn 1" in json_event_text(assistant[-1])


async def test_transient_resume_error_retries_without_fallback(mgr, monkeypatch, tmp_path):
    monkeypatch.setenv("MOCK_CLAUDE_MODE", "rate_limit")
    monkeypatch.setenv("MOCK_CLAUDE_RATE_LIMIT_ONCE_FILE", str(tmp_path / "rate-limit-seen"))
    transcript_file = tmp_path / "c-rate.json"
    transcript_file.write_text('{"type":"meta","session_uuid":"original-uuid"}\n')

    result = await mgr.spawn_turn_with_fallback(
        prompt="continue",
        session_uuid="original-uuid",
        is_resume=True,
        conversation_id="c-rate",
        conversation_file=transcript_file,
    )

    assert result.fallback_used is False
    assert result.new_session_uuid == "original-uuid"
    events = []
    async for ev in mgr.stream_events(result.proc):
        events.append(ev)
    assert any(ev.get("type") == "result" for ev in events)


async def test_stderr_drain_does_not_deadlock(mgr, monkeypatch):
    """Subprocess writes to stderr must be consumed concurrently with stdout."""
    monkeypatch.setenv("MOCK_CLAUDE_MODE", "crash")
    proc = await mgr.spawn_turn(
        prompt="will crash",
        session_uuid="s4",
        is_resume=False,
        conversation_id="c4",
        conversation_file=Path("/tmp/c4.json"),
    )
    events = []
    async for ev in mgr.stream_events(proc):
        events.append(ev)
    await proc.wait_closed()
    assert proc.returncode == 137
    assert "fatal: simulated crash" in proc.stderr_collected
    assert events == [
        {
            "type": "system",
            "subtype": "error",
            "is_error": True,
            "error": "subprocess exited rc=137 before result",
        }
    ]


def test_fallback_prompt_preserves_tool_context():
    prompt = SubprocessManager._assemble_fallback_prompt(
        [
            {"type": "user", "content": "please inspect"},
            {
                "type": "assistant",
                "blocks": [
                    {"kind": "text", "text": "I will check."},
                    {"kind": "tool_use", "name": "Read"},
                ],
            },
            {"type": "tool_use_result", "tool": "Read", "output": "abcdef" * 80},
            {"type": "usage", "input_tokens": 10},
        ],
        "continue",
    )

    assert "User: please inspect" in prompt
    assert "[ran tool: Read]" in prompt
    assert "[Tool Read:" in prompt
    assert len(prompt.split("[Tool Read:")[1].split("]")[0]) <= 306


def json_event_text(event: dict) -> str:
    message = event.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and isinstance(block.get("text"), str)
        )
    return ""
