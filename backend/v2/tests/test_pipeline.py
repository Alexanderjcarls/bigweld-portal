from unittest.mock import AsyncMock, patch

import pytest

from backend.v2.retrieval.pipeline import run_pre_retrieval


@pytest.mark.asyncio
async def test_run_pre_retrieval_skips_meta_message():
    block = await run_pre_retrieval("ok", None, AsyncMock(), AsyncMock())

    assert block == ""


@pytest.mark.asyncio
async def test_run_pre_retrieval_uses_last_assistant_msg_in_query():
    mcp_client = AsyncMock()
    pg_pool = AsyncMock()

    with (
        patch("backend.v2.retrieval.pipeline.embed_query", AsyncMock(return_value=[0.1] * 2560))
        as embed,
        patch(
            "backend.v2.retrieval.pipeline.nearest_entities",
            AsyncMock(
                return_value=[
                    {
                        "slug": "case-reopen",
                        "label": "Capability",
                        "name": "Case Reopen",
                        "score": 0.9,
                    }
                ]
            ),
        ) as nearest,
        patch("backend.v2.retrieval.pipeline.expand_neighbors", AsyncMock(return_value=[])),
        patch("backend.v2.retrieval.pipeline.nearest_summaries", AsyncMock(return_value=[])),
    ):
        block = await run_pre_retrieval(
            "What about case reopen?",
            "We were discussing SFDC routing.",
            mcp_client,
            pg_pool,
        )

    query = "We were discussing SFDC routing.\n\nWhat about case reopen?"
    embed.assert_awaited_once_with(query)
    nearest.assert_awaited_once_with(mcp_client, [0.1] * 2560, query_text=query)
    assert "<retrieved_context>" in block
