"""Cloudflare Access header trust for the single-user portal."""
from fastapi import Header, HTTPException, status

from backend.core.config import ALLOWED_EMAIL


async def require_cf_access_email(
    cf_access_authenticated_user_email: str | None = Header(default=None),
) -> str:
    if cf_access_authenticated_user_email != ALLOWED_EMAIL:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="CF Access email not authorized",
        )
    return cf_access_authenticated_user_email
