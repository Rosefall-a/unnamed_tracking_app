"""
src/core/config.py

Grabs all settings from enviorment.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables (and .env, if present)."""

    DATABASE_URL: str
    STEAMGRIDDB_API_KEY: str | None = None
    DEBUG: bool = False

    model_config = SettingsConfigDict(extra="ignore")


settings = Settings()  # type: ignore[call-arg]  # Values are loaded from the environment.
