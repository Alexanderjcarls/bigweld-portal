"""DAO helpers for Bigweld DA v2 artifacts and version history."""

from __future__ import annotations

import base64
import difflib
import json
import re
import uuid
from typing import Any

import asyncpg


class ConversationNotFound(ValueError):
    pass


class ArtifactNotFound(ValueError):
    pass


class ArtifactArchived(ValueError):
    pass


class SectionNotFound(ValueError):
    pass


def _row_to_payload(row: Any) -> dict[str, Any]:
    payload = dict(row)
    blob = payload.pop("body_blob", None)
    if blob is None:
        return payload

    blob_bytes = bytes(blob)
    try:
        payload["files"] = json.loads(blob_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        payload["body_blob_base64"] = base64.b64encode(blob_bytes).decode("ascii")
    return payload


def _encode_files(files: Any | None) -> bytes | None:
    if files is None:
        return None
    return json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _slugify_heading(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or value.lower()


def _replace_marked_section(body: str, section_id: str, new_content: str) -> str | None:
    marker_id = re.escape(section_id)
    pattern = re.compile(
        rf"(<!--\s*section:{marker_id}\s*-->)(.*?)(<!--\s*/section:{marker_id}\s*-->)",
        flags=re.DOTALL,
    )
    match = pattern.search(body)
    if match is None:
        return None
    content = new_content.strip("\n")
    replacement = f"{match.group(1)}\n{content}\n{match.group(3)}"
    return body[: match.start()] + replacement + body[match.end() :]


def _heading_matches(line: str, section_id: str) -> tuple[bool, int]:
    match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
    if match is None:
        return False, 0

    heading_text = match.group(2).strip()
    explicit_id = re.search(r"\s*\{#([A-Za-z0-9_.:-]+)\}\s*$", heading_text)
    clean_heading = re.sub(r"\s*\{#[^}]+\}\s*$", "", heading_text).strip()
    candidates = {clean_heading, _slugify_heading(clean_heading)}
    if explicit_id is not None:
        candidates.add(explicit_id.group(1))
    return section_id in candidates, len(match.group(1))


def _replace_heading_section(body: str, section_id: str, new_content: str) -> str | None:
    lines = body.splitlines(keepends=True)
    for index, line in enumerate(lines):
        matches, level = _heading_matches(line.rstrip("\n"), section_id)
        if not matches:
            continue

        start = index + 1
        end = len(lines)
        for next_index in range(start, len(lines)):
            heading_match = re.match(r"^(#{1,6})\s+", lines[next_index])
            if heading_match and len(heading_match.group(1)) <= level:
                end = next_index
                break

        replacement = new_content.strip("\n")
        if replacement:
            replacement += "\n"
        if end < len(lines):
            replacement += "\n"
        return "".join(lines[:start]) + replacement + "".join(lines[end:])
    return None


def replace_artifact_section(body: str, section_id: str, new_content: str) -> str:
    """Replace a named artifact section using explicit markers or markdown headings."""
    if section_id in {"body", "root", "__root__"}:
        return new_content

    marked = _replace_marked_section(body, section_id, new_content)
    if marked is not None:
        return marked

    heading = _replace_heading_section(body, section_id, new_content)
    if heading is not None:
        return heading

    raise SectionNotFound(f"section not found: {section_id}")


def _build_diff_summary(
    old_body: str,
    new_body: str,
    *,
    old_version: int,
    new_version: int,
) -> str:
    return "\n".join(
        difflib.unified_diff(
            old_body.splitlines(),
            new_body.splitlines(),
            fromfile=f"artifact@v{old_version}",
            tofile=f"artifact@v{new_version}",
            lineterm="",
        )
    )


async def create_artifact(
    pg_pool: asyncpg.Pool,
    *,
    conv_id: uuid.UUID,
    artifact_type: str,
    title: str,
    source: str,
    body: str | None = None,
    files: Any | None = None,
) -> dict[str, Any]:
    artifact_id = uuid.uuid4()
    body_blob = _encode_files(files)

    async with pg_pool.acquire() as conn:
        async with conn.transaction():
            conversation_exists = await conn.fetchval(
                "SELECT 1 FROM bigweld_v2.conversations WHERE id = $1",
                conv_id,
            )
            if not conversation_exists:
                raise ConversationNotFound(f"conversation not found: {conv_id}")

            artifact = await conn.fetchrow(
                """
                INSERT INTO bigweld_v2.artifacts
                    (id, conv_id, type, title, source)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id, conv_id, type, title, source, current_version,
                    archived_at, created_at, updated_at
                """,
                artifact_id,
                conv_id,
                artifact_type,
                title,
                source,
            )
            version = await conn.fetchrow(
                """
                INSERT INTO bigweld_v2.artifact_versions
                    (artifact_id, version, body, body_blob, diff_summary)
                VALUES ($1, 1, $2, $3, $4)
                RETURNING version, body, body_blob, diff_summary,
                    created_at AS version_created_at
                """,
                artifact_id,
                body,
                body_blob,
                "created",
            )

    return {**_row_to_payload(artifact), **_row_to_payload(version)}


async def list_artifacts(
    pg_pool: asyncpg.Pool,
    *,
    conv_id: uuid.UUID | None = None,
    global_library: bool = False,
) -> list[dict[str, Any]]:
    where = ["a.archived_at IS NULL"]
    args: list[Any] = []
    if not global_library:
        if conv_id is None:
            raise ValueError("conv_id is required unless global_library=True")
        args.append(conv_id)
        where.append(f"a.conv_id = ${len(args)}")

    query = f"""
        SELECT a.id, a.conv_id, a.type, a.title, a.source, a.current_version,
            a.archived_at, a.created_at, a.updated_at, v.version, v.body,
            v.body_blob, v.diff_summary, v.created_at AS version_created_at
        FROM bigweld_v2.artifacts a
        JOIN bigweld_v2.artifact_versions v
            ON v.artifact_id = a.id AND v.version = a.current_version
        WHERE {' AND '.join(where)}
        ORDER BY a.updated_at DESC, a.created_at DESC
    """
    async with pg_pool.acquire() as conn:
        rows = await conn.fetch(query, *args)
    return [_row_to_payload(row) for row in rows]


async def get_artifact(pg_pool: asyncpg.Pool, artifact_id: uuid.UUID) -> dict[str, Any]:
    async with pg_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT a.id, a.conv_id, a.type, a.title, a.source, a.current_version,
                a.archived_at, a.created_at, a.updated_at, v.version, v.body,
                v.body_blob, v.diff_summary, v.created_at AS version_created_at
            FROM bigweld_v2.artifacts a
            JOIN bigweld_v2.artifact_versions v
                ON v.artifact_id = a.id AND v.version = a.current_version
            WHERE a.id = $1 AND a.archived_at IS NULL
            """,
            artifact_id,
        )
    if row is None:
        raise ArtifactNotFound(f"artifact not found: {artifact_id}")
    return _row_to_payload(row)


async def get_artifact_version(
    pg_pool: asyncpg.Pool,
    artifact_id: uuid.UUID,
    version: int,
) -> dict[str, Any]:
    async with pg_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT a.id, a.conv_id, a.type, a.title, a.source, a.current_version,
                a.archived_at, a.created_at, a.updated_at, v.version, v.body,
                v.body_blob, v.diff_summary, v.created_at AS version_created_at
            FROM bigweld_v2.artifacts a
            JOIN bigweld_v2.artifact_versions v
                ON v.artifact_id = a.id AND v.version = $2
            WHERE a.id = $1 AND a.archived_at IS NULL
            """,
            artifact_id,
            version,
        )
    if row is None:
        raise ArtifactNotFound(f"artifact version not found: {artifact_id}@{version}")
    return _row_to_payload(row)


async def patch_artifact_section(
    pg_pool: asyncpg.Pool,
    *,
    artifact_id: uuid.UUID,
    section_id: str,
    new_content: str,
) -> dict[str, Any]:
    async with pg_pool.acquire() as conn:
        async with conn.transaction():
            artifact = await conn.fetchrow(
                """
                SELECT id, conv_id, type, title, source, current_version,
                    archived_at, created_at, updated_at
                FROM bigweld_v2.artifacts
                WHERE id = $1
                FOR UPDATE
                """,
                artifact_id,
            )
            if artifact is None:
                raise ArtifactNotFound(f"artifact not found: {artifact_id}")
            if artifact["archived_at"] is not None:
                raise ArtifactArchived(f"artifact archived: {artifact_id}")

            current = await conn.fetchrow(
                """
                SELECT body, body_blob
                FROM bigweld_v2.artifact_versions
                WHERE artifact_id = $1 AND version = $2
                """,
                artifact_id,
                artifact["current_version"],
            )
            if current is None or current["body"] is None:
                raise SectionNotFound("section patch requires a text artifact body")

            old_body = current["body"]
            new_body = replace_artifact_section(old_body, section_id, new_content)
            new_version = int(artifact["current_version"]) + 1
            diff_summary = _build_diff_summary(
                old_body,
                new_body,
                old_version=int(artifact["current_version"]),
                new_version=new_version,
            )
            version = await conn.fetchrow(
                """
                INSERT INTO bigweld_v2.artifact_versions
                    (artifact_id, version, body, body_blob, diff_summary)
                VALUES ($1, $2, $3, NULL, $4)
                RETURNING version, body, body_blob, diff_summary,
                    created_at AS version_created_at
                """,
                artifact_id,
                new_version,
                new_body,
                diff_summary,
            )
            updated = await conn.fetchrow(
                """
                UPDATE bigweld_v2.artifacts
                SET current_version = $2, updated_at = now()
                WHERE id = $1
                RETURNING id, conv_id, type, title, source, current_version,
                    archived_at, created_at, updated_at
                """,
                artifact_id,
                new_version,
            )

    return {**_row_to_payload(updated), **_row_to_payload(version)}


async def archive_artifact(pg_pool: asyncpg.Pool, artifact_id: uuid.UUID) -> uuid.UUID:
    async with pg_pool.acquire() as conn:
        archived_id = await conn.fetchval(
            """
            UPDATE bigweld_v2.artifacts
            SET archived_at = now(), updated_at = now()
            WHERE id = $1 AND archived_at IS NULL
            RETURNING id
            """,
            artifact_id,
        )
    if archived_id is None:
        raise ArtifactNotFound(f"artifact not found: {artifact_id}")
    return archived_id
