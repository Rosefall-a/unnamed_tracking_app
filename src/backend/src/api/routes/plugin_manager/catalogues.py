"""Catalogue sources, advertised releases and update discovery."""

from __future__ import annotations

import json
import os
import time
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urljoin
from uuid import NAMESPACE_URL, uuid5

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.notification import Notification
from src.database.models.user import User
from src.database.session import get_db
from src.plugin_api.catalogues import CatalogueStore, CatalogueStoreError
from src.plugin_api.contracts import parse_semver
from src.plugin_api.management_auth import get_plugin_manager_admin, get_plugin_manager_reader
from src.plugin_api.manager_state import manager_state

from . import acquisition, models, runtime

router = APIRouter(prefix="/api/plugins", tags=["plugins"])


_PLUGIN_CATALOG_URL = os.getenv(
    "PLUGIN_CATALOG_URL",
    "https://raw.githubusercontent.com/Rosefall-a/unnamed_tracking_app_plugins/main/list.json",
)


@lru_cache(maxsize=8)
def _catalogue_store_for(path: str, official_url: str) -> CatalogueStore:
    return CatalogueStore(Path(path), official_url)


def _catalogue_store() -> CatalogueStore:
    configured_path = os.getenv("PLUGIN_CATALOGUE_REGISTRY", "/data/plugin-catalogues.json")
    return _catalogue_store_for(configured_path, _PLUGIN_CATALOG_URL)


def _catalog_entries(payload: Any, *, source_url: str | None = None) -> list[dict[str, Any]]:
    """Validate the small, host-consumed catalogue contract."""
    if (
        not isinstance(payload, dict)
        or payload.get("version") != 1
        or not isinstance(payload.get("plugins"), list)
    ):
        raise HTTPException(status_code=502, detail="Plugin catalogue is invalid.")
    entries: list[dict[str, Any]] = []
    for raw_entry in payload["plugins"]:
        try:
            entry = models.PluginCatalogEntry.model_validate(raw_entry)
            icon_metadata = entry.icon if isinstance(entry.icon, dict) else entry.icon_metadata
            if icon_metadata:
                packaged_icon = models.CatalogueIcon.model_validate(icon_metadata)
                entry.icon_metadata = packaged_icon.model_dump()
                entry.icon = None
                source_path = str(entry.build.get("source_path", ""))
                if (
                    source_url
                    and source_path
                    and all(part not in {"", ".", ".."} for part in str(source_path).split("/"))
                    and "\\" not in source_path
                ):
                    entry.icon = acquisition._validate_remote_url(
                        urljoin(source_url, source_path + "/" + packaged_icon.path)
                    )
            if not entry.compatibility:
                entry.compatibility = f"SDK {raw_entry.get('sdk_version_range', '*')}; application {raw_entry.get('application_version_range', '*')}"
            parse_semver(entry.version)
            acquisition._validate_remote_url(entry.url)
            versions: set[str] = set()
            for release in entry.releases:
                parse_semver(release.version)
                acquisition._validate_remote_url(release.url)
                if release.version in versions:
                    raise ValueError("Catalogue release versions must be unique")
                versions.add(release.version)
                if parse_semver(release.version) > parse_semver(entry.version):
                    raise ValueError("Catalogue history cannot be newer than its current entry")
                if release.version == entry.version and (
                    release.url != entry.url
                    or release.digest != entry.digest
                    or release.package_sha256 != entry.package_sha256
                ):
                    raise ValueError("Catalogue current release and history disagree")
            publisher = acquisition._plugin_package_verifier().publishers.get(
                str(entry.signing.get("key_id", ""))
            )
            entry.catalogue_channel = (
                publisher.channel
                if publisher and publisher.allows_plugin(entry.plugin_id)
                else "unverified"
            )
            if entry.changelog_url:
                acquisition._validate_remote_url(entry.changelog_url)
        except (ValidationError, ValueError, HTTPException) as exc:
            raise HTTPException(
                status_code=502, detail="Plugin catalogue contains an invalid entry."
            ) from exc
        entries.append(entry.model_dump())
    return entries


