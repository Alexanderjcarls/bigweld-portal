"""Pytest fixtures for backend tests."""
import pytest
from fastapi import HTTPException, status
from httpx import ASGITransport, AsyncClient

from backend import auth
from backend.main import app

REAL_DECODE_CF_ACCESS_JWT = auth.decode_cf_access_jwt


@pytest.fixture(autouse=True)
def stub_cf_access_jwt(monkeypatch) -> None:
    def fake_decode(token: str) -> dict:
        if token == "valid-test-jwt":
            return {"email": "AlexanderJCarlson@gmail.com"}
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="CF Access JWT invalid",
        )

    monkeypatch.setattr(auth, "decode_cf_access_jwt", fake_decode)


@pytest.fixture
def use_real_cf_access_decode(monkeypatch):
    monkeypatch.setattr(auth, "decode_cf_access_jwt", REAL_DECODE_CF_ACCESS_JWT)
    return REAL_DECODE_CF_ACCESS_JWT


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
