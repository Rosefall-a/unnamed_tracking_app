"""Central environment/configuration resolution.

This module deliberately does not own users or database records. It provides a
small boundary between deployment inputs, generated secrets, startup validation,
and the rest of the application.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dotenv import dotenv_values

from .config_registry import CONFIG_REGISTRY, ConfigSource, DefaultMode
from .fernet_key import persistent_fernet_key


@dataclass(frozen=True)
class ConfigIssue:
    name: str
    severity: str
    message: str
    recoverable: bool = True


class EnvConfigHandler:
    """Resolve declared configuration and report dependency-aware issues."""

    def __init__(self, environ: dict[str, str] | None = None) -> None:
        file_values = {
            str(key).upper(): str(value)
            for key, value in dotenv_values(".env").items()
            if value is not None
        }
        file_values.update(
            {str(key).upper(): str(value) for key, value in (environ or {}).items()}
        )
        self.environ = file_values
        self.mode = self._parse_mode(self.environ.get("STARTUP_MODE", ""))

    @staticmethod
    def _parse_mode(value: str) -> DefaultMode:
        normalized = value.strip().lower()
        if normalized == "development":
            return DefaultMode.DEVELOPMENT
        if normalized == "testing":
            return DefaultMode.TESTING
        return DefaultMode.DEFAULT

    def has(self, name: str) -> bool:
        return bool(self.environ.get(name, "").strip())

    def source_allowed(self, name: str, source: ConfigSource) -> bool:
        spec = next(spec for spec in CONFIG_REGISTRY if spec.name == name)
        return spec.source in {ConfigSource.BOTH, source}

    @property
    def startup_ui_forced(self) -> bool:
        return str(self.get("STARTUP_UI") or "").strip().lower() == "forced"

    def bootstrap_primary_user(self) -> dict[str, str]:
        """Return initial-admin inputs without creating or mutating a user record."""
        return {
            "username": str(self.get("PRIMARY_USER_USERNAME") or ""),
            "email": str(self.get("PRIMARY_USER_EMAIL") or ""),
            "password": str(self.get("PRIMARY_USER_PASSWORD") or ""),
        }

    def setup_schema(self) -> list[dict[str, Any]]:
        """Return non-secret setup metadata; raw secrets are never exposed."""
        return [
            {
                "name": spec.name,
                "source": spec.source.value,
                "default": None if spec.secret else self.get(spec.name),
                "required": spec.required,
                "generated": spec.generated,
                "secret": spec.secret,
                "deprecated": spec.deprecated,
                "description": spec.description,
            }
            for spec in CONFIG_REGISTRY
            if spec.source in {ConfigSource.SETUP, ConfigSource.BOTH}
        ]

    def get(self, name: str) -> Any:
        spec = next(spec for spec in CONFIG_REGISTRY if spec.name == name)
        raw = self.environ.get(name)
        if raw is not None and raw.strip():
            return raw.strip()

        if self.mode is DefaultMode.DEVELOPMENT and spec.development_default is not None:
            return spec.development_default
        if self.mode is DefaultMode.TESTING and spec.testing_default is not None:
            return spec.testing_default
        return spec.default

    def resolved(self) -> dict[str, Any]:
        values = {spec.name: self.get(spec.name) for spec in CONFIG_REGISTRY}
        if not self.has("SECRET_KEY"):
            values["SECRET_KEY"] = persistent_fernet_key()
        return values

    def validate(self) -> list[ConfigIssue]:
        values = self.resolved()
        issues: list[ConfigIssue] = []

        database_names = ("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB")
        missing_db = [name for name in database_names if not str(values.get(name) or "").strip()]
        legacy_database_url = str(self.environ.get("DATABASE_URL") or "").strip()
        if missing_db and not legacy_database_url:
            issues.append(
                ConfigIssue(
                    "database",
                    "error",
                    "Database configuration is incomplete: " + ", ".join(missing_db),
                    recoverable=False,
                )
            )
        elif legacy_database_url and missing_db == list(database_names):
            issues.append(
                ConfigIssue(
                    "database",
                    "warning",
                    "DATABASE_URL is deprecated; use POSTGRES_USER, POSTGRES_PASSWORD, and POSTGRES_DB.",
                )
            )

        primary_names = (
            "PRIMARY_USER_USERNAME",
            "PRIMARY_USER_EMAIL",
            "PRIMARY_USER_PASSWORD",
        )
        primary_present = [bool(str(values.get(name) or "").strip()) for name in primary_names]
        if any(primary_present) and not all(primary_present):
            missing = [name for name, present in zip(primary_names, primary_present) if not present]
            issues.append(
                ConfigIssue(
                    "primary_user",
                    "error",
                    "Primary user configuration is incomplete: " + ", ".join(missing),
                    recoverable=False,
                )
            )

        issuer = str(values.get("OIDC_ISSUER_URL") or "").strip()
        if issuer:
            scopes = set(str(values.get("OIDC_SCOPES") or "").split())
            missing_scopes = {"openid", "profile", "email"} - scopes
            if missing_scopes:
                issues.append(
                    ConfigIssue(
                        "oidc",
                        "warning",
                        "OIDC issuer is configured but recommended scopes are missing: "
                        + ", ".join(sorted(missing_scopes)),
                    )
                )
            for name in ("OIDC_CLIENT_ID", "OIDC_CLIENT_SECRET"):
                if not str(values.get(name) or "").strip():
                    issues.append(
                        ConfigIssue(
                            "oidc",
                            "error",
                            f"OIDC issuer is configured but {name} is missing.",
                            recoverable=False,
                        )
                    )

        startup_mode = str(values.get("STARTUP_MODE") or "").strip().lower()
        if startup_mode not in {"", "development", "testing"}:
            issues.append(
                ConfigIssue(
                    "STARTUP_MODE",
                    "error",
                    "STARTUP_MODE must be empty, development, or testing.",
                    recoverable=False,
                )
            )

        return issues

    def startup_summary(self) -> dict[str, Any]:
        issues = self.validate()
        return {
            "mode": self.mode.value,
            "startup_ui": "forced" if self.startup_ui_forced else "auto",
            "ready": not any(issue.severity == "error" for issue in issues),
            "issues": [issue.__dict__ for issue in issues],
        }
