from typing import List
from uuid import UUID, uuid4
from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship # <-- Added relationship and fixed imports
from app.database.base import Base
from datetime import datetime


class Achievement(Base):
    """Defines a specific achievement possible for a game."""
    __tablename__ = "achievements"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=lambda: uuid4()
    )

    game_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False
    )
    game: Mapped["Game"] = relationship("Game", back_populates="achievements")

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon_url: Mapped[str | None] = mapped_column(String(500), nullable=True) # e.g., Steam icon URL
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


# Helper to generate achievements easily for a game
def get_default_achievements():
    """Placeholder function/logic that would typically be used during data seeding."""
    return [
        Achievement(name="First Play", description="Played the game once.", is_secret=False),
        Achievement(name="Completionist", description="Finished all levels/content.", is_secret=True)
    ]

