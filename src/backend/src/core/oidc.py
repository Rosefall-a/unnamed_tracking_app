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
    groups_claim: str = "groups"
    admin_group: str | None = None
    user_match_field: str = "email"
    allow_new_users: bool = True
    discovery_url: str | None = None

    @property
    def server_metadata_url(self) -> str:
        configured = (self.discovery_url or self.issuer_url).strip().rstrip("/")
        suffix = "/.well-known/openid-configuration"
        if configured.endswith(suffix):
            return configured
        return urljoin(configured + "/", ".well-known/openid-configuration")


def env_oidc_config() -> OidcConfig | None:
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
        allow_new_users=True,
        discovery_url=discovery_url,
    )


def register_oidc_provider(config: OidcConfig) -> None:
    oauth.register(
        name="oidc",
        client_id=config.client_id,
        client_secret=config.client_secret,
        server_metadata_url=config.server_metadata_url,
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
    return await client.authorize_redirect(request, callback_url(request, config))
