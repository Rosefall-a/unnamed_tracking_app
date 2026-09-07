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

    # library-sync credentials — pulling a whole owned-games + achievements
    # library, not just per-title metadata search, so these need more than
    # the search-only credentials above (a SteamID64 + Steam Web API key
    # pair, RetroAchievements' username alongside its existing api key —
    # PSN and Xbox reuse psn_npsso_token / xbox_client_id+secret above)
    # wide enough for a full profile URL, not just a bare SteamID64 — see
    # steam.resolve_steam_id, which accepts either and resolves to the
    # numeric ID at save time
    steam_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    steam_api_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    retroachievements_username: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # set by library_sync.py on a successful run — deliberately not derived
    # from Game.updated_at, which would also be touched by unrelated
    # metadata-search edits and make "last synced" lie
    steam_library_synced_at: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    retroachievements_library_synced_at: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    psn_library_synced_at: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # display identity pulled from each provider on a successful connect —
    # lets Settings show "who" is connected (name + avatar), not just a
    # green dot. RetroAchievements' display name is retroachievements_username
    # itself, so it only needs an avatar column here.
    steam_persona_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    steam_avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    retroachievements_avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    psn_online_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    psn_avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False, default=time.time)
    updated_at: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=time.time,
        onupdate=time.time,
    )
