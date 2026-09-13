"""
OpenID Connect authentication helpers.

The provider is configured entirely through environment variables. Discovery is
performed from the issuer's standard .well-known metadata endpoint and Authlib
handles authorization-code/token validation, including nonce/state handling.
"""
from __future__ import annotations

import secrets
from urllib.parse import urljoin

from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, Request
from starlette.responses import RedirectResponse

from src.core.config import settings


oauth = OAuth()


def oidc_enabled() -> bool:
    return bool(
        settings.OIDC_ISSUER_URL
        and settings.OIDC_CLIENT_ID
        and settings.OIDC_CLIENT_SECRET
    )


def register_oidc_provider() -> None:
    if oidc_enabled():
        oauth.register(
            name="oidc",
            client_id=settings.OIDC_CLIENT_ID,
            client_secret=settings.OIDC_CLIENT_SECRET,
            server_metadata_url=urljoin(
                settings.OIDC_ISSUER_URL.rstrip("/") + "/", ".well-known/openid-configuration"
            ),
            client_kwargs={"scope": settings.OIDC_SCOPES},
        )


def callback_url(request: Request) -> str:
    if settings.OIDC_REDIRECT_URI:
        return settings.OIDC_REDIRECT_URI
    return str(request.url_for("oidc_callback"))


def new_state() -> str:
    return secrets.token_urlsafe(32)


async def begin_oidc(request: Request) -> RedirectResponse:
    if not oidc_enabled():
        raise HTTPException(status_code=404, detail="OIDC login is not configured.")
    client = oauth.create_client("oidc")
    if client is None:
        raise HTTPException(status_code=503, detail="OIDC provider is unavailable.")
    return await client.authorize_redirect(request, callback_url(request), state=new_state())
