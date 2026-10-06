from __future__ import annotations

import time
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base, unix_timestamp


class GameNoteDetail(Base):
    # Repeated declarations preserve independent database table/enum contracts.
    # pylint: disable=duplicate-code
    """What a note carries beyond its text. The note itself is still a markdown
    file in the game's notes folder; this row adds the things a file cannot
    hold: when it was created, whether it is pinned, its tags, and the
    achievement it is about. Rows are created when a note is, and caught up for
    older notes the first time the list is read (see features/game_notes.py)."""

    __tablename__ = "game_note_details"
    __table_args__ = (UniqueConstraint("game_id", "name", name="uq_game_note_details_game_name"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    game_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("games.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False, default=unix_timestamp)
    pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    linked_achievement_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("achievements.id", ondelete="SET NULL"), nullable=True
    )


class GameNoteVersion(Base):
    """An earlier state of a note, saved just before an edit replaced it."""

    __tablename__ = "game_note_versions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    note_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("game_note_details.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Unix milliseconds
    saved_at: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=lambda: int(time.time() * 1000)
    )
