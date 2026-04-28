"""Conversations endpoints: create, list, replay."""
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from backend.api import conversations
from backend.core.config import SUMMARIZE_IDLE_THRESHOLD_S
from backend.core.conversation_store import ConversationStore
from backend.core.subprocess_mgr import SubprocessManager
from backend.metrics import turn_total

MOCK_CLAUDE = os.path.join(os.path.dirname(__file__), "fixtures", "mock_claude.py")

AUTH = {"Cf-Access-Jwt-Assertion": "valid-test-jwt"}


@pytest.fixture(autouse=True)
def isolate_root(tmp_path, monkeypatch):
    monkeypatch.setenv("BIGWELD_PORTAL_ROOT", str(tmp_path))


async def test_create_conversation_returns_uuid(client):
    r = await client.post("/api/conversations", headers=AUTH)
    assert r.status_code == 200
    body = r.json()
    assert "conv_id" in body
    assert len(body["conv_id"]) == 36


async def test_create_conversation_triggers_lazy_summarize_on_idle(
    client,
    tmp_path,
    monkeypatch,
):
    store = ConversationStore(root=tmp_path / "conversations")
    old_conv_id = store.create()
    old_ts = datetime.now(timezone.utc) - timedelta(
        seconds=SUMMARIZE_IDLE_THRESHOLD_S + 60,
    )
    path = store.path_for(old_conv_id)
    with path.open("a") as f:
        f.write(json.dumps({
            "type": "user",
            "content": "abandoned work",
            "ts": old_ts.isoformat(),
        }) + "\n")
    os.utime(path, (old_ts.timestamp(), old_ts.timestamp()))
    summarize = MagicMock(return_value=None)
    monkeypatch.setattr("backend.api.conversations.summarize_conversation", summarize)

    r = await client.post("/api/conversations", headers=AUTH)
    assert r.status_code == 200
    new_conv_id = r.json()["conv_id"]
    await asyncio.sleep(0.05)

    summarized_ids = [call.args[1] for call in summarize.call_args_list]
    assert old_conv_id in summarized_ids
    assert new_conv_id not in summarized_ids


async def test_list_empty(client):
    r = await client.get("/api/conversations", headers=AUTH)
    assert r.status_code == 200
    assert r.json() == {"conversations": []}


async def test_list_after_create(client):
    await client.post("/api/conversations", headers=AUTH)
    await client.post("/api/conversations", headers=AUTH)
    r = await client.get("/api/conversations", headers=AUTH)
    body = r.json()
    assert len(body["conversations"]) == 2


async def test_get_by_id_returns_events(client):
    create = await client.post("/api/conversations", headers=AUTH)
    conv_id = create.json()["conv_id"]
    r = await client.get(f"/api/conversations/{conv_id}", headers=AUTH)
    assert r.status_code == 200
    body = r.json()
    assert "events" in body
    assert any(ev.get("type") == "meta" for ev in body["events"])


async def test_get_by_id_404_for_unknown(client):
    r = await client.get(
        "/api/conversations/00000000-0000-0000-0000-000000000000",
        headers=AUTH,
    )
    assert r.status_code == 404


async def test_turn_crash_streams_error_and_counts_error(client, monkeypatch):
    monkeypatch.setenv("MOCK_CLAUDE_MODE", "crash")
    mgr = SubprocessManager(
        claude_command=[sys.executable, MOCK_CLAUDE],
        per_turn_timeout_s=10,
    )
    monkeypatch.setattr(conversations, "_subprocess_mgr", mgr)
    before = turn_total.labels(status="error")._value.get()

    created = await client.post("/api/conversations", headers=AUTH)
    conv_id = created.json()["conv_id"]
    response = await client.post(
        f"/api/conversations/{conv_id}/turn",
        headers=AUTH,
        json={"message": "crash now"},
    )

    events = [json.loads(line) for line in response.text.splitlines() if line.strip()]
    assert response.status_code == 200
    assert events[-1] == {
        "type": "system",
        "subtype": "error",
        "is_error": True,
        "error": "subprocess exited rc=137 before result",
    }
    assert turn_total.labels(status="error")._value.get() == before + 1
