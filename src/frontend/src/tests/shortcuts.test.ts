import { afterEach, describe, expect, it } from "vitest";
import {
  NAVIGATION_SHORTCUTS,
  navigationShortcutForPath,
  navigationTooltip,
  shortcutGroupsForPath,
} from "../utils/shortcuts";
import { preferences, resetSharedPreferences } from "../state/preferences";
import {
  keyboardShortcuts,
  registerPluginShortcut,
  retainPluginShortcuts,
  resolveShortcuts,
  matchesShortcut,
  shortcutForEvent,
  runPluginShortcut,
} from "../state/shortcuts";
import { CORE_SHORTCUTS } from "../utils/shortcutDefinitions";
import {
  normalizeShortcutKey,
  matchesShortcutKey,
} from "../utils/shortcutKeys";
afterEach(() => {
  resetSharedPreferences();
  retainPluginShortcuts(new Set());
});

describe("shared shortcut help", () => {
  it("shares Alt navigation hints with route controls", () => {
    expect(navigationShortcutForPath("/movies")).toBe("Alt+M");
    expect(
      navigationShortcutForPath("/plugins/official.collectors-archive/cards"),
    ).toBeUndefined();
    expect(navigationShortcutForPath("/settings?section=appearance")).toBe(
      "Alt+P",
    );
    expect(navigationTooltip("Movies", "/movies")).toBe("Movies · Alt + M");
    expect(navigationTooltip("Notifications", "/notifications")).toBe(
      "Notifications · Alt + O",
    );
  });
  it.each([
    ["/games", "Games library"],
    ["/games/example", "Game page"],
    ["/movies", "Page actions"],
    ["/tv", "Page actions"],
    ["/anime", "Page actions"],
    ["/collections", "Page actions"],
    ["/games/collections", "Page actions"],
    ["/lists", "Page actions"],
    ["/media/collections", "Page actions"],
    ["/calendar", "Calendar"],
  ])("prioritizes %s without dropping other help", (path, expected) => {
    const groups = shortcutGroupsForPath(path);
    expect(groups[0]?.title).toBe(expected);
    expect(groups.find((group) => group.title === "Anywhere")).toBeDefined();
    expect(new Set(groups.map((group) => group.title)).size).toBe(
      new Set(CORE_SHORTCUTS.map((item) => item.group)).size,
    );
  });
  it("offers global navigation on settings and plugin pages", () => {
    expect(shortcutGroupsForPath("/plugins/example/home")[0]?.title).toBe(
      "Anywhere",
    );
    expect(shortcutGroupsForPath("/settings")[0]?.title).toBe("Anywhere");
    expect(new Set(NAVIGATION_SHORTCUTS.map((item) => item.key)).size).toBe(
      NAVIGATION_SHORTCUTS.length,
    );
    const globalHelp = shortcutGroupsForPath("/settings").find(
      (group) => group.title === "Anywhere",
    )!;
    for (const item of NAVIGATION_SHORTCUTS) {
      expect(
        globalHelp.shortcuts.some(
          (shortcut) => shortcut.keys === "Alt + " + item.key.toUpperCase(),
        ),
      ).toBe(true);
    }
  });
  it("has no Archive feature shortcuts until the plugin contributes them", () => {
    expect(
      NAVIGATION_SHORTCUTS.some((item) =>
        ["/cards", "/sets", "/bounties"].includes(item.path),
      ),
    ).toBe(false);
    expect(
      shortcutGroupsForPath("/games").some((group) =>
        ["Cards", "Sets", "Bounties"].includes(group.title),
      ),
    ).toBe(false);
    registerPluginShortcut("official.collectors-archive", {
      id: "cards",
      label: "Open Cards",
      group: "Cards",
      keys: ["Alt+E"],
      destination: "/plugins/official.collectors-archive/cards",
    });
    expect(
      navigationTooltip("Cards", "/plugins/official.collectors-archive/cards"),
    ).toBe("Cards · Alt + E");
    retainPluginShortcuts(new Set());
    expect(
      navigationShortcutForPath("/plugins/official.collectors-archive/cards"),
    ).toBeUndefined();
  });
});

