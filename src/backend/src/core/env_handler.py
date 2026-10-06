"""Central environment/configuration resolution.

The handler is the backend half of the self-building setup UI. It reads the
declarative registry, resolves environment values before persisted values, and
produces a UI-safe schema containing section status and field metadata.
Secrets are represented only by a configured flag.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import dotenv_values

from .config_registry import (
    CONFIG_REGISTRY,
    CONFIG_SECTIONS,
    ConfigSectionSpec,
    ConfigSource,
    ConfigSpec,
    DefaultMode,
)
from .fernet_key import persistent_fernet_key


@dataclass(frozen=True)
class ConfigIssue:
    name: str
    severity: str
    message: str
    recoverable: bool = True


class EnvConfigHandler:
    """Resolve declared configuration and report dependency-aware issues."""

    @staticmethod
    def _find_env_file() -> str:
        explicit = os.getenv("ENV_FILE", "").strip()
        if explicit:
            return explicit
        current = Path.cwd().resolve()
        for directory in (current, *current.parents):
            candidate = directory / ".env"
            if candidate.is_file():
                return str(candidate)
        return ".env"

    def __init__(self, environ: dict[str, str] | None = None) -> None:
        file_values = {
            str(key).upper(): str(value)
            for key, value in dotenv_values(self._find_env_file()).items()
            if value is not None
        }
        # In production, the real process environment overrides .env values.
        # When an explicit mapping is supplied, it is intentionally isolated from
        # the host environment so tests and callers can model a complete environment.
        if environ is None:
            file_values.update({str(key).upper(): str(value) for key, value in os.environ.items()})
        else:
            file_values.update({str(key).upper(): str(value) for key, value in environ.items()})
        self.environ = file_values
        self.mode = self._parse_mode(self.environ.get("STARTUP_MODE", ""))

    @staticmethod
    def _parse_mode(value: str) -> DefaultMode:
        normalized = value.strip().lower()
        if normalized in {"dev", "development"}:
            return DefaultMode.DEVELOPMENT
        if normalized == "testing":
            return DefaultMode.TESTING
        return DefaultMode.DEFAULT

    def has(self, name: str) -> bool:
        return bool(self.environ.get(name, "").strip())

    def source_allowed(self, name: str, source: ConfigSource) -> bool:
        spec = next(spec for spec in CONFIG_REGISTRY if spec.name == name)
        return spec.source in {ConfigSource.BOTH, source}

    def startup_ui_enabled(self) -> bool:
        """Return whether startup/setup UI should be shown for the current mode.

        Development mode deliberately skips the setup UI. Testing and normal
        modes show it so developers can exercise configuration while still
        receiving development-friendly defaults in testing.
        """
        return self.mode is not DefaultMode.DEVELOPMENT

    def bootstrap_primary_user(self) -> dict[str, str]:
        return {
            "username": str(self.get("PRIMARY_USER_USERNAME") or ""),
            "email": str(self.get("PRIMARY_USER_EMAIL") or ""),
            "password": str(self.get("PRIMARY_USER_PASSWORD") or ""),
        }

    def get(self, name: str) -> Any:
        spec = next(spec for spec in CONFIG_REGISTRY if spec.name == name)
        raw = self.environ.get(name)
        if raw is not None and raw.strip():
            return self._coerce(spec.input_type, raw)
        if self.mode is DefaultMode.TESTING:
            if spec.testing_default is not None:
                return spec.testing_default
            if spec.development_default is not None:
                return spec.development_default
        if self.mode is DefaultMode.DEVELOPMENT and spec.development_default is not None:
            return spec.development_default
        return spec.default

    @staticmethod
    def _coerce(input_type: str, value: Any) -> Any:
        if input_type == "boolean":
            return str(value).strip().lower() in {"1", "true", "yes", "on"}
        if input_type == "integer":
            try:
                return int(str(value).strip())
            except ValueError:
                return value
        return str(value).strip()

    def resolved(self) -> dict[str, Any]:
        values = {spec.name: self.get(spec.name) for spec in CONFIG_REGISTRY}
        if not self.has("SECRET_KEY"):
            values["SECRET_KEY"] = persistent_fernet_key()
        return values

    def setup_schema(
        self,
        persisted: dict[str, Any] | None = None,
        generated_values: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Build setup sections with environment precedence and secrets redacted."""
        return [
            self._setup_section(section, persisted or {}, generated_values or {})
            for section in sorted(CONFIG_SECTIONS, key=lambda item: item.order)
        ]

    def _setup_field(
        self, spec: ConfigSpec, persisted: dict[str, Any], generated_values: dict[str, Any]
    ) -> dict[str, Any]:
        required = spec.required
        if spec.section == "oidc" and spec.name in {
            "OIDC_ISSUER_URL",
            "OIDC_CLIENT_ID",
            "OIDC_CLIENT_SECRET",
        }:
            required = True

        env_set = self.has(spec.name)
        generated_value = generated_values.get(spec.name)
        persisted_value = persisted.get(spec.name)
        persisted_configured = bool(persisted.get(f"{spec.name}__configured", False)) or (
            persisted_value is not None and str(persisted_value).strip() != ""
        )

        if generated_value is not None and spec.generated:
            value = generated_value
            source = "generated"
            configured = True
        elif env_set:
            value = self.get(spec.name)
            source = "env"
            configured = True
        elif persisted_configured:
            value = persisted_value
            source = "database"
            configured = True
        else:
            value = self.get(spec.name)
            source = "default" if value is not None else "unset"
            configured = False

        if spec.secret:
            value = None

        return {
            "name": spec.name,
            "label": spec.label or spec.name.replace("_", " ").title(),
            "type": spec.input_type,
            "choices": [{"value": value, "label": label} for value, label in spec.choices],
            "description": spec.description,
            "hint": spec.hint,
            "placeholder": spec.placeholder,
            "required": required,
            "required_group": spec.required_group,
            "heading": spec.heading,
            "secret": spec.secret,
            "generated": spec.generated,
            "deprecated": spec.deprecated,
            "deprecated_message": spec.deprecated_message if spec.deprecated else "",
            "visible": spec.visible and not (spec.source is ConfigSource.ENV and spec.secret),
            "env_only": spec.source is ConfigSource.ENV,
            "locked": spec.generated or spec.source is ConfigSource.ENV or env_set,
            "configured": configured,
            "source": source,
            "value": value,
        }

    def _setup_status(self, fields: list[dict[str, Any]]) -> tuple[str, bool]:
        """Evaluate required fields and alternative configuration groups independently."""
        configured_count = sum(field["configured"] for field in fields)
        required = [field for field in fields if field["required"] and not field["required_group"]]
        required_configured = sum(field["configured"] for field in required)
        env_configured_required = sum(self.has(field["name"]) for field in required)
        missing_env = sum(field["env_only"] and not self.has(field["name"]) for field in required)
        groups: dict[str, dict[str, list[dict[str, Any]]]] = {}
        for field in fields:
            if field["required_group"]:
                group, _, variant = field["required_group"].partition(":")
                groups.setdefault(group, {}).setdefault(variant or "default", []).append(field)
        satisfied = {
            group: next(
                (members for members in variants.values() if all(f["configured"] for f in members)),
                None,
            )
            for group, variants in groups.items()
        }
        missing_env += sum(
            satisfied[group] is None
            and all(field["env_only"] for members in variants.values() for field in members)
            for group, variants in groups.items()
        )
        if missing_env:
            status = "blocked_by_env"
        elif (required and required_configured != len(required)) or any(
            members is None for members in satisfied.values()
        ):
            status = "partial" if configured_count else "not_configured"
        elif (
            groups
            and not required
            and all(
                members is not None and all(self.has(field["name"]) for field in members)
                for members in satisfied.values()
            )
        ):
            status = "completed_by_env"
        elif required and required_configured == len(required):
            status = (
                "completed_by_env" if env_configured_required == len(required) else "configured"
            )
        else:
            status = "partial" if configured_count else "not_configured"
        return status, bool(missing_env)

    def _setup_section(
        self,
        section: ConfigSectionSpec,
        persisted: dict[str, Any],
        generated_values: dict[str, Any],
    ) -> dict[str, Any]:
        fields = [
            self._setup_field(spec, persisted, generated_values)
            for spec in CONFIG_REGISTRY
            if spec.section == section.id and spec.name != "VITE_USE_MOCK_DATA"
        ]
        status, blocked = self._setup_status(fields)
        return {
            "id": section.id,
            "title": section.title,
            "description": section.description,
            "required": section.required,
            "menu": section.menu,
            "removable": section.removable,
            "visible": section.visible,
            "default": section.required or section.default,
            "status": status,
            "blocked": blocked,
            "env_configured": any(
                field["source"] == "env" and field["configured"] for field in fields
            ),
            "blocked_message": (
                "This section has required deployment-only values missing from .env: "
                + ", ".join(
                    field["name"]
                    for field in fields
                    if field["required"] and field["env_only"] and not field["configured"]
                )
            )
            if blocked
            else "",
            "fields": fields,
        }

    def validate(self) -> list[ConfigIssue]:
        values = self.resolved()
        issues: list[ConfigIssue] = []

        required_groups: dict[str, dict[str, list[str]]] = {}
        for spec in CONFIG_REGISTRY:
            if not spec.required_group:
                continue
            group, _, variant = spec.required_group.partition(":")
            required_groups.setdefault(group, {}).setdefault(variant or "default", []).append(
                spec.name
            )

        for group, variants in required_groups.items():
            satisfied = next(
                (
                    variant
                    for variant, names in variants.items()
                    if all(str(values.get(name) or "").strip() for name in names)
                ),
                None,
            )
            if satisfied is not None:
                if group == "database" and satisfied == "url":
                    issues.append(
                        ConfigIssue(
                            "database",
                            "warning",
                            "DATABASE_URL is deprecated; use POSTGRES_USER, POSTGRES_PASSWORD, and POSTGRES_DB.",
                        )
                    )
                continue
            if group == "database":
                issues.append(
                    ConfigIssue(
                        "database",
                        "error",
                        "Database configuration is required. Configure either "
                        "POSTGRES_USER, POSTGRES_PASSWORD, and POSTGRES_DB OR DATABASE_URL.",
                        recoverable=False,
                    )
                )
            else:
                issues.append(
                    ConfigIssue(
                        group,
                        "error",
                        "Required configuration group is incomplete.",
                        recoverable=False,
                    )
                )

        primary_names = ("PRIMARY_USER_USERNAME", "PRIMARY_USER_EMAIL", "PRIMARY_USER_PASSWORD")
        primary_present = [bool(str(values.get(name) or "").strip()) for name in primary_names]
        if any(primary_present) and not all(primary_present):
            missing = [
                name
                for name, present in zip(primary_names, primary_present, strict=True)
                if not present
            ]
            issues.append(
                ConfigIssue(
                    "primary_user",
                    "error",
                    "Primary user configuration is incomplete: " + ", ".join(missing),
                    recoverable=False,
                )
            )

        # OIDC is optional. A partial environment configuration must not
        # activate startup validation; only a complete environment provider is
        # considered deployment-managed OIDC configuration.
        oidc_names = ("OIDC_ISSUER_URL", "OIDC_CLIENT_ID", "OIDC_CLIENT_SECRET")
        if all(str(values.get(name) or "").strip() for name in oidc_names):
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

        return issues

    def startup_summary(self) -> dict[str, Any]:
        issues = self.validate()
        return {
            "mode": self.mode.value,
            "ready": not any(issue.severity == "error" for issue in issues),
            "issues": [issue.__dict__ for issue in issues],
        }
