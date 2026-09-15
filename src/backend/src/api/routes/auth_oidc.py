from __future__ import annotations

import base64
import hashlib
import json
import logging
import re
import secrets
import time
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import RedirectResponse

from src.core.auth import SESSION_COOKIE, hash_password, hash_token
from src.core.config import settings
from src.core.crypto import decrypt_secret
from src.core.oidc import OidcConfig, begin_oidc, oauth, register_oidc_provider
from src.database.models.auth import MobileOidcHandoff, UserSession
from src.database.models.oidc_settings import OidcSettings
from src.database.models.user import User
from src.database.session import get_db

router = APIRouter(prefix="/api/auth/oidc", tags=["auth"])
_SESSION_SECONDS = 30 * 24 * 60 * 60
_MOBILE_HANDOFF_SECONDS = 120
_MOBILE_LOGIN_SECONDS = 10 * 60
_MOBILE_SESSION_KEY = "native_oidc"
_MOBILE_CALLBACK = "tracking-native://oidc/callback"
logger = logging.getLogger(__name__)


class MobileExchangeRequest(BaseModel):
    code: str = Field(min_length=32, max_length=256)
    verifier: str = Field(min_length=43, max_length=128, pattern=r"^[A-Za-z0-9._~-]+$")


def _pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _valid_challenge(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_-]{43}", value))


def _mobile_redirect(*, code: str | None = None, error: str | None = None) -> RedirectResponse:
    parameter = f"code={code}" if code else f"error={error or 'authentication_failed'}"
    return RedirectResponse(f"{_MOBILE_CALLBACK}?{parameter}", 303)


def _env_config():
    if not (settings.OIDC_ISSUER_URL and settings.OIDC_CLIENT_ID and settings.OIDC_CLIENT_SECRET):
        return None
    issuer = settings.OIDC_ISSUER_URL.strip()
    return OidcConfig(
        issuer_url=issuer,
        client_id=settings.OIDC_CLIENT_ID,
        client_secret=settings.OIDC_CLIENT_SECRET,
        scopes=settings.OIDC_SCOPES,
        redirect_uri=settings.OIDC_REDIRECT_URI,
        groups_claim=settings.OIDC_GROUPS_CLAIM,
        admin_group=settings.OIDC_ADMIN_GROUP,
        user_match_field=getattr(settings, "OIDC_USER_MATCH_FIELD", "email"),
        discovery_url=(issuer if issuer.endswith("/.well-known/openid-configuration") else None),
    )


def _named_rows(row):
    try:
        data = json.loads(row.providers_json or "[]")
    except (TypeError, ValueError):
        return []
    return [provider for provider in data if isinstance(provider, dict) and provider.get("slug")]


def _config_from_provider(provider):
    issuer = str(provider["issuer_url"]).strip()
    return OidcConfig(
        issuer_url=issuer,
        client_id=str(provider["client_id"]),
        client_secret=decrypt_secret(str(provider["client_secret"])),
        scopes=provider.get("scopes") or "openid profile email",
        redirect_uri=provider.get("redirect_uri") or None,
        groups_claim=provider.get("groups_claim") or "groups",
        admin_group=provider.get("admin_group") or None,
        user_match_field=provider.get("user_match_field") or "email",
        allow_new_users=bool(provider.get("allow_new_users", True)),
        discovery_url=(issuer if issuer.endswith("/.well-known/openid-configuration") else None),
        name=provider.get("name") or provider["slug"],
        slug=provider["slug"],
        button_text=provider.get("button_text") or "Continue with SSO",
        button_image_url=provider.get("button_image_url"),
    )


async def _get_config(db, slug="default", *, autostart=False):
    row = await db.scalar(select(OidcSettings).limit(1))

    if row and slug != "default":
        for provider in _named_rows(row):
            if provider.get("slug") != slug:
                continue
            if not provider.get("enabled", True):
                return None
            if not provider.get("client_secret"):
                return None
            if autostart and not provider.get("autostart_enabled", True):
                return None
            return _config_from_provider(provider)
        return None

    if row and row.issuer_url and row.client_id and row.client_secret:
        return OidcConfig(
            issuer_url=row.issuer_url.strip(),
            client_id=row.client_id,
            client_secret=decrypt_secret(row.client_secret),
            scopes=row.scopes or "openid profile email",
            redirect_uri=row.redirect_uri,
            groups_claim=row.groups_claim or "groups",
            admin_group=row.admin_group,
            user_match_field=row.user_match_field or "email",
            allow_new_users=row.allow_new_users,
        )
    return _env_config() if slug == "default" else None


