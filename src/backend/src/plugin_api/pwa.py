"""Host-owned, public PWA infrastructure with permissioned inert contributions."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from src.core.branding import load_branding, pwa_branding_icon
from src.database.models.plugin_permissions import PluginPermissionGrant
from src.database.session import get_db
from src.plugin_api.contracts import PluginPwaDeclaration
from src.plugin_api.grants import installation_is_executable
from src.plugin_api.pwa_contract import validate_pwa_assets
from src.plugin_api.runtime_client import (
    PluginRuntimeClient,
    PluginRuntimeRequestError,
    PluginRuntimeUnavailable,
)

router = APIRouter(tags=["pwa"])
client = PluginRuntimeClient()
_DB = Depends(get_db)
_ASSETS = Path(__file__).with_name("pwa_assets")
_HEADERS = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}
_OFFLINE_CSP = (
    "default-src 'none'; style-src 'self' 'unsafe-inline'; "
    "script-src 'unsafe-inline'; img-src 'self'; font-src 'self'"
)


def host_asset_revision() -> str:
    """Retire cached reconnect pages when reviewed host assets or policy change."""
    digest = hashlib.sha256(_OFFLINE_CSP.encode())
    for name in ("service-worker.js", "offline.html"):
        digest.update((_ASSETS / name).read_bytes())
    return digest.hexdigest()


_HOST_ASSET_REVISION = host_asset_revision()


async def provider(db: AsyncSession) -> dict[str, Any] | None:
    """Require one healthy provider with an installation-wide explicit grant."""
    try:
        installed = await client.plugins()
    except (PluginRuntimeUnavailable, PluginRuntimeRequestError) as exc:
        raise HTTPException(status_code=503, detail="PWA runtime unavailable") from exc
    candidates = []
    for plugin in installed:
        if not installation_is_executable(plugin) or not plugin.get("pwa"):
            continue
        try:
            installation_id = UUID(str(plugin["installation_id"]))
            declaration = PluginPwaDeclaration.model_validate(plugin["pwa"])
        except (ValueError, KeyError):
            continue
        grant = await db.scalar(
            select(PluginPermissionGrant.id).where(
                PluginPermissionGrant.plugin_id == plugin["plugin_id"],
                PluginPermissionGrant.installation_id == installation_id,
                PluginPermissionGrant.capability == "frontend.pwa",
                PluginPermissionGrant.capability_version == 1,
                PluginPermissionGrant.user_id.is_(None),
                PluginPermissionGrant.device_id.is_(None),
                PluginPermissionGrant.revoked_at.is_(None),
            )
        )
        if grant is not None:
            candidates.append({**plugin, "declaration": declaration})
    if len(candidates) > 1:
        raise HTTPException(
            status_code=409, detail="Multiple PWA providers are enabled; enable only one"
        )
    if not candidates:
        return None
    return {**candidates[0], "branding": await load_branding(db)}


def generation(plugin: dict[str, Any]) -> str:
    """Bind cache identity to the installation, branding and reviewed host assets."""
    identity = [
        plugin["plugin_id"],
        plugin["installation_id"],
        plugin["version"],
        plugin["digest"],
        _HOST_ASSET_REVISION,
    ]
    branding = plugin.get("branding")
    if branding and (
        branding.branding_name or branding.branding_logo_png or branding.branding_favicon_png
    ):
        identity.extend(
            [
                branding.branding_name,
                hashlib.sha256(branding.branding_logo_png or b"").hexdigest(),
                hashlib.sha256(branding.branding_favicon_png or b"").hexdigest(),
            ]
        )
    return hashlib.sha256(json.dumps(identity).encode()).hexdigest()


async def checked_assets(plugin: dict[str, Any]) -> dict[str, bytes]:
    """Revalidate the live contribution before exposing any install metadata."""
    declaration = plugin["declaration"]
    try:
        files = {
            path: await client.pwa_asset(plugin["plugin_id"], path)
            for path in (declaration.manifest, *declaration.icons)
        }
        validate_pwa_assets(declaration, files)
        return files
    except (
        ValueError,
        KeyError,
        OSError,
        PluginRuntimeRequestError,
        PluginRuntimeUnavailable,
    ) as exc:
        raise HTTPException(status_code=503, detail="PWA assets unavailable or invalid") from exc


@router.get("/pwa/status")
async def status(db: AsyncSession = _DB) -> JSONResponse:
    """Publish only non-sensitive provider state, without requiring a session."""
    plugin = await provider(db)
    if plugin is None:
        return JSONResponse({"enabled": False}, headers=_HEADERS)
    await checked_assets(plugin)
    return JSONResponse(
        {
            "enabled": True,
            "plugin_id": plugin["plugin_id"],
            "version": plugin["version"],
            "generation": generation(plugin),
        },
        headers=_HEADERS,
    )


@router.get("/manifest.webmanifest")
async def manifest(db: AsyncSession = _DB) -> Response:
    """Construct a root manifest from typed metadata, never plugin scripts."""
    plugin = await provider(db)
    if plugin is None:
        raise HTTPException(status_code=404, detail="PWA plugin is not enabled")
    await checked_assets(plugin)
    declaration = plugin["declaration"]
    branding = plugin.get("branding")
    name = branding.branding_name if branding else None
    data = {
        "id": "/",
        "start_url": "/?pwa=1",
        "scope": "/",
        "display": "standalone",
        "name": name or declaration.name,
        "short_name": name or declaration.short_name,
        "theme_color": declaration.theme_color,
        "background_color": declaration.background_color,
        "icons": [
            {
                "src": f"/pwa/icons/{generation(plugin)}/{size}.png",
                "sizes": f"{size}x{size}",
                "type": "image/png",
                "purpose": "any maskable",
            }
            for size in (192, 512)
        ],
    }
    return Response(json.dumps(data), media_type="application/manifest+json", headers=_HEADERS)


@router.get("/pwa/icons/{revision}/{size}.png")
async def icon(revision: str, size: int, db: AsyncSession = _DB) -> Response:
    """Serve inert icons only for the current live package generation."""
    plugin = await provider(db)
    if plugin is None or revision != generation(plugin) or size not in {192, 512}:
        raise HTTPException(status_code=404, detail="PWA icon not available")
    files = await checked_assets(plugin)
    branding = plugin.get("branding")
    image = (branding.branding_logo_png or branding.branding_favicon_png) if branding else None
    if image:
        content = await run_in_threadpool(
            pwa_branding_icon, image, size, plugin["declaration"].background_color
        )
        return Response(content, media_type="image/png", headers=_HEADERS)
    return Response(files[f"pwa/icon-{size}.png"], media_type="image/png", headers=_HEADERS)


@router.get("/pwa/offline.html")
async def offline() -> Response:
    """Serve a host-reviewed neutral reconnect page with no account data."""
    return Response(
        (_ASSETS / "offline.html").read_bytes(),
        media_type="text/html",
        headers={
            **_HEADERS,
            "Content-Security-Policy": _OFFLINE_CSP,
        },
    )


@router.get("/service-worker.js")
async def worker(db: AsyncSession = _DB) -> Response:
    """Keep the stable root worker URL alive even for affirmative withdrawal."""
    plugin = await provider(db)
    if plugin is not None:
        await checked_assets(plugin)
    config = {
        "enabled": plugin is not None,
        "generation": generation(plugin) if plugin else "disabled",
    }
    script = (_ASSETS / "service-worker.js").read_text(encoding="utf-8")
    return Response(
        "const PWA = " + json.dumps(config) + ";\n" + script,
        media_type="text/javascript",
        headers={**_HEADERS, "Service-Worker-Allowed": "/"},
    )
