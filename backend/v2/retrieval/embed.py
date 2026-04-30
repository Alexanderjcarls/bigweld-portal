"""Embedding client for Bigweld DA v2 retrieval and compaction.

Matches the bigweld substrate's embedding path (DeepInfra Qwen3-Embedding-4B at
2560 dim) so embeddings produced here are searchable against the same vector
space as the graph entities. NAS-local embedding (`http://192.168.0.25:8002`)
was retired in the 2026-04-21 all-cloud cutover; this client now defaults to
DeepInfra and includes the API key as an Authorization header when available.
"""

import httpx

from backend.v2.config import settings


EMBEDDING_MODEL = "Qwen/Qwen3-Embedding-4B"
EMBEDDING_DIM = 2560


async def embed_query(text: str) -> list[float]:
    headers: dict[str, str] = {}
    if settings.DEEPINFRA_API_KEY:
        headers["Authorization"] = f"Bearer {settings.DEEPINFRA_API_KEY}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{settings.EMBEDDING_URL.rstrip('/')}/embeddings",
            json={"model": EMBEDDING_MODEL, "input": text},
            headers=headers,
        )
    response.raise_for_status()
    embedding = response.json()["data"][0]["embedding"]
    if len(embedding) != EMBEDDING_DIM:
        raise RuntimeError(f"embedding dimension mismatch: expected {EMBEDDING_DIM}")
    return [float(value) for value in embedding]
