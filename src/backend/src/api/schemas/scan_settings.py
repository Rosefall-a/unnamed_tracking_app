from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

VALID_PROVIDERS = {
    "Steam",
    "SteamGridDB",
    "IGDB",
    "RetroAchievements",
    "GiantBomb",
    "ScreenScraper",
    "HowLongToBeat",
}
ScanProvider = Literal[
    "Steam", "SteamGridDB", "IGDB", "RetroAchievements", "GiantBomb", "ScreenScraper", "HowLongToBeat"
]


class ScanSettingsUpdate(BaseModel):
    """Partial update — every field optional."""

    provider_order: list[ScanProvider] | None = Field(default=None, max_length=7)
    save_developer: bool | None = None
    save_publisher: bool | None = None
    save_series: bool | None = None
    save_tags: bool | None = None
    save_features: bool | None = None
    save_description: bool | None = None
    save_age_rating: bool | None = None
    save_release_date: bool | None = None
    save_time_to_beat: bool | None = None

    @field_validator("provider_order")
    @classmethod
    def validate_provider_order(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        if len(set(value)) != len(value):
            raise ValueError("provider_order cannot contain duplicates.")
        if not set(value).issubset(VALID_PROVIDERS):
            raise ValueError(f"provider_order values must be a subset of {sorted(VALID_PROVIDERS)}.")
        return value


class ScanSettingsRead(BaseModel):
    """Full representation returned to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    provider_order: list[str]
    save_developer: bool
    save_publisher: bool
    save_series: bool
    save_tags: bool
    save_features: bool
    save_description: bool
    save_age_rating: bool
    save_release_date: bool
    save_time_to_beat: bool
    created_at: int
    updated_at: int