@router.get("/catalogues")
async def list_plugin_catalogues(
    admin: User = Depends(get_plugin_manager_admin),
) -> list[dict[str, Any]]:
    del admin
    try:
        return _catalogue_store().list()
    except CatalogueStoreError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/catalogues", status_code=201)
async def create_plugin_catalogue(
    payload: models.PluginCatalogueCreate,
    admin: User = Depends(get_plugin_manager_admin),
) -> dict[str, Any]:
    del admin
    url = acquisition._validate_remote_url(payload.url)
    try:
        return _catalogue_store().add(
            name=payload.name.strip(),
            url=url,
            enabled=payload.enabled,
            priority=payload.priority,
        )
    except CatalogueStoreError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.patch("/catalogues/{catalogue_id}")
async def update_plugin_catalogue(
    catalogue_id: str,
    payload: models.PluginCatalogueUpdate,
    admin: User = Depends(get_plugin_manager_admin),
) -> dict[str, Any]:
    del admin
    changes = payload.model_dump(exclude_unset=True)
    if "url" in changes:
        changes["url"] = acquisition._validate_remote_url(str(changes["url"]))
    if "name" in changes:
        changes["name"] = str(changes["name"]).strip()
    try:
        return _catalogue_store().update(catalogue_id, **changes)
    except CatalogueStoreError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/catalogues/{catalogue_id}", status_code=204)
async def delete_plugin_catalogue(
    catalogue_id: str,
    admin: User = Depends(get_plugin_manager_admin),
) -> Response:
    del admin
    try:
        _catalogue_store().remove(catalogue_id)
    except CatalogueStoreError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return Response(status_code=204)


@router.get("/catalog", response_model=list[models.PluginCatalogEntry])
async def plugin_catalog(
    source: str | None = Query(default=None, min_length=1, max_length=2048),
    user: User = Depends(get_plugin_manager_reader),
) -> list[models.PluginCatalogEntry]:
    del user
    catalog_url = source or _PLUGIN_CATALOG_URL
    path: Path | None = None
    configured = next(
        (item for item in _catalogue_store().list() if item.get("url") == catalog_url),
        None,
    )
    try:
        path, _, _ = await acquisition._download_remote_file(catalog_url, json_document=True)
        payload = json.loads(path.read_text(encoding="utf-8"))
        entries = [
            models.PluginCatalogEntry.model_validate(entry)
            for entry in _catalog_entries(payload, source_url=catalog_url)
        ]
        if configured is not None:
            _catalogue_store().record_check(str(configured["id"]), None)
        return entries
    except json.JSONDecodeError as exc:
        if configured is not None:
            _catalogue_store().record_check(str(configured["id"]), "Catalogue is not valid JSON.")
        raise HTTPException(status_code=502, detail="Plugin catalogue is not valid JSON.") from exc
    except HTTPException as exc:
        if configured is not None:
            _catalogue_store().record_check(str(configured["id"]), str(exc.detail)[:1000])
        raise
    finally:
        if path is not None:
            path.unlink(missing_ok=True)


