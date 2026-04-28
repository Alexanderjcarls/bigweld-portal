"""Cloudflare Access JWT validation for the single-user portal."""
import json
import time
from typing import Any

import httpx
import jwt
from fastapi import Header, HTTPException, status
from jwt import PyJWTError

from backend.core.config import (
    ALLOWED_EMAIL,
    CF_ACCESS_AUD,
    CF_ACCESS_CERTS_TTL_S,
    CF_ACCESS_CERTS_URL,
    CF_ACCESS_ISSUER,
)

_JWKS_CACHE: tuple[float, dict[str, Any]] | None = None


def _fetch_cf_access_jwks() -> dict[str, Any]:
    global _JWKS_CACHE
    now = time.time()
    if _JWKS_CACHE is not None:
        cached_at, cached = _JWKS_CACHE
        if now - cached_at < CF_ACCESS_CERTS_TTL_S:
            return cached

    try:
        response = httpx.get(CF_ACCESS_CERTS_URL, timeout=5.0)
        response.raise_for_status()
        jwks = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CF Access certificate fetch failed",
        ) from exc

    if not isinstance(jwks, dict) or not isinstance(jwks.get("keys"), list):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CF Access certificate response invalid",
        )
    _JWKS_CACHE = (now, jwks)
    return jwks


def decode_cf_access_jwt(token: str) -> dict[str, Any]:
    try:
        header = jwt.get_unverified_header(token)
    except PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="CF Access JWT header invalid",
        ) from exc

    kid = header.get("kid")
    if not isinstance(kid, str) or not kid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="CF Access JWT missing key id",
        )

    jwks = _fetch_cf_access_jwks()
    signing_key = None
    for key in jwks["keys"]:
        if isinstance(key, dict) and key.get("kid") == kid:
            signing_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
            break
    if signing_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="CF Access signing key not found",
        )

    try:
        claims = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=CF_ACCESS_AUD,
            issuer=CF_ACCESS_ISSUER,
        )
    except PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="CF Access JWT invalid",
        ) from exc
    if not isinstance(claims, dict):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="CF Access JWT invalid",
        )
    return claims


async def require_cf_access_email(
    cf_access_jwt_assertion: str | None = Header(default=None),
) -> str:
    if not cf_access_jwt_assertion:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="CF Access JWT missing",
        )
    claims = decode_cf_access_jwt(cf_access_jwt_assertion)
    email = claims.get("email")
    if not isinstance(email, str) or email.lower() != ALLOWED_EMAIL.lower():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="CF Access email not authorized",
        )
    return email
