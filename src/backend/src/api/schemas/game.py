from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from src.database.models.game import (
    FOLDER_NAME_MAX_LENGTH,
    FOLDER_NAME_PATTERN,
    GameStatus,
)


class GamePlatformData(BaseModel):
    platform: str = Field(min_length=1, max_length=50)
    playtime_seconds: int = Field(default=0, ge=0)
    completion_percent: Decimal | None = Field(default=None, ge=0, le=100)
    last_played_at: int | None = Field(default=None, ge=0)
from src.helpers.currency_codes import CURRENCY_CODES


class GameBase(BaseModel):
    """Fields shared by create and update payloads."""

    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    release_date: date | None = None
    developer: str | None = Field(default=None, max_length=200)
    publisher: str | None = Field(default=None, max_length=200)
    series: str | None = Field(default=None, max_length=200)
    tags: list[str] = Field(default_factory=list)
    features: list[str] = Field(default_factory=list)
    source: str | None = Field(default=None, max_length=50)
    age_rating: str | None = Field(default=None, max_length=20)

    folder_location: str = Field(
        min_length=1,
        max_length=FOLDER_NAME_MAX_LENGTH,
        pattern=FOLDER_NAME_PATTERN,
        description="Folder name only — letters, digits, underscore, hyphen. No spaces or path separators.",
    )

    status: GameStatus = GameStatus.BACKLOG
    priority: str | None = Field(default=None, max_length=20)
    favorite: bool = False
    notes: str | None = None
    resume_note: str | None = Field(default=None, max_length=2_000)
    playtime_seconds: int = Field(default=0, ge=0)
    platforms: list[GamePlatformData] = Field(default_factory=list)

    purchase_date: int | None = Field(
        default=None,
        ge=0,
        description="Unix timestamp in seconds for the purchase date.",
    )
    purchase_price: Decimal | None = Field(default=None, ge=0)
    purchase_price_currency_code: str | None = Field(default=None, max_length=3)
    physical_condition: str | None = Field(default=None, max_length=200)

    rating_story: Decimal | None = Field(default=None, ge=0, le=10)
    rating_gameplay: Decimal | None = Field(default=None, ge=0, le=10)
    rating_soundtrack: Decimal | None = Field(default=None, ge=0, le=10)
    rating_overall: Decimal | None = Field(default=None, ge=0, le=10)

    personal_rank: int | None = None

    @field_validator("purchase_price_currency_code")
    @classmethod
    def validate_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.upper()

        if value not in CURRENCY_CODES:
            raise ValueError(f"Invalid currency code: {value}")

        return value


class GameCreate(GameBase):
    """Payload for creating a game. sort_title is derived if not given."""

    sort_title: str | None = Field(default=None, max_length=500)


class GameUpdate(BaseModel):
    """Payload for partial updates — every field optional."""

    title: str | None = Field(default=None, min_length=1, max_length=500)
    sort_title: str | None = Field(default=None, max_length=500)
    description: str | None = None
    release_date: date | None = None
    developer: str | None = Field(default=None, max_length=200)
    publisher: str | None = Field(default=None, max_length=200)
    series: str | None = Field(default=None, max_length=200)
    tags: list[str] | None = None
    features: list[str] | None = None
    source: str | None = Field(default=None, max_length=50)
    age_rating: str | None = Field(default=None, max_length=20)

    folder_location: str | None = Field(
        default=None,
        min_length=1,
        max_length=FOLDER_NAME_MAX_LENGTH,
        pattern=FOLDER_NAME_PATTERN,
    )

    status: GameStatus | None = None
    priority: str | None = Field(default=None, max_length=20)
    favorite: bool | None = None
    notes: str | None = None
    resume_note: str | None = Field(default=None, max_length=2_000)
    playtime_seconds: int | None = Field(default=None, ge=0)
    platforms: list[GamePlatformData] | None = None

    purchase_date: int | None = Field(
        default=None,
        ge=0,
        description="Unix timestamp in seconds for the purchase date.",
    )
    purchase_price: Decimal | None = Field(default=None, ge=0)
    purchase_price_currency_code: str | None = Field(default=None, max_length=3)
    physical_condition: str | None = Field(default=None, max_length=200)

    rating_story: Decimal | None = Field(default=None, ge=0, le=10)
    rating_gameplay: Decimal | None = Field(default=None, ge=0, le=10)
    rating_soundtrack: Decimal | None = Field(default=None, ge=0, le=10)
    rating_overall: Decimal | None = Field(default=None, ge=0, le=10)

    personal_rank: int | None = None

    @field_validator("purchase_price_currency_code")
    @classmethod
    def validate_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.upper()

        if value not in CURRENCY_CODES:
            raise ValueError(f"Invalid currency code: {value}")

        return value


class GameRead(GameBase):
    """Full representation returned to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    sort_title: str
    created_at: int = Field(description="Unix timestamp in seconds when the game was created.")
    updated_at: int = Field(description="Unix timestamp in seconds when the game was last updated.")

    @computed_field
    @property
    def total_playtime_seconds(self) -> int:
        """Sum of platform playtimes, or the stored game total when no platforms exist."""
        if self.platforms:
            return sum(platform.playtime_seconds for platform in self.platforms)
        return self.playtime_seconds
