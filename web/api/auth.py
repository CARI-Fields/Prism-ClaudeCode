from __future__ import annotations

from fastapi import Header, HTTPException, status

from web.api.config import get_settings


def require_token(authorization: str | None = Header(default=None)) -> None:
    token = get_settings().api_token
    if not token:
        return  # auth disabled (no token configured) — dev only
    if authorization != f"Bearer {token}":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or missing token",
        )
