# pylint: disable=duplicate-code
"""API routes for user API keys."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import get_current_user
from src.database.models.auth import UserApiKey
from src.database.models.user import User
from src.database.session import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])
_CURRENT_USER_DEPENDENCY = Depends(get_current_user)
_DB_DEPENDENCY = Depends(get_db)


@router.get("/api-keys")
async def list_user_api_keys(
    user: User = _CURRENT_USER_DEPENDENCY,
    db: AsyncSession = _DB_DEPENDENCY,
) -> list[dict[str, str | int | list[str] | None]]:
    """Return the caller's API keys, including revoked keys."""
    keys = await db.scalars(
        select(UserApiKey)
        .where(
            UserApiKey.user_id == user.id,
            UserApiKey.revoked_at.is_(None),
        )
        .order_by(UserApiKey.created_at.desc())
    )
    return [
        {
            "id": str(api_key.id),
            "name": api_key.name,
            "key_prefix": api_key.key_prefix,
            "scopes": api_key.scopes,
            "created_at": api_key.created_at,
            "revoked_at": api_key.revoked_at,
        }
        for api_key in keys
    ]
