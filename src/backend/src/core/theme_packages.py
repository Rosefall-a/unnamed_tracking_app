"""Bounded inert CSS packages, independent from executable plugin infrastructure."""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import stat
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from threading import RLock
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

MAX_THEME_UPLOAD = 10 * 1024 * 1024
_ASSET_EXTENSIONS = {
    ".css",
    ".md",
    ".txt",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".svg",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
}
_STORE_LOCK = RLock()


def theme_asset_path(value: str) -> str:
    """Reject paths that could escape a package on either supported host platform."""
    path = PurePosixPath(value)
    if not value or "\\" in value or ":" in value:
        raise ValueError("Theme assets must use plain relative paths.")
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise ValueError("Theme assets must use plain relative paths.")
    return value


class ThemeManifest(BaseModel):
    """Format 1 CSS-only metadata; no executable entrypoints or SDK permissions."""

    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)
    format_version: Literal[1]
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,127}$")
    name: str = Field(min_length=1, max_length=120)
    version: str = Field(pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
    publisher: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=1000)
    kind: Literal["official", "example"]
    stylesheet: str
    supports: list[Literal["light", "dark"]] = Field(min_length=1, max_length=2)

    @field_validator("format_version", mode="before")
    @classmethod
    def check_format(cls, value: Any) -> int:
        """A boolean is not a package format number."""
        if isinstance(value, bool) or not isinstance(value, int) or value != 1:
            raise ValueError("Use theme package format 1.")
        return value

    @field_validator("id")
    @classmethod
    def check_identifier(cls, value: str) -> str:
        """Keep native and server selection sentinels outside package identities."""
        if value in {"native", "server"}:
            raise ValueError("This theme identifier is reserved.")
        return value

    @field_validator("stylesheet")
    @classmethod
    def check_stylesheet(cls, value: str) -> str:
        """Require a bounded CSS entrypoint inside the archive."""
        theme_asset_path(value)
        if not value.endswith(".css") or len(value) > 240:
            raise ValueError("Declare a relative CSS stylesheet.")
        return value

    @field_validator("supports")
    @classmethod
    def check_modes(cls, value: list[Literal["light", "dark"]]) -> list[Literal["light", "dark"]]:
        """Declare each supported mode once."""
        if len(set(value)) != len(value):
            raise ValueError("Theme modes must be unique.")
        return value


@dataclass(frozen=True)
class ThemePackage:
    """An inspected upload whose contents have not yet reached persistent storage."""

    manifest: ThemeManifest
    digest: str
    files: dict[str, bytes]


def inspect_theme_package(data: bytes) -> ThemePackage:
    """Inspect every archive member before accepting a CSS package or writing files."""
    if not data or len(data) > MAX_THEME_UPLOAD:
        raise ValueError("Theme packages must be smaller than 10 MiB.")
    files: dict[str, bytes] = {}
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            members = archive.infolist()
            if len(members) > 128 or sum(item.file_size for item in members) > 20 * 1024 * 1024:
                raise ValueError("Theme package contains too many or oversized assets.")
            for item in members:
                name = theme_asset_path(item.filename.rstrip("/"))
                mode = stat.S_IFMT(item.external_attr >> 16)
                if mode not in {0, stat.S_IFREG, stat.S_IFDIR} or item.flag_bits & 1:
                    raise ValueError(
                        "Theme packages cannot contain links, devices or encrypted files."
                    )
                if item.is_dir():
                    continue
                if item.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}:
                    raise ValueError("Theme packages must use stored or deflated ZIP assets.")
                if name in files:
                    raise ValueError("Theme package contains duplicate asset paths.")
                suffix = PurePosixPath(name).suffix.lower()
                if name != "manifest.json" and suffix not in _ASSET_EXTENSIONS:
                    raise ValueError(
                        "Theme packages contain CSS, documentation, images and fonts only."
                    )
                if (suffix == ".css" and item.file_size > 1024 * 1024) or (
                    name == "manifest.json" and item.file_size > 32 * 1024
                ):
                    raise ValueError("Theme stylesheet or manifest is too large.")
                content = archive.read(item)
                if suffix == ".css":
                    content.decode("utf-8")
                files[name] = content
        manifest = ThemeManifest.model_validate_json(files["manifest.json"])
    except (OSError, UnicodeError, zipfile.BadZipFile, KeyError, ValidationError) as exc:
        raise ValueError("Invalid theme package or manifest.") from exc
    if manifest.stylesheet not in files:
        raise ValueError("Declared theme stylesheet is missing.")
    return ThemePackage(manifest, hashlib.sha256(data).hexdigest(), files)


