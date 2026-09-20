"""Deployment-wide (not per-user) integration credentials singleton —
lives here rather than in api/routes/settings.py so both route handlers
and background features (features/metadata/refresh.py) can depend on it
without a route module importing another route module."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.app_integration_settings import AppIntegrationSettings


async def get_or_create_app_integration_settings(db: AsyncSession) -> AppIntegrationSettings:
    """Exactly one row for the whole deployment — created lazily, on first
    access, same as get_or_create_scan_settings but with no user_id since
    this isn't per-user."""
    row = await db.scalar(select(AppIntegrationSettings).limit(1))
    if row is None:
        row = AppIntegrationSettings()
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return row
