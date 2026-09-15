from __future__ import annotations

import asyncio
import secrets
import time
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import SESSION_COOKIE, get_current_admin, hash_password, hash_token, validate_password
from src.core.email import send_email
from src.database.models.app_integration_settings import AppIntegrationSettings
from src.database.models.auth import UserSession
from src.database.models.user import User
from src.database.models.user_invitation import UserInvitation
from src.database.session import get_db

router = APIRouter(prefix="/api/auth/invitations", tags=["auth"])
_INVITATION_SECONDS = 7 * 24 * 60 * 60
_SESSION_SECONDS = 30 * 24 * 60 * 60


class InvitationCreateRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    email: EmailStr
    is_admin: bool = False


class InvitationAcceptRequest(BaseModel):
    token: str = Field(min_length=1)
    password: str = Field(min_length=1)

    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_password(value)


def _public_app_origin(request: Request) -> str:
    origin = request.headers.get("origin", "").strip().rstrip("/")
    if origin:
        return origin
    forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",")[0].strip()
    forwarded_host = request.headers.get("x-forwarded-host", "").split(",")[0].strip()
    if forwarded_host:
        return f"{forwarded_proto or 'http'}://{forwarded_host}"
    return str(request.base_url).rstrip("/")


def _public_request_is_secure(request: Request) -> bool:
    forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",")[0].strip().lower()
    if forwarded_proto:
        return forwarded_proto == "https"
    origin = request.headers.get("origin", "").strip().lower()
    if origin:
        return origin.startswith("https://")
    return request.url.scheme == "https"


async def _smtp_settings(db: AsyncSession) -> AppIntegrationSettings:
    settings_row = await db.scalar(select(AppIntegrationSettings).limit(1))
    if (
        settings_row is None
        or not settings_row.smtp_enabled
        or not settings_row.smtp_host
        or not settings_row.smtp_from_email
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SMTP email is not configured.",
        )
    return settings_row


async def _create_invitation(
    payload: InvitationCreateRequest,
    admin: User,
    request: Request,
    db: AsyncSession,
) -> tuple[UserInvitation, str]:
    settings_row = await _smtp_settings(db)
    email = str(payload.email).strip().lower()
    username = payload.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username is required.")

    existing_user = await db.scalar(
        select(User).where((User.email == email) | (User.username == username))
    )
    if existing_user is not None:
        raise HTTPException(status_code=409, detail="That username or email is already in use.")

    await db.execute(
        delete(UserInvitation).where(
            UserInvitation.email == email,
            UserInvitation.accepted_at.is_(None),
            UserInvitation.revoked_at.is_(None),
        )
    )

    raw_token = secrets.token_urlsafe(48)
    invitation = UserInvitation(
        id=uuid4(),
        email=email,
        username=username,
        is_admin=payload.is_admin,
        invited_by=admin.id,
        token_hash=hash_token(raw_token),
        expires_at=int(time.time()) + _INVITATION_SECONDS,
    )
    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)

    invite_url = f"{_public_app_origin(request)}/invite?token={raw_token}"
    body = (
        f"You have been invited to join Archive as {username}.\n\n"
        f"Set your password and finish creating your account here:\n{invite_url}\n\n"
        "This invitation expires in 7 days and can only be used once. "
        "If you were not expecting this invitation, you can safely ignore this email."
    )
    try:
        await asyncio.to_thread(
            send_email, settings_row, email, "You have been invited to Archive", body
        )
    except Exception as exc:
        invitation.revoked_at = int(time.time())
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The invitation could not be emailed. Check the SMTP configuration and try again.",
        ) from exc
    return invitation, raw_token


