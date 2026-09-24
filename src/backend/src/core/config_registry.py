"""Declarative application configuration metadata.

The registry is the single place where backend-owned configuration declares its
defaults, source policy, and validation requirements. Resolution is handled by
EnvConfigHandler; account creation remains in the authentication/setup layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ConfigSource(str, Enum):
    ENV = "env"
    SETUP = "setup"
    BOTH = "both"


class DefaultMode(str, Enum):
    DEFAULT = "default"
    DEVELOPMENT = "development"
    TESTING = "testing"


@dataclass(frozen=True)
class ConfigSpec:
    name: str
    source: ConfigSource = ConfigSource.BOTH
    default: Any = None
    development_default: Any = None
    testing_default: Any = None
    required: bool = False
    secret: bool = False
    generated: bool = False
    description: str = ""
    deprecated: bool = False


CONFIG_REGISTRY: tuple[ConfigSpec, ...] = (
    ConfigSpec("POSTGRES_USER", source=ConfigSource.ENV, required=True),
    ConfigSpec("POSTGRES_PASSWORD", source=ConfigSource.ENV, required=True, secret=True),
    ConfigSpec("POSTGRES_DB", source=ConfigSource.ENV, required=True),
    ConfigSpec("POSTGRES_HOST", source=ConfigSource.ENV, default="db"),
    ConfigSpec("POSTGRES_PORT", source=ConfigSource.ENV, default=5432),
    ConfigSpec("DATABASE_URL", source=ConfigSource.ENV, deprecated=True, description="Legacy database connection string."),
    ConfigSpec(
        "SECRET_KEY",
        source=ConfigSource.ENV,
        secret=True,
        generated=True,
        description="Stable Fernet/session signing key; generated and persisted when omitted.",
    ),
    ConfigSpec("AUTH_COOKIE_SECURE", default=False),
    ConfigSpec("DEBUG", default=False, development_default=True),
    ConfigSpec(
        "STARTUP_MODE",
        source=ConfigSource.ENV,
        default="",
        description="Optional profile: development, testing, or empty/default.",
    ),
    ConfigSpec(
        "PRIMARY_USER_USERNAME",
        default="",
        development_default="admin",
        source=ConfigSource.BOTH,
    ),
    ConfigSpec(
        "PRIMARY_USER_EMAIL",
        default="",
        development_default="admin@localhost",
        source=ConfigSource.BOTH,
    ),
    ConfigSpec(
        "PRIMARY_USER_PASSWORD",
        default="",
        development_default="Admin123!",
        source=ConfigSource.BOTH,
        secret=True,
    ),
    ConfigSpec("MAX_UPLOAD_SIZE_MB", default=15),
    ConfigSpec("MAX_SAVE_ARCHIVE_SIZE_MB", default=4096),
    ConfigSpec("MAX_CLIP_SIZE_MB", default=500),
    ConfigSpec("MAX_WORLD_SAVE_SIZE_MB", default=2000),
    ConfigSpec("STEAMGRIDDB_API_KEY", secret=True, default=None),
    ConfigSpec("RETROACHIEVEMENTS_API_KEY", secret=True, default=None),
    ConfigSpec("GIANTBOMB_API_KEY", secret=True, default=None),
    ConfigSpec("IGDB_CLIENT_ID", default=None),
    ConfigSpec("IGDB_CLIENT_SECRET", secret=True, default=None),
    ConfigSpec("TMDB_API_KEY", secret=True, default=None),
    ConfigSpec("OMDB_API_KEY", secret=True, default=None),
    ConfigSpec("TVDB_API_KEY", secret=True, default=None),
    ConfigSpec("SCREENSCRAPER_DEVID", default=None),
    ConfigSpec("SCREENSCRAPER_DEVPASSWORD", secret=True, default=None),
    ConfigSpec("SCREENSCRAPER_SSID", default=None),
    ConfigSpec("SCREENSCRAPER_SSPASSWORD", secret=True, default=None),
    ConfigSpec("XBOX_CLIENT_ID", default=None),
    ConfigSpec("XBOX_CLIENT_SECRET", secret=True, default=None),
    ConfigSpec("OIDC_ISSUER_URL", default=None),
    ConfigSpec("OIDC_CLIENT_ID", default=None),
    ConfigSpec("OIDC_CLIENT_SECRET", secret=True, default=None),
    ConfigSpec("OIDC_REDIRECT_URI", default=None),
    ConfigSpec("OIDC_SCOPES", default="openid profile email"),
    ConfigSpec("OIDC_GROUPS_CLAIM", default="groups"),
    ConfigSpec("OIDC_ADMIN_GROUP", default=None),
    ConfigSpec("OIDC_USER_MATCH_FIELD", default="email"),
    ConfigSpec(
        "VITE_USE_MOCK_DATA",
        source=ConfigSource.ENV,
        default=False,
        description="Frontend development/testing switch; never exposed as a setup setting.",
    ),
)


def get_config_spec(name: str) -> ConfigSpec:
    for spec in CONFIG_REGISTRY:
        if spec.name == name:
            return spec
    raise KeyError(name)
