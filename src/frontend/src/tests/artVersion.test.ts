import { describe, expect, it } from "vitest";
import { bumpArt, withArtVersion } from "../utils/artVersion";

describe("artVersion", () => {
  it("leaves an address alone until the art is replaced", () => {
    expect(withArtVersion("/api/game/g1/assets/key_art", "g1")).toBe(
      "/api/game/g1/assets/key_art",
    );
  });

  it("gives the replaced game's addresses a new version, and no one else's", () => {
    bumpArt("g2");
    expect(withArtVersion("/api/game/g2/assets/banner", "g2")).toMatch(
      /^\/api\/game\/g2\/assets\/banner\?v=\d+$/,
    );
    expect(withArtVersion("/api/game/g3/assets/banner", "g3")).toBe(
      "/api/game/g3/assets/banner",
    );
  });
});

describe("artVersion across a reload", () => {
  it("remembers a replaced game's version in this browser", async () => {
    const { vi } = await import("vitest");
    const store = new Map<string, string>();
    vi.stubGlobal("localStorage", {
      getItem: (k: string) => store.get(k) ?? null,
      setItem: (k: string, v: string) => void store.set(k, v),
    });
    vi.resetModules();
    const first = await import("../utils/artVersion");
    first.bumpArt("g9");
    vi.resetModules();
    const reloaded = await import("../utils/artVersion");
    expect(reloaded.withArtVersion("/api/game/g9/assets/banner", "g9")).toMatch(
      /\?v=\d+$/,
    );
    vi.unstubAllGlobals();
  });
});
