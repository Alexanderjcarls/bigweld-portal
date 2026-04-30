"""Entity-only pre-retrieval over Capability and Functionality nodes."""

from __future__ import annotations

import json
from typing import Any


DEFAULT_TOP_K = 5
DEFAULT_COSINE_FLOOR = 0.70
ENTITY_LABELS = ("Capability", "Functionality")


async def nearest_entities(
    mcp_client: Any,
    embedding: list[float],
    top_k: int = DEFAULT_TOP_K,
    cosine_floor: float = DEFAULT_COSINE_FLOOR,
    query_text: str | None = None,
) -> list[dict[str, Any]]:
    """Return top-K entities above the cosine floor.

    The Phase 2 retrieval spec calls `nearest_nodes` with a precomputed
    embedding. The current bigweld-mcp server still accepts query_text and
    embeds internally, so callers can pass `query_text` to use that signature.
    """

    merged: list[dict[str, Any]] = []
    for label in ENTITY_LABELS:
        merged.extend(await _nearest_for_label(mcp_client, embedding, label, top_k, query_text))

    by_identity: dict[tuple[str, str], dict[str, Any]] = {}
    for result in merged:
        score = float(result.get("score") or 0)
        if score < cosine_floor:
            continue
        label = result.get("label") or result.get("type") or ""
        slug = result.get("slug") or result.get("id") or ""
        if not slug:
            continue
        result["score"] = score
        identity = (str(label), str(slug))
        current = by_identity.get(identity)
        if current is None or score > current["score"]:
            by_identity[identity] = result

    ranked = list(by_identity.values())
    ranked.sort(key=lambda r: r["score"], reverse=True)
    return ranked[:top_k]


async def _nearest_for_label(
    mcp_client: Any,
    embedding: list[float],
    label: str,
    top_k: int,
    query_text: str | None,
) -> list[dict[str, Any]]:
    payload = {"label": label, "embedding": embedding, "top_k": top_k}
    if query_text is not None:
        payload = {"label": label, "query_text": query_text, "k": top_k}

    # Use direct_call_tool for external (non-agent-managed) MCP calls;
    # call_tool requires RunContext + ToolsetTool wiring that's only available
    # inside an Agent run loop.
    response = await mcp_client.direct_call_tool("nearest_nodes", payload)
    results = _extract_payload(response, preferred_key="results")
    normalized: list[dict[str, Any]] = []
    for item in results:
        if not isinstance(item, dict) or "error" in item:
            continue
        item.setdefault("label", label)
        normalized.append(item)
    return normalized


def _extract_payload(response: Any, preferred_key: str | None = None) -> list[Any]:
    if isinstance(response, dict):
        if preferred_key and preferred_key in response:
            value = response[preferred_key]
        elif "result" in response:
            value = response["result"]
        else:
            value = response
        return value if isinstance(value, list) else [value]

    if isinstance(response, list):
        return response

    content = getattr(response, "content", None)
    if content is not None:
        values: list[Any] = []
        for part in content:
            text = getattr(part, "text", None)
            if text is None:
                continue
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, list):
                values.extend(parsed)
            else:
                values.append(parsed)
        return values

    return []
