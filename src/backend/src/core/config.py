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

    model_config = SettingsConfigDict(extra="ignore")


settings = Settings()  # type: ignore[call-arg]  # Values are loaded from the environment.
