from typing import List # Import necessary types for modern Python type hinting
from uuid import uuid4 # <-- Added missing import for UUID generation
from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

class Developer(Base):
    __tablename__ = "developers"

    id: Mapped[uuid4] = mapped_column( # Fixed the default assignment to use uuid4() directly as a function call
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    # Relationship back to games
    games: Mapped[list["Game"]] = relationship(back_populates="developer")

