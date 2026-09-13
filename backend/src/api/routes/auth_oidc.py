from __future__ import annotations

import logging
import secrets
import time
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import RedirectResponse

from src.core.auth import SESSION_COOKIE, hash_password, hash_token
from src.core.config import settings
from src.core.crypto import decrypt_secret
from src.core.oidc import OidcConfig, begin_oidc, oauth, register_oidc_provider
from src.database.models.auth import UserSession
from src.database.models.oidc_settings import OidcSettings
from src.database.models.user import User
from src.database.session import get_db

router = APIRouter(prefix="/api/auth/oidc", tags=["auth"])
_SESSION_SECONDS = 30 * 24 * 60 * 60
logger = logging.getLogger(__name__)


def _env_config() -> OidcConfig | None:
    if not (settings.OIDC_ISSUER_URL and settings.OIDC_CLIENT_ID and settings.OIDC_CLIENT_SECRET):
        return None
    issuer = settings.OIDC_ISSUER_URL.strip()
    discovery_url = issuer if issuer.endswith("/.well-known/openid-configuration") else None
    return OidcConfig(
        issuer_url=issuer,
        client_id=settings.OIDC_CLIENT_ID,
        client_secret=settings.OIDC_CLIENT_SECRET,
        scopes=settings.OIDC_SCOPES,
        redirect_uri=settings.OIDC_REDIRECT_URI,
        groups_claim=settings.OIDC_GROUPS_CLAIM,
        admin_group=settings.OIDC_ADMIN_GROUP,
        user_match_field=getattr(settings, "OIDC_USER_MATCH_FIELD", "email"),
        discovery_url=discovery_url,
    )


async def _get_config(db: AsyncSession) -> OidcConfig | None:
    row = await db.scalar(select(OidcSettings).limit(1))
    if row and row.issuer_url and row.client_id and row.client_secret:
        issuer = row.issuer_url.strip()
        discovery_url = issuer if issuer.endswith("/.well-known/openid-configuration") else None
        return OidcConfig(
            issuer_url=issuer,
            client_id=row.client_id,
            client_secret=decrypt_secret(row.client_secret),
            scopes=row.scopes or "openid profile email",
            redirect_uri=row.redirect_uri,
            groups_claim=row.groups_claim or "groups",
            admin_group=row.admin_group,
            user_match_field=row.user_match_field or "email",
            discovery_url=discovery_url,
        )
    return _env_config()


def _safe_username(value: str, email: str) -> str:
    candidate = "".join(c for c in value.strip() if c.isalnum() or c in "._-")[:100]
    return candidate or email.split("@", 1)[0][:90] or f"user-{secrets.token_hex(4)}"


def _oidc_groups(claims: dict, claim_name: str) -> set[str]:
    value = claims.get(claim_name)
    if isinstance(value, str):
        return {value}
    if isinstance(value, (list, tuple, set)):
        return {str(group) for group in value if str(group).strip()}
    return set()


def _oidc_match_value(claims: dict, field: str, email: str) -> str:
    if field == "username":
        return str(claims.get("preferred_username") or claims.get("name") or "").strip()
    return email


async def _oidc_row(db: AsyncSession) -> OidcSettings | None:
    return await db.scalar(select(OidcSettings).limit(1))


