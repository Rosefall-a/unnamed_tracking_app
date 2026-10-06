"""Resolve candidate dependencies and reverse constraints without installing code."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Iterable, Mapping

from .contracts import PluginDependency, PluginManifest, version_satisfies


class DependencyState(StrEnum):
    SATISFIED = "satisfied"
    MISSING = "missing"
    INCOMPATIBLE = "incompatible"
    OPTIONAL_MISSING = "optional_missing"
    OPTIONAL_INCOMPATIBLE = "optional_incompatible"
    AVAILABLE = "available"


@dataclass(frozen=True, slots=True)
class DependencyPlanItem:
    plugin_id: str
    version_range: str
    optional: bool
    state: DependencyState
    installed_version: str | None = None
    available_version: str | None = None
    source_url: str | None = None


@dataclass(frozen=True, slots=True)
class DependencyPlan:
    items: tuple[DependencyPlanItem, ...]
    installation_order: tuple[str, ...]
    conflicts: tuple[str, ...]

    @property
    def ready(self) -> bool:
        blocking = {
            DependencyState.MISSING,
            DependencyState.INCOMPATIBLE,
            DependencyState.AVAILABLE,
        }
        return not self.conflicts and not any(
            item.state in blocking and not item.optional for item in self.items
        )


def _summary_version(summary: Mapping[str, Any] | None) -> str | None:
    if summary is None:
        return None
    value = summary.get("version")
    return str(value) if isinstance(value, str) else None


def _dependencies(summary: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    value = summary.get("dependencies", ())
    if not isinstance(value, (list, tuple)):
        return ()
    return (item for item in value if isinstance(item, Mapping))


def _plan_item(
    dependency: PluginDependency,
    installed_item: Mapping[str, Any] | None,
    available_item: Mapping[str, Any] | None,
) -> DependencyPlanItem:
    """Resolve the candidate's one direct dependency without modifying any installation."""
    installed_version = _summary_version(installed_item)
    available_version = _summary_version(available_item)
    source_url = (
        str(available_item.get("url"))
        if available_item is not None and isinstance(available_item.get("url"), str)
        else None
    )
    if installed_version and version_satisfies(installed_version, dependency.version_range):
        state = DependencyState.SATISFIED
    elif installed_version:
        state = (
            DependencyState.OPTIONAL_INCOMPATIBLE
            if dependency.optional
            else DependencyState.INCOMPATIBLE
        )
    elif available_version and version_satisfies(available_version, dependency.version_range):
        state = DependencyState.AVAILABLE
    else:
        state = DependencyState.OPTIONAL_MISSING if dependency.optional else DependencyState.MISSING
    return DependencyPlanItem(
        plugin_id=dependency.plugin_id,
        version_range=dependency.version_range,
        optional=dependency.optional,
        state=state,
        installed_version=installed_version,
        available_version=available_version,
        source_url=source_url,
    )


def _dependency_order(
    manifest: PluginManifest,
    installed_by_id: Mapping[str, Mapping[str, Any]],
    available_by_id: Mapping[str, Mapping[str, Any]],
) -> tuple[tuple[str, ...], set[str], list[str]]:
    """Visit the installed/candidate graph in dependency order and retain cycle diagnostics."""
    cycles: list[str] = []
    graph: dict[str, tuple[str, ...]] = {
        plugin_id: tuple(
            str(item.get("plugin_id"))
            for item in _dependencies(summary)
            if not bool(item.get("optional")) and item.get("plugin_id")
        )
        for plugin_id, summary in available_by_id.items()
    }
    graph.update(
        {
            plugin_id: tuple(
                str(item.get("plugin_id"))
                for item in _dependencies(summary)
                if not bool(item.get("optional")) and item.get("plugin_id")
            )
            for plugin_id, summary in installed_by_id.items()
        }
    )
    graph[manifest.plugin_id] = tuple(
        dependency.plugin_id for dependency in manifest.dependencies if not dependency.optional
    )
    visiting: set[str] = set()
    visited: set[str] = set()
    order: list[str] = []

    def visit(plugin_id: str, path: tuple[str, ...]) -> None:
        if plugin_id in visiting:
            cycle = " -> ".join((*path, plugin_id))
            cycles.append(f"dependency cycle detected: {cycle}")
            return
        if plugin_id in visited:
            return
        visiting.add(plugin_id)
        for dependency_id in graph.get(plugin_id, ()):
            if dependency_id in graph:
                visit(dependency_id, (*path, plugin_id))
        visiting.remove(plugin_id)
        visited.add(plugin_id)
        order.append(plugin_id)

    visit(manifest.plugin_id, ())
    return tuple(order), visited, cycles


def _reverse_conflicts(
    manifest: PluginManifest,
    installed_by_id: Mapping[str, Mapping[str, Any]],
    visited: set[str],
) -> list[str]:
    conflicts: list[str] = []
    # Check transitive dependencies and reverse constraints on an update, not
    # just the candidate's direct declarations. Available packages are preview
    # hints; they cannot satisfy the installed graph before activation.
    versions = {plugin_id: _summary_version(item) for plugin_id, item in installed_by_id.items()}
    versions[manifest.plugin_id] = manifest.version
    for owner_id, summary in installed_by_id.items():
        if owner_id == manifest.plugin_id:
            continue
        for summary_dependency in _dependencies(summary):
            dependency_id = str(summary_dependency.get("plugin_id", ""))
            if bool(summary_dependency.get("optional")):
                continue
            if owner_id not in visited and dependency_id != manifest.plugin_id:
                continue
            version = versions.get(dependency_id)
            version_range = str(summary_dependency.get("version_range", "*"))
            if version is None or not version_satisfies(version, version_range):
                conflicts.append(f"{owner_id} requires {dependency_id} matching {version_range}")
    return conflicts


def plan_dependencies(
    manifest: PluginManifest,
    installed: Iterable[Mapping[str, Any]],
    available: Iterable[Mapping[str, Any]] = (),
) -> DependencyPlan:
    """Resolve one candidate against installed and source-advertised versions."""
    installed_by_id = {
        str(item.get("plugin_id")): item
        for item in installed
        if item.get("plugin_id") and not item.get("installation_pending")
    }
    available_by_id = {
        str(item.get("plugin_id")): item for item in available if item.get("plugin_id")
    }
    items: list[DependencyPlanItem] = []
    conflicts: list[str] = []

    for dependency in manifest.dependencies:
        item = _plan_item(
            dependency,
            installed_by_id.get(dependency.plugin_id),
            available_by_id.get(dependency.plugin_id),
        )
        if item.state is DependencyState.INCOMPATIBLE:
            conflicts.append(
                f"{dependency.plugin_id} {item.installed_version} does not satisfy "
                f"{dependency.version_range}"
            )
        items.append(item)

    order, visited, cycles = _dependency_order(manifest, installed_by_id, available_by_id)
    conflicts.extend(cycles)
    conflicts.extend(_reverse_conflicts(manifest, installed_by_id, visited))
    return DependencyPlan(tuple(items), order, tuple(dict.fromkeys(conflicts)))
