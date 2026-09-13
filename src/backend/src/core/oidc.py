"""OpenID Connect helpers.

OIDC client secrets stay on the backend. The browser only receives a boolean
status and starts the authorization redirect; Authlib performs the code/token
exchange on the server.
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urljoin

from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, Request
from starlette.responses import RedirectResponse

from src.core.config import settings


oauth = OAuth()


@dataclass(frozen=True)
class OidcConfig:
    issuer_url: str
    client_id: str
    client_secret: str
    scopes: str = "openid profile email"
    redirect_uri: str | None = None


def env_oidc_config() -> OidcConfig | None:
    if not (settings.OIDC_ISSUER_URL and settings.OIDC_CLIENT_ID and settings.OIDC_CLIENT_SECRET):
        return None
    return OidcConfig(
        issuer_url=settings.OIDC_ISSUER_URL,
        client_id=settings.OIDC_CLIENT_ID,
        client_secret=settings.OIDC_CLIENT_SECRET,
        scopes=settings.OIDC_SCOPES,
        redirect_uri=settings.OIDC_REDIRECT_URI,
    )


def register_oidc_provider(config: OidcConfig) -> None:
    oauth.register(
        name="oidc",
        client_id=config.client_id,
        client_secret=config.client_secret,
        server_metadata_url=urljoin(config.issuer_url.rstrip("/") + "/", ".well-known/openid-configuration"),
        client_kwargs={"scope": config.scopes},
        overwrite=True,
    )


def callback_url(request: Request, config: OidcConfig) -> str:
    return config.redirect_uri or str(request.url_for("oidc_callback"))


async def begin_oidc(request: Request, config: OidcConfig) -> RedirectResponse:
    register_oidc_provider(config)
    client = oauth.create_client("oidc")
    if client is None:
        raise HTTPException(status_code=503, detail="OIDC provider is unavailable.")
    # Authlib stores and validates the authorization state in the Starlette
    # session. No separate state cookie is necessary.
    return await client.authorize_redirect(request, callback_url(request, config))
