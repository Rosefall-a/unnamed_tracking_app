from __future__ import annotations

import time
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base


class AppIntegrationSettings(Base):
    """Singleton row (exactly one, created lazily on first access — see
    get_or_create_app_integration_settings) holding API credentials that
    belong to this deployment as a whole, not to any one user — an IGDB/
    Twitch developer app is registered once per server, not once per
    person using it. Admin-only to read/write (see /api/settings/
    app-integrations), and igdb_client_id is the only field ever echoed
    back to the client; igdb_client_secret never is, same rule as every
    other Fernet-encrypted credential in this codebase."""

    __tablename__ = "app_integration_settings"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    igdb_client_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    igdb_client_secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[int] = mapped_column(BigInteger, nullable=False, default=time.time, onupdate=time.time)
