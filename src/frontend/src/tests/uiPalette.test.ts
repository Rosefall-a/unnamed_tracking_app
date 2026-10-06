import { describe, expect, it } from "vitest";
import {
  ORANGE_PALETTE,
  applyPalette,
  contrastRatio,
  paletteContrastIssues,
  paletteTokens,
} from "../services/uiPalette";

describe("personal palette contrast and withdrawal", () => {
  it("keeps preset text and accent controls readable in both modes", () => {
    for (const id of ["orange", "green"] as const)
      for (const mode of ["light", "dark"] as const) {
        const tokens = paletteTokens(id, mode);
        expect(
          contrastRatio(tokens["--ui-text"]!, tokens["--ui-bg"]!),
        ).toBeGreaterThanOrEqual(4.5);
        expect(
          contrastRatio(tokens["--ui-accent"]!, tokens["--ui-on-accent"]!),
        ).toBeGreaterThanOrEqual(4.5);
      }
  });
  it("identifies unreadable custom roles across every background before applying", () => {
    const colors = {
      ...ORANGE_PALETTE.light,
      text: "#ffffff",
      muted: "#ffffff",
    };
    expect(paletteContrastIssues(colors)).toContain(
      "Main text on Page background",
    );
    expect(paletteContrastIssues(colors)).toContain(
      "Secondary text on Cards & menus",
    );
    expect(paletteContrastIssues(ORANGE_PALETTE.light)).toEqual([]);
    expect(paletteContrastIssues(ORANGE_PALETTE.dark)).toEqual([]);
  });
  it("withdraws all owned colors when returning to the default without removing other styles", () => {
    const properties = new Map([
      ["--ui-edge-left", "32px"],
      ["--plugin-custom", "value"],
    ]);
    const root = {
      dataset: {},
      style: {
        removeProperty: (key: string) => properties.delete(key),
        setProperty: (key: string, value: string) => properties.set(key, value),
      },
    } as unknown as HTMLElement;
    applyPalette(root, "green", "dark", {});
    expect(properties.get("--ui-bg")).toBe("#141c18");
    applyPalette(root, "green", "dark", {}, true);
    expect(properties.get("--ui-dim")).toBe(properties.get("--ui-text"));
    expect(properties.get("--ui-border")).toBe(
      properties.get("--ui-border-strong"),
    );
    applyPalette(root, "orange", "light", {});
    expect(properties.has("--ui-bg")).toBe(false);
    expect(properties.get("--ui-edge-left")).toBe("32px");
    expect(properties.get("--plugin-custom")).toBe("value");
  });
});
