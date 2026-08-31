from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.database.models.game import GameStatus


class GameBase(BaseModel):
    """Fields shared by create and update payloads."""

    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    release_date: date | None = None
    developer: str | None = Field(default=None, max_length=200)
    publisher: str | None = Field(default=None, max_length=200)

    status: GameStatus = GameStatus.NOT_PLAYED
    priority: str | None = Field(default=None, max_length=20)
    favorite: bool = False
    notes: str | None = None
    resume_note: str | None = Field(default=None, max_length=2_000)
    playtime_seconds: int = Field(default=0, ge=0)

    rating_story: Decimal | None = Field(default=None, ge=0, le=10)
    rating_gameplay: Decimal | None = Field(default=None, ge=0, le=10)
    rating_soundtrack: Decimal | None = Field(default=None, ge=0, le=10)
    rating_overall: Decimal | None = Field(default=None, ge=0, le=10)

    personal_rank: int | None = None


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

    status: GameStatus | None = None
    priority: str | None = Field(default=None, max_length=20)
    favorite: bool | None = None
    notes: str | None = None
    resume_note: str | None = Field(default=None, max_length=2_000)
    playtime_seconds: int | None = Field(default=None, ge=0)

    rating_story: Decimal | None = Field(default=None, ge=0, le=10)
    rating_gameplay: Decimal | None = Field(default=None, ge=0, le=10)
    rating_soundtrack: Decimal | None = Field(default=None, ge=0, le=10)
    rating_presentation: Decimal | None = Field(default=None, ge=0, le=10)
    rating_enjoyment: Decimal | None = Field(default=None, ge=0, le=10)
    rating_overall: Decimal | None = Field(default=None, ge=0, le=10)
    rating_confidence: Decimal | None = Field(default=None, ge=0, le=10)

    personal_rank: int | None = None


class GameRead(GameBase):
    """Full representation returned to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sort_title: str
    created_at: datetime
    updated_at: datetime