@router.get("/status")
async def oidc_status(db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    row = await _oidc_row(db)
    config = await _get_config(db)
    return {
        "enabled": config is not None,
        "issuer": urlparse(config.issuer_url).hostname if config else None,
        "default_login_method": (
            row.default_login_method
            if row and row.default_login_method in {"local", "sso"}
            else "local"
        ),
        "login_button_text": (
            row.login_button_text.strip()
            if row and row.login_button_text.strip()
            else "Continue with SSO"
        ),
    }


@router.get("/login", name="oidc_login")
async def oidc_login(request: Request, db: AsyncSession = Depends(get_db)) -> Response:
    config = await _get_config(db)
    if config is None:
        raise HTTPException(status_code=404, detail="OIDC login is not configured.")
    return await begin_oidc(request, config)


async def _fetch_oidc_token(request: Request, client) -> dict:
    """Fetch the OAuth token while preserving Authlib's state/CSRF checks.

    Authlib 1.4.x does not expose the ``leeway`` argument on the Starlette
    client's ``parse_id_token`` method. Keep ID-token validation on Authlib and
    use only arguments supported by the pinned dependency. Providers whose JWKS
    response is unusable can still fall back to their authenticated UserInfo
    endpoint after the code exchange.
    """
    if request.method == "GET":
        params = {
            "code": request.query_params.get("code"),
            "state": request.query_params.get("state"),
        }
    else:
        form = await request.form()
        params = {"code": form.get("code"), "state": form.get("state")}

    state = params.get("state")
    if not state:
        raise ValueError("Missing OIDC state parameter")

    state_data = await client.framework.get_state_data(request.session, state)
    if not state_data:
        raise ValueError("Invalid OIDC state parameter")

    client.framework.clear_state_data(request.session, state)
    params = client._format_state_params(state_data, params)
    token = await client.fetch_access_token(**params)

    if "id_token" not in token or "nonce" not in state_data:
        return token

    try:
        token["userinfo"] = await client.parse_id_token(
            token,
            nonce=state_data["nonce"],
            claims_options=None,
        )
    except ValueError as exc:
        if str(exc) != "Invalid key set format":
            raise
        logger.warning(
            "OIDC provider returned an invalid JWKS document; using the authenticated UserInfo endpoint instead"
        )
        token["userinfo"] = await client.userinfo(token=token)

    return token


@router.get("/callback", name="oidc_callback")
async def oidc_callback(request: Request, db: AsyncSession = Depends(get_db)) -> Response:
    config = await _get_config(db)
    if config is None:
        return RedirectResponse(url="/login?oidc_error=not_configured", status_code=303)

    register_oidc_provider(config)
    client = oauth.create_client("oidc")
    if client is None:
        return RedirectResponse(url="/login?oidc_error=provider_unavailable", status_code=303)

    try:
        token = await _fetch_oidc_token(request, client)
        userinfo = token.get("userinfo")
        if not userinfo:
            userinfo = await client.userinfo(token=token)
        claims = dict(userinfo)
        for key, value in token.items():
            claims.setdefault(key, value)
    except Exception:
        logger.exception("OIDC callback token/userinfo exchange failed")
        return RedirectResponse(url="/login?oidc_error=authentication_failed", status_code=303)

    subject = str(claims.get("sub", "")).strip()
    email = str(claims.get("email", "")).strip().lower()
    email_verified = claims.get("email_verified")
    if not subject or not email or email_verified is False:
        logger.warning(
            "OIDC callback missing required verified identity claims (subject=%s, email_present=%s, email_verified=%s)",
            bool(subject),
            bool(email),
            email_verified,
        )
        return RedirectResponse(url="/login?oidc_error=verified_email_required", status_code=303)

    match_field = (
        config.user_match_field if config.user_match_field in {"email", "username"} else "email"
    )
    match_value = _oidc_match_value(claims, match_field, email)
    if not match_value:
        return RedirectResponse(url="/login?oidc_error=identity_missing", status_code=303)

    user = await db.scalar(select(User).where(User.oidc_subject == subject))
    if user is None:
        if match_field == "username":
            user = await db.scalar(select(User).where(User.username == match_value))
        else:
            user = await db.scalar(select(User).where(User.email == email))

    groups = _oidc_groups(claims, config.groups_claim)
    group_is_admin = bool(config.admin_group and config.admin_group in groups)

    if user is None:
        username = _safe_username(
            str(claims.get("preferred_username") or claims.get("name") or ""), email
        )
        base = username
        suffix = 1
        while await db.scalar(select(User.id).where(User.username == username)) is not None:
            suffix += 1
            username = f"{base[: 100 - len(str(suffix)) - 1]}-{suffix}"
        user = User(
            username=username,
            email=email,
            password_hash=hash_password(secrets.token_urlsafe(48) + "A!a"),
            is_active=True,
            is_admin=group_is_admin,
            oidc_subject=subject,
        )
        db.add(user)
        await db.flush()
    else:
        if not user.is_active:
            return RedirectResponse(url="/login?oidc_error=account_disabled", status_code=303)
        if user.oidc_subject and user.oidc_subject != subject:
            return RedirectResponse(url="/login?oidc_error=identity_conflict", status_code=303)
        user.oidc_subject = subject
        user.email = email
        if config.admin_group:
            user.is_admin = group_is_admin

    session_token = secrets.token_urlsafe(32)
    session = UserSession(
        user_id=user.id,
        token_hash=hash_token(session_token),
        expires_at=int(time.time()) + _SESSION_SECONDS,
    )
    db.add(session)
    await db.commit()

    logger.info("OIDC login established application session for user %s", user.id)

    redirect = RedirectResponse(url="/login?oidc=success", status_code=status.HTTP_303_SEE_OTHER)
    redirect.set_cookie(
        key=SESSION_COOKIE,
        value=session_token,
        max_age=_SESSION_SECONDS,
        httponly=True,
        samesite="lax",
        secure=settings.AUTH_COOKIE_SECURE,
        path="/",
    )
    return redirect
