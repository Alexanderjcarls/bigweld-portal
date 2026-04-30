from unittest.mock import AsyncMock

import pytest

from backend.v2.retrieval.expansion import STRUCTURAL_EDGES, expand_neighbors


@pytest.mark.asyncio
async def test_expand_neighbors_uses_structural_allowlist():
    mcp_client = AsyncMock()
    mcp_client.call_tool.return_value = {
        "neighbors": [
            {
                "slug": "func-x",
                "label": "Functionality",
                "edge_type": "ENABLES",
                "confidence": "verified",
                "last_reviewed_at": "2026-04-29",
            },
        ]
    }

    seeds = [{"slug": "cap-1", "label": "Capability"}]
    result = await expand_neighbors(mcp_client, seeds, hop_limit=1, neighbor_cap=5)

    assert len(result) == 1
    call_args = mcp_client.call_tool.call_args
    assert call_args.args[0] == "get_neighbors"
    assert set(call_args.args[1]["edge_types"]) == set(STRUCTURAL_EDGES)


def test_structural_edges_excludes_mentions_and_relates_to():
    assert "MENTIONS" not in STRUCTURAL_EDGES
    assert "RELATES_TO" not in STRUCTURAL_EDGES
    assert "DOCUMENTS" not in STRUCTURAL_EDGES
    assert "CITED_BY" not in STRUCTURAL_EDGES


def test_structural_edges_includes_all_5():
    assert set(STRUCTURAL_EDGES) == {
        "ENABLES",
        "IMPLEMENTS",
        "COMPOSED_OF",
        "DEPENDS_ON",
        "MAPS_TO",
    }


@pytest.mark.asyncio
async def test_expand_neighbors_normalizes_current_mcp_shape_and_sorts_per_edge():
    mcp_client = AsyncMock()
    mcp_client.call_tool.return_value = [
        {
            "neighbor": {
                "slug": "func-old",
                "label": "Functionality",
                "name": "Old",
                "confidence": "verified",
                "last_reviewed_at": "2026-04-28",
            },
            "edge_type": "ENABLES",
        },
        {
            "neighbor": {
                "slug": "func-new",
                "label": "Functionality",
                "name": "New",
                "confidence": "verified",
                "last_reviewed_at": "2026-04-29",
            },
            "edge_type": "ENABLES",
        },
        {
            "neighbor": {
                "slug": "func-reviewed",
                "label": "Functionality",
                "name": "Reviewed",
                "confidence": "reviewed",
                "last_reviewed_at": "2026-04-30",
            },
            "edge_type": "ENABLES",
        },
    ]

    result = await expand_neighbors(
        mcp_client,
        [{"slug": "cap-1", "label": "Capability"}],
        neighbor_cap=2,
    )

    assert [item["slug"] for item in result] == ["func-new", "func-old"]
    assert all(item["from_slug"] == "cap-1" for item in result)
