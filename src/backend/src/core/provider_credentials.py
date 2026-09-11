"""Resolve provider credentials with one consistent precedence order."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.core.config import settings
from src.core.crypto import decrypt_secret

if TYPE_CHECKING:
    from src.database.models.app_integration_settings import AppIntegrationSettings
    from src.database.models.user import User


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
            settings.STEAMGRIDDB_API_KEY,
        ),
        igdb_client_id=_prefer(
            app_integrations.igdb_client_id if app_integrations else None,
            settings.IGDB_CLIENT_ID,
        ),
        igdb_client_secret=_prefer(
            _decrypt(app_integrations.igdb_client_secret) if app_integrations else None,
            settings.IGDB_CLIENT_SECRET,
        ),
        retroachievements_api_key=_prefer(
            user_retroachievements,
            _decrypt(app_integrations.retroachievements_api_key) if app_integrations else None,
            settings.RETROACHIEVEMENTS_API_KEY,
        ),
        giantbomb_api_key=_prefer(
            user_giantbomb,
            _decrypt(app_integrations.giantbomb_api_key) if app_integrations else None,
            settings.GIANTBOMB_API_KEY,
        ),
        screenscraper_ssid=_prefer(
            user_screenscraper_ssid,
            app_integrations.screenscraper_ssid if app_integrations else None,
            settings.SCREENSCRAPER_SSID,
        ),
        screenscraper_sspassword=_prefer(
            user_screenscraper_password,
            _decrypt(app_integrations.screenscraper_sspassword) if app_integrations else None,
            settings.SCREENSCRAPER_SSPASSWORD,
        ),
        screenscraper_devid=_prefer(
            app_integrations.screenscraper_devid if app_integrations else None,
            settings.SCREENSCRAPER_DEVID,
        ),
        screenscraper_devpassword=_prefer(
            _decrypt(app_integrations.screenscraper_devpassword) if app_integrations else None,
            settings.SCREENSCRAPER_DEVPASSWORD,
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
