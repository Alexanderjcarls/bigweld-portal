import os

import asyncpg
import pytest_asyncio


PG_URL = os.environ.get("BIGWELD_V2_TEST_PG_URL") or "postgresql:///aegis"


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def pg_pool():
    pool = await asyncpg.create_pool(PG_URL, min_size=1, max_size=4)
    yield pool
    await pool.close()
