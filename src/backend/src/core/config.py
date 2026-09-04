"""
src/core/config.py

Grabs all settings from enviorment.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables (and .env, if present)."""

    DATABASE_URL: str
    STEAMGRIDDB_API_KEY: str | None = None
    PRIMARY_USER_USERNAME: str
    PRIMARY_USER_EMAIL: str
    PRIMARY_USER_PASSWORD: str
    AUTH_COOKIE_SECURE: bool = False
    DEBUG: bool = False
    # Fernet key (Fernet.generate_key()) used to encrypt secrets at rest (e.g. the
    # PSN npsso token) — required, no default, so a deploy can't silently run unsafe
    SECRET_KEY: str
    MAX_UPLOAD_SIZE_MB: int = 15

    # App-registered dev credentials, shared across all users on this server
    # (not a personal login) — same tier as STEAMGRIDDB_API_KEY's fallback.
    IGDB_CLIENT_ID: str | None = None
    IGDB_CLIENT_SECRET: str | None = None
    SCREENSCRAPER_DEVID: str | None = None
    SCREENSCRAPER_DEVPASSWORD: str | None = None

    model_config = SettingsConfigDict(extra="ignore")


settings = Settings()  # type: ignore[call-arg]  # Values are loaded from the environment.
