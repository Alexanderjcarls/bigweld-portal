"""Conversation file I/O tests."""
from datetime import datetime, timezone
from pathlib import Path

import pytest

from backend.core.conversation_store import ConversationStore


@pytest.fixture
def store(tmp_path) -> ConversationStore:
    return ConversationStore(root=tmp_path)


def test_create_returns_uuid(store):
    conv_id = store.create()
    assert len(conv_id) == 36  # UUID4
    path = store.path_for(conv_id)
    assert path.exists()
    # File should contain a meta event line
    content = path.read_text()
    assert '"type":"meta"' in content or '"type": "meta"' in content


def test_path_for_uses_year_month(store, monkeypatch):
    # Freeze time to a known month
    fixed = datetime(2026, 4, 27, tzinfo=timezone.utc)
    monkeypatch.setattr(
        "backend.core.conversation_store.datetime",
        type("FakeDT", (), {"now": staticmethod(lambda tz=None: fixed)})
    )
    conv_id = store.create()
    path = store.path_for(conv_id)
    assert "2026-04" in str(path)


def test_session_uuid_extraction(store):
    conv_id = store.create()
    sid = store.read_session_uuid(conv_id)
    assert sid is None  # newly created — meta has no session_uuid yet

    # Simulate the backend updating meta after first turn
    store.set_session_uuid(conv_id, "abc-123")
    assert store.read_session_uuid(conv_id) == "abc-123"


def test_read_events_skips_corrupt_lines(store):
    conv_id = store.create()
    path = store.path_for(conv_id)
    with path.open("a") as f:
        f.write('not valid json\n')
        f.write('{"type":"user","content":"hi","ts":"2026-04-27T12:00:00Z"}\n')
        f.write('also broken\n')
        f.write('{"type":"assistant","content":"hello","ts":"2026-04-27T12:00:01Z"}\n')

    events = store.read_events(conv_id)
    user_and_assistant = [e for e in events if e["type"] in ("user", "assistant")]
    assert len(user_and_assistant) == 2
    assert user_and_assistant[0]["content"] == "hi"
    assert user_and_assistant[1]["content"] == "hello"


def test_read_events_empty_file(store):
    conv_id = store.create()
    # Wipe to truly empty
    store.path_for(conv_id).write_text("")
    events = store.read_events(conv_id)
    assert events == []


def test_list_conversations_sorted_by_mtime(store, tmp_path):
    import time
    a = store.create()
    time.sleep(0.01)
    b = store.create()
    time.sleep(0.01)
    c = store.create()
    listed = store.list_all()
    ids = [item["id"] for item in listed]
    # Most recent first
    assert ids[0] == c
    assert ids[-1] == a


def test_summary_path_sibling(store):
    conv_id = store.create()
    summary = store.summary_path_for(conv_id)
    json_path = store.path_for(conv_id)
    assert summary.parent == json_path.parent
    assert summary.suffix == ".md"
    assert summary.stem == json_path.stem + ".summary"


def test_atomic_write_summary(store):
    conv_id = store.create()
    store.write_summary(conv_id, "## Decisions\n- X locked")
    summary = store.summary_path_for(conv_id)
    assert summary.exists()
    assert "X locked" in summary.read_text()


def test_idle_since_last_event(store):
    conv_id = store.create()
    path = store.path_for(conv_id)
    # Append a user event with a known timestamp
    with path.open("a") as f:
        f.write('{"type":"user","content":"hi","ts":"2026-04-26T12:00:00Z"}\n')
    # Read idle: should compute from last event ts
    idle_seconds = store.idle_seconds_since_last_event(
        conv_id,
        now=datetime(2026, 4, 27, 12, 0, 0, tzinfo=timezone.utc),
    )
    assert idle_seconds == 86400  # exactly 24h
