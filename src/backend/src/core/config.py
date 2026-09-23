"""
src/core/config.py

Application runtime settings loaded from environment variables.

SetupConfiguration is deliberately separate: it owns setup-page environment
namespaces and precedence, while Settings owns runtime values consumed by the
application.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.core.fernet_key import persistent_fernet_key


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env."""

    DATABASE_URL: str
    STEAMGRIDDB_API_KEY: str | None = None
    RETROACHIEVEMENTS_API_KEY: str | None = None
    GIANTBOMB_API_KEY: str | None = None
    IGDB_CLIENT_ID: str | None = None
    IGDB_CLIENT_SECRET: str | None = None

    PRIMARY_USER_USERNAME: str = ""
    PRIMARY_USER_EMAIL: str = ""
    PRIMARY_USER_PASSWORD: str = ""

    AUTH_COOKIE_SECURE: bool = False
    DEBUG: bool = False
    SECRET_KEY: str = Field(default_factory=persistent_fernet_key)
    MAX_UPLOAD_SIZE_MB: int = 15
    MAX_CLIP_SIZE_MB: int = 500
    MAX_WORLD_SAVE_SIZE_MB: int = 2000

    SCREENSCRAPER_DEVID: str | None = None
    SCREENSCRAPER_DEVPASSWORD: str | None = None
    SCREENSCRAPER_SSID: str | None = None
    SCREENSCRAPER_SSPASSWORD: str | None = None

    OIDC_ISSUER_URL: str | None = None
    OIDC_CLIENT_ID: str | None = None
    OIDC_CLIENT_SECRET: str | None = None
    OIDC_REDIRECT_URI: str | None = None
    OIDC_SCOPES: str = "openid profile email"
    OIDC_GROUPS_CLAIM: str = "groups"
    OIDC_ADMIN_GROUP: str | None = None
    OIDC_USER_MATCH_FIELD: str = "email"

    SETUP_MODE: str = "auto"
    APP_DATA_DIR: str = "/data"
    ALLOW_DEPLOYMENT_SECRETS_DOWNLOAD: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()  # type: ignore[call-arg]
