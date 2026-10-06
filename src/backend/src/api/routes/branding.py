"""Public branding reads; administrator-only name and image changes."""

from hashlib import sha256
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from src.core.app_integrations import get_or_create_app_integration_settings
from src.core.auth import get_current_admin
from src.core.branding import (
    DEFAULT_APP_NAME,
    DEFAULT_ICON,
    MAX_BRANDING_BYTES,
    load_branding,
    normalize_branding_image,
    public_branding,
)
from src.database.session import get_db

router = APIRouter(prefix="/api/branding", tags=["branding"])
AssetKind = Literal["logo", "favicon"]
_DB = Depends(get_db)
_FILE = File(...)


class BrandingUpdate(BaseModel):
    """Names are plain text; no remote HTML, styles or URLs can be configured."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    app_name: str = Field(min_length=1, max_length=64)

    @field_validator("app_name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        """Reject control characters in the public plain-text identity."""
        if not value.isprintable():
            raise ValueError("Application name must be printable text.")
        return value


@router.get("")
async def get_branding(db: AsyncSession = _DB) -> dict[str, str | None]:
    """Available before login so public and signed-in pages share one identity."""
    return public_branding(await load_branding(db))


@router.put("", dependencies=[Depends(get_current_admin)])
async def update_branding(payload: BrandingUpdate, db: AsyncSession = _DB) -> dict[str, str | None]:
    """Save the deployment name while preserving integrations and assets."""
    row = await get_or_create_app_integration_settings(db)
    row.branding_name = None if payload.app_name == DEFAULT_APP_NAME else payload.app_name
    await db.commit()
    return public_branding(row)


@router.post("/assets/{kind}", dependencies=[Depends(get_current_admin)])
async def upload_branding_asset(
    kind: AssetKind, file: UploadFile = _FILE, db: AsyncSession = _DB
) -> dict[str, str | None]:
    """Normalize and replace one administrator-owned identity image."""
    # Read one byte beyond the cap to reject oversized uploads without buffering
    # arbitrary bodies. Decode format rather than trusting the submitted MIME.
    data = await file.read(MAX_BRANDING_BYTES + 1)
    try:
        normalized = await run_in_threadpool(normalize_branding_image, data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    row = await get_or_create_app_integration_settings(db)
    setattr(row, f"branding_{kind}_png", normalized)
    await db.commit()
    return public_branding(row)


@router.delete("/assets/{kind}", dependencies=[Depends(get_current_admin)])
async def remove_branding_asset(kind: AssetKind, db: AsyncSession = _DB) -> dict[str, str | None]:
    """Clear one image without changing the other image or the application name."""
    row = await get_or_create_app_integration_settings(db)
    setattr(row, f"branding_{kind}_png", None)
    await db.commit()
    return public_branding(row)


@router.get("/default-icon.svg")
async def default_branding_icon() -> Response:
    """Serve the host-owned default mark without requiring a login."""
    return Response(
        DEFAULT_ICON,
        media_type="image/svg+xml",
        headers={
            "Cache-Control": "public, max-age=3600",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/assets/{kind}/{revision}.png")
async def get_branding_asset(kind: AssetKind, revision: str, db: AsyncSession = _DB) -> Response:
    """Serve only the current, content-addressed inert identity image."""
    row = await load_branding(db)
    data = getattr(row, f"branding_{kind}_png", None) if row else None
    if not data or sha256(data).hexdigest() != revision:
        raise HTTPException(status_code=404, detail="Branding asset is unavailable.")
    return Response(
        data,
        media_type="image/png",
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "X-Content-Type-Options": "nosniff",
        },
    )
