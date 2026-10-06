"""Shared dependency traversal for strict activation and diagnostic planning."""

from collections.abc import Callable, Iterable


def walk_dependency_graph(
    roots: Iterable[str],
    dependencies: Callable[[str], Iterable[str]],
    on_cycle: Callable[[tuple[str, ...]], None],
) -> tuple[tuple[str, ...], set[str]]:
    """Visit dependencies first, preserving caller order and cycle-reporting policy."""
    visiting: set[str] = set()
    visited: set[str] = set()
    order: list[str] = []

    def visit(plugin_id: str, path: tuple[str, ...]) -> None:
        if plugin_id in visiting:
            on_cycle((*path, plugin_id))
            return
        if plugin_id in visited:
            return
        visiting.add(plugin_id)
        for dependency_id in dependencies(plugin_id):
            visit(dependency_id, (*path, plugin_id))
        visiting.remove(plugin_id)
        visited.add(plugin_id)
        order.append(plugin_id)

    for plugin_id in roots:
        visit(plugin_id, ())
    return tuple(order), visited
