import { describe, expect, it } from "vitest";
import { autoCollectionNames } from "../utils/autoCollections";
import type { Game } from "../types/game";

function game(over: Partial<Game>): Game {
  return {
    id: "1",
    title: "T",
    series: null,
    source: null,
    collections: [],
    ...over,
  } as Game;
}

describe("autoCollectionNames", () => {
  it("finds collections made from a series or a source", () => {
    const games = [
      game({
        id: "1",
        series: "Dark Souls",
        source: "Steam",
        collections: ["Dark Souls", "Steam"],
      }),
      game({
        id: "2",
        series: "Dark Souls",
        source: "Steam",
        collections: ["Dark Souls", "Steam", "Replays"],
      }),
    ];
    expect([...autoCollectionNames(games)].sort()).toEqual([
      "Dark Souls",
      "Steam",
    ]);
  });

  it("does not treat your own collection as automatic", () => {
    const games = [
      game({ id: "1", series: "Zelda", collections: ["Zelda", "Cozy"] }),
      game({ id: "2", series: null, collections: ["Cozy"] }),
    ];
    expect([...autoCollectionNames(games)]).toEqual(["Zelda"]);
  });

  it("is not fooled by a collection you made with a series name for other games", () => {
    const games = [
      game({ id: "1", series: "Halo", collections: ["Halo"] }),
      game({ id: "2", series: "Other", collections: ["Halo"] }),
    ];
    expect(autoCollectionNames(games).size).toBe(0);
  });

  it("ignores case", () => {
    const games = [game({ series: "halo", collections: ["Halo"] })];
    expect(autoCollectionNames(games).has("Halo")).toBe(true);
  });
});