@router.get("")
async def list_invitations(
    admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)
) -> list[dict[str, str | bool | int | None]]:
    del admin
    invitations = await db.scalars(select(UserInvitation).order_by(UserInvitation.created_at.desc()))
    return [
        {
            "id": str(inv.id),
            "email": inv.email,
            "username": inv.username,
            "is_admin": inv.is_admin,
            "expires_at": inv.expires_at,
            "accepted_at": inv.accepted_at,
            "revoked_at": inv.revoked_at,
            "created_at": inv.created_at,
        }
        for inv in invitations
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_invitation(
    payload: InvitationCreateRequest,
    request: Request,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str | bool | int]:
    invitation, _ = await _create_invitation(payload, admin, request, db)
    return {
        "id": str(invitation.id),
        "email": invitation.email,
        "username": invitation.username,
        "is_admin": invitation.is_admin,
        "expires_at": invitation.expires_at,
    }


@router.post("/{invitation_id}/resend", status_code=status.HTTP_201_CREATED)
async def resend_invitation(
    invitation_id: UUID,
    request: Request,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str | bool | int]:
    invitation = await db.scalar(select(UserInvitation).where(UserInvitation.id == invitation_id))
    if invitation is None:
        raise HTTPException(status_code=404, detail="Invitation not found.")
    if invitation.accepted_at is not None:
        raise HTTPException(status_code=409, detail="This invitation has already been accepted.")
    payload = InvitationCreateRequest(
        username=invitation.username, email=invitation.email, is_admin=invitation.is_admin
    )
    await db.execute(
        delete(UserInvitation).where(UserInvitation.id == invitation_id)
    )
    await db.commit()
    replacement, _ = await _create_invitation(payload, admin, request, db)
    return {
        "id": str(replacement.id),
        "email": replacement.email,
        "username": replacement.username,
        "is_admin": replacement.is_admin,
        "expires_at": replacement.expires_at,
    }


@router.delete("/{invitation_id}")
async def revoke_invitation(
    invitation_id: UUID,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    del admin
    invitation = await db.scalar(select(UserInvitation).where(UserInvitation.id == invitation_id))
    if invitation is None:
        raise HTTPException(status_code=404, detail="Invitation not found.")
    if invitation.accepted_at is not None:
        raise HTTPException(status_code=409, detail="This invitation has already been accepted.")
    invitation.revoked_at = int(time.time())
    await db.commit()
    return {"status": "revoked", "invitation_id": str(invitation_id)}


@router.get("/validate")
async def validate_invitation(token: str, db: AsyncSession = Depends(get_db)) -> dict[str, str | bool | int]:
    invitation = await db.scalar(
        select(UserInvitation).where(
            UserInvitation.token_hash == hash_token(token.strip()),
            UserInvitation.accepted_at.is_(None),
            UserInvitation.revoked_at.is_(None),
            UserInvitation.expires_at > int(time.time()),
        )
    )
    if invitation is None:
        raise HTTPException(status_code=400, detail="This invitation is invalid or has expired.")
    return {
        "username": invitation.username,
        "email": invitation.email,
        "is_admin": invitation.is_admin,
        "expires_at": invitation.expires_at,
    }


@router.post("/accept")
async def accept_invitation(
    payload: InvitationAcceptRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    token_hash = hash_token(payload.token.strip())
    now = int(time.time())
    invitation = await db.scalar(
        select(UserInvitation).where(
            UserInvitation.token_hash == token_hash,
            UserInvitation.accepted_at.is_(None),
            UserInvitation.revoked_at.is_(None),
            UserInvitation.expires_at > now,
        )
    )
    if invitation is None:
        raise HTTPException(status_code=400, detail="This invitation is invalid or has expired.")

    existing_user = await db.scalar(
        select(User).where((User.email == invitation.email) | (User.username == invitation.username))
    )
    if existing_user is not None:
        raise HTTPException(
            status_code=409,
            detail="The invited username or email is already in use. Ask an administrator to resend the invitation.",
        )

    user = User(
        username=invitation.username,
        email=invitation.email,
        password_hash=hash_password(payload.password),
        is_active=True,
        is_admin=invitation.is_admin,
    )
    invitation.accepted_at = now
    db.add(user)
    try:
        await db.flush()
        await db.execute(delete(UserSession).where(UserSession.user_id == user.id))
        session_token = secrets.token_urlsafe(32)
        db.add(
            UserSession(
                user_id=user.id,
                token_hash=hash_token(session_token),
                expires_at=now + _SESSION_SECONDS,
            )
        )
        await db.commit()
        await db.refresh(user)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="That username or email is already in use.") from exc

    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_token,
        max_age=_SESSION_SECONDS,
        httponly=True,
        samesite="lax",
        secure=_public_request_is_secure(request),
        path="/",
    )
    return {"message": "Your Archive account is ready. You are now signed in.", "user_id": str(user.id)}
