"""Commit plugin grants and runtime packages with recoverable transaction phases.

This host-owned coordinator keeps database consent, runtime preparation, and
activation in their existing order. Ambiguous database commits leave code disabled
until recovery can establish the durable receipt.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from urllib.parse import quote
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.plugin_permission_audit import PluginPermissionAudit
from src.database.models.plugin_permissions import (
    PluginLifecycleTransaction,
    PluginPermissionGrant,
    PluginPermissionRequest,
)

from .capabilities import permission_key
from .contracts import PluginManifest, parse_semver
from .dependency_plan import plan_dependencies
from .manager_state import manager_state
from .runtime_client import PluginRuntimeClient, PluginRuntimeRequestError, PluginRuntimeUnavailable

if TYPE_CHECKING:
    from .installer import InstallationConsent, InstallationPlan


@dataclass
class _CommitState:
    """Evidence required to recover the database/runtime installation transaction."""

    plan: InstallationPlan
    now: int = field(default_factory=lambda: int(time.time()))
    operation_id: str = field(default_factory=lambda: str(uuid4()))
    removed_grants: list[UUID] = field(default_factory=list)
    added_grants: list[PluginPermissionGrant] = field(default_factory=list)
    prepared: bool = False
    commit_attempted: bool = False

    @property
    def manifest(self) -> PluginManifest:
        return self.plan.inspected.package.manifest

    @property
    def plugin_id(self) -> str:
        return self.manifest.plugin_id


@dataclass(frozen=True)
class _InstallationPolicy:
    """The previous package and source/update policy restored if activation fails."""

    previous: dict[str, Any]
    source: dict[str, Any]
    updates: dict[str, Any]


@dataclass
class _ActivationResult:
    status: str
    healthy: bool
    failed: bool


def _installation_policy(
    plan: InstallationPlan, source: dict[str, Any] | None, operation: str
) -> _InstallationPolicy:
    manifest = plan.inspected.package.manifest
    plugin_id = manifest.plugin_id
    previous = {
        **manager_state().read()["plugins"].get(plugin_id, {}),
        **(plan.installed or {}),
    }
    selected_source = source or previous.get("source", {"type": "upload"})
    latest = selected_source.get("latest_version")
    older = bool(latest and parse_semver(manifest.version) < parse_semver(latest))
    if previous.get("version"):
        older = older or parse_semver(manifest.version) < parse_semver(previous["version"])
    pin = manifest.version if older or operation == "rollback" else None
    if (
        previous.get("version") == manifest.version
        and previous.get("version_pin") == manifest.version
    ):
        pin = manifest.version
    update_policy = {
        "version_pin": pin,
        "automatic_updates": "disabled" if pin else previous.get("automatic_updates", "follow"),
    }
    return _InstallationPolicy(previous, selected_source, update_policy)


async def _record_permissions(
    state: _CommitState, consent: InstallationConsent, admin: Any, db: AsyncSession
) -> None:
    approved = set(consent.approved_permissions)
    if (state.plan.installed is not None) and not state.plan.can_retain_grants:
        previous_grants = await db.scalars(
            select(PluginPermissionGrant).where(
                PluginPermissionGrant.plugin_id == state.plugin_id,
                PluginPermissionGrant.installation_id == state.plan.installation_id,
                PluginPermissionGrant.revoked_at.is_(None),
            )
        )
        state.removed_grants.extend(grant.id for grant in previous_grants)
        await db.execute(
            update(PluginPermissionGrant)
            .where(
                PluginPermissionGrant.plugin_id == state.plugin_id,
                PluginPermissionGrant.installation_id == state.plan.installation_id,
                PluginPermissionGrant.revoked_at.is_(None),
            )
            .values(revoked_at=state.now, revoked_by_operation=UUID(state.operation_id))
        )
    rows: list[Any] = []
    for ref in state.plan.permissions.newly_requested_grants:
        allowed = permission_key(ref) in approved
        rationale = next(p.rationale for p in state.manifest.permissions if p.capability == ref)
        identity = {
            "plugin_id": state.plugin_id,
            "installation_id": state.plan.installation_id,
            "capability": ref.name.value,
            "capability_version": ref.version,
        }
        rows.append(
            PluginPermissionRequest(
                **identity,
                rationale=rationale,
                status="approved" if allowed else "denied",
                resolved_at=state.now,
                resolved_by=getattr(admin, "id", None),
            )
        )
        if allowed:
            grant = PluginPermissionGrant(id=uuid4(), **identity)
            rows.append(grant)
            state.added_grants.append(grant)
        rows.append(
            PluginPermissionAudit(
                **identity,
                user_id=getattr(admin, "id", None),
                decision="allowed" if allowed else "denied",
                reason="administrator update consent"
                if (state.plan.installed is not None)
                else "administrator install consent",
            )
        )
    db.add_all(rows)


def _runtime_options(state: _CommitState, source: dict[str, Any] | None) -> dict[str, Any]:
    options: dict[str, Any] = {
        "installation_id": str(state.plan.installation_id),
        "operation_id": state.operation_id,
        "source_metadata": source,
        "trust_metadata": {
            "status": state.plan.inspected.trust.status.value,
            "signature_present": state.plan.inspected.trust.signature_present,
            "signature_verified": state.plan.inspected.trust.signature_verified,
            "publisher_key_id": state.plan.inspected.trust.publisher_key_id,
            "publisher_identity": state.plan.inspected.trust.publisher_identity,
            "publisher_channel": state.plan.inspected.trust.publisher_channel,
            "signing_version": state.plan.inspected.package.signing_version,
        },
    }
    if state.plan.installed is not None:
        options["replace"] = True
        assert state.plan.installed is not None
        options["expected_version"] = str(state.plan.installed["version"])
    return options


def _record_candidate(
    state: _CommitState, policy: _InstallationPolicy, options: dict[str, Any]
) -> None:
    manager_state().patch(
        state.plugin_id,
        **{
            **(state.plan.installed or {}),
            **policy.updates,
            "plugin_id": state.plugin_id,
            "name": state.manifest.name,
            "version": state.manifest.version,
            "api_contract_version": state.manifest.api_contract_version,
            "sdk_version_range": state.manifest.sdk_version_range,
            "application_version_range": state.manifest.application_version_range,
            "description": state.manifest.description,
            "installation_id": str(state.plan.installation_id),
            "digest": state.manifest.integrity.sha256,
            "permissions": [p.capability.name.value for p in state.manifest.permissions],
            "permission_refs": [
                p.capability.model_dump(mode="json") for p in state.manifest.permissions
            ],
            "source": policy.source,
            "trust": options["trust_metadata"],
            "status": "stopped",
            "enabled": False,
            "compatible": True,
            "health": "unknown",
        },
    )


async def _revoke_removed_permissions(state: _CommitState, db: AsyncSession) -> None:
    if state.plan.can_retain_grants:
        removed = {(ref.name.value, ref.version) for ref in state.plan.permissions.removed}
        for grant in await db.scalars(
            select(PluginPermissionGrant).where(
                PluginPermissionGrant.plugin_id == state.plugin_id,
                PluginPermissionGrant.installation_id == state.plan.installation_id,
                PluginPermissionGrant.revoked_at.is_(None),
            )
        ):
            if (grant.capability, grant.capability_version) in removed:
                state.removed_grants.append(grant.id)
                grant.revoked_at = state.now
                grant.revoked_by_operation = UUID(state.operation_id)


def _transaction_receipt(state: _CommitState, admin: Any) -> PluginLifecycleTransaction:
    return PluginLifecycleTransaction(
        id=UUID(state.operation_id),
        plugin_id=state.plugin_id,
        user_id=getattr(admin, "id", None),
        added_grants=[str(grant.id) for grant in state.added_grants],
        removed_grants=[str(grant_id) for grant_id in state.removed_grants],
        grant_timestamp=state.now,
        completed=False,
    )


async def _abort_failed_commit(
    runtime: PluginRuntimeClient,
    state: _CommitState,
    db: AsyncSession,
    policy: _InstallationPolicy,
    exc: Exception,
) -> None:
    await db.rollback()
    # A lost COMMIT acknowledgement is not proof of rollback. Restoring
    # old unverified code could expose it to a newly committed grant.
    # Only abort on a definite rejection or an error before COMMIT.
    definite_rejection = not state.commit_attempted or isinstance(exc, (DataError, IntegrityError))
    if state.prepared and definite_rejection:
        try:
            await runtime.finish_installation(state.plugin_id, state.operation_id, commit=False)
            if state.plan.installed:
                manager_state().patch(
                    state.plugin_id,
                    **{"version_pin": None, "automatic_updates": "follow", **policy.previous},
                )
            else:
                manager_state().remove(state.plugin_id)
        except (PluginRuntimeRequestError, PluginRuntimeUnavailable):
            logging.getLogger(__name__).exception(
                "Plugin installation remains pending and cannot activate: plugin_id=%s",
                state.plugin_id,
            )


async def _prepare_installation(
    runtime: PluginRuntimeClient,
    state: _CommitState,
    package: bytes,
    *,
    consent: InstallationConsent,
    admin: Any,
    db: AsyncSession,
    source: dict[str, Any] | None,
    policy: _InstallationPolicy,
) -> tuple[dict[str, Any], PluginLifecycleTransaction]:
    try:
        await _record_permissions(state, consent, admin, db)
        options = _runtime_options(state, source)
        result = await runtime.install_package(
            package, f"{state.plugin_id}-{state.manifest.version}.utp", **options
        )
        if result.get("operation_id") != state.operation_id:
            raise PluginRuntimeRequestError("runtime did not prepare the installation transaction")
        state.prepared = True
        _record_candidate(state, policy, options)
        await _revoke_removed_permissions(state, db)
        receipt = _transaction_receipt(state, admin)
        db.add_all([receipt])
        state.commit_attempted = True
        await db.commit()
    except Exception as exc:
        await _abort_failed_commit(runtime, state, db, policy, exc)
        raise
    # A failed finalization leaves the package durably disabled and pending.
    # Never fall back to start or claim activation on an ambiguous commit.
    await runtime.finish_installation(state.plugin_id, state.operation_id, commit=True)
    return result, receipt


async def _activate_candidate(
    runtime: PluginRuntimeClient, state: _CommitState, result: dict[str, Any], admin: Any
) -> _ActivationResult:
    status = result.get("status", "updated" if (state.plan.installed is not None) else "installed")
    healthy = False
    if state.plan.installed is None or state.plan.installed.get(
        "activation_requested", state.plan.installed.get("enabled")
    ):
        try:
            encoded = quote(state.plugin_id, safe="")
            if state.manifest.dependencies:
                dependencies = plan_dependencies(state.manifest, await runtime.plugins())
                if not dependencies.ready:
                    raise PluginRuntimeRequestError("plugin dependencies changed before activation")
            await runtime.start(encoded, user_id=str(getattr(admin, "id", "")) or None)
            healthy = await runtime.plugin_health(encoded)
            status = "running" if healthy else "unhealthy"
        except (PluginRuntimeRequestError, PluginRuntimeUnavailable) as exc:
            logging.getLogger(__name__).warning(
                "Plugin activation failed: plugin_id=%s error=%s", state.plugin_id, exc
            )
            status = "failed_activation"
    return _ActivationResult(status, healthy, status in {"unhealthy", "failed_activation"})


async def _finish_activation(
    runtime: PluginRuntimeClient,
    state: _CommitState,
    activation: _ActivationResult,
    *,
    db: AsyncSession,
    policy: _InstallationPolicy,
) -> None:
    if (state.plan.installed is not None) and activation.failed:
        # Candidate code is stopped before its grants are withdrawn. Restore
        # only grants this transaction removed; never revive unrelated revocations.
        await runtime.stop(quote(state.plugin_id, safe=""))
        for grant in state.added_grants:
            await db.execute(
                update(PluginPermissionGrant)
                .where(PluginPermissionGrant.id == grant.id)
                .values(revoked_at=int(time.time()))
            )
        if state.removed_grants:
            await db.execute(
                update(PluginPermissionGrant)
                .where(
                    PluginPermissionGrant.id.in_(state.removed_grants),
                    PluginPermissionGrant.revoked_by_operation == UUID(state.operation_id),
                )
                .values(revoked_at=None, revoked_by_operation=None)
            )
        await db.commit()
        await runtime.finish_activation(state.plugin_id, state.operation_id, commit=False)
        manager_state().patch(
            state.plugin_id,
            version_pin=policy.previous.get("version_pin"),
            automatic_updates=policy.previous.get("automatic_updates", "follow"),
            last_update_error="Candidate failed startup/health; previous release restored.",
        )
        activation.status = "rolled_back"
        activation.healthy = await runtime.plugin_health(quote(state.plugin_id, safe=""))
    else:
        if (
            state.plan.installed
            and state.plan.installed.get("enabled")
            and state.plan.installed.get("status") == "stopped"
        ):
            await runtime.stop_runtime(state.plugin_id)
            activation.status = "stopped"
        await runtime.finish_activation(state.plugin_id, state.operation_id, commit=True)
        await runtime.prune_history(
            state.plugin_id, int(manager_state().settings()["retained_versions"])
        )


def _installation_response(
    state: _CommitState,
    result: dict[str, Any],
    activation: _ActivationResult,
    consent: InstallationConsent,
    dangerous: list[str],
) -> dict[str, Any]:
    approved = set(consent.approved_permissions)
    response = {
        "plugin_id": state.plugin_id,
        "version": state.plan.installed["version"]
        if activation.status == "rolled_back" and state.plan.installed
        else state.manifest.version,
        "permissions_requested": len(state.plan.permissions.newly_requested_grants),
        "permissions_granted": len(approved),
        "dangerous_permissions_reauthenticated": dangerous,
        "trust_status": state.plan.inspected.trust.status.value,
        "install_status": result.get(
            "status", "updated" if (state.plan.installed is not None) else "installed"
        ),
        "status": activation.status,
        "healthy": activation.healthy,
    }
    if state.plan.installed is not None:
        response["permission_delta"] = state.plan.permissions.model_dump(mode="json")
    else:
        response.update(
            {
                "name": state.manifest.name,
                "publisher": state.plan.inspected.trust.publisher_identity,
                "publisher_key_id": state.plan.inspected.trust.publisher_key_id,
                "installation_id": str(state.plan.installation_id),
                "permissions_denied": len(state.plan.permissions.newly_requested_grants)
                - len(approved),
                "trust_warning": state.plan.inspected.trust.warning,
            }
        )
    return response


async def commit_installation(
    runtime: PluginRuntimeClient,
    plan: InstallationPlan,
    package: bytes,
    *,
    consent: InstallationConsent,
    admin: Any,
    db: AsyncSession,
    source: dict[str, Any] | None,
    dangerous: list[str],
    operation: str,
) -> dict[str, Any]:
    """Prepare grants/package, commit their receipt, then activate and recover if needed."""
    state = _CommitState(plan)
    policy = _installation_policy(plan, source, operation)
    # Forward the same explicit consent/database inputs across the commit boundary.
    # pylint: disable=duplicate-code
    result, receipt = await _prepare_installation(
        runtime,
        state,
        package,
        consent=consent,
        admin=admin,
        db=db,
        source=source,
        policy=policy,
    )
    # pylint: enable=duplicate-code
    activation = await _activate_candidate(runtime, state, result, admin)
    await _finish_activation(runtime, state, activation, db=db, policy=policy)
    manager_state().reconcile(await runtime.plugins())
    receipt.completed = True
    await db.commit()
    if not activation.failed:
        manager_state().patch(state.plugin_id, staged_update=None, available_update=None)
        manager_state().stage_path(state.plugin_id).unlink(missing_ok=True)
    return _installation_response(state, result, activation, consent, dangerous)
