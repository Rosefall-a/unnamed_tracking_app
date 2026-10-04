import { describe, expect, it } from "vitest";
import {
  NAVIGATION_SHORTCUTS,
  SHORTCUT_GROUPS,
  shortcutGroupsForPath,
} from "../utils/shortcuts";

describe("shared shortcut help", () => {
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
          (shortcut) => shortcut.keys === "g then " + item.key,
        ),
      ).toBe(true);
    }
  });
});
