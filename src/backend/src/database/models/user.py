from __future__ import annotations

import time
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Boolean, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base


class User(Base):
    """Application account prepared for future authentication flows."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # per-user, not a shared app-wide default — each user brings their own key
    steamgriddb_api_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Fernet ciphertext (src.core.crypto) — never store or return the raw npsso value
    psn_npsso_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    psn_validated_at: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Additional metadata provider credentials — see
    # src.api.routes.settings.PROVIDER_FIELD_MAP for which of these are
    # plaintext third-party API keys vs. Fernet-encrypted account secrets.
    retroachievements_api_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    giantbomb_api_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    screenscraper_ssid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    screenscraper_sspassword: Mapped[str | None] = mapped_column(Text, nullable=True)
    xbox_client_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    xbox_client_secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    gog_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False, default=time.time)
    updated_at: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=time.time,
        onupdate=time.time,
    )
