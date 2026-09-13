from __future__ import annotations

import secrets
import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import SESSION_COOKIE, hash_password, hash_token, validate_password
from src.core.config import settings
from src.core.oidc import begin_oidc, callback_url, new_state, oauth, oidc_enabled, register_oidc_provider
from src.database.models.auth import UserSession
from src.database.models.user import User
from src.database.session import get_db

router = APIRouter(prefix="/api/auth/oidc", tags=["auth"])
_SESSION_SECONDS = 30 * 24 * 60 * 60

register_oidc_provider()


def _safe_username(value: str, email: str) -> str:
    candidate = "".join(c for c in value.strip() if c.isalnum() or c in "._-")[:100]
    return candidate or email.split("@", 1)[0][:90] or f"user-{secrets.token_hex(4)}"


@router.get("/status")
async def oidc_status() -> dict[str, bool]:
    return {"enabled": oidc_enabled()}


@router.get("/login", name="oidc_login")
async def oidc_login(request: Request) -> Response:
    response = await begin_oidc(request)
    # Starlette/Authlib validates the OAuth state on callback. The cookie also
    # makes the browser's intent explicit and gives us a stable CSRF boundary.
    response.set_cookie(
        "oidc_state",
        new_state(),
        max_age=600,
        httponly=True,
        samesite="lax",
        secure=settings.AUTH_COOKIE_SECURE,
    )
    return response


@router.get("/callback", name="oidc_callback")
async def oidc_callback(request: Request, response: Response, db: AsyncSession = Depends(get_db)) -> Response:
    if not oidc_enabled():
        raise HTTPException(status_code=404, detail="OIDC login is not configured.")

    client = oauth.create_client("oidc")
    if client is None:
        raise HTTPException(status_code=503, detail="OIDC provider is unavailable.")

    try:
        token = await client.authorize_access_token(request)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="OIDC authentication failed.") from exc

    userinfo = token.get("userinfo")
    if not userinfo:
        try:
            userinfo = await client.userinfo(token=token)
        except Exception as exc:
            raise HTTPException(status_code=401, detail="OIDC provider did not return user information.") from exc

    subject = str(userinfo.get("sub", "")).strip()
    email = str(userinfo.get("email", "")).strip().lower()
    email_verified = userinfo.get("email_verified")
    if not subject or not email or email_verified is False:
        raise HTTPException(status_code=403, detail="OIDC account must provide a verified email address.")

    # OIDC accounts are linked by provider subject when present, otherwise by
    # verified email. We deliberately do not auto-link an unverified email.
    user = await db.scalar(select(User).where(User.oidc_subject == subject))
    if user is None:
        user = await db.scalar(select(User).where(User.email == email))

    if user is None:
        username = _safe_username(str(userinfo.get("preferred_username") or userinfo.get("name") or ""), email)
        base = username
        suffix = 1
        while await db.scalar(select(User.id).where(User.username == username)) is not None:
            suffix += 1
            username = f"{base[:100-len(str(suffix))-1]}-{suffix}"
        user = User(
            username=username,
            email=email,
            # OIDC-only accounts cannot authenticate through the password form.
            password_hash=hash_password(secrets.token_urlsafe(48) + "A!a"),
            is_active=True,
            is_admin=False,
            oidc_subject=subject,
        )
        db.add(user)
    else:
        if not user.is_active:
            raise HTTPException(status_code=403, detail="This account is disabled.")
        if user.oidc_subject and user.oidc_subject != subject:
            raise HTTPException(status_code=409, detail="OIDC identity is linked to another account.")
        user.oidc_subject = subject
        if user.email != email:
            user.email = email

    session_token = secrets.token_urlsafe(32)
    db.add(
        UserSession(
            user_id=user.id,
            token_hash=hash_token(session_token),
            expires_at=int(time.time()) + _SESSION_SECONDS,
        )
    )
    await db.commit()

    redirect = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    redirect.set_cookie(
        SESSION_COOKIE,
        session_token,
        max_age=_SESSION_SECONDS,
        httponly=True,
        samesite="lax",
        secure=settings.AUTH_COOKIE_SECURE,
    )
    return redirect
