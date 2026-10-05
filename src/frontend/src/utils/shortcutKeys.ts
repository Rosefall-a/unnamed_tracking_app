export interface ShortcutKeyEvent {
  key: string;
  code?: string;
  ctrlKey: boolean;
  metaKey: boolean;
  altKey: boolean;
  shiftKey: boolean;
}

const modifiers = ["CtrlOrMeta", "Ctrl", "Meta", "Alt", "Shift"];
const namedKeys = [
  "ArrowUp",
  "ArrowDown",
  "ArrowLeft",
  "ArrowRight",
  "Enter",
  "Escape",
  "Space",
  "Tab",
  "Home",
  "End",
  "PageUp",
  "PageDown",
  "Delete",
  "Backspace",
  "Plus",
];
export function normalizeShortcutKey(value: string): string | undefined {
  if (typeof value !== "string" || value.length > 64) return;
  const parts = value
    .trim()
    .split("+")
    .map((part) => part.trim());
  const raw = parts.pop() ?? "";
  const key =
    namedKeys.find((item) => item.toLowerCase() === raw.toLowerCase()) ??
    (/^[a-z0-9/?.,;[\]\-='`]$/i.test(raw) ||
    /^F(?:[1-9]|1\d|2[0-4])$/i.test(raw)
      ? raw.toUpperCase()
      : undefined);
  if (!key) return;
  const mods = parts.map((part) =>
    modifiers.find((item) => item.toLowerCase() === part.toLowerCase()),
  );
  if (
    mods.some((part) => !part) ||
    new Set(mods).size !== mods.length ||
    (mods.includes("CtrlOrMeta") &&
      (mods.includes("Ctrl") || mods.includes("Meta")))
  )
    return;
  return [...modifiers.filter((part) => mods.includes(part)), key].join("+");
}
export function matchesShortcutKey(
  binding: string,
  event: ShortcutKeyEvent,
): boolean {
  const normalized = normalizeShortcutKey(binding);
  if (!normalized) return false;
  const parts = normalized.split("+");
  const key = parts.pop()!;
  const portable = parts.includes("CtrlOrMeta");
  if (
    portable
      ? !(
          (event.ctrlKey && !event.metaKey) ||
          (event.metaKey && !event.ctrlKey)
        )
      : event.ctrlKey !== parts.includes("Ctrl") ||
        event.metaKey !== parts.includes("Meta")
  )
    return false;
  if (event.altKey !== parts.includes("Alt")) return false;
  // A question mark already includes Shift on many keyboard layouts.
  if (key !== "?" && event.shiftKey !== parts.includes("Shift")) return false;
  const actual =
    event.key === " " ? "Space" : event.key === "+" ? "Plus" : event.key;
  if (actual.toUpperCase() === key.toUpperCase()) return true;
  return event.altKey && /^[A-Z]$/.test(key) && event.code === `Key${key}`;
}
export function shortcutKeyLabel(key: string): string {
  return key.replace("CtrlOrMeta", "Ctrl/Cmd").replaceAll("+", " + ");
}
export function shortcutKeysOverlap(first: string, second: string): boolean {
  const expand = (key: string) =>
    key.includes("CtrlOrMeta")
      ? [key.replace("CtrlOrMeta", "Ctrl"), key.replace("CtrlOrMeta", "Meta")]
      : [key];
  return expand(first).some((key) => expand(second).includes(key));
}

export function shortcutKeyEvent(
  binding: string,
): ShortcutKeyEvent | undefined {
  const normalized = normalizeShortcutKey(binding);
  if (!normalized) return;
  const parts = normalized.split("+");
  const key = parts.pop()!;
  return {
    key: key === "Space" ? " " : key === "Plus" ? "+" : key,
    code: /^[A-Z]$/.test(key) ? `Key${key}` : undefined,
    ctrlKey: parts.includes("Ctrl") || parts.includes("CtrlOrMeta"),
    metaKey: parts.includes("Meta"),
    altKey: parts.includes("Alt"),
    shiftKey: parts.includes("Shift") || key === "?",
  };
}
