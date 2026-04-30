"""Thin MCP Streamable-HTTP client for retrieval-side direct tool calls.

The agent's MCP integration is handled inside claude-agent-sdk via its
mcp_servers config. This client is for the OTHER MCP path: pre-retrieval
which calls bigweld-mcp tools directly (nearest_nodes, neighbors) to seed
the system prompt before the LLM is invoked.

Exposes the same `direct_call_tool(name, args) -> dict` surface that
Pydantic AI's MCPServerStreamableHTTP did, plus async-context-manager
lifecycle, so retrieval/pipeline.py works unchanged.
"""

from __future__ import annotations

import json
from typing import Any

from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client


class MCPStreamableHTTPClient:
    def __init__(self, url: str):
        self.url = url
        self._http_cm = None
        self._read = None
        self._write = None
        self._session_cm = None
        self._session: ClientSession | None = None

    async def __aenter__(self) -> "MCPStreamableHTTPClient":
        self._http_cm = streamablehttp_client(self.url)
        self._read, self._write, _ = await self._http_cm.__aenter__()
        self._session_cm = ClientSession(self._read, self._write)
        self._session = await self._session_cm.__aenter__()
        await self._session.initialize()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        try:
            if self._session_cm is not None:
                await self._session_cm.__aexit__(exc_type, exc, tb)
        finally:
            if self._http_cm is not None:
                await self._http_cm.__aexit__(exc_type, exc, tb)

    async def direct_call_tool(self, name: str, args: dict[str, Any]) -> Any:
        if self._session is None:
            raise RuntimeError("MCPStreamableHTTPClient must be entered before use")
        result = await self._session.call_tool(name, arguments=args)
        if getattr(result, "structuredContent", None):
            return result.structuredContent
        content = getattr(result, "content", None) or []
        if len(content) == 1 and hasattr(content[0], "text"):
            text = content[0].text
            try:
                return json.loads(text)
            except (json.JSONDecodeError, TypeError):
                return text
        return [c.model_dump() if hasattr(c, "model_dump") else c for c in content]
