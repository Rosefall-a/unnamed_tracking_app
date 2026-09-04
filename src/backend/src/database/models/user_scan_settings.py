from __future__ import annotations

import time
from uuid import UUID, uuid4

from sqlalchemy import Boolean, ForeignKey, JSON, BigInteger
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base

DEFAULT_PROVIDER_ORDER = [
    "Steam",
    "IGDB",
    "GiantBomb",
    "RetroAchievements",
    "SteamGridDB",
    "ScreenScraper",
    "HowLongToBeat",
]


class UserScanSettings(Base):
    """Per-user metadata search preferences — provider priority and which
    fields a search result is allowed to save. One row per user."""

    __tablename__ = "user_scan_settings"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    provider_order: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=lambda: list(DEFAULT_PROVIDER_ORDER)
    )
    save_developer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    save_publisher: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    save_series: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    save_tags: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    save_features: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    save_description: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    save_age_rating: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    save_release_date: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    save_time_to_beat: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False, default=time.time)
    updated_at: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=time.time,
        onupdate=time.time,
    )
