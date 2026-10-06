from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, unix_timestamp

if TYPE_CHECKING:
    from src.database.models.achievement import Achievement
    from src.database.models.game import Game


class MediaItem(Base):
    # Repeated declarations preserve independent database table/enum contracts.
    # pylint: disable=duplicate-code
    """A screenshot, clip, or soundtrack file for a game. The file itself
    still lives on disk (games/<folder>/<screenshots|clips|soundtrack>/) —
    this row is what makes it taggable, note-able, and linkable to an
    achievement, none of which a bare directory listing can support."""

    __tablename__ = "media_items"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    game_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("games.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "screenshot" | "clip" | "soundtrack"
    filename: Mapped[str] = mapped_column(String(300), nullable=False)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    # which GameProfile (e.g. an OSRS account) this belongs to, if any — lets
    # a game with several accounts filter its gallery down to one instead of
    # scrolling through every account's screenshots together. NULL means
    # "not tied to a specific profile" (most games never set this).
    profile_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("game_profiles.id", ondelete="SET NULL"), nullable=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # a screenshot/clip that captures a specific achievement moment — shown
    # on both the media item and the achievement's own detail page
    linked_achievement_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("achievements.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False, default=unix_timestamp)
    # a name for the file inside the app; the file on disk keeps its own name
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # when it was really taken, and where that came from ("photo", "filename",
    # "file", "uploaded" or "manual", see helpers/media_dates.py). NULL on rows
    # from before this existed, which fall back to created_at.
    taken_at: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    taken_source: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # a clip's saved preview picture (a file under the game's thumbs folder) and
    # its length, so the gallery does not have to load every video to show them
    thumb_filename: Mapped[str | None] = mapped_column(String(300), nullable=True)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    # set instead of deleting the row — the file moves to a trash folder
    # alongside it (see features/trash/media_trash.py) and
    # features/trash/sweep.py purges both after 7 days. NULL means active.
    deleted_at: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    game: Mapped["Game"] = relationship()
    linked_achievement: Mapped["Achievement | None"] = relationship()
