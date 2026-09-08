from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import get_current_admin, get_current_user
from src.database.models.global_settings import GlobalSettings
from src.database.models.user import User
from src.database.session import get_db
from src.helpers.currency_codes import CURRENCY_CODES

router = APIRouter(prefix="/api/settings", tags=["settings"])


class GlobalSettingsPayload(BaseModel):
    app_name: str = Field(min_length=1, max_length=200)
    default_currency_code: str = Field(min_length=3, max_length=3)
    timezone: str = Field(min_length=1, max_length=100)
    allow_registration: bool

    @field_validator("default_currency_code")
    @classmethod
    def validate_currency_code(cls, value: str) -> str:
        value = value.upper()
        if value not in CURRENCY_CODES:
            raise ValueError(f"Invalid currency code: {value}")
        return value


class GlobalSettingsResponse(GlobalSettingsPayload):
    id: int
    created_at: int
    updated_at: int


def _settings_response(settings: GlobalSettings) -> GlobalSettingsResponse:
    return GlobalSettingsResponse.model_validate(settings, from_attributes=True)


async def _get_or_create_settings(db: AsyncSession) -> GlobalSettings:
    settings = await db.get(GlobalSettings, 1)
    if settings is None:
        settings = GlobalSettings(id=1)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    return settings


@router.get("/global", response_model=GlobalSettingsResponse)
async def get_global_settings(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GlobalSettingsResponse:
    del user
    return _settings_response(await _get_or_create_settings(db))


@router.put("/global", response_model=GlobalSettingsResponse)
async def update_global_settings(
    payload: GlobalSettingsPayload,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> GlobalSettingsResponse:
    del admin
    settings = await _get_or_create_settings(db)
    for field, value in payload.model_dump().items():
        setattr(settings, field, value)
    await db.commit()
    await db.refresh(settings)
    return _settings_response(settings)
