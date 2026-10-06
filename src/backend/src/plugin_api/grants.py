"""Persistence-backed capability grant lookup shared by gateway consumers."""

import hashlib
import time
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.plugin_permissions import PluginPermissionGrant
from src.plugin_api.capabilities import capability_grant_candidates, expand_capabilities
from src.plugin_api.lifecycle import plugin_contributions_active


def permission_scope_filters(grant: PluginPermissionGrant) -> tuple:
    """Match a capability's exact installation, user and device scope."""
    return (
        PluginPermissionGrant.plugin_id == grant.plugin_id,
        PluginPermissionGrant.installation_id == grant.installation_id,
        PluginPermissionGrant.capability == grant.capability,
        PluginPermissionGrant.capability_version == grant.capability_version,
        PluginPermissionGrant.user_id == grant.user_id,
        PluginPermissionGrant.device_id == grant.device_id,
    )


async def lock_permission_scope(db: AsyncSession, grant: PluginPermissionGrant) -> None:
    """Serialize first creation and reinstatement of the same persisted grant."""
    if db.get_bind().dialect.name == "postgresql":
        identity = (
            f"plugin-grant/{grant.plugin_id}/{grant.installation_id}/"
            f"{grant.capability}/v{grant.capability_version}/{grant.user_id}/{grant.device_id}"
        )
        key = int.from_bytes(hashlib.sha256(identity.encode()).digest()[:8], "big", signed=True)
        await db.execute(select(func.pg_advisory_xact_lock(key)))


async def ensure_capability_grant(
    db: AsyncSession, proposed: PluginPermissionGrant
) -> PluginPermissionGrant:
    """Reuse one exact-scope grant while retaining historical revocation records."""
    await lock_permission_scope(db, proposed)
    rows = list(
        await db.scalars(
            select(PluginPermissionGrant)
            .where(*permission_scope_filters(proposed))
            .order_by(
                PluginPermissionGrant.revoked_at.is_not(None),
                PluginPermissionGrant.granted_at,
                PluginPermissionGrant.id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    )
    if not rows:
        db.add(proposed)
        return proposed
    current = rows[0]
    if current.revoked_at is not None:
        current.granted_at = int(time.time())
        current.revoked_at = None
        current.revoked_by_operation = None
    for duplicate in rows[1:]:
        if duplicate.revoked_at is None:
            duplicate.revoked_at = int(time.time())
            duplicate.revoked_by_operation = None
    return current


def installation_is_executable(plugin: dict[str, Any]) -> bool:
    """Accept only affirmative live lifecycle metadata from the runtime registry."""
    return plugin_contributions_active(plugin)


async def effective_capabilities(
    db: AsyncSession, plugin_id: str, installation_id: UUID, user_id: UUID, granted: list[str]
) -> frozenset[str]:
    """UI contributions obey the same exact-scope revocation tombstones as APIs."""
    revoked = await db.scalars(
        select(PluginPermissionGrant.capability).where(
            PluginPermissionGrant.plugin_id == plugin_id,
            PluginPermissionGrant.installation_id == installation_id,
            PluginPermissionGrant.capability_version == 1,
            PluginPermissionGrant.revoked_at.is_not(None),
            PluginPermissionGrant.device_id.is_(None),
            or_(PluginPermissionGrant.user_id.is_(None), PluginPermissionGrant.user_id == user_id),
        )
    )
    denied = set(revoked) - set(granted)
    return frozenset(expand_capabilities(granted)) - denied


async def active_user_capabilities(
    db: AsyncSession, plugin_id: str, installation_id: UUID, user_id: UUID
) -> list[str]:
    """List active v1 grants for this installation and account, excluding device scopes."""
    rows = await db.execute(
        select(
            PluginPermissionGrant.capability,
            PluginPermissionGrant.capability_version,
        ).where(
            PluginPermissionGrant.plugin_id == plugin_id,
            PluginPermissionGrant.installation_id == installation_id,
            PluginPermissionGrant.revoked_at.is_(None),
            PluginPermissionGrant.device_id.is_(None),
            or_(PluginPermissionGrant.user_id.is_(None), PluginPermissionGrant.user_id == user_id),
        )
    )
    return [str(capability) for capability, version in rows if version == 1]


async def has_capability_grant(
    db: AsyncSession,
    *,
    plugin_id: str,
    installation_id: UUID,
    capability: str,
    user_id: UUID,
    capability_version: int = 1,
    device_id: UUID | None = None,
) -> bool:
    """Resolve a grant against the exact installation and authenticated user context."""
    context_filters = (
        PluginPermissionGrant.plugin_id == plugin_id,
        PluginPermissionGrant.installation_id == installation_id,
        PluginPermissionGrant.capability == capability,
        PluginPermissionGrant.capability_version == capability_version,
        or_(PluginPermissionGrant.user_id.is_(None), PluginPermissionGrant.user_id == user_id),
        or_(
            PluginPermissionGrant.device_id.is_(None), PluginPermissionGrant.device_id == device_id
        ),
    )
    explicit = await db.scalar(
        select(PluginPermissionGrant.id).where(
            *context_filters,
            PluginPermissionGrant.revoked_at.is_(None),
        )
    )
    if explicit is not None:
        return True
    revoked = await db.scalar(
        select(PluginPermissionGrant.id).where(
            *context_filters,
            PluginPermissionGrant.revoked_at.is_not(None),
        )
    )
    if revoked is not None:
        return False
    grant = await db.scalar(
        select(PluginPermissionGrant.id).where(
            PluginPermissionGrant.plugin_id == plugin_id,
            PluginPermissionGrant.installation_id == installation_id,
            PluginPermissionGrant.capability.in_(capability_grant_candidates(capability)),
            PluginPermissionGrant.capability_version == capability_version,
            PluginPermissionGrant.revoked_at.is_(None),
            or_(
                PluginPermissionGrant.user_id.is_(None),
                PluginPermissionGrant.user_id == user_id,
            ),
            or_(
                PluginPermissionGrant.device_id.is_(None),
                PluginPermissionGrant.device_id == device_id,
            ),
        )
    )
    return grant is not None
