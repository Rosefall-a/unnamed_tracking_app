import { describe, expect, it } from "vitest";

import { gameGenres, genreOptionsFor, hasGenre } from "../utils/genres";

describe("gameGenres", () => {
  it("keeps the provider's genre and adds the shared ones it stands for", () => {
    expect(gameGenres(["Hack and slash/Beat 'em up", "Adventure"])).toEqual([
      "Hack and slash/Beat 'em up",
      "Action",
      "Adventure",
    ]);
    expect(gameGenres(["Role-playing (RPG)"])).toEqual([
      "Role-playing (RPG)",
      "RPG",
    ]);
  });

  it("spells shared genres one way and drops duplicates", () => {
    expect(gameGenres(["action", "Action", " ACTION "])).toEqual(["Action"]);
  });

  it("leaves genres it doesn't know as they are", () => {
    expect(gameGenres(["Indie", "Nintendo 64"])).toEqual([
      "Indie",
      "Nintendo 64",
    ]);
  });
});

describe("hasGenre", () => {
  it("matches across providers and letter case", () => {
    expect(hasGenre(["Shooter"], "Action")).toBe(true);
    expect(hasGenre(["Platform"], "platformer")).toBe(true);
    expect(hasGenre(["Puzzle"], "Action")).toBe(false);
    expect(hasGenre([], "Action")).toBe(false);
  });
});

describe("genreOptionsFor", () => {
  it("offers each genre once, shared spelling first", () => {
    const options = genreOptionsFor([["action", "Indie"], ["Indie"]]);
    expect(options.filter((o) => o.toLowerCase() === "action")).toEqual([
      "Action",
    ]);
    expect(options.filter((o) => o === "Indie")).toHaveLength(1);
    expect(options).toContain("RPG");
  });
});
