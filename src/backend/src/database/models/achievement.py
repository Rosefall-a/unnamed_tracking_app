from __future__ import annotations

import time
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Boolean, Float, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base

if TYPE_CHECKING:
    from src.database.models.game import Game


class Achievement(Base):
    # Repeated declarations preserve independent database table/enum contracts.
    # pylint: disable=duplicate-code
    """One achievement/trophy pulled from a library-sync provider (Steam,
    PlayStation, RetroAchievements). Fully replaced (delete + reinsert) on
    every sync for a given game rather than diffed field-by-field — simpler
    and cheap at the achievement-list scale these APIs return."""

    __tablename__ = "achievements"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    game_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("games.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    external_id: Mapped[str] = mapped_column(String(200), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    unlocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    unlocked_at: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # a spoiler until it is unlocked: Steam and PlayStation both flag these in
    # what they send, and the page keeps them hidden until you reveal them
    hidden: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    # the share of all players who have it (0-100), as the provider reports it
    global_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    # "progression" | "missable" | "win_condition" | None — RetroAchievements
    # is the only provider that classifies achievements this way today
    tier: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False, default=time.time)

    game: Mapped["Game"] = relationship()
