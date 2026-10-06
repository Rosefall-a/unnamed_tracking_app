"""Adapt approved plugin actions to the host's existing Tasks scheduler."""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID, uuid5

from pydantic import ValidationError
from sqlalchemy import or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.plugin_permissions import PluginPermissionGrant
from src.database.models.user import User
from src.database.session import SessionLocal
from src.features.jobs import JobSpec, record_run
from src.plugin_api.contracts import PluginScheduledTask, PluginUiDocument, UiAction
from src.plugin_api.grants import effective_capabilities, installation_is_executable
from src.plugin_api.runtime_client import (
    PluginRuntimeClient,
    PluginRuntimeRequestError,
    PluginRuntimeUnavailable,
)

logger = logging.getLogger(__name__)
client = PluginRuntimeClient()
_last_inventory: list[dict[str, Any]] = []
_running: dict[str, asyncio.Task[None]] = {}


def task_job_id(installation_id: UUID, task_id: str) -> str:
    """Keep schedules stable across updates without sharing another installation's rows."""
    return "plugin:" + str(uuid5(installation_id, task_id))


async def _background_capabilities(
    db: AsyncSession, plugin: dict[str, Any], installation_id: UUID
) -> frozenset[str]:
    """Use the existing worker identity, never the administrator pressing Run now."""
    try:
        user_id = UUID(str(plugin.get("background_user_id", "")))
    except ValueError:
        return frozenset()
    user = await db.get(User, user_id)
    if user is None or not user.is_active or not user.is_admin:
        return frozenset()
    grants = await db.execute(
        select(PluginPermissionGrant.capability).where(
            PluginPermissionGrant.plugin_id == plugin["plugin_id"],
            PluginPermissionGrant.installation_id == installation_id,
            PluginPermissionGrant.capability_version == 1,
            PluginPermissionGrant.revoked_at.is_(None),
            PluginPermissionGrant.device_id.is_(None),
            or_(PluginPermissionGrant.user_id.is_(None), PluginPermissionGrant.user_id == user_id),
        )
    )
    return await effective_capabilities(
        db, plugin["plugin_id"], installation_id, user_id, list(grants.scalars())
    )


async def _task_availability(
    db: AsyncSession, plugin: dict[str, Any], installation_id: UUID, runtime_available: bool
) -> tuple[frozenset[str], dict[str, UiAction], str]:
    """Resolve lifecycle, exact-scope grants and declared actions before exposing controls."""
    if not runtime_available:
        return frozenset(), {}, "Plugin runtime is unavailable. Scheduling is paused."
    if not installation_is_executable(plugin):
        return frozenset(), {}, "Start this compatible plugin to use its tasks."
    capabilities = await _background_capabilities(db, plugin, installation_id)
    if "tasks.background" not in capabilities:
        return (
            capabilities,
            {},
            "Background permission or the plugin's administrator identity is unavailable.",
        )
    try:
        document = PluginUiDocument.model_validate(await client.plugin_ui(plugin["plugin_id"]))
    except (PluginRuntimeUnavailable, PluginRuntimeRequestError, ValidationError):
        return capabilities, {}, "Plugin task declarations are unavailable."
    return capabilities, {action.id: action for action in document.actions}, ""


def _result_summary(result: dict[str, Any]) -> str:
    """Display only the bounded public task summary."""
    return str(result.get("summary") or "")[:512]


def _action_unavailable_reason(action: UiAction | None, capabilities: frozenset[str]) -> str:
    """Keep missing action and revoked permission diagnostics explicit."""
    if action is None or action.handler is None or action.confirmation is not None:
        return "This task must reference a declared action with no confirmation."
    if action.capability is not None and action.capability.name.value not in capabilities:
        return f"Required permission {action.capability.name.value} is unavailable."
    return ""


