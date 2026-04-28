"""Input upload endpoint tests."""
import pytest

AUTH = {"Cf-Access-Authenticated-User-Email": "alexanderjcarlson@gmail.com"}


@pytest.fixture(autouse=True)
def isolate_root(tmp_path, monkeypatch):
    monkeypatch.setenv("BIGWELD_PORTAL_ROOT", str(tmp_path))


async def test_upload_put_roundtrip(client, tmp_path):
    content = b"%PDF-1.7\n\x00\xffbinary"

    r = await client.put(
        "/api/upload/test-conv/doc.pdf",
        headers=AUTH,
        content=content,
    )

    target = tmp_path / "uploads" / "test-conv" / "doc.pdf"
    assert r.status_code == 200
    assert r.json() == {
        "ok": True,
        "path": str(target.resolve()),
        "bytes": len(content),
    }
    assert target.read_bytes() == content


async def test_upload_rejects_path_traversal(client):
    r = await client.put(
        "/api/upload/test/%2E%2E",
        headers=AUTH,
        content=b"x",
    )
    assert r.status_code == 400


async def test_upload_allows_substring_dot_dot(client, tmp_path):
    content = b"pdf-ish"

    r = await client.put(
        "/api/upload/test/v1..2.pdf",
        headers=AUTH,
        content=content,
    )

    target = tmp_path / "uploads" / "test" / "v1..2.pdf"
    assert r.status_code == 200
    assert r.json() == {
        "ok": True,
        "path": str(target.resolve()),
        "bytes": len(content),
    }
    assert target.read_bytes() == content


async def test_upload_empty_body_creates_file(client, tmp_path):
    r = await client.put(
        "/api/upload/test/empty.bin",
        headers=AUTH,
        content=b"",
    )

    target = tmp_path / "uploads" / "test" / "empty.bin"
    assert r.status_code == 200
    assert r.json() == {
        "ok": True,
        "path": str(target.resolve()),
        "bytes": 0,
    }
    assert target.exists()
    assert target.read_bytes() == b""


async def test_upload_requires_auth(client):
    r = await client.put(
        "/api/upload/test/doc.pdf",
        content=b"x",
    )
    assert r.status_code == 401
