"""Embedding client for Bigweld DA v2 retrieval and compaction."""

import httpx

from backend.v2.config import settings


EMBEDDING_MODEL = "Qwen/Qwen3-Embedding-4B"
EMBEDDING_DIM = 2560


async def embed_query(text: str) -> list[float]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{settings.EMBEDDING_URL.rstrip('/')}/embeddings",
            json={"model": EMBEDDING_MODEL, "input": text},
        )
    response.raise_for_status()
    embedding = response.json()["data"][0]["embedding"]
    if len(embedding) != EMBEDDING_DIM:
        raise RuntimeError(f"embedding dimension mismatch: expected {EMBEDDING_DIM}")
    return [float(value) for value in embedding]
