from __future__ import annotations

import time
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Boolean, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base


class AppIntegrationSettings(Base):
    """Singleton row containing deployment-wide provider, email and runtime settings."""

    __tablename__ = "app_integration_settings"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    steamgriddb_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    retroachievements_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    giantbomb_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    igdb_client_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    igdb_client_secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    screenscraper_ssid: Mapped[str | None] = mapped_column(String(128), nullable=True)
    screenscraper_sspassword: Mapped[str | None] = mapped_column(Text, nullable=True)
    screenscraper_devid: Mapped[str | None] = mapped_column(String(128), nullable=True)
    screenscraper_devpassword: Mapped[str | None] = mapped_column(Text, nullable=True)
    xbox_client_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    xbox_client_secret: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Application-wide runtime settings. These are intentionally persisted in
    # PostgreSQL rather than requiring operators to edit .env for normal app
    # configuration.
    auth_cookie_secure: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    max_upload_size_mb: Mapped[int] = mapped_column(nullable=False, default=15)
    max_clip_size_mb: Mapped[int] = mapped_column(nullable=False, default=500)
    max_world_save_size_mb: Mapped[int] = mapped_column(nullable=False, default=2000)
    runtime_settings_initialized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Optional deployment SMTP transport. Individual email capabilities are
    # kept as explicit feature flags so more email features can be added
    # without coupling them to SMTP transport configuration.
    smtp_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    smtp_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    smtp_port: Mapped[int] = mapped_column(nullable=False, default=587)
    smtp_username: Mapped[str | None] = mapped_column(String(320), nullable=True)
    smtp_password: Mapped[str | None] = mapped_column(Text, nullable=True)
    smtp_use_tls: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    smtp_use_ssl: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    smtp_from_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    smtp_from_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    password_reset_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    updated_at: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=time.time, onupdate=time.time
    )