describe("editable bindings and plugin conflicts", () => {
  const event = {
    key: "k",
    code: "KeyK",
    ctrlKey: true,
    metaKey: false,
    altKey: false,
    shiftKey: false,
  };
  it("keeps the existing portable search binding and flags a new plugin on both operating systems", () => {
    registerPluginShortcut("example.keys", {
      id: "conflict",
      label: "Demo conflict",
      keys: ["CtrlOrMeta+K"],
    });
    const demo = keyboardShortcuts.value.find((item) => item.pluginId)!;
    expect(demo.activeKeys).toEqual([]);
    expect(demo.conflicts[0]?.id).toBe("app.search");
    expect(shortcutForEvent(event, "/movies")?.id).toBe("app.search");
    expect(
      shortcutForEvent({ ...event, ctrlKey: false, metaKey: true }, "/games")
        ?.id,
    ).toBe("app.search");
    preferences.value.keyboard_shortcut_overrides = {
      [demo.id]: { keys: ["CtrlOrMeta+J"] },
    };
    expect(shortcutForEvent({ ...event, key: "j" }, "/movies")?.id).toBe(
      demo.id,
    );
    expect(
      keyboardShortcuts.value.find((item) => item.id === demo.id)?.conflicts,
    ).toEqual([]);
  });
  it("reacts to remapped keys, master/per-binding disabling and tooltips", () => {
    preferences.value.keyboard_shortcut_overrides = {
      "nav.m": { keys: ["Alt+Shift+M"] },
      "app.search": { enabled: false },
    };
    expect(
      matchesShortcut("nav.m", {
        ...event,
        key: "m",
        ctrlKey: false,
        altKey: true,
      }),
    ).toBe(false);
    expect(
      matchesShortcut("nav.m", {
        ...event,
        key: "m",
        ctrlKey: false,
        altKey: true,
        shiftKey: true,
      }),
    ).toBe(true);
    expect(navigationTooltip("Movies", "/movies")).toBe(
      "Movies · Alt + Shift + M",
    );
    expect(matchesShortcut("app.search", event)).toBe(false);
    preferences.value.keyboard_shortcuts_enabled = false;
    expect(
      shortcutForEvent(
        { ...event, key: "m", ctrlKey: false, altKey: true, shiftKey: true },
        "/games",
      ),
    ).toBeUndefined();
    expect(navigationTooltip("Movies", "/movies")).toBe("Movies");
  });
  it("only reports collisions in overlapping routes and view contexts", () => {
    const entries = resolveShortcuts(CORE_SHORTCUTS, {});
    expect(entries.flatMap((item) => item.conflicts)).toEqual([]);
    const plugin = {
      id: "plugin:demo:local",
      pluginId: "demo",
      group: "Demo",
      label: "Local next",
      keys: ["J"],
      paths: ["/plugins/demo/page"],
    };
    expect(
      resolveShortcuts([...CORE_SHORTCUTS, plugin], {}).at(-1)?.conflicts,
    ).toEqual([]);
    expect(
      resolveShortcuts(
        [...CORE_SHORTCUTS, { ...plugin, paths: ["/games/*"] }],
        {},
      ).at(-1)?.conflicts[0]?.id,
    ).toBe("games.next");
  });
  it("retains the first plugin registration, supports removing random keys and prevents stale cleanup removing a replacement", async () => {
    let count = 0;
    const key = { id: "random", label: "Random action", keys: ["Alt+Shift+Q"] };
    const oldStop = registerPluginShortcut("example.keys", key, () => {
      count++;
    });
    registerPluginShortcut("example.other", { ...key, label: "Later action" });
    const stop = registerPluginShortcut("example.keys", key, () => {
      count += 2;
    });
    oldStop();
    expect(
      keyboardShortcuts.value.find((item) => item.pluginId === "example.other")
        ?.conflicts,
    ).toHaveLength(1);
    await runPluginShortcut("plugin:example.keys:random");
    expect(count).toBe(2);
    stop();
    expect(
      keyboardShortcuts.value.find((item) => item.pluginId === "example.other")
        ?.activeKeys,
    ).toEqual(["Alt+Shift+Q"]);
    retainPluginShortcuts(new Set());
    await runPluginShortcut("plugin:example.keys:random");
    expect(count).toBe(2);
  });
  it("rejects invalid dynamic metadata and never reaches outside a plugin route scope", () => {
    for (const destination of [
      "/games",
      "/plugins/example.keys/../../games",
      "/plugins/example.keys/%2e%2e/games",
    ])
      expect(() =>
        registerPluginShortcut("example.keys", {
          id: "escape",
          label: "Escape",
          keys: ["Alt+X"],
          destination,
        }),
      ).toThrow();
    expect(() =>
      registerPluginShortcut("example.keys", {
        id: "bad",
        label: "Bad",
        keys: ["Ctrl+javascript:evil"],
      }),
    ).toThrow();
    expect(() =>
      registerPluginShortcut("example.keys", {
        id: "bad",
        label: "Bad",
        keys: ["N"],
        paths: ["/settings"],
      }),
    ).toThrow();
  });
});

describe("portable key grammar", () => {
  it("matches Option physical letters and requires exact modifiers", () => {
    const option = {
      key: "©",
      code: "KeyG",
      altKey: true,
      ctrlKey: false,
      metaKey: false,
      shiftKey: false,
    };
    expect(matchesShortcutKey("Alt+G", option)).toBe(true);
    expect(matchesShortcutKey("Alt+G", { ...option, ctrlKey: true })).toBe(
      false,
    );
    expect(
      matchesShortcutKey("?", {
        ...option,
        key: "?",
        altKey: false,
        shiftKey: true,
      }),
    ).toBe(true);
  });
  it("canonicalizes combinations and rejects unsupported sequences and duplicate modifiers", () => {
    expect(normalizeShortcutKey("shift + alt + g")).toBe("Alt+Shift+G");
    for (const value of [
      "g g",
      "Ctrl+Ctrl+K",
      "CtrlOrMeta+Meta+K",
      "Ctrl+",
      "<script>",
    ])
      expect(normalizeShortcutKey(value)).toBeUndefined();
  });
});

it("resolves only mapped single-letter navigation, including Upload and Notifications", async () => {
  const { navigationShortcutForKey } = await import("../utils/shortcuts");
  expect(navigationShortcutForKey("U")?.path).toBe("/upload");
  expect(navigationShortcutForKey("o")?.path).toBe("/notifications");
  for (const key of [null, undefined, 12, "", "../../admin", "x"])
    expect(navigationShortcutForKey(key)).toBeUndefined();
});
