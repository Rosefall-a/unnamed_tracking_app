from __future__ import annotations

import time
import secrets
import shutil
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import (
    SESSION_COOKIE,
    create_api_key,
    get_current_admin,
    get_current_user,
    hash_password,
    hash_token,
    validate_password,
    verify_password,
)
from src.core.config import settings
from src.database.models.auth import UserApiKey, UserSession
from src.database.models.user import User
from src.database.session import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])
_SESSION_SECONDS = 30 * 24 * 60 * 60


class LoginRequest(BaseModel):
    username_or_email: str = Field(min_length=1)
    password: str = Field(min_length=1)


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    scopes: list[str] = Field(default_factory=list)


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1)
    is_admin: bool = False

    @field_validator("password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return validate_password(value)


class UserProfileUpdateRequest(BaseModel):
    username: str | None = Field(default=None, min_length=1, max_length=100)
    email: str | None = Field(default=None, min_length=3, max_length=320)
    current_password: str = Field(min_length=1)
    new_password: str | None = Field(default=None, min_length=1)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str | None) -> str | None:
        return validate_password(value) if value is not None else None


@router.post("/login")
async def login(payload: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    identifier = payload.username_or_email.strip()
    user = await db.scalar(
        select(User).where((User.username == identifier) | (User.email == identifier.lower()))
    )
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

    session_token = secrets.token_urlsafe(32)
    db.add(
        UserSession(
            user_id=user.id,
            token_hash=hash_token(session_token),
            expires_at=int(time.time()) + _SESSION_SECONDS,
        )
    )
    await db.commit()
    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_token,
        max_age=_SESSION_SECONDS,
        httponly=True,
        samesite="lax",
        secure=settings.AUTH_COOKIE_SECURE,
    )
    return {"status": "logged_in", "user_id": str(user.id)}


@router.post("/logout")
async def logout(
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    del user
    response.delete_cookie(SESSION_COOKIE)
    return {"status": "logged_out"}


@router.get("/me")
async def current_user(user: User = Depends(get_current_user)) -> dict[str, str | bool]:
    return {"id": str(user.id), "username": user.username, "email": user.email, "is_admin": user.is_admin}


@router.patch("/me")
async def update_current_user(
    payload: UserProfileUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str | bool]:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect.")

    if payload.username is not None:
        user.username = payload.username.strip()
    if payload.email is not None:
        user.email = payload.email.strip().lower()
    if payload.new_password is not None:
        user.password_hash = hash_password(payload.new_password)

    if not user.username or not user.email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username and email are required.")

    try:
        await db.commit()
        await db.refresh(user)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username or email already exists.") from exc

    return {"id": str(user.id), "username": user.username, "email": user.email, "is_admin": user.is_admin}


@router.get("/users")
async def list_users(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, str | bool]]:
    del admin
    users = await db.scalars(select(User).order_by(User.username))
    return [
        {"id": str(user.id), "username": user.username, "email": user.email, "is_admin": user.is_admin}
        for user in users
    ]


@router.post("/api-keys")
async def create_user_api_key(
    payload: ApiKeyCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str | list[str]]:
    api_key, key_prefix, key_hash = create_api_key()
    db.add(UserApiKey(user_id=user.id, name=payload.name, key_prefix=key_prefix, key_hash=key_hash, scopes=payload.scopes))
    await db.commit()
    return {
        "api_key": api_key,
        "key_prefix": key_prefix,
        "name": payload.name,
        "scopes": payload.scopes,
        "warning": "Store this key now. It will not be shown again.",
    }


@router.delete("/api-keys/{key_id}")
async def revoke_user_api_key(
    key_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    api_key = await db.scalar(
        select(UserApiKey).where(UserApiKey.id == key_id, UserApiKey.user_id == user.id)
    )
    if api_key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found.")
    api_key.revoked_at = int(time.time())
    await db.commit()
    return {"status": "revoked", "key_id": str(key_id)}


@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreateRequest,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str | bool]:
    del admin
    username = payload.username.strip()
    email = payload.email.strip().lower()
    if not username or not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username and email are required.")

    user = User(
        username=username,
        email=email,
        password_hash=hash_password(payload.password),
        is_active=True,
        is_admin=payload.is_admin,
    )
    db.add(user)
    try:
        await db.commit()
        await db.refresh(user)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username or email already exists.") from exc

    return {"id": str(user.id), "username": user.username, "email": user.email, "is_admin": user.is_admin}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: UUID,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    user = await db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if user.username == settings.PRIMARY_USER_USERNAME or user.email == settings.PRIMARY_USER_EMAIL.lower():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The primary user cannot be deleted.")
    if user.id == admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot delete your own account.")

    await db.delete(user)
    await db.commit()
    shutil.rmtree(Path("/data/user") / str(user_id), ignore_errors=True)
    return {"status": "deleted", "user_id": str(user_id)}
