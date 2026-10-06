import { describe, expect, it } from "vitest";
import { matchesTourShortcut, quickTourSteps } from "../utils/quickTour";

const key = {
  key: "g",
  code: "KeyG",
  altKey: true,
  ctrlKey: false,
  metaKey: false,
  shiftKey: false,
};
describe("guided tour practice", () => {
  it("uses configured keys and gives disabled bindings a clickable practice path", () => {
    const steps = quickTourSteps(false, {
      search: "Ctrl/Cmd + J",
      games: "Alt + Shift + G",
      media: undefined,
      settings: "Alt + P",
      help: undefined,
    });
    expect(steps.find((step) => step.id === "games")?.description).toContain(
      "Alt + Shift + G",
    );
    expect(steps.find((step) => step.id === "search")?.description).toContain(
      "Ctrl/Cmd + J",
    );
    expect(steps.find((step) => step.id === "media")?.requirement).toBe(
      "navigate",
    );
    expect(steps.find((step) => step.id === "help")?.requirement).toBe(
      "open-close",
    );
  });
  it("requires the documented shortcut and ignores conflicting modifiers", () => {
    expect(matchesTourShortcut("games", key)).toBe(true);
    expect(matchesTourShortcut("games", { ...key, altKey: false })).toBe(false);
    expect(matchesTourShortcut("games", { ...key, ctrlKey: true })).toBe(false);
    expect(matchesTourShortcut("games", { ...key, shiftKey: true })).toBe(
      false,
    );
    expect(matchesTourShortcut("media", key)).toBe(false);
    expect(matchesTourShortcut("games", { ...key, key: "©" })).toBe(true);
  });
  it("supports search and help on both desktop modifier conventions", () => {
    expect(
      matchesTourShortcut("search", {
        ...key,
        key: "k",
        altKey: false,
        ctrlKey: true,
      }),
    ).toBe(true);
    expect(
      matchesTourShortcut("search", {
        ...key,
        key: "k",
        altKey: false,
        metaKey: true,
      }),
    ).toBe(true);
    expect(
      matchesTourShortcut("search", { ...key, key: "k", altKey: false }),
    ).toBe(false);
    expect(
      matchesTourShortcut("help", {
        ...key,
        key: "?",
        altKey: false,
        shiftKey: true,
      }),
    ).toBe(true);
  });
  it("lets touch users complete the same real-dialog tour without a keyboard", () => {
    const desktop = quickTourSteps(false);
    const mobile = quickTourSteps(true);
    expect(mobile.map((step) => step.id)).toEqual(
      desktop.map((step) => step.id),
    );
    expect(
      desktop.filter((step) => step.requirement === "shortcut").length,
    ).toBeGreaterThan(2);
    expect(mobile.some((step) => step.requirement === "shortcut")).toBe(false);
    for (const step of desktop.filter(
      (step) => step.requirement === "shortcut",
    ))
      expect(Boolean(step.destination || step.openedTarget)).toBe(true);
  });
});
