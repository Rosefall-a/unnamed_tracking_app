"""Resolve metadata-provider credentials with a consistent precedence order."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.core.config import settings
from src.core.crypto import decrypt_secret

if TYPE_CHECKING:
    from src.database.models.app_integration_settings import AppIntegrationSettings
    from src.database.models.user import User


def _prefer_user(user_value: str | None, fallback: str | None) -> str | None:
    """Use a user's credential when present, otherwise use the server fallback."""
    return user_value or fallback


@dataclass(frozen=True)
class MetadataProviderCredentials:
    """Effective credentials used by metadata providers for one user."""

    steamgriddb_api_key: str | None
    igdb_client_id: str | None
    igdb_client_secret: str | None
    retroachievements_api_key: str | None
    giantbomb_api_key: str | None
    screenscraper_ssid: str | None
    screenscraper_sspassword: str | None
    screenscraper_devid: str | None
    screenscraper_devpassword: str | None


def resolve_metadata_provider_credentials(
    user: "User | None",
    app_integrations: "AppIntegrationSettings | None" = None,
) -> MetadataProviderCredentials:
    """Resolve all metadata credentials in one place.

    Per-user credentials always win. Server-level credentials are only used
    when the user has not configured that credential. IGDB is special because
    its client credentials belong to the deployment-level integration row;
    those take precedence over the environment fallback.
    """
    user_steamgriddb = user.steamgriddb_api_key if user else None
    user_retroachievements = user.retroachievements_api_key if user else None
    user_giantbomb = user.giantbomb_api_key if user else None
    user_screenscraper_ssid = user.screenscraper_ssid if user else None
    user_screenscraper_password = user.screenscraper_sspassword if user else None

    if user_screenscraper_password:
        user_screenscraper_password = decrypt_secret(user_screenscraper_password)

    igdb_client_id = (
        app_integrations.igdb_client_id
        if app_integrations and app_integrations.igdb_client_id
        else settings.IGDB_CLIENT_ID
    )
    igdb_client_secret = (
        decrypt_secret(app_integrations.igdb_client_secret)
        if app_integrations and app_integrations.igdb_client_secret
        else settings.IGDB_CLIENT_SECRET
    )

    return MetadataProviderCredentials(
        steamgriddb_api_key=_prefer_user(user_steamgriddb, settings.STEAMGRIDDB_API_KEY),
        igdb_client_id=igdb_client_id,
        igdb_client_secret=igdb_client_secret,
        retroachievements_api_key=_prefer_user(
            user_retroachievements, settings.RETROACHIEVEMENTS_API_KEY
        ),
        giantbomb_api_key=_prefer_user(user_giantbomb, settings.GIANTBOMB_API_KEY),
        screenscraper_ssid=_prefer_user(user_screenscraper_ssid, settings.SCREENSCRAPER_SSID),
        screenscraper_sspassword=_prefer_user(
            user_screenscraper_password, settings.SCREENSCRAPER_SSPASSWORD
        ),
        screenscraper_devid=settings.SCREENSCRAPER_DEVID,
        screenscraper_devpassword=settings.SCREENSCRAPER_DEVPASSWORD,
    )
