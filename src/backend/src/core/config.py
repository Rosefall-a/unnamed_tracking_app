"""
src/core/config.py

Application runtime settings loaded from environment variables.

SetupConfiguration is deliberately separate: it owns setup-page environment
namespaces and precedence, while Settings owns runtime values consumed by the
application.
"""

from urllib.parse import quote

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.core.fernet_key import persistent_fernet_key


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env."""

    DATABASE_URL: str | None = None
    POSTGRES_USER: str | None = None
    POSTGRES_PASSWORD: str | None = None
    POSTGRES_DB: str | None = None
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432

    STEAMGRIDDB_API_KEY: str | None = None
    RETROACHIEVEMENTS_API_KEY: str | None = None
    GIANTBOMB_API_KEY: str | None = None

    PRIMARY_USER_USERNAME: str = ""
    PRIMARY_USER_EMAIL: str = ""
    PRIMARY_USER_PASSWORD: str = ""

    AUTH_COOKIE_SECURE: bool = False
    DEBUG: bool = False
    SECRET_KEY: str = Field(default_factory=persistent_fernet_key)
    MAX_UPLOAD_SIZE_MB: int = 15
    MAX_CLIP_SIZE_MB: int = 500
    MAX_WORLD_SAVE_SIZE_MB: int = 2000

    # App-registered dev credentials, shared across all users on this server
    # (not a personal login). IGDB moved to the DB-backed
    # AppIntegrationSettings singleton (admin-entered through Settings, see
    # api/routes/settings.py) instead of .env — a downloaded copy of this
    # app must never ship with someone else's credentials baked in.
    #
    # These are only a fallback for a deploy that wants to set the metadata
    # keys from its compose file: a key saved in Settings wins over them,
    # and none of them ship with the app (see core/integrations.py).
    IGDB_CLIENT_ID: str | None = None
    IGDB_CLIENT_SECRET: str | None = None
    TMDB_API_KEY: str | None = None
    OMDB_API_KEY: str | None = None
    TVDB_API_KEY: str | None = None
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

    @model_validator(mode="after")
    def resolve_database_url(self) -> "Settings":
        """Accept either DATABASE_URL or the standard PostgreSQL variables."""
        if self.DATABASE_URL:
            return self

        if not self.POSTGRES_USER or self.POSTGRES_PASSWORD is None or not self.POSTGRES_DB:
            raise ValueError(
                "Configure DATABASE_URL or POSTGRES_USER, POSTGRES_PASSWORD, and POSTGRES_DB."
            )

        user = quote(self.POSTGRES_USER, safe="")
        password = quote(self.POSTGRES_PASSWORD, safe="")
        database = quote(self.POSTGRES_DB, safe="")
        self.DATABASE_URL = (
            f"postgresql+psycopg://{user}:{password}@"
            f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{database}"
        )
        return self


settings = Settings()  # type: ignore[call-arg]
