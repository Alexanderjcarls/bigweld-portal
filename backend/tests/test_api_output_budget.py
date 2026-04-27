"""Output and budget endpoint smoke tests."""
import pytest

AUTH = {"Cf-Access-Authenticated-User-Email": "alexanderjcarlson@gmail.com"}


@pytest.fixture(autouse=True)
def isolate_root(tmp_path, monkeypatch):
    monkeypatch.setenv("BIGWELD_PORTAL_ROOT", str(tmp_path))


async def test_budget_stub_returns_zeroes(client):
    r = await client.get("/api/budget", headers=AUTH)
    assert r.status_code == 200
    assert r.json() == {
        "conversation_context_pct": 0.0,
        "max_5h_pct": 0.0,
        "max_7d_pct": 0.0,
    }


async def test_put_then_get_output_roundtrip(client):
    conv_id = "00000000-0000-0000-0000-000000000000"
    content = b"## artifact\nhello"

    put = await client.put(
        f"/api/output/{conv_id}/artifact.md",
        headers=AUTH,
        content=content,
    )
    assert put.status_code == 200
    assert put.json() == {"ok": True, "bytes": len(content)}

    get = await client.get(f"/api/output/{conv_id}/artifact.md", headers=AUTH)
    assert get.status_code == 200
    assert get.content == content


async def test_output_put_get_round_trip(client):
    conv_id = "test-conv-001"
    filename = "diagram.svg"
    content = b"<svg>hello</svg>"

    put = await client.put(
        f"/api/output/{conv_id}/{filename}",
        headers=AUTH,
        content=content,
    )
    assert put.status_code == 200
    assert put.json() == {"ok": True, "bytes": len(content)}

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