async def _execute_task(spec: JobSpec, installation_id: UUID, task_id: str, mode: str) -> None:
    """Recheck current identity and grants immediately before isolated dispatch."""
    result: dict[str, Any] = {
        "completed": False,
        "summary": "Plugin task could not run. Check its diagnostics.",
    }
    try:
        async with SessionLocal() as db:
            current = next((job for job in await get_plugin_jobs(db) if job.id == spec.id), None)
            if current is None or not current.available:
                result["summary"] = (
                    current.unavailable_reason
                    if current
                    else "This plugin task is no longer installed."
                )
            else:
                response = await client.run_scheduled_task(
                    str(spec.plugin_id),
                    str(installation_id),
                    task_id,
                    "scheduled" if mode == "needed" else "manual",
                )
                completed = response.get("completed") is not False
                summary = response.get("summary")
                result = {
                    "completed": completed,
                    "summary": summary[:512]
                    if isinstance(summary, str)
                    else "Completed"
                    if completed
                    else "Task reported a failure.",
                }
    except (PluginRuntimeUnavailable, PluginRuntimeRequestError):
        logger.warning("Plugin task dispatch failed: %s", spec.id)
    except (SQLAlchemyError, OSError, ValueError):
        logger.exception("Plugin task failed: %s", spec.id)
    finally:
        try:
            await record_run(spec.id, result, spec=spec)
        except SQLAlchemyError:
            logger.exception("Plugin task result could not be saved: %s", spec.id)
        finally:
            _running.pop(spec.id, None)


def _job_spec(
    plugin: dict[str, Any], installation_id: UUID, declaration: PluginScheduledTask, reason: str
) -> JobSpec:
    """Reuse ordinary schedule persistence, Run now and no-overlap behavior."""
    job_id = task_job_id(installation_id, declaration.id)

    def start(mode: str) -> dict[str, Any]:
        if reason:
            return {"running": False, "detail": reason}
        if job_id not in _running:
            _running[job_id] = asyncio.create_task(
                _execute_task(spec, installation_id, declaration.id, mode)
            )
        return {"running": True}

    spec = JobSpec(
        id=job_id,
        name=declaration.name,
        description=declaration.description,
        min_interval_minutes=declaration.min_interval_minutes,
        max_interval_minutes=declaration.max_interval_minutes,
        default_interval_minutes=declaration.default_interval_minutes,
        default_enabled=False,
        start=start,
        is_running=lambda: job_id in _running,
        summarize=_result_summary,
        manual_mode="all",
        plugin_id=str(plugin["plugin_id"]),
        plugin_name=str(plugin.get("name") or plugin["plugin_id"]),
        available=not reason,
        unavailable_reason=reason,
    )
    return spec


async def get_plugin_jobs(db: AsyncSession) -> list[JobSpec]:
    """Return bounded v1.1 jobs; cached declarations stay visibly paused during outages."""
    try:
        inventory = await client.plugins()
        _last_inventory[:] = inventory
        runtime_available = True
    except (PluginRuntimeUnavailable, PluginRuntimeRequestError):
        inventory = _last_inventory
        runtime_available = False
    jobs: list[JobSpec] = []
    for plugin in inventory:
        raw_tasks = plugin.get("scheduled_tasks")
        if (
            plugin.get("legacy_compatibility")
            or not isinstance(raw_tasks, list)
            or not raw_tasks
            or len(raw_tasks) > 32
        ):
            continue
        try:
            installation_id = UUID(str(plugin.get("installation_id", "")))
            declarations = [PluginScheduledTask.model_validate(task) for task in raw_tasks]
        except (ValueError, ValidationError):
            continue
        if len({task.id for task in declarations}) != len(declarations):
            continue
        capabilities, actions, shared_reason = await _task_availability(
            db, plugin, installation_id, runtime_available
        )
        for declaration in declarations:
            reason = shared_reason or _action_unavailable_reason(
                actions.get(declaration.action_id), capabilities
            )
            jobs.append(_job_spec(plugin, installation_id, declaration, reason))
    return jobs
