from __future__ import annotations

import time
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base


class GameMatch(Base):
    """Two entries in a library that look like the same game: one added by hand (or
    from another provider) and one that a Steam sync created. Nothing is merged
    until the person decides, and the decision can be changed afterwards.

    status: "pending" (not decided), "kept_both" (decided they are different), or
    "merged" (the Steam entry was folded into the original and sits in the trash)."""

    __tablename__ = "game_matches"
    __table_args__ = (UniqueConstraint("original_id", "steam_id", name="uq_game_matches_pair"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # the entry the person made, which keeps its notes, screenshots and files
    original_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("games.id", ondelete="CASCADE"), nullable=False
    )
    # the entry the Steam sync created
    steam_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("games.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="pending")
    # "mine" or "steam": whose details won when they were merged
    prefer: Mapped[str | None] = mapped_column(String(8), nullable=True)
    # what the original looked like before the merge, so it can be put back
    undo: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False, default=lambda: int(time.time()))
    resolved_at: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
