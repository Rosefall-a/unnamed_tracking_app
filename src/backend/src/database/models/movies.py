import time
from datetime import date
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    Enum as SAEnum,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base


class MovieStatus(str, Enum):
    """Movie status aligned with a media library workflow."""

    DROPPED = "DROPPED"
    WISHLIST = "WISHLIST"
    WATCHLIST = "WATCHLIST"
    BACKLOG = "BACKLOG"
    IN_PROGRESS = "IN_PROGRESS"
    WATCHED = "WATCHED"
    FAVORITE = "FAVORITE"
    REWATCH = "REWATCH"


class Movie(Base):
    __tablename__ = "movies"

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
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

    runtime_minutes: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    director: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    writer: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    studios: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=list,
    )

    countries: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=list,
    )

    languages: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=list,
    )

    genres: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=list,
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

    age_rating: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    tmdb_score: Mapped[Decimal | None] = mapped_column(
        Numeric(4, 2),
        nullable=True,
    )

    source: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Personal library state
    # ------------------------------------------------------------------

    status: Mapped[MovieStatus] = mapped_column(
        SAEnum(MovieStatus, native_enum=False, length=30),
        nullable=False,
        default=MovieStatus.WISHLIST,
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

    rewatches: Mapped[int] = mapped_column(
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

    rating_performance: Mapped[Decimal | None] = mapped_column(
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

    created_at: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=time.time,
    )

    updated_at: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=time.time,
        onupdate=time.time,
    )
