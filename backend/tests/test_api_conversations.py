"""Conversations endpoints: create, list, replay."""
import pytest

AUTH = {"Cf-Access-Authenticated-User-Email": "alexanderjcarlson@gmail.com"}


@pytest.fixture(autouse=True)
def isolate_root(tmp_path, monkeypatch):
    monkeypatch.setenv("BIGWELD_PORTAL_ROOT", str(tmp_path))


async def test_create_conversation_returns_uuid(client):
    r = await client.post("/api/conversations", headers=AUTH)
    assert r.status_code == 200
    body = r.json()
    assert "conv_id" in body
    assert len(body["conv_id"]) == 36


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
