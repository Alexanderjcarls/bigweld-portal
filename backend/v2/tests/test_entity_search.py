from unittest.mock import AsyncMock

import pytest

from backend.v2.retrieval.entity_search import nearest_entities


@pytest.mark.asyncio
async def test_nearest_entities_filters_by_cosine_floor():
    mcp_client = AsyncMock()
    mcp_client.direct_call_tool.return_value = {
        "results": [
            {"slug": "cap-1", "label": "Capability", "name": "Cap 1", "score": 0.92},
            {"slug": "func-2", "label": "Functionality", "name": "Func 2", "score": 0.78},
            {"slug": "func-3", "label": "Functionality", "name": "Func 3", "score": 0.65},
            {"slug": "cap-4", "label": "Capability", "name": "Cap 4", "score": 0.71},
        ]
    }
    embedding = [0.1] * 2560

    result = await nearest_entities(mcp_client, embedding, top_k=10, cosine_floor=0.70)

    slugs = [r["slug"] for r in result]
    assert slugs == ["cap-1", "func-2", "cap-4"]


@pytest.mark.asyncio
async def test_nearest_entities_caps_to_top_k():
    mcp_client = AsyncMock()
    mcp_client.direct_call_tool.return_value = {
        "results": [
            {
                "slug": f"cap-{i}",
                "label": "Capability",
                "name": f"Cap {i}",
                "score": 0.9 - i * 0.01,
            }
            for i in range(15)
        ]
    }
    embedding = [0.1] * 2560

    result = await nearest_entities(mcp_client, embedding, top_k=5, cosine_floor=0.70)

    assert len(result) == 5


@pytest.mark.asyncio
async def test_nearest_entities_can_use_query_text_for_current_mcp_signature():
    mcp_client = AsyncMock()
    mcp_client.direct_call_tool.return_value = {
        "results": [{"slug": "cap-1", "label": "Capability", "name": "Cap 1", "score": 0.92}]
    }

    await nearest_entities(mcp_client, [0.1] * 2560, query_text="case routing")

    assert mcp_client.direct_call_tool.call_args.args[0] == "nearest_nodes"
    assert mcp_client.direct_call_tool.call_args.args[1]["query_text"] == "case routing"
    assert mcp_client.direct_call_tool.call_args.args[1]["k"] == 5
