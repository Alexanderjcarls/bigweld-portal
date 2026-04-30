import pytest


@pytest.mark.asyncio(loop_scope="session")
async def test_bigweld_v2_schema_exists(pg_pool):
    async with pg_pool.acquire() as conn:
        result = await conn.fetchval(
            "SELECT 1 FROM information_schema.schemata WHERE schema_name = 'bigweld_v2'"
        )
    assert result == 1


@pytest.mark.asyncio(loop_scope="session")
async def test_conversations_table_shape(pg_pool):
    async with pg_pool.acquire() as conn:
        cols = await conn.fetch(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_schema='bigweld_v2' AND table_name='conversations' "
            "ORDER BY ordinal_position"
        )
    names = [c["column_name"] for c in cols]
    assert names == ["id", "title", "started_at", "last_active_at", "archived"]


@pytest.mark.asyncio(loop_scope="session")
async def test_messages_table_shape(pg_pool):
    async with pg_pool.acquire() as conn:
        cols = await conn.fetch(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema='bigweld_v2' AND table_name='messages' "
            "ORDER BY ordinal_position"
        )
    names = [c["column_name"] for c in cols]
    assert names == [
        "id",
        "conv_id",
        "turn_idx",
        "role",
        "content",
        "raw_message",
        "token_count",
        "ts",
    ]


@pytest.mark.asyncio(loop_scope="session")
async def test_compacted_summaries_table_shape(pg_pool):
    async with pg_pool.acquire() as conn:
        cols = await conn.fetch(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema='bigweld_v2' AND table_name='compacted_summaries' "
            "ORDER BY ordinal_position"
        )
    names = [c["column_name"] for c in cols]
    assert names == [
        "id",
        "conv_id",
        "range_start_idx",
        "range_end_idx",
        "summary",
        "embedding",
        "ts",
    ]


@pytest.mark.asyncio(loop_scope="session")
async def test_artifacts_table_shape(pg_pool):
    async with pg_pool.acquire() as conn:
        cols = await conn.fetch(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema='bigweld_v2' AND table_name='artifacts' "
            "ORDER BY ordinal_position"
        )
    names = [c["column_name"] for c in cols]
    assert "id" in names and "type" in names and "title" in names and "current_version" in names
