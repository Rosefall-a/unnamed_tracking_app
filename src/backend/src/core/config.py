"""
src/core/config.py

Application settings loaded from environment variables (and .env, if present).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables (and .env, if present)."""

    DATABASE_URL: str
    STEAMGRIDDB_API_KEY: str | None = None
    RETROACHIEVEMENTS_API_KEY: str | None = None
    GIANTBOMB_API_KEY: str | None = None
    IGDB_CLIENT_ID: str | None = None
    IGDB_CLIENT_SECRET: str | None = None

    # Initial administrator setup is performed through the web UI. These are
    # retained as optional legacy settings so existing deployments can still
    # read old .env files while new deployments no longer need them.
    PRIMARY_USER_USERNAME: str = ""
    PRIMARY_USER_EMAIL: str = ""
    PRIMARY_USER_PASSWORD: str = ""

    AUTH_COOKIE_SECURE: bool = False
    DEBUG: bool = False
    # Fernet key used to encrypt secrets at rest (e.g. PSN npsso token).
    SECRET_KEY: str
    MAX_UPLOAD_SIZE_MB: int = 15
    MAX_CLIP_SIZE_MB: int = 500
    MAX_WORLD_SAVE_SIZE_MB: int = 2000

    SCREENSCRAPER_DEVID: str | None = None
    SCREENSCRAPER_DEVPASSWORD: str | None = None
    SCREENSCRAPER_SSID: str | None = None
    SCREENSCRAPER_SSPASSWORD: str | None = None

    # Optional OpenID Connect provider. OIDC_REDIRECT_URI is useful when the
    # app is behind a reverse proxy; otherwise the callback URL is derived
    # from the incoming request.
    OIDC_ISSUER_URL: str | None = None
    OIDC_CLIENT_ID: str | None = None
    OIDC_CLIENT_SECRET: str | None = None
    OIDC_REDIRECT_URI: str | None = None
    OIDC_SCOPES: str = "openid profile email"
    OIDC_GROUPS_CLAIM: str = "groups"
    OIDC_ADMIN_GROUP: str | None = None

    model_config = SettingsConfigDict(extra="ignore")


settings = Settings()  # type: ignore[call-arg]
