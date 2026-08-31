from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Date, DateTime, Enum as SAEnum, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base

# Folder name rules: letters, digits, underscore, hyphen only — no spaces,
# no path separators, no reserved filesystem characters. Adjust the
# character class here and in schemas/game.py if you want to allow more.
FOLDER_NAME_PATTERN = r"^[A-Za-z0-9_-]+$"
FOLDER_NAME_MAX_LENGTH = 150


class GameStatus(str, Enum):
    """Game status aligned with Playnite."""
    DROPPED = "DROPPED"
    WISHLIST = "WISHLIST"
    BACKLOG = "BACKLOG"
    ON_HOLD = "ON_HOLD"
    PLAYING = "PLAYING"
    PLAYED = "PLAYED"
    BEATEN = "BEATEN"
    MASTERED = "MASTERED"
    

class Game(Base):
    __tablename__ = "games"

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )


    folder_location: Mapped[str | None] = mapped_column(
        String(FOLDER_NAME_MAX_LENGTH),
        unique=True,
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Basic metadata
    # ------------------------------------------------------------------

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    sort_title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    release_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    developer: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    publisher: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    series: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    tags: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=list,
    )

    features: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=list,
    )

    # ------------------------------------------------------------------
    # Personal library state
    # ------------------------------------------------------------------

    status: Mapped[GameStatus] = mapped_column(
        SAEnum(GameStatus, native_enum=False, length=30),
        nullable=False,
        default=GameStatus.WISHLIST,
    )

    priority: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    favorite: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    resume_note: Mapped[str | None] = mapped_column(
        String(2_000),
        nullable=True,
    )

    playtime_seconds: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )


    # ------------------------------------------------------------------
    # Ratings
    # ------------------------------------------------------------------

    rating_story: Mapped[Decimal | None] = mapped_column(
        Numeric(4, 2),
        nullable=True,
    )

    rating_gameplay: Mapped[Decimal | None] = mapped_column(
        Numeric(4, 2),
        nullable=True,
    )

    rating_soundtrack: Mapped[Decimal | None] = mapped_column(
        Numeric(4, 2),
        nullable=True,
    )


    rating_overall: Mapped[Decimal | None] = mapped_column(
        Numeric(4, 2),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Personal ranking
    # ------------------------------------------------------------------

    personal_rank: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