class ThemeStore:
    """Persist reviewed assets and administrator choices with atomic index writes."""

    def __init__(self, root: Path):
        self.root = root

    def _read(self) -> dict[str, Any]:
        index = self.root / "index.json"
        if not index.exists():
            return {"default_theme": "native", "themes": {}}
        try:
            value = json.loads(index.read_text(encoding="utf-8"))
            if not isinstance(value, dict) or not isinstance(value.get("themes"), dict):
                raise ValueError("Invalid theme index")
            return value
        except (OSError, ValueError) as exc:
            raise ValueError(
                "Theme storage is unavailable. Check the server's theme data."
            ) from exc

    def _save(self, state: dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        descriptor, filename = tempfile.mkstemp(prefix=".index-", dir=self.root)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as output:
                json.dump(state, output)
            os.replace(filename, self.root / "index.json")
        finally:
            Path(filename).unlink(missing_ok=True)

    def catalogue(self, *, administration: bool = False) -> dict[str, Any]:
        """Public choices contain enabled themes only; administrators can manage all."""
        with _STORE_LOCK:
            state = self._read()
            return {
                "default_theme": state["default_theme"],
                "themes": sorted(
                    [
                        dict(item)
                        for item in state["themes"].values()
                        if administration or item["enabled"]
                    ],
                    key=lambda item: (item["kind"], item["name"].casefold(), item["id"]),
                ),
            }

    def install(self, package: ThemePackage) -> dict[str, Any]:
        """Install inert assets, preserving the server default on replacements."""
        with _STORE_LOCK:
            state = self._read()
            target = self.root / "packages" / package.manifest.id / package.digest
            self.root.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                with tempfile.TemporaryDirectory(prefix=".install-", dir=self.root) as temporary:
                    staging = Path(temporary) / "package"
                    staging.mkdir()
                    for name, content in package.files.items():
                        destination = staging / name
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        destination.write_bytes(content)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(staging, target)
            entry = {**package.manifest.model_dump(), "digest": package.digest, "enabled": True}
            state["themes"][package.manifest.id] = entry
            self._save(state)
            return entry

    def configure(self, theme_id: str, enabled: bool) -> dict[str, Any]:
        """Enable or disable one installed theme and repair a disabled default."""
        with _STORE_LOCK:
            state = self._read()
            entry = state["themes"].get(theme_id)
            if entry is None:
                raise KeyError(theme_id)
            entry["enabled"] = enabled
            if not enabled and state["default_theme"] == theme_id:
                state["default_theme"] = "native"
            self._save(state)
            return dict(entry)

    def set_default(self, theme_id: str) -> dict[str, Any]:
        """Only an enabled installed theme can become the server's default."""
        with _STORE_LOCK:
            state = self._read()
            if theme_id != "native" and not state["themes"].get(theme_id, {}).get("enabled"):
                raise ValueError("Choose an enabled installed theme or the native interface.")
            state["default_theme"] = theme_id
            self._save(state)
            return {"default_theme": theme_id}

    def remove(self, theme_id: str) -> None:
        """Remove one installed package and return a removed default to native."""
        with _STORE_LOCK:
            state = self._read()
            if theme_id not in state["themes"]:
                raise KeyError(theme_id)
            del state["themes"][theme_id]
            if state["default_theme"] == theme_id:
                state["default_theme"] = "native"
            self._save(state)
            target = self.root / "packages" / theme_id
            target.resolve().relative_to((self.root / "packages").resolve())
            if target.exists():
                shutil.rmtree(target)

    def asset(self, theme_id: str, digest: str, relative: str) -> Path:
        """Serve only an enabled package's current digest and confined regular assets."""
        with _STORE_LOCK:
            state = self._read()
            entry = state["themes"].get(theme_id)
            if not entry or not entry["enabled"] or entry["digest"] != digest:
                raise KeyError(theme_id)
            base = self.root / "packages" / theme_id / digest
            path = base / theme_asset_path(relative)
            try:
                path.resolve(strict=True).relative_to(base.resolve())
            except (OSError, ValueError) as exc:
                raise KeyError(relative) from exc
            if not path.is_file() or path.is_symlink():
                raise KeyError(relative)
            return path


def get_theme_store() -> ThemeStore:
    """Resolve the normal persistent data directory, with an isolated test override."""
    return ThemeStore(Path(os.getenv("THEME_STORE_PATH", "/data/themes")))
