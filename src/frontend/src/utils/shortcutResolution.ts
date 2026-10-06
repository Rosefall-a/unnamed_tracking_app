import {
  shortcutScopesOverlap,
  type ShortcutDefinition,
} from "./shortcutDefinitions";
import { normalizeShortcutKey, shortcutKeysOverlap } from "./shortcutKeys";

export interface ShortcutOverride {
  enabled?: boolean;
  keys?: string[];
  enabled_order?: number;
}
export interface ResolvedShortcut extends ShortcutDefinition {
  enabled: boolean;
  requestedEnabled: boolean;
  activeKeys: string[];
  conflicts: Array<{ key: string; id: string; label: string }>;
}

function priority(item: ShortcutDefinition, override?: ShortcutOverride) {
  return override?.enabled_order ?? (item.pluginId ? Infinity : 0);
}

/** Resolve ownership before displaying entries in their original help order. */
export function resolveShortcuts(
  definitions: ShortcutDefinition[],
  overrides: Record<string, ShortcutOverride>,
): ResolvedShortcut[] {
  const entries = definitions.map((item): ResolvedShortcut => ({
    ...item,
    keys: (overrides[item.id]?.keys ?? item.keys)
      .map(normalizeShortcutKey)
      .filter((key): key is string => !!key),
    requestedEnabled: overrides[item.id]?.enabled !== false,
    enabled: false,
    activeKeys: [],
    conflicts: [],
  }));
  const owners: ResolvedShortcut[] = [];
  const findConflicts = (entry: ResolvedShortcut) =>
    entry.keys.flatMap((key) => {
      const owner = owners.find(
        (other) =>
          other.id !== entry.id &&
          shortcutScopesOverlap(entry, other) &&
          other.activeKeys.some((otherKey) =>
            shortcutKeysOverlap(key, otherKey),
          ),
      );
      return owner ? [{ key, id: owner.id, label: owner.label }] : [];
    });
  for (const entry of [...entries].sort(
    (a, b) => priority(a, overrides[a.id]) - priority(b, overrides[b.id]),
  )) {
    if (!entry.requestedEnabled) continue;
    entry.conflicts = findConflicts(entry);
    if (entry.conflicts.length) continue;
    entry.enabled = true;
    entry.activeKeys = [...entry.keys];
    owners.push(entry);
  }
  // Disabled bindings still explain the current owner without claiming a key.
  for (const entry of entries)
    if (!entry.enabled) entry.conflicts = findConflicts(entry);
  return entries;
}

function copyOverrides(overrides: Record<string, ShortcutOverride>) {
  const copy = Object.fromEntries(
    Object.entries(overrides).map(([id, value]) => [id, { ...value }]),
  );
  const orders = Object.values(copy)
    .map((item) => item.enabled_order ?? 0)
    .filter(Number.isSafeInteger);
  // Keep incrementing safe even for imported preferences at the integer limit.
  if (Math.max(0, ...orders) >= Number.MAX_SAFE_INTEGER - 1024) {
    Object.values(copy)
      .filter((item) => item.enabled_order !== undefined)
      .sort((a, b) => a.enabled_order! - b.enabled_order!)
      .forEach((item, index) => (item.enabled_order = index + 1));
  }
  return copy;
}

function nextOrder(overrides: Record<string, ShortcutOverride>): number {
  return (
    Math.max(
      0,
      ...Object.values(overrides).map((item) => item.enabled_order ?? 0),
    ) + 1
  );
}

/** Persist first activation and disable newcomers once, rather than auto-resume. */
export function reconcileShortcutOverrides(
  definitions: ShortcutDefinition[],
  overrides: Record<string, ShortcutOverride>,
) {
  const next = copyOverrides(overrides);
  for (const item of definitions) {
    if (
      next[item.id]?.enabled === false ||
      next[item.id]?.enabled_order !== undefined
    )
      continue;
    next[item.id] = { ...next[item.id], enabled_order: nextOrder(next) };
  }
  const disabled = resolveShortcuts(definitions, next).filter(
    (item) => item.requestedEnabled && !item.enabled,
  );
  for (const item of disabled)
    next[item.id] = { ...next[item.id], enabled: false };
  return { overrides: next, disabled };
}

/** A re-enable or changed active key joins the end of the activation order. */
export function prepareShortcutOverride(
  definitions: ShortcutDefinition[],
  overrides: Record<string, ShortcutOverride>,
  id: string,
  changes: ShortcutOverride,
) {
  const next = copyOverrides(overrides);
  const current = next[id] ?? {};
  const definition = definitions.find((item) => item.id === id);
  const entry = { ...current, ...changes };
  const keysChanged =
    JSON.stringify(entry.keys ?? definition?.keys) !==
    JSON.stringify(current.keys ?? definition?.keys);
  if (
    entry.enabled !== false &&
    (current.enabled === false || keysChanged || !entry.enabled_order)
  )
    entry.enabled_order = nextOrder(next);
  next[id] = entry;
  return reconcileShortcutOverrides(definitions, next);
}
