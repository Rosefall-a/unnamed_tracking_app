import { computed, shallowRef } from "vue";
import { preferences } from "./preferences";
import {
  resolveShortcuts,
  type ResolvedShortcut,
} from "../utils/shortcutResolution";
export { resolveShortcuts } from "../utils/shortcutResolution";
export type {
  ShortcutOverride,
  ResolvedShortcut,
} from "../utils/shortcutResolution";
import {
  CORE_SHORTCUTS,
  shortcutPathMatches,
  type ShortcutDefinition,
} from "../utils/shortcutDefinitions";
import {
  matchesShortcutKey,
  normalizeShortcutKey,
  shortcutKeyLabel,
  type ShortcutKeyEvent,
} from "../utils/shortcutKeys";

interface PluginRegistration {
  definition: ShortcutDefinition;
  callback?: () => void | Promise<void>;
  dynamic: boolean;
  sequence: number;
}
const registrations = shallowRef<Map<string, PluginRegistration>>(new Map());
let sequence = 0;
export const shortcutDefinitions = computed(() => [
  ...CORE_SHORTCUTS,
  ...[...registrations.value.values()]
    .sort((a, b) => a.sequence - b.sequence)
    .map((item) => item.definition),
]);
export const keyboardShortcuts = computed(() =>
  resolveShortcuts(
    shortcutDefinitions.value,
    preferences.value.keyboard_shortcut_overrides ?? {},
  ),
);
export interface NativeShortcut {
  id: string;
  label: string;
  keys: string[];
  group?: string;
  paths?: string[];
  destination?: string;
  control?: "search" | "create";
}
function ownsShortcutPath(pluginId: string, path: string): boolean {
  try {
    const url = new URL(path, "https://host.invalid");
    return (
      path.startsWith(`/plugins/${pluginId}/`) &&
      url.pathname.startsWith(`/plugins/${pluginId}/`) &&
      path
        .split(/[/?#]/)
        .every((part) => ![".", ".."].includes(decodeURIComponent(part)))
    );
  } catch {
    return false;
  }
}
export function registerPluginShortcut(
  pluginId: string,
  shortcut: NativeShortcut,
  callback?: () => void | Promise<void>,
  dynamic = true,
): () => void {
  if (
    !/^[a-z0-9][a-z0-9._-]{0,127}$/.test(shortcut.id) ||
    !shortcut.label.trim() ||
    shortcut.label.length > 256 ||
    (shortcut.group?.length ?? 0) > 128 ||
    !shortcut.keys.length ||
    shortcut.keys.length > 4 ||
    shortcut.keys.some((key) => !normalizeShortcutKey(key)) ||
    (shortcut.paths?.length ?? 0) > 32 ||
    shortcut.paths?.some((path) => !ownsShortcutPath(pluginId, path)) ||
    (shortcut.destination &&
      !ownsShortcutPath(pluginId, shortcut.destination)) ||
    (shortcut.control && !["search", "create"].includes(shortcut.control))
  )
    throw new Error("Plugin shortcut declaration is invalid.");
  const id = `plugin:${pluginId}:${shortcut.id}`;
  const previous = registrations.value.get(id);
  if (
    !previous &&
    [...registrations.value.values()].filter(
      (item) => item.definition.pluginId === pluginId,
    ).length >= 64
  )
    throw new Error("Plugins can register at most 64 shortcuts.");
  if (previous && previous.dynamic !== dynamic)
    throw new Error("A shortcut with this ID is already declared.");
  const next = new Map(registrations.value);
  const registration = {
    definition: {
      ...shortcut,
      id,
      pluginId,
      group: shortcut.group || pluginId,
    },
    callback,
    dynamic,
    sequence: previous?.sequence ?? sequence++,
  };
  next.set(id, registration);
  registrations.value = next;
  return () => {
    if (registrations.value.get(id) !== registration) return;
    const remaining = new Map(registrations.value);
    remaining.delete(id);
    registrations.value = remaining;
  };
}
export function retainPluginShortcuts(
  pluginIds: ReadonlySet<string>,
  declaredIds?: ReadonlySet<string>,
): void {
  registrations.value = new Map(
    [...registrations.value].filter(
      ([id, item]) =>
        pluginIds.has(item.definition.pluginId!) &&
        (!declaredIds || item.dynamic || declaredIds.has(id)),
    ),
  );
}
export function shortcutBinding(id: string): ResolvedShortcut | undefined {
  return keyboardShortcuts.value.find((item) => item.id === id);
}
export function activeShortcutKeys(id: string): string[] {
  return preferences.value.keyboard_shortcuts_enabled === false
    ? []
    : (shortcutBinding(id)?.activeKeys ?? []);
}
export function matchesShortcut(id: string, event: ShortcutKeyEvent): boolean {
  return activeShortcutKeys(id).some((key) => matchesShortcutKey(key, event));
}
export function shortcutHint(id: string): string | undefined {
  const keys = activeShortcutKeys(id);
  return keys.length ? keys.map(shortcutKeyLabel).join(" / ") : undefined;
}
export function shortcutAriaKeys(id: string): string | undefined {
  const expand = (key: string) =>
    key.includes("CtrlOrMeta")
      ? [
          key.replace("CtrlOrMeta", "Control"),
          key.replace("CtrlOrMeta", "Meta"),
        ]
      : [key.replace("Ctrl", "Control")];
  return activeShortcutKeys(id).flatMap(expand).join(" ") || undefined;
}
export function shortcutForEvent(
  event: ShortcutKeyEvent,
  path: string,
  context?: string,
): ResolvedShortcut | undefined {
  if (preferences.value.keyboard_shortcuts_enabled === false) return;
  return keyboardShortcuts.value.find(
    (item) =>
      shortcutPathMatches(item.paths, path) &&
      (!item.context || item.context === context) &&
      item.activeKeys.some((key) => matchesShortcutKey(key, event)),
  );
}
export async function runPluginShortcut(id: string): Promise<void> {
  await registrations.value.get(id)?.callback?.();
}
