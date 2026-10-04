import { describe, expect, it } from "vitest";
import {
  NAVIGATION_SHORTCUTS,
  navigationShortcutForPath,
  navigationTooltip,
  SHORTCUT_GROUPS,
  shortcutGroupsForPath,
} from "../utils/shortcuts";

describe("shared shortcut help", () => {
  it("shares Alt navigation hints with route controls", () => {
    expect(navigationShortcutForPath("/movies")).toBe("Alt+M");
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
    ["/movies", "Media libraries"],
    ["/tv", "Media libraries"],
    ["/anime", "Media libraries"],
    ["/collections", "Collections & lists"],
    ["/lists", "Collections & lists"],
    ["/cards", "Cards"],
    ["/sets", "Sets"],
    ["/bounties", "Bounties"],
    ["/calendar", "Calendar"],
  ])("prioritizes %s without dropping other help", (path, expected) => {
    const groups = shortcutGroupsForPath(path);
    expect(groups[0]?.title).toBe(expected);
    expect(groups[1]?.title).toBe("Anywhere");
    expect(new Set(groups.map((group) => group.title)).size).toBe(
      SHORTCUT_GROUPS.length,
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
    const globalHelp = SHORTCUT_GROUPS.find(
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
});

it("resolves only mapped single-letter navigation, including Upload and Notifications", async () => {
  const { navigationShortcutForKey } = await import("../utils/shortcuts");
  expect(navigationShortcutForKey("U")?.path).toBe("/upload");
  expect(navigationShortcutForKey("o")?.path).toBe("/notifications");
  for (const key of [null, undefined, 12, "", "../../admin", "x"])
    expect(navigationShortcutForKey(key)).toBeUndefined();
});
