import json
from datetime import datetime, timedelta, timezone
from typing import Callable

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from backend import auth


@pytest.fixture
def cf_access_token_factory(monkeypatch, use_real_cf_access_decode) -> Callable[..., str]:
    _ = use_real_cf_access_decode
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk = json.loads(RSAAlgorithm.to_jwk(private_key.public_key()))
    public_jwk.update({"kid": "test-kid", "alg": "RS256", "use": "sig"})

    monkeypatch.setattr(auth, "_JWKS_CACHE", None)
    monkeypatch.setattr(auth, "_fetch_cf_access_jwks", lambda: {"keys": [public_jwk]})

    def make_token(
        *,
        email: str = "alexanderjcarlson@gmail.com",
        aud: str = auth.CF_ACCESS_AUD,
        signing_key=private_key,
    ) -> str:
        now = datetime.now(timezone.utc)
        return jwt.encode(
            {
                "iss": auth.CF_ACCESS_ISSUER,
                "aud": aud,
                "email": email,
                "iat": now,
                "exp": now + timedelta(minutes=5),
            },
            signing_key,
            algorithm="RS256",
            headers={"kid": "test-kid"},
        )

    return make_token


async def test_health_does_not_require_auth(client):
    r = await client.get("/health")
    assert r.status_code == 200


async def test_protected_endpoint_rejects_missing_jwt(client):
    r = await client.get("/api/conversations")
    assert r.status_code == 401


async def test_protected_endpoint_accepts_valid_jwt(client, cf_access_token_factory):
    r = await client.get(
        "/api/conversations",
        headers={"Cf-Access-Jwt-Assertion": cf_access_token_factory()},
    )
    assert r.status_code == 200


async def test_protected_endpoint_rejects_invalid_signature(client, cf_access_token_factory):
    wrong_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    r = await client.get(
        "/api/conversations",
        headers={"Cf-Access-Jwt-Assertion": cf_access_token_factory(signing_key=wrong_key)},
    )
    assert r.status_code == 401


async def test_protected_endpoint_rejects_wrong_audience(client, cf_access_token_factory):
    r = await client.get(
        "/api/conversations",
        headers={"Cf-Access-Jwt-Assertion": cf_access_token_factory(aud="wrong-audience")},
    )
    assert r.status_code == 401


async def test_protected_endpoint_allows_email_case_mismatch(client, cf_access_token_factory):
    r = await client.get(
        "/api/conversations",
        headers={
            "Cf-Access-Jwt-Assertion": cf_access_token_factory(
                email="AlexanderJCarlson@gmail.com",
            ),
        },
    )
    assert r.status_code == 200
