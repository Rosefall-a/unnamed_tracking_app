from __future__ import annotations

import logging
from urllib.parse import urljoin

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import SESSION_COOKIE, create_session, hash_password
from src.core.oidc import OidcConfig, register_oidc_provider
from src.database.models.oidc_settings import OidcSettings
from src.database.models.user import User
from src.database.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth/oidc", tags=["oidc"])


def _env_config() -> OidcConfig | None:
    from src.core.config import settings

    issuer = (settings.OIDC_ISSUER_URL or "").strip()
    client_id = (settings.OIDC_CLIENT_ID or "").strip()
    client_secret = (settings.OIDC_CLIENT_SECRET or "").strip()
    if not issuer or not client_id or not client_secret:
        return None
    discovery_url = (
        issuer if issuer.rstrip("/").endswith("/.well-known/openid-configuration") else None
    )
    return OidcConfig(
        issuer_url=issuer,
        client_id=client_id,
        client_secret=client_secret,
        scopes=settings.OIDC_SCOPES or "openid profile email",
        redirect_uri=settings.OIDC_REDIRECT_URI,
        groups_claim=settings.OIDC_GROUPS_CLAIM or "groups",
        admin_group=settings.OIDC_ADMIN_GROUP,
        user_match_field=settings.OIDC_USER_MATCH_FIELD or "email",
        discovery_url=discovery_url,
    )


async def _get_config(db: AsyncSession) -> OidcConfig | None:
    row = await db.scalar(select(OidcSettings).order_by(OidcSettings.id.desc()))
    if row is None:
        return _env_config()
    issuer = (row.issuer_url or "").strip()
    client_secret = row.client_secret
    if not issuer or not row.client_id or not client_secret:
        return None
    discovery_url = (
        issuer if issuer.rstrip("/").endswith("/.well-known/openid-configuration") else None
    )
    return OidcConfig(
        issuer_url=issuer,
        client_id=row.client_id,
        client_secret=client_secret,
        scopes=row.scopes or "openid profile email",
        redirect_uri=row.redirect_uri,
        groups_claim=row.groups_claim or "groups",
        admin_group=row.admin_group,
        user_match_field=row.user_match_field or "email",
        discovery_url=discovery_url,
    )


oauth = OAuth()


def _register(config: OidcConfig):
    return register_oidc_provider(oauth, config)


@router.get("/status")
async def oidc_status(db: AsyncSession = Depends(get_db)):
    config = await _get_config(db)
    if config is None:
        return {"enabled": False, "issuer": None}
    return {"enabled": True, "issuer": config.issuer_url}


@router.get("/login")
async def oidc_login(request: Request, db: AsyncSession = Depends(get_db)):
    config = await _get_config(db)
    if config is None:
        return RedirectResponse(url="/login?oidc_error=not_configured", status_code=303)
    client = _register(config)
    redirect_uri = config.redirect_uri or str(request.url_for("oidc_callback"))
    return await client.authorize_redirect(request, redirect_uri)


async def _fetch_oidc_token(request: Request, client) -> dict:
    """Fetch the OAuth token while preserving Authlib's state/CSRF checks.

    Authlib's Starlette OIDC helper immediately validates the returned ID token.
    Some otherwise usable OIDC providers expose a JWKS URL that does not return
    a standards-compliant JWK Set, which makes Authlib fail with
    ``ValueError: Invalid key set format`` after the code exchange has already
    succeeded. In that case the provider's authenticated UserInfo endpoint is
    still the appropriate source of identity claims.
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
            leeway=120,
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
    client = oauth.oidc
    try:
        token = await _fetch_oidc_token(request, client)
    except Exception:
        logger.exception("OIDC callback token/userinfo exchange failed")
        return RedirectResponse(url="/login?oidc_error=authentication_failed", status_code=303)

    userinfo = token.get("userinfo")
    if not userinfo:
        try:
            userinfo = await client.userinfo(token=token)
        except Exception:
            logger.exception("OIDC userinfo request failed")
            return RedirectResponse(url="/login?oidc_error=authentication_failed", status_code=303)

    subject = userinfo.get("sub")
    email = userinfo.get("email")
    if not subject or not email:
        return RedirectResponse(url="/login?oidc_error=identity_missing", status_code=303)
    if userinfo.get("email_verified") is False:
        return RedirectResponse(url="/login?oidc_error=verified_email_required", status_code=303)

    result = await db.execute(select(User).where(User.oidc_subject == subject))
    user = result.scalar_one_or_none()
    if user is None:
        match_value = (
            email
            if config.user_match_field == "email"
            else userinfo.get("preferred_username") or userinfo.get("name")
        )
        if match_value:
            if config.user_match_field == "email":
                result = await db.execute(select(User).where(User.email == match_value))
            else:
                result = await db.execute(select(User).where(User.username == match_value))
            user = result.scalar_one_or_none()

    if user is None:
        username = (
            userinfo.get("preferred_username") or userinfo.get("name") or email.split("@", 1)[0]
        )
        user = User(
            username=username, email=email, oidc_subject=subject, password_hash=hash_password(None)
        )
        db.add(user)
        await db.flush()
    else:
        user.oidc_subject = subject
        user.email = email

    if config.admin_group:
        groups = userinfo.get(config.groups_claim) or []
        user.is_admin = config.admin_group in groups

    await create_session(db, user.id)
    await db.commit()

    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=str(user.id),
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )
    return response
