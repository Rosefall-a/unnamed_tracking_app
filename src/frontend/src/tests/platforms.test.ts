import { describe, expect, it } from "vitest";

import {
  normalizePlatformFamily,
  PLATFORM_OPTIONS,
  RETRO_PLATFORM_OPTIONS,
} from "../utils/platforms";

describe("normalizePlatformFamily", () => {
  it("normalizes common platform aliases case-insensitively", () => {
    expect(normalizePlatformFamily(" PS5 ")).toBe("PlayStation");
    expect(normalizePlatformFamily("Xbox One")).toBe("Xbox");
    expect(normalizePlatformFamily("nintendo switch")).toBe("Nintendo");
    expect(normalizePlatformFamily("Steam")).toBe("PC");
  });

  it("preserves unknown platforms while trimming whitespace", () => {
    expect(normalizePlatformFamily("  WonderConsole  ")).toBe("WonderConsole");
  });
});

describe("platform option lists", () => {
  it("contains the four normalized platform families", () => {
    expect(PLATFORM_OPTIONS).toEqual(["PC", "PlayStation", "Xbox", "Nintendo"]);
    expect(new Set(PLATFORM_OPTIONS).size).toBe(PLATFORM_OPTIONS.length);
  });

  it("keeps retro platforms separate from the default filter", () => {
    expect(RETRO_PLATFORM_OPTIONS).toContain("Arcade");
    expect(RETRO_PLATFORM_OPTIONS).toContain("Sega Dreamcast");
    expect(RETRO_PLATFORM_OPTIONS).not.toEqual(
      expect.arrayContaining(PLATFORM_OPTIONS),
    );
  });
});
