"""Declarative setup/environment configuration.

Environment variables use a double-underscore tree such as
OIDC__AUTHENTIK__ISSUER_URL and OIDC__AUTHENTIK__CLIENT_ID.

The first component identifies a setup page, the second identifies a named
object on that page, and the remaining components identify fields. Environment
values are authoritative and always override browser-supplied values.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


def _coerce(value: str) -> str | bool | int:
    lowered = value.strip().lower()
    if lowered in {"true", "yes", "on"}:
        return True
    if lowered in {"false", "no", "off"}:
        return False
    try:
        return int(value)
    except ValueError:
        return value


@dataclass(frozen=True)
class SetupPage:
    """A setup page and its environment-variable namespace."""

    key: str
    label: str
    description: str = ""


class SetupConfiguration:
    """Build setup pages and resolve authoritative environment overrides."""

    def __init__(self, environ: dict[str, str] | None = None) -> None:
        self.environ = dict(os.environ if environ is None else environ)
        self.pages: dict[str, SetupPage] = {}

    def register_page(self, key: str, label: str, description: str = "") -> None:
        self.pages[key.upper()] = SetupPage(key.upper(), label, description)

    def tree(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for raw_name, raw_value in self.environ.items():
            parts = raw_name.split("__")
            if len(parts) < 2:
                continue
            page_key = parts[0].upper()
            if page_key not in self.pages:
                continue
            cursor = result.setdefault(page_key, {})
            for part in parts[1:-1]:
                cursor = cursor.setdefault(part.lower(), {})
            cursor[parts[-1].lower()] = _coerce(raw_value)
        return result

    def overrides_for(self, page_key: str) -> dict[str, Any]:
        return self.tree().get(page_key.upper(), {})

    def has_override(self, page_key: str) -> bool:
        return bool(self.overrides_for(page_key))

    def setup_enabled(self, setup_mode: str | None = None) -> bool:
        mode = (setup_mode or self.environ.get("SETUP_MODE", "auto")).strip().lower()
        return mode not in {"false", "off", "disabled", "0"}

    def apply(self, page_key: str, values: dict[str, Any]) -> dict[str, Any]:
        """Merge browser/default values while preserving env authority."""
        forced = self.overrides_for(page_key)

        def merge(current: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
            result = dict(current)
            for key, value in overrides.items():
                if isinstance(value, dict) and isinstance(result.get(key), dict):
                    result[key] = merge(result[key], value)
                else:
                    result[key] = value
            return result

        return merge(values, forced)


def default_setup_configuration(environ: dict[str, str] | None = None) -> SetupConfiguration:
    config = SetupConfiguration(environ)
    config.register_page("ACCOUNT", "Administrator", "Initial administrator account.")
    config.register_page("OIDC", "OpenID Connect / SSO", "Identity provider configuration.")
    config.register_page("BACKUP", "Deployment backup", "Deployment export/import settings.")
    return config
