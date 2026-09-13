from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.settings import get_or_create_app_integration_settings
from src.core.auth import get_current_admin
from src.core.crypto import encrypt_secret
from src.core.provider_credentials import apply_deployment_provider_credentials
from src.database.models.oidc_settings import OidcSettings
from src.database.models.user import User
from src.database.session import get_db

router = APIRouter(
    prefix="/api/settings/deployment", tags=["settings"], dependencies=[Depends(get_current_admin)]
)


class DeploymentSettingsRequest(BaseModel):
    steamgriddb_api_key: str | None = None
    retroachievements_api_key: str | None = None
    giantbomb_api_key: str | None = None
    igdb_client_id: str | None = None
    igdb_client_secret: str | None = None
    screenscraper_ssid: str | None = None
    screenscraper_sspassword: str | None = None
    screenscraper_devid: str | None = None
    screenscraper_devpassword: str | None = None
    xbox_client_id: str | None = None
    xbox_client_secret: str | None = None
    oidc_issuer_url: str | None = None
    oidc_client_id: str | None = None
    oidc_client_secret: str | None = None
    oidc_scopes: str | None = None
    oidc_redirect_uri: str | None = None
    oidc_groups_claim: str | None = None
    oidc_admin_group: str | None = None


_SECRET_FIELDS = {
    "steamgriddb_api_key",
    "retroachievements_api_key",
    "giantbomb_api_key",
    "igdb_client_secret",
    "screenscraper_sspassword",
    "screenscraper_devpassword",
    "xbox_client_secret",
}
_SAFE_PROVIDER_FIELDS = {
    "igdb_client_id",
    "screenscraper_ssid",
    "screenscraper_devid",
    "xbox_client_id",
}


async def _oidc_row(db: AsyncSession) -> OidcSettings:
    row = await db.scalar(select(OidcSettings).limit(1))
    if row is None:
        row = OidcSettings()
        db.add(row)
        await db.flush()
    return row


async def get_deployment_settings(db: AsyncSession, admin: User) -> dict:
    del admin
    app = await get_or_create_app_integration_settings(db)
    oidc = await _oidc_row(db)
    providers = {field: getattr(app, field) for field in _SAFE_PROVIDER_FIELDS}
    for field in _SECRET_FIELDS:
        providers[field + "_configured"] = bool(getattr(app, field))
    return {
        "providers": providers,
        "oidc": {
            "issuer_url": oidc.issuer_url,
            "client_id": oidc.client_id,
            "scopes": oidc.scopes,
            "redirect_uri": oidc.redirect_uri,
            "groups_claim": oidc.groups_claim,
            "admin_group": oidc.admin_group,
            "client_secret_configured": bool(oidc.client_secret),
        },
    }


@router.get("")
async def read_deployment_settings(
    db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)
) -> dict:
    return await get_deployment_settings(db, admin)


@router.put("")
async def update_deployment_settings(
    payload: DeploymentSettingsRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> dict:
    app = await get_or_create_app_integration_settings(db)
    oidc = await _oidc_row(db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field.startswith("oidc_"):
            if field == "oidc_client_secret":
                if value:
                    oidc.client_secret = encrypt_secret(value)
            elif value is not None:
                setattr(oidc, field.removeprefix("oidc_"), value or None)
        elif field in _SECRET_FIELDS:
            if value:
                setattr(app, field, encrypt_secret(value))
        elif field in _SAFE_PROVIDER_FIELDS:
            setattr(app, field, value or None)
    await db.commit()
    apply_deployment_provider_credentials(app)
    return await get_deployment_settings(db, admin)
