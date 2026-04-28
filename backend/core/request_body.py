"""Request body helpers with explicit size caps."""
from fastapi import HTTPException, Request, status


async def read_limited_body(request: Request, max_bytes: int) -> bytes:
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            declared = int(content_length)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid content-length",
            ) from None
        if declared > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="request body too large",
            )

    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="request body too large",
            )
    return bytes(body)
