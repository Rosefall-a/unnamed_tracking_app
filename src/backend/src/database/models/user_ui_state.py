"""What a person last chose on a page (a view mode, a sort, a filter, a Home
pick), kept on the server so nothing is stored in their browser and it follows
them to every device. One row per name; `updated_at` is when it last changed."""

from uuid import UUID

from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base


class UserUiState(Base):
    """One saved choice of one person, by name."""

    __tablename__ = "user_ui_state"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    value: Mapped[object] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
