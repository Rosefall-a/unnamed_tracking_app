from __future__ import annotations

import time
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Boolean, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base


class AppIntegrationSettings(Base):
    """Singleton row containing deployment-wide provider credentials.

    These credentials are shared fallbacks for users who have not supplied
    their own provider credentials. User credentials take precedence over
    this row, and this row takes precedence over environment variables.
    Secret values are stored encrypted; only safe identifiers are returned
    by the settings API.
    """

    __tablename__ = "app_integration_settings"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Metadata providers
    steamgriddb_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    retroachievements_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    giantbomb_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)

    igdb_client_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    igdb_client_secret: Mapped[str | None] = mapped_column(Text, nullable=True)

    screenscraper_ssid: Mapped[str | None] = mapped_column(String(128), nullable=True)
    screenscraper_sspassword: Mapped[str | None] = mapped_column(Text, nullable=True)
    screenscraper_devid: Mapped[str | None] = mapped_column(String(128), nullable=True)
    screenscraper_devpassword: Mapped[str | None] = mapped_column(Text, nullable=True)

    # OAuth application credentials can safely be shared by the deployment;
    # user-specific refresh/access tokens remain on User.
    xbox_client_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    xbox_client_secret: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Application-wide runtime settings are persisted so administrators can
    # change these values from Settings without relying on environment-only
    # configuration. Environment values are used only to initialize a new row.
    auth_cookie_secure: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    max_upload_size_mb: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    max_clip_size_mb: Mapped[int] = mapped_column(Integer, nullable=False, default=500)
    max_world_save_size_mb: Mapped[int] = mapped_column(Integer, nullable=False, default=2000)
    runtime_settings_initialized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    updated_at: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=time.time, onupdate=time.time
    )
