"""Resolve provider credentials with one consistent precedence order."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.core.config import settings
from src.core.crypto import decrypt_secret

if TYPE_CHECKING:
    from src.database.models.app_integration_settings import AppIntegrationSettings
    from src.database.models.user import User


_ENVIRONMENT_FALLBACKS = {
    "steamgriddb_api_key": settings.STEAMGRIDDB_API_KEY,
    "retroachievements_api_key": settings.RETROACHIEVEMENTS_API_KEY,
    "giantbomb_api_key": settings.GIANTBOMB_API_KEY,
    "igdb_client_id": settings.IGDB_CLIENT_ID,
    "igdb_client_secret": settings.IGDB_CLIENT_SECRET,
    "screenscraper_ssid": settings.SCREENSCRAPER_SSID,
    "screenscraper_sspassword": settings.SCREENSCRAPER_SSPASSWORD,
    "screenscraper_devid": settings.SCREENSCRAPER_DEVID,
    "screenscraper_devpassword": settings.SCREENSCRAPER_DEVPASSWORD,
}


def _prefer(*values: str | None) -> str | None:
    """Return the first configured value in precedence order."""
    return next((value for value in values if value), None)


def _decrypt(value: str | None) -> str | None:
    """Decrypt a stored secret, leaving an unset value unset."""
    return decrypt_secret(value) if value else None


@dataclass(frozen=True)
class MetadataProviderCredentials:
    """Effective provider credentials for one user and deployment."""

    steamgriddb_api_key: str | None
    igdb_client_id: str | None
    igdb_client_secret: str | None
    retroachievements_api_key: str | None
    giantbomb_api_key: str | None
    screenscraper_ssid: str | None
    screenscraper_sspassword: str | None
    screenscraper_devid: str | None
    screenscraper_devpassword: str | None
    xbox_client_id: str | None
    xbox_client_secret: str | None


def resolve_metadata_provider_credentials(
    user: "User | None",
    app_integrations: "AppIntegrationSettings | None" = None,
) -> MetadataProviderCredentials:
    """Resolve credentials using user > database > environment precedence.

    User credentials remain the most specific and therefore win. The
    deployment-wide database row is the administrator-managed fallback.
    Environment variables remain useful for bootstrap and installations that
    have not configured the database row yet.
    """
    user_steamgriddb = user.steamgriddb_api_key if user else None
    user_retroachievements = user.retroachievements_api_key if user else None
    user_giantbomb = user.giantbomb_api_key if user else None
    user_screenscraper_ssid = user.screenscraper_ssid if user else None
    user_screenscraper_password = _decrypt(user.screenscraper_sspassword if user else None)

    return MetadataProviderCredentials(
        steamgriddb_api_key=_prefer(
            user_steamgriddb,
            _decrypt(app_integrations.steamgriddb_api_key) if app_integrations else None,
            _ENVIRONMENT_FALLBACKS["steamgriddb_api_key"],
        ),
        igdb_client_id=_prefer(
            app_integrations.igdb_client_id if app_integrations else None,
            _ENVIRONMENT_FALLBACKS["igdb_client_id"],
        ),
        igdb_client_secret=_prefer(
            _decrypt(app_integrations.igdb_client_secret) if app_integrations else None,
            _ENVIRONMENT_FALLBACKS["igdb_client_secret"],
        ),
        retroachievements_api_key=_prefer(
            user_retroachievements,
            _decrypt(app_integrations.retroachievements_api_key) if app_integrations else None,
            _ENVIRONMENT_FALLBACKS["retroachievements_api_key"],
        ),
        giantbomb_api_key=_prefer(
            user_giantbomb,
            _decrypt(app_integrations.giantbomb_api_key) if app_integrations else None,
            _ENVIRONMENT_FALLBACKS["giantbomb_api_key"],
        ),
        screenscraper_ssid=_prefer(
            user_screenscraper_ssid,
            app_integrations.screenscraper_ssid if app_integrations else None,
            _ENVIRONMENT_FALLBACKS["screenscraper_ssid"],
        ),
        screenscraper_sspassword=_prefer(
            user_screenscraper_password,
            _decrypt(app_integrations.screenscraper_sspassword) if app_integrations else None,
            _ENVIRONMENT_FALLBACKS["screenscraper_sspassword"],
        ),
        screenscraper_devid=_prefer(
            app_integrations.screenscraper_devid if app_integrations else None,
            _ENVIRONMENT_FALLBACKS["screenscraper_devid"],
        ),
        screenscraper_devpassword=_prefer(
            _decrypt(app_integrations.screenscraper_devpassword) if app_integrations else None,
            _ENVIRONMENT_FALLBACKS["screenscraper_devpassword"],
        ),
        xbox_client_id=_prefer(
            user.xbox_client_id if user else None,
            app_integrations.xbox_client_id if app_integrations else None,
        ),
        xbox_client_secret=_prefer(
            _decrypt(user.xbox_client_secret if user else None),
            _decrypt(app_integrations.xbox_client_secret) if app_integrations else None,
        ),
    )


def apply_deployment_provider_credentials(app_integrations: "AppIntegrationSettings") -> None:
    """Apply database credentials as the in-process deployment fallback.

    Existing provider clients already read deployment defaults from `settings`.
    Loading the database row into those defaults keeps the precedence centralized
    without duplicating database lookups throughout every provider client.
    User-specific credentials still win because callers pass them explicitly.
    """
    credentials = resolve_metadata_provider_credentials(None, app_integrations)
    settings.STEAMGRIDDB_API_KEY = credentials.steamgriddb_api_key
    settings.RETROACHIEVEMENTS_API_KEY = credentials.retroachievements_api_key
    settings.GIANTBOMB_API_KEY = credentials.giantbomb_api_key
    settings.IGDB_CLIENT_ID = credentials.igdb_client_id
    settings.IGDB_CLIENT_SECRET = credentials.igdb_client_secret
    settings.SCREENSCRAPER_SSID = credentials.screenscraper_ssid
    settings.SCREENSCRAPER_SSPASSWORD = credentials.screenscraper_sspassword
    settings.SCREENSCRAPER_DEVID = credentials.screenscraper_devid
    settings.SCREENSCRAPER_DEVPASSWORD = credentials.screenscraper_devpassword
