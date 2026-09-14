"""
src/core/config.py

Application settings loaded from environment variables (and .env, if present).
Deployment secrets such as the Fernet encryption key are bootstrapped once and
then persisted under APP_DATA_DIR so normal deployments do not need to manage
a SECRET_KEY manually.
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote_plus

from cryptography.fernet import Fernet
from dotenv import dotenv_values
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _bootstrap_value(name: str) -> str:
    value = os.getenv(name, "").strip()
    if value:
        return value
    return str(dotenv_values(".env").get(name) or "").strip()


def _persistent_fernet_key() -> str:
    """Load a persistent Fernet key, creating it on first startup.

    SECRET_KEY remains a backwards-compatible bootstrap mechanism. If an
    existing deployment supplies SECRET_KEY and has no persisted key yet, the
    supplied key is copied into persistent storage so encrypted data survives
    removal of SECRET_KEY from .env. Once a persisted key exists it is the
    authoritative key; accidentally supplying a different environment key must
    never silently invalidate the existing encrypted secrets.
    """
    data_dir = Path(_bootstrap_value("APP_DATA_DIR") or "/data")
    key_path = data_dir / "config" / "fernet.key"
    env_key = _bootstrap_value("SECRET_KEY")

    if key_path.exists():
        key = key_path.read_text(encoding="utf-8").strip()
    else:
        key = env_key or Fernet.generate_key().decode()
        try:
            key_path.parent.mkdir(parents=True, exist_ok=True)
            key_path.write_text(key + "\n", encoding="utf-8")
            key_path.chmod(0o600)
        except OSError as exc:
            raise RuntimeError(
                f"Could not persist the Fernet key at {key_path}. "
                "Mount APP_DATA_DIR as a writable persistent volume."
            ) from exc

    try:
        Fernet(key.encode())
    except (ValueError, TypeError) as exc:
        raise RuntimeError(
            f"Invalid Fernet key in {key_path}. The key must be a valid Fernet key."
        ) from exc
    return key


class Settings(BaseSettings):
    """Application settings loaded from environment variables (and .env, if present)."""

    # DATABASE_URL is an optional escape hatch. When it is absent, the normal
    # Docker-friendly POSTGRES_* values are assembled into the async psycopg URL.
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

    AUTH_COOKIE_SECURE: bool = False
    DEBUG: bool = False
    # Runtime deployment settings are persisted in the database after first
    # startup. These environment defaults are migrated once for upgrades.
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

    # The generated/persisted key is deliberately not a normal .env setting.
    SECRET_KEY: str = _persistent_fernet_key()

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
