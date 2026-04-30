import pytest
import respx
from httpx import Response

from backend.v2.retrieval.embed import embed_query


@pytest.mark.asyncio
async def test_embed_query_returns_2560_dim():
    fake_vec = [0.0] * 2560
    with respx.mock(base_url="http://192.168.0.25:8002/v1") as mock:
        mock.post("/embeddings").mock(
            return_value=Response(
                200,
                json={
                    "data": [{"embedding": fake_vec, "index": 0, "object": "embedding"}],
                    "model": "Qwen/Qwen3-Embedding-4B",
                    "object": "list",
                    "usage": {"prompt_tokens": 5, "total_tokens": 5},
                },
            )
        )
        result = await embed_query("explain case-reopen")

    assert len(result) == 2560
