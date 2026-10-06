import { describe, expect, it } from "vitest";
import { ORANGE_PALETTE } from "../services/uiPalette";
import { readPaletteFile, writePaletteFile } from "../services/paletteFiles";

describe("portable palette files", () => {
  it("round trips both modes without account data", () => {
    const file = writePaletteFile(ORANGE_PALETTE);
    expect(readPaletteFile(file)).toEqual(ORANGE_PALETTE);
    expect(Object.keys(JSON.parse(file))).toEqual([
      "format",
      "version",
      "colors",
    ]);
  });
  it("accepts every valid hex color even with low contrast", () => {
    const colors = structuredClone(ORANGE_PALETTE);
    for (const mode of ["light", "dark"] as const)
      for (const role of Object.keys(
        colors[mode],
      ) as (keyof typeof colors.light)[])
        colors[mode][role] = "#FFFFFF";
    const imported = readPaletteFile(writePaletteFile(colors));
    expect(imported.light.text).toBe("#ffffff");
    expect(imported.dark.background).toBe("#ffffff");
  });
  it.each([
    "{}",
    "broken",
    JSON.stringify({
      format: "uta-color-palette",
      version: 2,
      colors: ORANGE_PALETTE,
    }),
    " ".repeat(8193),
  ])("rejects malformed, unsupported or oversized files", (file) => {
    expect(() => readPaletteFile(file)).toThrow();
  });
  it("rejects missing colors and stylesheet values while ignoring unrelated file metadata", () => {
    const data = JSON.parse(writePaletteFile(ORANGE_PALETTE));
    data.account_id = "do-not-import";
    expect(readPaletteFile(JSON.stringify(data))).toEqual(ORANGE_PALETTE);
    delete data.colors.light.accent;
    expect(() => readPaletteFile(JSON.stringify(data))).toThrow();
    data.colors.light.accent = "url(https://example.invalid)";
    expect(() => readPaletteFile(JSON.stringify(data))).toThrow();
  });
});
