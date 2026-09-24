"""Central environment/configuration resolution.

The handler is the backend half of the self-building setup UI. It reads the
declarative registry, resolves environment values before persisted values, and
produces a UI-safe schema containing section status and field metadata.
Secrets are represented only by a configured flag.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dotenv import dotenv_values

from .config_registry import CONFIG_REGISTRY, CONFIG_SECTIONS, ConfigSource, DefaultMode
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
        file_values.update({str(key).upper(): str(value) for key, value in (environ or {}).items()})
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

    @staticmethod
    def _bool(value: Any, default: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    def has(self, name: str) -> bool:
        return bool(self.environ.get(name, "").strip())

    def source_allowed(self, name: str, source: ConfigSource) -> bool:
        spec = next(spec for spec in CONFIG_REGISTRY if spec.name == name)
        return spec.source in {ConfigSource.BOTH, source}

    @property
    def startup_ui_forced(self) -> bool:
        return str(self.get("STARTUP_UI") or "").strip().lower() == "forced"

    def oidc_enabled(self, persisted: dict[str, Any] | None = None) -> bool:
        if self.has("OIDC_ENABLED"):
            return self._bool(self.environ.get("OIDC_ENABLED"), True)
        if persisted and "OIDC_ENABLED" in persisted:
            return self._bool(persisted.get("OIDC_ENABLED"), True)
        return self._bool(self.get("OIDC_ENABLED"), True)

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
        if self.mode is DefaultMode.DEVELOPMENT and spec.development_default is not None:
            return spec.development_default
        if self.mode is DefaultMode.TESTING and spec.testing_default is not None:
            return spec.testing_default
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

    def setup_schema(self, persisted: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Build the complete schema consumed by Setup.vue.

        Environment values always win over persisted values. The same method
        is used for first-run setup and forced post-install configuration.
        """
        persisted = persisted or {}
        sections: list[dict[str, Any]] = []

        for section in sorted(CONFIG_SECTIONS, key=lambda item: item.order):
            fields: list[dict[str, Any]] = []
            configured_count = 0
            required_fields = 0
            required_configured = 0
            env_configured_required = 0

            for spec in CONFIG_REGISTRY:
                if spec.section != section.id or spec.name == "VITE_USE_MOCK_DATA":
                    continue

                required = spec.required
                if section.id == "oidc" and spec.name in {"OIDC_ISSUER_URL", "OIDC_CLIENT_ID", "OIDC_CLIENT_SECRET"}:
                    required = self.oidc_enabled(persisted)

                env_set = self.has(spec.name)
                persisted_value = persisted.get(spec.name)
                persisted_configured = bool(persisted.get(f"{spec.name}__configured", False)) or (
                    persisted_value is not None and str(persisted_value).strip() != ""
                )

                if env_set:
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

                if configured:
                    configured_count += 1
                if required:
                    required_fields += 1
                    if configured:
                        required_configured += 1
                    if env_set:
                        env_configured_required += 1

                fields.append({
                    "name": spec.name,
                    "label": spec.label or spec.name.replace("_", " ").title(),
                    "type": spec.input_type,
                    "choices": [{"value": value, "label": label} for value, label in spec.choices],
                    "description": spec.description,
                    "hint": spec.hint,
                    "placeholder": spec.placeholder,
                    "required": required,
                    "secret": spec.secret,
                    "generated": spec.generated,
                    "deprecated": spec.deprecated,
                    "locked": env_set,
                    "configured": configured,
                    "source": source,
                    "value": value,
                })

            if required_fields and required_configured == required_fields:
                status = "completed_by_env" if env_configured_required == required_fields else "configured"
            elif configured_count:
                status = "partial"
            else:
                status = "not_configured"

            sections.append({
                "id": section.id,
                "title": section.title,
                "description": section.description,
                "required": section.required,
                "removable": section.removable,
                "status": status,
                "fields": fields,
            })

        return sections

    def validate(self) -> list[ConfigIssue]:
        values = self.resolved()
        issues: list[ConfigIssue] = []

        database_names = ("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB")
        missing_db = [name for name in database_names if not str(values.get(name) or "").strip()]
        legacy_database_url = str(self.environ.get("DATABASE_URL") or "").strip()
        if missing_db and not legacy_database_url:
            issues.append(ConfigIssue("database", "error", "Database configuration is incomplete: " + ", ".join(missing_db), recoverable=False))
        elif legacy_database_url and missing_db == list(database_names):
            issues.append(ConfigIssue("database", "warning", "DATABASE_URL is deprecated; use POSTGRES_USER, POSTGRES_PASSWORD, and POSTGRES_DB."))

        primary_names = ("PRIMARY_USER_USERNAME", "PRIMARY_USER_EMAIL", "PRIMARY_USER_PASSWORD")
        primary_present = [bool(str(values.get(name) or "").strip()) for name in primary_names]
        if any(primary_present) and not all(primary_present):
            missing = [name for name, present in zip(primary_names, primary_present) if not present]
            issues.append(ConfigIssue("primary_user", "error", "Primary user configuration is incomplete: " + ", ".join(missing), recoverable=False))

        if self.oidc_enabled():
            issuer = str(values.get("OIDC_ISSUER_URL") or "").strip()
            if issuer:
                scopes = set(str(values.get("OIDC_SCOPES") or "").split())
                missing_scopes = {"openid", "profile", "email"} - scopes
                if missing_scopes:
                    issues.append(ConfigIssue("oidc", "warning", "OIDC issuer is configured but recommended scopes are missing: " + ", ".join(sorted(missing_scopes))))
                for name in ("OIDC_CLIENT_ID", "OIDC_CLIENT_SECRET"):
                    if not str(values.get(name) or "").strip():
                        issues.append(ConfigIssue("oidc", "error", f"OIDC issuer is configured but {name} is missing.", recoverable=False))

        startup_mode = str(values.get("STARTUP_MODE") or "").strip().lower()
        if startup_mode not in {"", "development", "testing"}:
            issues.append(ConfigIssue("STARTUP_MODE", "error", "STARTUP_MODE must be empty, development, or testing.", recoverable=False))

        return issues

    def startup_summary(self) -> dict[str, Any]:
        issues = self.validate()
        return {
            "mode": self.mode.value,
            "startup_ui": "forced" if self.startup_ui_forced else "auto",
            "ready": not any(issue.severity == "error" for issue in issues),
            "issues": [issue.__dict__ for issue in issues],
        }
