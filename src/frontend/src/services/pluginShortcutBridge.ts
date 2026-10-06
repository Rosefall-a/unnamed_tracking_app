import {
  activeShortcutKeys,
  keyboardShortcuts,
  shortcutForEvent,
} from "../state/shortcuts";
import { NAVIGATION_SHORTCUTS } from "../utils/shortcutDefinitions";
import { shortcutKeyEvent, type ShortcutKeyEvent } from "../utils/shortcutKeys";

/** Read-only bindings let opaque frames forward keys through the normal host guards. */
export function pluginShortcutBindings(path: string) {
  return keyboardShortcuts.value.flatMap((item) =>
    activeShortcutKeys(item.id)
      .filter((key) => {
        const event = shortcutKeyEvent(key);
        return (
          event &&
          shortcutForEvent(event, path)?.id === item.id &&
          (!!item.destination ||
            !!item.pluginId ||
            ["app.search", "app.help"].includes(item.id))
        );
      })
      .map((key) => ({ id: item.id, key })),
  );
}

export function pluginShortcutEvent(
  payload: Record<string, unknown>,
  path: string,
): ShortcutKeyEvent | undefined {
  // Preserve the old bridge only while its original key is still enabled.
  const legacy = NAVIGATION_SHORTCUTS.find((item) => item.key === payload.key);
  const id =
    typeof payload.id === "string"
      ? payload.id
      : legacy
        ? `nav.${legacy.key}`
        : payload.key === "help"
          ? "app.help"
          : payload.key === "search"
            ? "app.search"
            : "";
  const key =
    typeof payload.id === "string" && typeof payload.key === "string"
      ? payload.key
      : legacy
        ? `Alt+${legacy.key.toUpperCase()}`
        : payload.key === "help"
          ? "?"
          : "CtrlOrMeta+K";
  if (
    !pluginShortcutBindings(path).some(
      (item) => item.id === id && item.key === key,
    )
  )
    return;
  return shortcutKeyEvent(key);
}
