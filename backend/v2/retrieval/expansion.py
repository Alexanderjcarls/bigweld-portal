"""One-hop graph expansion on structural edges."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from backend.v2.retrieval.entity_search import _extract_payload


STRUCTURAL_EDGES = ["ENABLES", "IMPLEMENTS", "COMPOSED_OF", "DEPENDS_ON", "MAPS_TO"]
DEFAULT_HOP_LIMIT = 1
DEFAULT_NEIGHBOR_CAP = 5

_CONFIDENCE_RANK = {
    "verified": 3,
    "reviewed": 2,
    "extracted": 1,
}


async def expand_neighbors(
    mcp_client: Any,
    seeds: list[dict[str, Any]],
    hop_limit: int = DEFAULT_HOP_LIMIT,
    neighbor_cap: int = DEFAULT_NEIGHBOR_CAP,
) -> list[dict[str, Any]]:
    if hop_limit != 1:
        raise ValueError("pre-retrieval expansion currently supports only one hop")

    expanded: list[dict[str, Any]] = []
    for seed in seeds:
        response = await mcp_client.call_tool(
            "get_neighbors",
            {
                "slug": seed["slug"],
                "label": seed["label"],
                "edge_types": STRUCTURAL_EDGES,
            },
        )
        neighbors = [_normalize_neighbor(seed, item) for item in _extract_payload(response, "neighbors")]
        per_edge: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for neighbor in neighbors:
            edge_type = neighbor.get("edge_type")
            if edge_type in STRUCTURAL_EDGES:
                per_edge[edge_type].append(neighbor)

        for items in per_edge.values():
            items.sort(
                key=lambda item: (
                    _CONFIDENCE_RANK.get(str(item.get("confidence") or "").lower(), 0),
                    item.get("last_reviewed_at") or "",
                ),
                reverse=True,
            )
            expanded.extend(items[:neighbor_cap])

    return expanded


def _normalize_neighbor(seed: dict[str, Any], item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {}

    if isinstance(item.get("neighbor"), dict):
        normalized = dict(item["neighbor"])
        normalized["edge_type"] = item.get("edge_type")
    else:
        normalized = dict(item)

    normalized.setdefault("from_slug", seed.get("slug"))
    normalized.setdefault("from_label", seed.get("label"))
    return normalized
