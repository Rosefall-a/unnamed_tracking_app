"""Concurrent grant creation and reinstatement against the production database."""

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import delete, select, update

from src.database.models.plugin_permissions import PluginPermissionGrant
from src.database.session import SessionLocal
from src.plugin_api.grants import ensure_capability_grant


@pytest.mark.asyncio
async def test_concurrent_grants_and_reinstatement_share_one_record():
    """Transaction locks protect first creation as well as reuse of a denied scope."""
    installation_id = uuid4()
    plugin_id = "test.grant-reinstatement." + installation_id.hex

    async def approve():
        async with SessionLocal() as db:
            grant = await ensure_capability_grant(
                db,
                PluginPermissionGrant(
                    plugin_id=plugin_id,
                    installation_id=installation_id,
                    capability="sessions.read",
                    capability_version=1,
                ),
            )
            await db.commit()
            return grant.id

    try:
        original_ids = await asyncio.gather(*(approve() for _ in range(4)))
        assert len(set(original_ids)) == 1
        async with SessionLocal() as db:
            await db.execute(
                update(PluginPermissionGrant)
                .where(PluginPermissionGrant.installation_id == installation_id)
                .values(revoked_at=1)
            )
            await db.commit()
        restored_ids = await asyncio.gather(*(approve() for _ in range(4)))
        assert set(restored_ids) == set(original_ids)
        async with SessionLocal() as db:
            rows = list(
                await db.scalars(
                    select(PluginPermissionGrant).where(
                        PluginPermissionGrant.installation_id == installation_id
                    )
                )
            )
            assert len(rows) == 1 and rows[0].revoked_at is None
    finally:
        async with SessionLocal() as db:
            await db.execute(
                delete(PluginPermissionGrant).where(
                    PluginPermissionGrant.installation_id == installation_id
                )
            )
            await db.commit()
