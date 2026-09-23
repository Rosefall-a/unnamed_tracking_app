"""Application configuration.

Runtime settings remain explicit Pydantic settings. SetupConfiguration is kept
separate because it describes setup-page precedence rather than runtime config.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

from src.core.fernet_key import persistent_fernet_key


class Settings(BaseSettings):
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

    # SETUP_MODE controls the interactive setup surface. It is intentionally
    # separate from the declarative OIDC__... setup tree.
    SETUP_MODE: str = "auto"
    APP_DATA_DIR: str = "/data"
    ALLOW_DEPLOYMENT_SECRETS_DOWNLOAD: bool = False

    # If SECRET_KEY is omitted, persistent_fernet_key() creates it once and
    # stores redundant copies below APP_DATA_DIR/config.
    SECRET_KEY: str = persistent_fernet_key()

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()  # type: ignore[call-arg]