async def _check_plugin_update(
    plugin: dict[str, Any],
    admin: User,
) -> dict[str, Any]:
    plugin_id = str(plugin.get("plugin_id", ""))
    current_version = str(plugin.get("version", "0.0.0"))
    source_value = plugin.get("source")
    source: dict[str, Any] = source_value if isinstance(source_value, dict) else {}
    source_type = source.get("type")
    candidate_url: str | None = None
    release_notes: str | None = None
    changelog_url: str | None = None
    available_version: str | None = None

    if source_type == "catalogue" and isinstance(source.get("catalogue_url"), str):
        entries = await plugin_catalog(source=str(source["catalogue_url"]), user=admin)
        entry = next((item for item in entries if item.plugin_id == plugin_id), None)
        if entry is None:
            raise HTTPException(
                status_code=404, detail="Plugin is no longer listed by its catalogue."
            )
        candidate_url = entry.url
        available_version = entry.version
        release_notes = entry.release_notes
        changelog_url = entry.changelog_url
    elif source_type == "url" and isinstance(source.get("url"), str):
        candidate_url = str(source["url"])
        path: Path | None = None
        try:
            path, _, _ = await acquisition._download_remote_file(candidate_url)
            inspected = acquisition._inspect_install_candidate(path)
            if inspected.package.manifest.plugin_id != plugin_id:
                raise HTTPException(
                    status_code=409, detail="Update source returned a different plugin."
                )
            available_version = inspected.package.manifest.version
        finally:
            if path is not None:
                path.unlink(missing_ok=True)
        release_notes = source.get("release_notes")
        changelog_url = source.get("changelog_url")
    else:
        return {
            "plugin_id": plugin_id,
            "current_version": current_version,
            "update_available": False,
            "reason": "No update-capable source metadata is recorded.",
        }

    update_available = bool(
        available_version and parse_semver(available_version) > parse_semver(current_version)
    )
    return {
        "plugin_id": plugin_id,
        "current_version": current_version,
        "available_version": available_version,
        "update_available": update_available,
        "url": candidate_url,
        "release_notes": release_notes,
        "changelog_url": changelog_url,
        "source": source,
        "automatic_update": entry.automatic_update
        if source_type == "catalogue" and entry is not None
        else False,
        "digest": entry.digest if source_type == "catalogue" and entry is not None else None,
        "package_sha256": entry.package_sha256
        if source_type == "catalogue" and entry is not None
        else None,
    }


async def _notify_plugin_update(
    db: AsyncSession,
    update: dict[str, Any],
    *,
    failed: bool = False,
) -> None:
    if not update.get("update_available"):
        return
    plugin_id = str(update["plugin_id"])
    version = str(update["available_version"])
    dedupe_key = f"plugin-update:{plugin_id}:{version}" + (":failed" if failed else "")
    admin_ids = list(
        await db.scalars(select(User.id).where(User.is_admin.is_(True), User.is_active.is_(True)))
    )
    if not admin_ids:
        return
    existing = set(
        await db.scalars(
            select(Notification.user_id).where(
                Notification.user_id.in_(admin_ids),
                Notification.dedupe_key == dedupe_key,
            )
        )
    )
    now = int(time.time())
    for user_id in admin_ids:
        if user_id in existing:
            continue
        db.add(
            Notification(
                user_id=user_id,
                kind="plugin_update",
                media_type="plugin",
                media_id=uuid5(NAMESPACE_URL, f"urn:unnamed-tracking:plugin:{plugin_id}"),
                title=f"Plugin update {'failed' if failed else 'available'}: {plugin_id}",
                body=(
                    f"Version {version} could not be activated. The previous package is retained; inspect Plugin Manager diagnostics."
                    if failed
                    else f"Version {version} is available (installed: {update['current_version']})."
                ),
                poster_url=None,
                event_at=now,
                dedupe_key=dedupe_key,
            )
        )


@router.post("/updates/check")
async def check_plugin_updates(
    admin: User = Depends(get_plugin_manager_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    updates: list[dict[str, Any]] = []
    for plugin in await runtime._installed_plugins():
        try:
            update = await _check_plugin_update(plugin, admin)
        except HTTPException as exc:
            update = {
                "plugin_id": plugin.get("plugin_id"),
                "current_version": plugin.get("version"),
                "update_available": False,
                "error": str(exc.detail),
            }
        updates.append(update)
        manager_state().patch(str(plugin["plugin_id"]), available_update=update)
        await _notify_plugin_update(db, update)
    await db.commit()
    return {
        "updates": updates,
        "available": sum(bool(item.get("update_available")) for item in updates),
        "checked_at": int(time.time()),
    }
