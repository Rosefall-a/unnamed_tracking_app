"""Schedule contracts and persisted installation/user permission boundaries."""

import asyncio
import io
import json
import time
import zipfile
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import delete, select

from src.api.routes import jobs as job_routes
from src.database.models.job_setting import JobSetting
from src.database.models.plugin_permissions import PluginPermissionGrant
from src.database.models.user import User
from src.database.session import SessionLocal
from src.features import plugin_jobs
from src.plugin_api.contracts import PluginManifest, PluginScheduledTask
from src.plugin_api.runtime_client import PluginRuntimeUnavailable
from src.plugin_api.updates import (
    PackageFormatError,
    PluginPackageVerifier,
    canonical_payload_digest,
)


def manifest(**changes):
    """One v1.1 action declaration; no plugin implementation or private imports."""
    return {
        "plugin_id": "example.tasks",
        "name": "Example tasks",
        "version": "1.1.0",
        "api_contract_version": "1.1.0",
        "entrypoint": "plugin:main",
        "sdk_version_range": "^1.1.0",
        "application_version_range": "*",
        "integrity": {"sha256": "0" * 64},
        "capabilities": [{"name": "tasks.background", "version": 1}],
        "permissions": [
            {
                "capability": {"name": "tasks.background", "version": 1},
                "rationale": "Run a reviewed task.",
            }
        ],
        "scheduled_tasks": [{"id": "summary", "name": "Summary", "action_id": "summarize"}],
        **changes,
    }


@pytest.mark.parametrize(
    "changes",
    [
        {"api_contract_version": "1.0.0"},
        {"capabilities": [], "permissions": []},
        {"scheduled_tasks": [{"id": "summary", "name": "Summary", "action_id": "summarize"}] * 2},
        {"scheduled_tasks": [{"id": "summary", "name": "Summary", "action_id": "summarize"}] * 33},
    ],
)
def test_tasks_require_v11_explicit_permission_unique_bounded_declarations(changes):
    with pytest.raises(ValidationError):
        PluginManifest.model_validate(manifest(**changes))


@pytest.mark.parametrize(
    "changes",
    [
        {"default_interval_minutes": 1},
        {"max_interval_minutes": 30},
        {"min_interval_minutes": 0},
        {"max_interval_minutes": 43_201},
        {"default_interval_minutes": True},
        {"default_interval_minutes": 1.5},
    ],
)
def test_task_periods_are_strict_and_within_declared_bounds(changes):
    with pytest.raises(ValidationError):
        PluginScheduledTask(id="summary", name="Summary", action_id="summarize", **changes)


@pytest.mark.parametrize(
    "action",
    [
        None,
        {
            "id": "summarize",
            "label": "Summary",
            "handler": "plugin:summary",
            "confirmation": "Confirm this destructive action",
        },
        {"id": "summarize", "label": "Summary"},
    ],
)
def test_package_verifier_rejects_missing_or_confirmed_scheduled_actions(action, tmp_path):
    document = {
        "api_contract_version": "1.1.0",
        "plugin_id": "example.tasks",
        "title": "Tasks",
        "actions": [action] if action else [],
    }
    payload = [("ui.json", json.dumps(document).encode())]
    package = io.BytesIO()
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr(
            "manifest.json",
            json.dumps(manifest(integrity={"sha256": canonical_payload_digest(payload)})),
        )
        archive.writestr("payload/ui.json", payload[0][1])
    path = tmp_path / "task.utp"
    path.write_bytes(package.getvalue())
    with pytest.raises(PackageFormatError, match="scheduled task targets"):
        PluginPackageVerifier(require_signature=False).inspect(path)


@pytest.fixture
async def scheduled(monkeypatch):
    """Real grants and job rows, with only the isolated runtime transport substituted."""
    installation_id, actor_id, other_id = uuid4(), uuid4(), uuid4()
    task = {"id": "summary", "name": "Summary", "action_id": "summarize"}
    installed = {
        "plugin_id": "example.tasks",
        "name": "Tasks example",
        "installation_id": str(installation_id),
        "background_user_id": str(actor_id),
        "api_contract_version": "1.1.0",
        "enabled": True,
        "compatible": True,
        "status": "running",
        "health": "healthy",
        "scheduled_tasks": [task],
    }
    transport = AsyncMock()
    transport.plugins.return_value = [installed]
    transport.plugin_ui.return_value = {
        "api_contract_version": "1.1.0",
        "plugin_id": "example.tasks",
        "title": "Tasks",
        "actions": [
            {
                "id": "summarize",
                "label": "Summary",
                "handler": "plugin:summary",
                "capability": {"name": "games.read", "version": 1},
            }
        ],
    }
    transport.run_scheduled_task.return_value = {
        "completed": True,
        "summary": "Read 3 games",
        "private": "not persisted",
    }
    monkeypatch.setattr(plugin_jobs, "client", transport)
    monkeypatch.setattr(plugin_jobs, "_last_inventory", [])
    monkeypatch.setattr(plugin_jobs, "_running", {})
    async with SessionLocal() as db:
        for user_id in (actor_id, other_id):
            db.add(
                User(
                    id=user_id,
                    username="task-" + str(user_id),
                    email=f"{user_id}@example.invalid",
                    password_hash="unused",
                    is_admin=True,
                )
            )
        await db.flush()
        for capability in ("tasks.background", "games.read"):
            db.add(
                PluginPermissionGrant(
                    plugin_id="example.tasks",
                    installation_id=installation_id,
                    user_id=actor_id,
                    capability=capability,
                    capability_version=1,
                )
            )
        await db.commit()
    try:
        yield installed, transport, installation_id, actor_id, other_id
    finally:
        running = list(plugin_jobs._running.values())
        for task_run in running:
            task_run.cancel()
        await asyncio.gather(*running, return_exceptions=True)
        async with SessionLocal() as db:
            await db.execute(
                delete(JobSetting).where(
                    JobSetting.job_id == plugin_jobs.task_job_id(installation_id, "summary")
                )
            )
            await db.execute(delete(User).where(User.id.in_([actor_id, other_id])))
            await db.commit()


