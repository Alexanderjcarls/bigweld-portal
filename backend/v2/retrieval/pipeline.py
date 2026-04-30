"""Top-level GraphRAG pre-retrieval pipeline."""

from __future__ import annotations

from typing import Any

from backend.v2.retrieval.cross_conv import nearest_summaries
from backend.v2.retrieval.embed import embed_query
from backend.v2.retrieval.entity_search import nearest_entities
from backend.v2.retrieval.expansion import expand_neighbors
from backend.v2.retrieval.heuristic_gate import should_skip_retrieval
from backend.v2.retrieval.render import render_retrieved_context


async def run_pre_retrieval(
    user_msg: str,
    last_assistant_msg: str | None,
    mcp_client: Any,
    pg_pool: Any,
) -> str:
    """Return a rendered <retrieved_context> block, or an empty string."""

    if should_skip_retrieval(user_msg):
        return ""

    query = user_msg if not last_assistant_msg else f"{last_assistant_msg}\n\n{user_msg}"
    embedding = await embed_query(query)

    # MCP server must be entered as an async context manager before
    # direct_call_tool can be invoked. The deps.mcp_client is a fresh instance
    # per turn (separate from the agent's toolset), so we manage its lifecycle
    # here.
    async with mcp_client:
        entities = await nearest_entities(mcp_client, embedding, query_text=query)
        if not entities:
            summaries = await nearest_summaries(pg_pool, embedding)
            return render_retrieved_context([], [], summaries)

        expansion = await expand_neighbors(mcp_client, entities)
    summaries = await nearest_summaries(pg_pool, embedding)
    return render_retrieved_context(entities, expansion, summaries)
