"""Common episode validation shared by anime and television APIs."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EpisodeUpdateBase(BaseModel):
    """Partial update for a single episode — only the two fields a user
    can actually change; everything else is provider-synced."""

    watched: bool | None = None
    rating: Decimal | None = Field(default=None, ge=0, le=10)
    note: str | None = Field(default=None, max_length=2000)


class EpisodesBulkWatchedBase(BaseModel):
    """Sets `watched` on a batch of episodes in one request — a range
    select or "mark watched up to here" shouldn't cost one round trip
    per episode, especially on a 500+ episode season."""

    episode_ids: list[UUID] = Field(min_length=1, max_length=2000)
    watched: bool


class EpisodeReadBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    season_id: UUID
    episode_number: int
    title: str | None
    description: str | None
    air_date: date | None
    runtime_minutes: int | None
    still_url: str | None
    watched: bool
    rating: Decimal | None
    note: str | None = None
    created_at: int
    updated_at: int