@router.get("/status")
async def oidc_status(db: AsyncSession = Depends(get_db)):
    row = await db.scalar(select(OidcSettings).limit(1))
    config = await _get_config(db)
    providers = []
    if row:
        for provider in _named_rows(row):
            if provider.get("enabled", True) and provider.get("show_on_login", True):
                providers.append(
                    {
                        "name": provider.get("name", provider["slug"]),
                        "slug": provider["slug"],
                        "button_text": provider.get("button_text") or "Continue with SSO",
                        "button_image_url": provider.get("button_image_url"),
                        "button_color": provider.get("button_color") or "#d68a34",
                        "autostart_enabled": bool(provider.get("autostart_enabled", True)),
                    }
                )
    if not providers and config:
        providers = [
            {
                "name": config.name,
                "slug": "default",
                "button_text": (
                    row.login_button_text.strip()
                    if row and row.login_button_text.strip()
                    else config.button_text
                ),
                "button_image_url": config.button_image_url,
                "button_color": "#d68a34",
                "autostart_enabled": True,
            }
        ]
    return {
        "enabled": config is not None or bool(providers),
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
        "providers": providers,
    }


async def _begin_mobile_login(
    request: Request,
    db: AsyncSession,
    challenge: str,
    provider_slug: str = "default",
):
    if not _valid_challenge(challenge):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid PKCE challenge.")
    config = await _get_config(
        db,
        provider_slug,
        autostart=provider_slug != "default",
    )
    if config is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "OIDC login is not configured.")
    request.session[_MOBILE_SESSION_KEY] = {
        "challenge": challenge,
        "created_at": int(time.time()),
    }
    return await begin_oidc(request, config)


@router.get("/mobile/login")
async def mobile_oidc_login(
    request: Request,
    challenge: str,
    db: AsyncSession = Depends(get_db),
):
    return await _begin_mobile_login(request, db, challenge)


@router.get("/mobile/login/{provider_slug}")
async def mobile_oidc_provider_login(
    provider_slug: str,
    request: Request,
    challenge: str,
    db: AsyncSession = Depends(get_db),
):
    return await _begin_mobile_login(request, db, challenge, provider_slug)


