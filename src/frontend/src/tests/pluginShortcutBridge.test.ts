import { afterEach, expect, it } from "vitest";
import {
  pluginShortcutBindings,
  pluginShortcutEvent,
} from "../services/pluginShortcutBridge";
import { preferences, resetSharedPreferences } from "../state/preferences";
import {
  registerPluginShortcut,
  retainPluginShortcuts,
} from "../state/shortcuts";

afterEach(() => {
  resetSharedPreferences();
  retainPluginShortcuts(new Set());
});

it("forwards active remapped keys and retires default iframe bindings", () => {
  preferences.value.keyboard_shortcut_overrides = {
    "nav.g": { keys: ["Alt+Shift+G"] },
    "app.search": { enabled: false },
  };
  expect(pluginShortcutBindings("/plugins/example.test/home")).toContainEqual({
    id: "nav.g",
    key: "Alt+Shift+G",
  });
  expect(pluginShortcutEvent({ key: "g" }, "/")).toBeUndefined();
  expect(pluginShortcutEvent({ key: "search" }, "/")).toBeUndefined();
  expect(
    pluginShortcutEvent({ id: "nav.g", key: "Alt+Shift+G" }, "/"),
  ).toMatchObject({ key: "G", altKey: true, shiftKey: true });
  expect(
    pluginShortcutEvent({ id: "nav.g", key: "Alt+M" }, "/"),
  ).toBeUndefined();
  preferences.value.keyboard_shortcuts_enabled = false;
  expect(pluginShortcutBindings("/")).toEqual([]);
  expect(pluginShortcutEvent({ key: "help" }, "/")).toBeUndefined();
});

it("does not advertise conflicting keys or plugin keys scoped to another page", () => {
  registerPluginShortcut("example.test", {
    id: "conflict",
    label: "Conflict",
    keys: ["CtrlOrMeta+K"],
  });
  registerPluginShortcut("example.test", {
    id: "scoped",
    label: "Scoped",
    keys: ["Alt+Shift+W"],
    paths: ["/plugins/example.test/work"],
  });
  expect(pluginShortcutBindings("/plugins/example.test/work")).toContainEqual({
    id: "plugin:example.test:scoped",
    key: "Alt+Shift+W",
  });
  expect(
    pluginShortcutEvent(
      { id: "plugin:example.test:scoped", key: "Alt+Shift+W" },
      "/movies",
    ),
  ).toBeUndefined();
  expect(
    pluginShortcutEvent(
      { id: "plugin:example.test:conflict", key: "CtrlOrMeta+K" },
      "/",
    ),
  ).toBeUndefined();
});
