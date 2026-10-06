"""Administrator CSS theme installation and public pre-login appearance assets."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool

from src.core.auth import get_current_admin
from src.core.theme_packages import (
    MAX_THEME_UPLOAD,
    ThemeStore,
    get_theme_store,
    inspect_theme_package,
)

router = APIRouter(prefix="/api/themes", tags=["themes"])
Store = Annotated[ThemeStore, Depends(get_theme_store)]
_THEME_FILE = File(...)
_ADMIN = [Depends(get_current_admin)]


class ThemeEnabled(BaseModel):
    """Administrator toggle for an already reviewed package."""

    model_config = ConfigDict(extra="forbid", strict=True)
    enabled: bool


class ThemeDefault(BaseModel):
    """Server appearance default, with native as the explicit reset choice."""

    model_config = ConfigDict(extra="forbid", strict=True)
    theme_id: str = Field(min_length=1, max_length=128)


@router.get("")
def list_themes(store: Store) -> dict:
    """Expose enabled cosmetic choices before login and OIDC redirects."""
    return store.catalogue()


@router.get("/manage", dependencies=_ADMIN)
def manage_themes(store: Store) -> dict:
    """List disabled packages as well as enabled packages for administrators."""
    return store.catalogue(administration=True)


@router.post("/install/preview", dependencies=_ADMIN)
async def preview_theme(file: UploadFile = _THEME_FILE) -> dict:
    """Review metadata only after validating every member of the bounded archive."""
    try:
        package = await run_in_threadpool(
            inspect_theme_package, await file.read(MAX_THEME_UPLOAD + 1)
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {**package.manifest.model_dump(), "digest": package.digest}


@router.post("/install", status_code=201, dependencies=_ADMIN)
async def install_theme(store: Store, file: UploadFile = _THEME_FILE) -> dict:
    """Install reviewed CSS without a worker, permission prompts or automatic updates."""
    try:
        package = await run_in_threadpool(
            inspect_theme_package, await file.read(MAX_THEME_UPLOAD + 1)
        )
        return await run_in_threadpool(store.install, package)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.put("/default", dependencies=_ADMIN)
def set_theme_default(payload: ThemeDefault, store: Store) -> dict:
    """Choose one installed theme as the optional server default."""
    try:
        return store.set_default(payload.theme_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.patch("/{theme_id}", dependencies=_ADMIN)
def configure_theme(theme_id: str, payload: ThemeEnabled, store: Store) -> dict:
    """Change availability without deleting installed assets or personal choices."""
    try:
        return store.configure(theme_id, payload.enabled)
    except KeyError as exc:
        raise HTTPException(404, "Theme is not installed.") from exc


@router.delete("/{theme_id}", status_code=204, dependencies=_ADMIN)
def remove_theme(theme_id: str, store: Store) -> None:
    """Remove exactly one installed theme; executable plugins are independent."""
    try:
        store.remove(theme_id)
    except KeyError as exc:
        raise HTTPException(404, "Theme is not installed.") from exc


@router.get("/assets/{theme_id}/{digest}/{asset_path:path}")
def theme_asset(theme_id: str, digest: str, asset_path: str, store: Store) -> FileResponse:
    """Serve current cosmetic assets with stable digest URLs and no document scripts."""
    try:
        path = store.asset(theme_id, digest, asset_path)
    except (KeyError, ValueError) as exc:
        raise HTTPException(404, "Theme asset not found.") from exc
    return FileResponse(
        path,
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox",
        },
    )
