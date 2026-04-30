import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from backend.v2.api import artifacts as artifacts_api
from backend.v2.main import app


async def _seed_conversation(pg_pool, conv_id: uuid.UUID) -> None:
    async with pg_pool.acquire() as conn:
        await conn.execute("DELETE FROM bigweld_v2.artifacts WHERE conv_id = $1", conv_id)
        await conn.execute("DELETE FROM bigweld_v2.conversations WHERE id = $1", conv_id)
        await conn.execute("INSERT INTO bigweld_v2.conversations (id) VALUES ($1)", conv_id)


async def _delete_conversation(pg_pool, conv_id: uuid.UUID) -> None:
    async with pg_pool.acquire() as conn:
        await conn.execute("DELETE FROM bigweld_v2.artifacts WHERE conv_id = $1", conv_id)
        await conn.execute("DELETE FROM bigweld_v2.conversations WHERE id = $1", conv_id)


@pytest.mark.asyncio(loop_scope="session")
async def test_artifact_crud_and_section_patch_endpoints(pg_pool, monkeypatch):
    conv_id = uuid.uuid4()
    await _seed_conversation(pg_pool, conv_id)
    monkeypatch.setattr(artifacts_api, "get_pool", lambda: pg_pool)

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            created = await client.post(
                "/api/artifacts",
                json={
                    "conv_id": str(conv_id),
                    "type": "markdown",
                    "title": "Migration note",
                    "source": "bigweld",
                    "body": "# Migration note\n\n## Scope\nOld scope.\n\n## Risks\nNone.\n",
                },
            )

            assert created.status_code == 201
            artifact = created.json()
            artifact_id = artifact["id"]
            assert artifact["current_version"] == 1
            assert artifact["body"].startswith("# Migration note")

            listed = await client.get(f"/api/artifacts?conv_id={conv_id}")
            assert listed.status_code == 200
            assert [item["id"] for item in listed.json()["artifacts"]] == [artifact_id]

            patched = await client.patch(
                f"/api/artifacts/{artifact_id}",
                json={"section_id": "scope", "new_content": "New scope."},
            )
            assert patched.status_code == 200
            patched_body = patched.json()
            assert patched_body["current_version"] == 2
            assert "## Scope\nNew scope.\n\n## Risks" in patched_body["body"]
            assert "-Old scope." in patched_body["diff_summary"]
            assert "+New scope." in patched_body["diff_summary"]

            current = await client.get(f"/api/artifacts/{artifact_id}")
            assert current.status_code == 200
            assert current.json()["version"] == 2
            assert "New scope." in current.json()["body"]

            version_1 = await client.get(f"/api/artifacts/{artifact_id}/versions/1")
            assert version_1.status_code == 200
            assert version_1.json()["version"] == 1
            assert "Old scope." in version_1.json()["body"]

            deleted = await client.delete(f"/api/artifacts/{artifact_id}")
            assert deleted.status_code == 200
            assert deleted.json() == {"ok": True, "id": artifact_id}

            missing_after_delete = await client.get(f"/api/artifacts/{artifact_id}")
            assert missing_after_delete.status_code == 404
    finally:
        await _delete_conversation(pg_pool, conv_id)


@pytest.mark.asyncio(loop_scope="session")
async def test_artifact_list_requires_conv_unless_global(pg_pool, monkeypatch):
    conv_a = uuid.uuid4()
    conv_b = uuid.uuid4()
    await _seed_conversation(pg_pool, conv_a)
    await _seed_conversation(pg_pool, conv_b)
    monkeypatch.setattr(artifacts_api, "get_pool", lambda: pg_pool)

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            missing_scope = await client.get("/api/artifacts")
            assert missing_scope.status_code == 422

            created_ids = []
            for conv_id, title in ((conv_a, "A"), (conv_b, "B")):
                response = await client.post(
                    "/api/artifacts",
                    json={
                        "conv_id": str(conv_id),
                        "type": "markdown",
                        "title": title,
                        "source": "bigweld",
                        "body": f"# {title}\n",
                    },
                )
                assert response.status_code == 201
                created_ids.append(response.json()["id"])

            scoped = await client.get(f"/api/artifacts?conv_id={conv_a}")
            assert scoped.status_code == 200
            assert [item["id"] for item in scoped.json()["artifacts"]] == [created_ids[0]]

            global_list = await client.get("/api/artifacts?global=true")
            assert global_list.status_code == 200
            global_ids = {item["id"] for item in global_list.json()["artifacts"]}
            assert set(created_ids) <= global_ids
    finally:
        await _delete_conversation(pg_pool, conv_a)
        await _delete_conversation(pg_pool, conv_b)


@pytest.mark.asyncio(loop_scope="session")
async def test_artifact_create_requires_body_or_files(pg_pool, monkeypatch):
    conv_id = uuid.uuid4()
    await _seed_conversation(pg_pool, conv_id)
    monkeypatch.setattr(artifacts_api, "get_pool", lambda: pg_pool)

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/artifacts",
                json={
                    "conv_id": str(conv_id),
                    "type": "markdown",
                    "title": "Empty",
                    "source": "bigweld",
                },
            )
        assert response.status_code == 422
    finally:
        await _delete_conversation(pg_pool, conv_id)
