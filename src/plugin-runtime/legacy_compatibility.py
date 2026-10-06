"""Runtime-side legacy eligibility, using the same reviewed ID list as the host."""

import json
from pathlib import Path
from collections.abc import Mapping
from uuid import UUID

_policy_path = Path(__file__).with_name("legacy_compatibility.json")
if not _policy_path.is_file():
    _policy_path = (
        Path(__file__).parents[1] / "backend/src/plugin_api/legacy_compatibility.json"
    )
SHIPPED_PLUGIN_IDS = frozenset(
    json.loads(_policy_path.read_text(encoding="utf-8"))["shipped_plugin_ids"]
)
LEGACY_WARNING = (
    "This plugin was built for the old v1.0 UI and runs with limited compatibility. "
    "Existing backend features, declarative settings and embedded pages are supported. "
    "New native UI, themes, shortcuts and built-in section placement need a v1.1 update; "
    "some old pages may look different or have limited features."
)


def legacy_plugin_allowed(plugin_id: str, state: Mapping[str, object]) -> bool:
    if plugin_id in SHIPPED_PLUGIN_IDS:
        return True
    installed = state.get(plugin_id)
    if not isinstance(installed, Mapping):
        return False
    try:
        UUID(str(installed.get("installation_id", "")))
    except ValueError:
        return False
    return True
