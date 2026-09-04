"""API routes for app/user Settings — scan (metadata) preferences,
per-user metadata-provider credentials, and read-only server config the
frontend needs to display (e.g. upload limits)."""

import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.scan_settings import ScanSettingsRead, ScanSettingsUpdate
from src.core.auth import get_current_user
from src.core.config import settings
from src.core.crypto import decrypt_secret, encrypt_secret
from src.database.models.user import User
from src.database.models.user_scan_settings import UserScanSettings
from src.database.session import get_db
from src.features.metadata.games.giant_bomb import GiantBombClient, GiantBombError
from src.features.metadata.games.gog import GOGClient, GOGError
from src.features.metadata.games.retroachievements import RetroAchievementsClient, RetroAchievementsError
from src.features.metadata.games.screenscraper import ScreenScraperClient, ScreenScraperError
from src.features.metadata.games.xbox import XboxClient, XboxError

router = APIRouter(
    prefix="/api/settings",
    tags=["settings"],
    dependencies=[Depends(get_current_user)],
)

# provider key -> [(payload field name, User column name, is Fernet-encrypted)]
PROVIDER_FIELD_MAP: dict[str, list[tuple[str, str, bool]]] = {
    "RetroAchievements": [("api_key", "retroachievements_api_key", False)],
    "GiantBomb": [("api_key", "giantbomb_api_key", False)],
    "ScreenScraper": [("ssid", "screenscraper_ssid", False), ("sspassword", "screenscraper_sspassword", True)],
    "Xbox": [("client_id", "xbox_client_id", False), ("client_secret", "xbox_client_secret", True)],
    "GOG": [("refresh_token", "gog_refresh_token", True)],
}

_ProviderClientError = (RetroAchievementsError, GiantBombError, ScreenScraperError, XboxError, GOGError)


def _validate_provider(provider: str, user: User) -> dict:
    """Builds the right client for `provider` from the user's stored
    credentials and calls its `.validate()`. Raises one of
    `_ProviderClientError` on failure."""
    if provider == "RetroAchievements":
        return RetroAchievementsClient(user.retroachievements_api_key or "").validate()
    if provider == "GiantBomb":
        return GiantBombClient(user.giantbomb_api_key or "").validate()
    if provider == "ScreenScraper":
        return ScreenScraperClient(
            devid=settings.SCREENSCRAPER_DEVID or "",
            devpassword=settings.SCREENSCRAPER_DEVPASSWORD or "",
            ssid=user.screenscraper_ssid or "",
            sspassword=decrypt_secret(user.screenscraper_sspassword) if user.screenscraper_sspassword else "",
        ).validate()
    if provider == "Xbox":
        return XboxClient(
            user.xbox_client_id or "",
            decrypt_secret(user.xbox_client_secret) if user.xbox_client_secret else "",
        ).validate()
    if provider == "GOG":
        return GOGClient(decrypt_secret(user.gog_refresh_token) if user.gog_refresh_token else "").validate()
    raise ValueError(f"Unknown provider: {provider}")


class ProviderCredentialsRequest(BaseModel):
    fields: dict[str, str]


async def get_or_create_scan_settings(user_id: UUID, db: AsyncSession) -> UserScanSettings:
    """Every user gets a scan-settings row lazily, on first access, rather
    than needing one created at signup time."""
    scan_settings = await db.scalar(
        select(UserScanSettings).where(UserScanSettings.user_id == user_id)
    )
    if scan_settings is None:
        scan_settings = UserScanSettings(user_id=user_id)
        db.add(scan_settings)
        await db.commit()
        await db.refresh(scan_settings)
    return scan_settings


@router.get("/scan", response_model=ScanSettingsRead)
async def get_scan_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserScanSettings:
    """Return the caller's metadata-scan preferences (provider order, which
    fields a search result is allowed to save)."""
    return await get_or_create_scan_settings(current_user.id, db)


@router.put("/scan", response_model=ScanSettingsRead)
async def update_scan_settings(
    payload: ScanSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserScanSettings:
    """Update the caller's metadata-scan preferences."""
    scan_settings = await get_or_create_scan_settings(current_user.id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(scan_settings, field, value)
    await db.commit()
    await db.refresh(scan_settings)
    return scan_settings


@router.get("/upload-limits")
async def get_upload_limits() -> dict[str, int]:
    """Read-only — the effective max upload size, set server-wide via
    MAX_UPLOAD_SIZE_MB. Not user-editable from Settings."""
    return {"max_upload_size_mb": settings.MAX_UPLOAD_SIZE_MB}


@router.get("/provider-credentials")
async def get_provider_credentials(current_user: User = Depends(get_current_user)) -> dict[str, dict]:
    """Status for every per-user metadata-provider credential, plus the two
    app-wide-only providers (IGDB, and ScreenScraper's server half) for
    display purposes. Does not re-validate against each provider on every
    call — that would mean a live network round-trip per provider on every
    Settings page load. Save (PUT) is the only place a fresh "connected"
    vs "error" state gets surfaced; this just reports whether credentials
    are present."""
    result: dict[str, dict] = {}
    for provider, field_map in PROVIDER_FIELD_MAP.items():
        configured = all(getattr(current_user, column) for _, column, _ in field_map)
        result[provider] = {"status": "configured" if configured else "not_configured"}
    result["IGDB"] = {
        "status": "configured" if (settings.IGDB_CLIENT_ID and settings.IGDB_CLIENT_SECRET) else "not_configured",
    }
    result["ScreenScraper"]["app_configured"] = bool(
        settings.SCREENSCRAPER_DEVID and settings.SCREENSCRAPER_DEVPASSWORD
    )
    return result


@router.put("/provider-credentials/{provider}")
async def save_provider_credentials(
    provider: str,
    payload: ProviderCredentialsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str | None]:
    field_map = PROVIDER_FIELD_MAP.get(provider)
    if field_map is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown provider: {provider}")

    for payload_field, column, encrypted in field_map:
        value = payload.fields.get(payload_field)
        if value is None:
            continue
        value = value.strip()
        setattr(current_user, column, encrypt_secret(value) if (encrypted and value) else (value or None))
    await db.commit()

    try:
        result = await asyncio.to_thread(_validate_provider, provider, current_user)
    except _ProviderClientError as exc:
        return {"provider": provider, "status": "error", "detail": str(exc)}

    connected = result.get("validated", True)
    return {"provider": provider, "status": "connected" if connected else "saved", "detail": None}


@router.delete("/provider-credentials/{provider}")
async def delete_provider_credentials(
    provider: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    field_map = PROVIDER_FIELD_MAP.get(provider)
    if field_map is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown provider: {provider}")

    for _, column, _ in field_map:
        setattr(current_user, column, None)
    await db.commit()
    return {"provider": provider, "status": "not_configured"}
