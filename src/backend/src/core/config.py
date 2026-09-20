"""Application configuration."""

from __future__ import annotations

from urllib.parse import quote_plus

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.core.fernet_key import persistent_fernet_key


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env."""

    DATABASE_URL: str = ""
    POSTGRES_USER: str | None = None
    POSTGRES_PASSWORD: str | None = None
    POSTGRES_DB: str | None = None
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432

    STEAMGRIDDB_API_KEY: str | None = None
    RETROACHIEVEMENTS_API_KEY: str | None = None
    GIANTBOMB_API_KEY: str | None = None
    IGDB_CLIENT_ID: str | None = None
    IGDB_CLIENT_SECRET: str | None = None

    PRIMARY_USER_USERNAME: str = ""
    PRIMARY_USER_EMAIL: str = ""
    PRIMARY_USER_PASSWORD: str = ""
    APPLICATION_JSON_PASSWORD: str = ""
    APPLICATION_JSON_PATH: str = "/data/application.json"

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

    SECRET_KEY: str = persistent_fernet_key()
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def build_database_url(self) -> "Settings":
        if self.DATABASE_URL.strip():
            url = self.DATABASE_URL.strip()
            if url.startswith("postgres://"):
                url = "postgresql+psycopg://" + url.removeprefix("postgres://")
            elif url.startswith("postgresql://"):
                url = "postgresql+psycopg://" + url.removeprefix("postgresql://")
            self.DATABASE_URL = url
            return self

        missing = [
            name
            for name, value in (
                ("POSTGRES_USER", self.POSTGRES_USER),
                ("POSTGRES_PASSWORD", self.POSTGRES_PASSWORD),
                ("POSTGRES_DB", self.POSTGRES_DB),
            )
            if not value
        ]
        if missing:
            raise ValueError(
                "Database configuration is incomplete. Set DATABASE_URL, or set "
                + ", ".join(missing)
                + "."
            )

        self.DATABASE_URL = (
            "postgresql+psycopg://"
            f"{quote_plus(self.POSTGRES_USER or '')}:"
            f"{quote_plus(self.POSTGRES_PASSWORD or '')}@"
            f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/"
            f"{quote_plus(self.POSTGRES_DB or '')}"
        )
        return self


settings = Settings()  # type: ignore[call-arg]
settings.SECRET_KEY = persistent_fernet_key()