@pytest.mark.asyncio
async def test_tasks_start_off_and_keep_schedules_results_and_no_overlap(scheduled):
    installed, transport, installation_id, _, _ = scheduled
    started, release = asyncio.Event(), asyncio.Event()

    async def complete_after_release(*_args):
        started.set()
        await release.wait()
        return {"completed": True, "summary": "Read 3 games", "private": "not persisted"}

    transport.run_scheduled_task.side_effect = complete_after_release
    job_id = plugin_jobs.task_job_id(installation_id, "summary")
    assert len(job_id) <= 50
    assert job_id != plugin_jobs.task_job_id(uuid4(), "summary")
    async with SessionLocal() as db:
        listed = next(job for job in await job_routes.list_jobs(db) if job["id"] == job_id)
        assert (
            listed["available"]
            and not listed["enabled"]
            and listed["plugin_id"] == installed["plugin_id"]
        )
        await job_routes.update_job(
            job_id, job_routes.JobUpdate(enabled=True, interval_minutes=15), db
        )
        with pytest.raises(HTTPException) as invalid:
            await job_routes.update_job(job_id, job_routes.JobUpdate(interval_minutes=1), db)
        assert invalid.value.status_code == 400
        assert await job_routes.run_job(job_id, None, db) == {"running": True}
        await started.wait()
        assert await job_routes.run_job(job_id, None, db) == {"running": True}
    release.set()
    await asyncio.gather(*list(plugin_jobs._running.values()))
    transport.run_scheduled_task.assert_awaited_once_with(
        "example.tasks", str(installation_id), "summary", "manual"
    )
    async with SessionLocal() as db:
        row = await db.get(JobSetting, job_id)
        assert row.enabled and row.interval_minutes == 15 and row.last_run_at
        assert row.last_result == {"completed": True, "summary": "Read 3 games"}
        again = next(job for job in await job_routes.list_jobs(db) if job["id"] == job_id)
        assert again["last_summary"] == "Read 3 games"


@pytest.mark.asyncio
async def test_other_account_grants_cannot_replace_the_worker_grant(scheduled):
    _, transport, installation_id, actor_id, other_id = scheduled
    async with SessionLocal() as db:
        await db.execute(
            delete(PluginPermissionGrant).where(
                PluginPermissionGrant.installation_id == installation_id,
                PluginPermissionGrant.capability == "tasks.background",
            )
        )
        db.add(
            PluginPermissionGrant(
                plugin_id="example.tasks",
                installation_id=installation_id,
                user_id=other_id,
                capability="tasks.background",
                capability_version=1,
            )
        )
        await db.commit()
        spec = (await plugin_jobs.get_plugin_jobs(db))[0]
        assert not spec.available and "Background permission" in spec.unavailable_reason
        with pytest.raises(HTTPException) as denied:
            await job_routes.run_job(spec.id, None, db)
        assert denied.value.status_code == 409
        transport.run_scheduled_task.assert_not_awaited()
        db.add(
            PluginPermissionGrant(
                plugin_id="example.tasks",
                installation_id=installation_id,
                user_id=actor_id,
                capability="tasks.background",
                capability_version=1,
            )
        )
        await db.commit()
        assert (await plugin_jobs.get_plugin_jobs(db))[0].available


@pytest.mark.asyncio
async def test_revoke_action_permission_stop_legacy_and_outage_pause_tasks(scheduled):
    installed, transport, installation_id, _, _ = scheduled
    async with SessionLocal() as db:
        assert (await plugin_jobs.get_plugin_jobs(db))[0].available
        grant = await db.scalar(
            select(PluginPermissionGrant).where(
                PluginPermissionGrant.installation_id == installation_id,
                PluginPermissionGrant.capability == "games.read",
            )
        )
        grant.revoked_at = int(time.time())
        await db.commit()
        assert "games.read" in (await plugin_jobs.get_plugin_jobs(db))[0].unavailable_reason
        grant.revoked_at = None
        await db.commit()
        installed["status"] = "stopped"
        assert not (await plugin_jobs.get_plugin_jobs(db))[0].available
        installed["status"] = "running"
        installed["legacy_compatibility"] = True
        assert not await plugin_jobs.get_plugin_jobs(db)
        installed["legacy_compatibility"] = False
        assert (await plugin_jobs.get_plugin_jobs(db))[0].available
        transport.plugins.side_effect = PluginRuntimeUnavailable("offline")
        assert (
            "runtime is unavailable"
            in (await plugin_jobs.get_plugin_jobs(db))[0].unavailable_reason
        )


@pytest.mark.asyncio
async def test_revocation_between_start_and_dispatch_is_rechecked(scheduled):
    _, transport, installation_id, _, _ = scheduled
    async with SessionLocal() as db:
        spec = (await plugin_jobs.get_plugin_jobs(db))[0]
        await db.execute(
            delete(PluginPermissionGrant).where(
                PluginPermissionGrant.installation_id == installation_id,
                PluginPermissionGrant.capability == "tasks.background",
            )
        )
        await db.commit()
    spec.start("needed")
    await asyncio.gather(*list(plugin_jobs._running.values()))
    transport.run_scheduled_task.assert_not_awaited()
