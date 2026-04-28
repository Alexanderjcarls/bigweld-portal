"""Output and budget endpoint smoke tests."""
import pytest

from backend.core.conversation_store import ConversationStore

AUTH = {"Cf-Access-Authenticated-User-Email": "alexanderjcarlson@gmail.com"}


@pytest.fixture(autouse=True)
def isolate_root(tmp_path, monkeypatch):
    monkeypatch.setenv("BIGWELD_PORTAL_ROOT", str(tmp_path))


async def test_budget_without_conversation_returns_zero_context_window(client):
    r = await client.get("/api/budget", headers=AUTH)
    assert r.status_code == 200
    assert r.json() == {
        "context_window_pct": 0.0,
        "context_window_total": 1000000,
    }


async def test_budget_empty_conversation_returns_zero(client):
    created = await client.post("/api/conversations", headers=AUTH)
    conv_id = created.json()["conv_id"]

    r = await client.get(f"/api/budget?conv_id={conv_id}", headers=AUTH)

    assert r.status_code == 200
    assert r.json() == {
        "context_window_pct": 0.0,
        "context_window_total": 1000000,
    }


async def test_budget_uses_latest_synthetic_usage_event(client, tmp_path):
    store = ConversationStore(root=tmp_path / "conversations")
    conv_id = store.create()
    store.append_event(
        conv_id,
        {
            "type": "usage",
            "input_tokens": 900000,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
            "output_tokens": 1,
        },
    )
    store.append_event(
        conv_id,
        {
            "type": "usage",
            "input_tokens": 1000,
            "cache_creation_input_tokens": 1000,
            "cache_read_input_tokens": 3000,
            "output_tokens": 500,
        },
    )

    r = await client.get(f"/api/budget?conv_id={conv_id}", headers=AUTH)

    assert r.status_code == 200
    assert r.json() == {
        "context_window_pct": 0.5,
        "context_window_total": 1000000,
    }


async def test_budget_context_window_env_override(client, tmp_path, monkeypatch):
    monkeypatch.setenv("BIGWELD_PORTAL_CONTEXT_WINDOW", "10000")
    store = ConversationStore(root=tmp_path / "conversations")
    conv_id = store.create()
    store.append_event(
        conv_id,
        {
            "type": "usage",
            "input_tokens": 2000,
            "cache_creation_input_tokens": 1000,
            "cache_read_input_tokens": 2000,
            "output_tokens": 500,
        },
    )

    r = await client.get(f"/api/budget?conv_id={conv_id}", headers=AUTH)

    assert r.status_code == 200
    assert r.json() == {
        "context_window_pct": 50.0,
        "context_window_total": 10000,
    }


async def test_put_then_get_output_roundtrip(client, tmp_path):
    conv_id = "00000000-0000-0000-0000-000000000000"
    content = b"## artifact\nhello"

    put = await client.put(
        f"/api/output/{conv_id}/artifact.md",
        headers=AUTH,
        content=content,
    )
    target = tmp_path / "output" / conv_id / "artifact.md"
    assert put.status_code == 200
    assert put.json() == {
        "ok": True,
        "path": str(target.resolve()),
        "bytes": len(content),
    }

    get = await client.get(f"/api/output/{conv_id}/artifact.md", headers=AUTH)
    assert get.status_code == 200
    assert get.content == content


async def test_output_put_get_round_trip(client, tmp_path):
    conv_id = "test-conv-001"
    filename = "diagram.svg"
    content = b"<svg>hello</svg>"

    put = await client.put(
        f"/api/output/{conv_id}/{filename}",
        headers=AUTH,
        content=content,
    )
    target = tmp_path / "output" / conv_id / filename
    assert put.status_code == 200
    assert put.json() == {
        "ok": True,
        "path": str(target.resolve()),
        "bytes": len(content),
    }

    get = await client.get(f"/api/output/{conv_id}/{filename}", headers=AUTH)
    assert get.status_code == 200
    assert get.content == content


async def test_output_rejects_path_traversal(client):
    r = await client.put(
        "/api/output/%2E/artifact.md",
        headers=AUTH,
        content=b"x",
    )
    assert r.status_code == 400


async def test_output_rejects_dot_dot_filename(client):
    r = await client.put(
        "/api/output/test/%2E%2E",
        headers=AUTH,
        content=b"x",
    )
    assert r.status_code == 400


async def test_output_allows_substring_dot_dot(client):
    content = b"<svg>v1..2</svg>"

    put = await client.put(
        "/api/output/test/v1..2.svg",
        headers=AUTH,
        content=content,
    )
    assert put.status_code == 200

    get = await client.get("/api/output/test/v1..2.svg", headers=AUTH)
    assert get.status_code == 200
    assert get.content == content
