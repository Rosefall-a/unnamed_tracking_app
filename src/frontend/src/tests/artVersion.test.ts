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
