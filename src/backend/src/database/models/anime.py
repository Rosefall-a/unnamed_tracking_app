import time
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base

if TYPE_CHECKING:
    from src.database.models.user import User


class AnimeStatus(str, Enum):
    """Anime status aligned with a media library workflow — same value
    set as MovieStatus/TVShowStatus, shared here since a season also
    uses it."""

    DROPPED = "DROPPED"
    WISHLIST = "WISHLIST"
    WATCHLIST = "WATCHLIST"
    BACKLOG = "BACKLOG"
    IN_PROGRESS = "IN_PROGRESS"
    WATCHED = "WATCHED"
    FAVORITE = "FAVORITE"
    REWATCH = "REWATCH"


class Anime(Base):
    __tablename__ = "anime"

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user: Mapped["User"] = relationship()

    # set instead of actually deleting the row — same soft-delete
    # convention as Movie/TVShow/Game/Card. NULL means active/not deleted.
    deleted_at: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # ------------------------------------------------------------------
    # Basic metadata
    # ------------------------------------------------------------------

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    sort_title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_air_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # average minutes per episode
    episode_runtime_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # the animation studio(s) — anime's equivalent of TVShow.creators as
    # the primary credited-work field
    studios: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)

    countries: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    languages: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    genres: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    features: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)

    age_rating: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # the media sub-format (TV, Movie, OVA, ONA, Special, Music) as
    # reported by AniList/Jikan — distinct from `kind`, which is fixed to
    # "anime" for every row in this table; this is what actually varies
    # per entry and drives the "TV"/"Movie"/"OVA" label shown in the UI
    format: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # two external scores, matching how Movie/TVShow keep one provider's
    # score (tmdb_score) — here AniList and MyAnimeList (via Jikan) are
    # both real, independent sources worth keeping separately rather than
    # merging into one field
    anilist_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    mal_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)

    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # the source provider's own id for this show (MyAnimeList's id via
    # Jikan) — kept so episode sync can hit that exact show again later
    # instead of re-searching by title and hoping for an exact match
    external_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # AniList's own id, kept separately from external_id (which is MAL's)
    # — Jikan/MyAnimeList is unreliable (rate limits, occasional outages),
    # so episode sync tries it first when known but falls back to AniList's
    # streamingEpisodes data when Jikan is unavailable or external_id is
    # unknown. Two independent episode sources instead of one single point
    # of failure.
    anilist_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # NULL until the airing-check loop has actually looked (nothing to
    # filter on yet); True/False once AniList's own nextAiringEpisode
    # presence has been checked at least once. Lets the frequent
    # airing-check loop skip a show entirely once it's known to have
    # finished, instead of re-querying it every cycle forever.
    is_airing: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # a direct external URL (AniList's CDN / Jikan's image field), stored
    # as-is — same convention as Movie.poster_url, never downloaded/resized
    poster_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # a wide-format background image (AniList's bannerImage), distinct
    # from the portrait poster_url above — used for the detail page hero
    backdrop_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # names of fields an admin has manually changed away from what a
    # metadata provider last set — "Apply metadata" skips these instead
    # of silently overwriting a deliberate fix
    locked_fields: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)

    # The Related tab's {chain, branches, recommendations} payload from
    # AniList, cached after the first fetch instead of re-fetched on every
    # visit — a single load can already mean a dozen+ AniList requests
    # (one per prequel/sequel chain hop, one per branch-group reorder
    # lookup), and AniList's rate limit is shared and low. NULL means
    # never fetched yet.
    relations_cache: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    relations_cached_at: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # ------------------------------------------------------------------
    # Personal library state
    # ------------------------------------------------------------------

    status: Mapped[AnimeStatus] = mapped_column(
        SAEnum(AnimeStatus, native_enum=False, length=30),
        nullable=False,
        default=AnimeStatus.WISHLIST,
    )
    priority: Mapped[str | None] = mapped_column(String(20), nullable=True)
    favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rewatches: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # ------------------------------------------------------------------
    # Ratings
    # ------------------------------------------------------------------

    rating_story: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    rating_performance: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    rating_soundtrack: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    rating_overall: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)

    personal_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # eager (selectin, not the default lazy) — AnimeRead serializes
    # `seasons` straight into the API response (same reason as
    # Game.links / TVShow.seasons: a lazy load can't run once the async
    # session that produced the row is out of the request's await context)
    seasons: Mapped[list["AnimeSeason"]] = relationship(
        back_populates="show",
        order_by="AnimeSeason.season_number",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------

    created_at: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=lambda: int(time.time())
    )
    updated_at: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=lambda: int(time.time()),
        onupdate=lambda: int(time.time()),
    )


class AnimeSeason(Base):
    """One season/cour of an Anime — a real child row, not just a count,
    so progress and status can be tracked per season independently of the
    show overall. Most anime will carry exactly one season row (a new
    cour is usually its own separate AniList entry rather than a season
    of an existing one). `episodes_watched`/`episode_count` stay as the
    flat progress numbers used everywhere else in the app; `episodes`
    below is the optional richer per-episode breakdown."""

    __tablename__ = "anime_seasons"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    show_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("anime.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    show: Mapped["Anime"] = relationship(back_populates="seasons")

    season_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    episode_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    episodes_watched: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    status: Mapped[AnimeStatus] = mapped_column(
        SAEnum(AnimeStatus, native_enum=False, length=30, name="animeseasonstatus"),
        nullable=False,
        default=AnimeStatus.WISHLIST,
    )
    air_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    poster_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    episodes: Mapped[list["AnimeEpisode"]] = relationship(
        back_populates="season",
        order_by="AnimeEpisode.episode_number",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    created_at: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=lambda: int(time.time())
    )
    updated_at: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=lambda: int(time.time()),
        onupdate=lambda: int(time.time()),
    )


class AnimeEpisode(Base):
    """One episode of an AnimeSeason. Rows are synced in from the source
    provider (Jikan/MyAnimeList) the first time a season's episode list
    is requested, then persisted here — later requests read straight from
    this table instead of re-fetching, and `watched`/`rating` are purely
    local, never touched by a re-sync."""

    __tablename__ = "anime_episodes"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    season_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("anime_seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    season: Mapped["AnimeSeason"] = relationship(back_populates="episodes")

    episode_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    air_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    runtime_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    still_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    watched: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rating: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)

    created_at: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=lambda: int(time.time())
    )
    updated_at: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=lambda: int(time.time()),
        onupdate=lambda: int(time.time()),
    )
