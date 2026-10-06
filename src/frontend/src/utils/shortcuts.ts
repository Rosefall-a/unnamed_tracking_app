import { keyboardShortcuts, activeShortcutKeys } from "../state/shortcuts";
import {
  shortcutPathMatches,
  NAVIGATION_SHORTCUTS,
} from "./shortcutDefinitions";
import { shortcutKeyLabel } from "./shortcutKeys";
export { NAVIGATION_SHORTCUTS } from "./shortcutDefinitions";

export interface ShortcutGroup {
  title: string;
  current: boolean;
  shortcuts: {
    keys: string;
    label: string;
    disabled?: boolean;
    conflict?: string;
  }[];
}
export function shortcutGroupsForPath(path: string): ShortcutGroup[] {
  const groups = new Map<string, ShortcutGroup>();
  const relevance = new Map<string, number>();
  for (const item of keyboardShortcuts.value) {
    const group = groups.get(item.group) ?? {
      title: item.group,
      current: false,
      shortcuts: [],
    };
    group.current ||=
      !!item.paths?.length && shortcutPathMatches(item.paths, path);
    if (item.paths?.length && shortcutPathMatches(item.paths, path))
      relevance.set(
        item.group,
        Math.min(relevance.get(item.group) ?? Infinity, item.paths.length),
      );
    group.shortcuts.push({
      keys: item.keys.map(shortcutKeyLabel).join(" / "),
      label: item.label,
      disabled: !activeShortcutKeys(item.id).length,
      conflict: item.conflicts.length
        ? `Conflicts with ${item.conflicts.map((conflict) => conflict.label).join(", ")}`
        : undefined,
    });
    groups.set(item.group, group);
  }
  return [...groups.values()].sort(
    (a, b) =>
      Number(b.current) - Number(a.current) ||
      (a.current
        ? (relevance.get(a.title) ?? Infinity) -
          (relevance.get(b.title) ?? Infinity)
        : 0) ||
      Number(b.title === "Anywhere") - Number(a.title === "Anywhere"),
  );
}
export function navigationShortcutForKey(key: unknown) {
  if (typeof key !== "string" || key.length !== 1) return undefined;
  return NAVIGATION_SHORTCUTS.find((item) => item.key === key.toLowerCase());
}
export function navigationShortcutForPath(path: string): string | undefined {
  const pathname = path.split("?")[0];
  const item = keyboardShortcuts.value.find(
    (item) =>
      item.destination === pathname && activeShortcutKeys(item.id).length,
  );
  return item
    ? activeShortcutKeys(item.id)
        .map(shortcutKeyLabel)
        .join(" / ")
        .replaceAll(" + ", "+")
    : undefined;
}
export function navigationTooltip(label: string, path: string): string {
  const shortcut = navigationShortcutForPath(path);
  return shortcut ? `${label} · ${shortcut.replaceAll("+", " + ")}` : label;
}