@router.post("/mobile/exchange")
async def mobile_oidc_exchange(
    payload: MobileExchangeRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    now = int(time.time())
    handoff = await db.scalar(
        select(MobileOidcHandoff)
        .where(
            MobileOidcHandoff.code_hash == hash_token(payload.code),
            MobileOidcHandoff.expires_at > now,
        )
        .with_for_update()
    )
    if handoff is None or not secrets.compare_digest(
        _pkce_challenge(payload.verifier), handoff.verifier_challenge
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired OIDC handoff.")

    session_token = secrets.token_urlsafe(32)
    db.add(
        UserSession(
            user_id=handoff.user_id,
            token_hash=hash_token(session_token),
            expires_at=now + _SESSION_SECONDS,
        )
    )
    await db.delete(handoff)
    await db.commit()
    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_token,
        max_age=_SESSION_SECONDS,
        httponly=True,
        samesite="lax",
        secure=settings.AUTH_COOKIE_SECURE,
        path="/",
    )
    return {"status": "logged_in"}


@router.get("/login", name="oidc_login")
async def oidc_login(request: Request, db: AsyncSession = Depends(get_db)):
    config = await _get_config(db)
    if config is None:
        raise HTTPException(404, "OIDC login is not configured.")
    return await begin_oidc(request, config)


@router.get("/login/{provider_slug}")
async def oidc_provider_login(
    provider_slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    config = await _get_config(db, provider_slug, autostart=True)
    if config is None:
        return RedirectResponse("/login", 303)
    return await begin_oidc(request, config)


async def _fetch_oidc_token(request, client):
    params = {
        "code": request.query_params.get("code"),
        "state": request.query_params.get("state"),
    }
    state = params["state"]
    if not state:
        raise ValueError("Missing OIDC state parameter")
    state_data = await client.framework.get_state_data(request.session, state)
    if not state_data:
        raise ValueError("Invalid OIDC state parameter")
    await client.framework.clear_state_data(request.session, state)
    params = client._format_state_params(state_data, params)
    token = await client.fetch_access_token(**params)
    if "id_token" not in token or "nonce" not in state_data:
        return token
    try:
        token["userinfo"] = await client.parse_id_token(
            token, nonce=state_data["nonce"], claims_options=None
        )
    except ValueError as exc:
        if str(exc) != "Invalid key set format":
            raise
        logger.warning("OIDC provider returned an invalid JWKS document; using UserInfo endpoint")
        token["userinfo"] = await client.userinfo(token=token)
    return token


def _groups(claims, name):
    value = claims.get(name)
    if isinstance(value, str):
        return {value}
    if isinstance(value, (list, tuple, set)):
        return {str(item) for item in value if str(item).strip()}
    return set()


def _match_value(claims, field, email):
    if field == "username":
        return str(claims.get("preferred_username") or claims.get("name") or "").strip()
    return email


def _safe_username(value, email):
    username = "".join(c for c in value.strip() if c.isalnum() or c in "._-")[:100]
    return username or email.split("@", 1)[0][:90] or f"user-{secrets.token_hex(4)}"


async def _complete_callback(request, db, config, client_name):
    mobile_context = request.session.pop(_MOBILE_SESSION_KEY, None)

    def error_redirect(reason: str) -> RedirectResponse:
        return (
            _mobile_redirect(error=reason)
            if isinstance(mobile_context, dict)
            else RedirectResponse(f"/login?oidc_error={reason}", 303)
        )

    register_oidc_provider(config, client_name)
    client = oauth.create_client(client_name)
    if client is None:
        return error_redirect("provider_unavailable")
    try:
        token = await _fetch_oidc_token(request, client)
        claims = dict(token.get("userinfo") or await client.userinfo(token=token))
        claims.update({k: v for k, v in token.items() if k not in claims})
    except Exception:
        logger.exception("OIDC callback token/userinfo exchange failed")
        return error_redirect("authentication_failed")
    subject = str(claims.get("sub", "")).strip()
    email = str(claims.get("email", "")).strip().lower()
    if not subject or not email or claims.get("email_verified") is False:
        return error_redirect("verified_email_required")
    field = config.user_match_field if config.user_match_field in {"email", "username"} else "email"
    match = _match_value(claims, field, email)
    if not match:
        return error_redirect("identity_missing")
    linked_subject = f"{config.slug}:{subject}"
    user = await db.scalar(select(User).where(User.oidc_subject == linked_subject))
    if user is None:
        if field == "username":
            user = await db.scalar(select(User).where(User.username == match))
        else:
            user = await db.scalar(select(User).where(User.email == email))
    is_admin = bool(
        config.admin_group and config.admin_group in _groups(claims, config.groups_claim)
    )
    if user is None:
        if not config.allow_new_users:
            return error_redirect("user_creation_disabled")
        username = _safe_username(
            str(claims.get("preferred_username") or claims.get("name") or ""),
            email,
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
            is_admin=is_admin,
            oidc_subject=linked_subject,
        )
        db.add(user)
        await db.flush()
    else:
        if not user.is_active:
            return error_redirect("account_disabled")
        if user.oidc_subject and user.oidc_subject not in {linked_subject, subject}:
            return error_redirect("identity_conflict")
        user.oidc_subject = linked_subject
        user.email = email
        if config.admin_group:
            user.is_admin = is_admin
    now = int(time.time())
    if isinstance(mobile_context, dict):
        challenge = str(mobile_context.get("challenge", ""))
        created_at = mobile_context.get("created_at")
        if (
            not _valid_challenge(challenge)
            or not isinstance(created_at, int)
            or created_at < now - _MOBILE_LOGIN_SECONDS
            or created_at > now + 30
        ):
            await db.rollback()
            return _mobile_redirect(error="handoff_expired")
        handoff_code = secrets.token_urlsafe(32)
        db.add(
            MobileOidcHandoff(
                code_hash=hash_token(handoff_code),
                user_id=user.id,
                verifier_challenge=challenge,
                expires_at=now + _MOBILE_HANDOFF_SECONDS,
            )
        )
        await db.commit()
        return _mobile_redirect(code=handoff_code)

    session_token = secrets.token_urlsafe(32)
    db.add(
        UserSession(
            user_id=user.id,
            token_hash=hash_token(session_token),
            expires_at=now + _SESSION_SECONDS,
        )
    )
    await db.commit()
    response = RedirectResponse("/login?oidc=success", 303)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_token,
        max_age=_SESSION_SECONDS,
        httponly=True,
        samesite="lax",
        secure=settings.AUTH_COOKIE_SECURE,
        path="/",
    )
    return response


@router.get("/callback", name="oidc_callback")
async def oidc_callback(request: Request, db: AsyncSession = Depends(get_db)):
    config = await _get_config(db)
    if config is None:
        return RedirectResponse("/login?oidc_error=not_configured", 303)
    return await _complete_callback(request, db, config, "oidc")


@router.get("/callback/{provider_slug}", name="oidc_callback_provider")
async def oidc_callback_provider(
    provider_slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    config = await _get_config(db, provider_slug)
    if config is None:
        return RedirectResponse("/login?oidc_error=not_configured", 303)
    return await _complete_callback(request, db, config, f"oidc_{provider_slug}")
