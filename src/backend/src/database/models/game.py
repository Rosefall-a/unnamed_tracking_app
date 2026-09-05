import time
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Integer,
    Boolean,
    Column,
    Date,
    ForeignKey,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base

if TYPE_CHECKING:
    from src.database.models.user import User

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

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    user: Mapped["User"] = relationship()

    folder_location: Mapped[str] = mapped_column(
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

    age_rating: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    links: Mapped[list["GameLink"]] = relationship(
        back_populates="game",
        cascade="all, delete-orphan",
    )

    source: Mapped[str | None] = mapped_column(  # source (string — e.g. "Steam", "GOG", "physical")
        String(50),
        nullable=True,
    )

    how_long_to_beat: Mapped[int | None] = mapped_column( # Stored in seconds
        Integer,
        nullable=True
    )

    genre: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=list,
    )

    region: Mapped[str | None] = mapped_column(  # e.g. "NA", "PAL", "JP", "Global"
        String(50),
        nullable=True,
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

    hidden: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    resume_note: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True,
    )

    playtime_seconds: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )

    play_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    took_to_beat: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    platforms: Mapped[list["GamePlatform"]] = relationship(
        back_populates="game",
        cascade="all, delete-orphan",
    )
    # ownership ({ format: "digital" | "physical", purchase_date, price, condition })

    screenshots: Mapped[list["Screenshot"]] = relationship(
        back_populates="game",
        cascade="all, delete-orphan",
    )

    purchase_date: Mapped[int | None] = (
        mapped_column(  # Unix timestamp, midnight = no time set just date
            BigInteger,
            nullable=True,
        )
    )

    purchase_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    purchase_price_currency_code: Mapped[str | None] = mapped_column(  # ISO 4217 currency code
        String(3),  # Should always be uppercase
        nullable=True,
    )

    physical_condition: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
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


##########################
#          Links         #
##########################


class GameLink(Base):
    __tablename__ = "game_links"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    game_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("games.id"),
        nullable=False,
    )

    label: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    url: Mapped[str] = mapped_column(
        String(2_048),
        nullable=False,
    )

    game: Mapped["Game"] = relationship(
        back_populates="links",
    )


class GamePlatform(Base):
    __tablename__ = "game_platforms"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("games.id", ondelete="CASCADE"),
        nullable=False,
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    playtime_seconds: Mapped[int] = mapped_column(nullable=False, default=0)
    completion_percent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    last_played_at: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    game: Mapped["Game"] = relationship(back_populates="platforms")


##########################
#       Screenshots      #
##########################

# Screenshot name rules: if the caller doesn't supply one, we fall back to
# the original upload filename (minus extension), and if that's not usable
# either, to "<upload date>-<short unique id>". See save_game_screenshot.py.
SCREENSHOT_NAME_MAX_LENGTH = 255


class Screenshot(Base):
    __tablename__ = "screenshots"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    game_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("games.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(SCREENSHOT_NAME_MAX_LENGTH),
        nullable=False,
    )

    original_filename: Mapped[str | None] = mapped_column(  # filename as uploaded, kept for reference
        String(255),
        nullable=True,
    )

    extension: Mapped[str] = mapped_column(  # e.g. ".png", ".jpg" — the on-disk file is "<id><extension>"
        String(10),
        nullable=False,
    )

    content_type: Mapped[str | None] = mapped_column(  # e.g. "image/png"
        String(100),
        nullable=True,
    )

    tags: Mapped[list["ScreenshotTag"]] = relationship(
        secondary="screenshot_tag_links",
        back_populates="screenshots",
        order_by="ScreenshotTag.name",
        lazy="selectin",
    )

    file_size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    width: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    height: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    created_at: Mapped[int] = mapped_column(  # also serves as "upload date"
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

    game: Mapped["Game"] = relationship(back_populates="screenshots")


##########################
#     Screenshot Tags    #
##########################

# Many-to-many: a tag is scoped to a user (not a single game) and can be
# reused across every screenshot that user owns, across all their games.
screenshot_tag_links = Table(
    "screenshot_tag_links",
    Base.metadata,
    Column(
        "screenshot_id",
        PG_UUID(as_uuid=True),
        ForeignKey("screenshots.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        PG_UUID(as_uuid=True),
        ForeignKey("screenshot_tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class ScreenshotTag(Base):
    """A reusable, per-user tag. Renaming or deleting one applies everywhere it's attached."""

    __tablename__ = "screenshot_tags"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_screenshot_tags_user_id_name"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    created_at: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=time.time,
    )

    screenshots: Mapped[list["Screenshot"]] = relationship(
        secondary=screenshot_tag_links,
        back_populates="tags",
    )
