"""Pytest fixtures for backend tests."""
import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
