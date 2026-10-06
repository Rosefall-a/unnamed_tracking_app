import { describe, expect, it } from "vitest";

import type { Game, GameStatus } from "../types/game";
import {
  DEFAULT_PICKER_FILTERS,
  matchesPickerFilters,
  parseMaxHours,
  pickRandomGame,
  pickWeight,
} from "../utils/randomPicker";
import type { PickerFilters } from "../utils/randomPicker";

function game(
  id: string,
  overrides: Partial<Game> & { status?: GameStatus } = {},
): Game {
  return {
    id,
    title: id,
    status: "backlog",
    tags: [],
    timeToBeatHours: null,
    priority: null,
    platforms: [
      {
        platform: "Steam",
        playtimeMinutes: 0,
        completionPercent: null,
        lastPlayedAt: null,
      },
    ],
    ...overrides,
  } as Game;
}

const filters = (overrides: Partial<PickerFilters> = {}): PickerFilters => ({
  ...DEFAULT_PICKER_FILTERS,
  statuses: [...DEFAULT_PICKER_FILTERS.statuses],
  ...overrides,
});

describe("matchesPickerFilters", () => {
  it("leaves finished games out when no status is chosen", () => {
    const f = filters({ statuses: [] });
    expect(matchesPickerFilters(game("a", { status: "wishlist" }), f)).toBe(
      true,
    );
    expect(matchesPickerFilters(game("b", { status: "beaten" }), f)).toBe(
      false,
    );
  });

  it("filters by platform family, genre, length and priority (#33)", () => {
    const switchRpg = game("switch-rpg", {
      tags: ["RPG"],
      timeToBeatHours: 40,
      priority: "2",
      platforms: [
        {
          platform: "Nintendo Switch",
          playtimeMinutes: 0,
          completionPercent: null,
          lastPlayedAt: null,
        },
      ],
    });
    expect(
      matchesPickerFilters(switchRpg, filters({ platform: "Nintendo" })),
    ).toBe(true);
    expect(matchesPickerFilters(switchRpg, filters({ platform: "PC" }))).toBe(
      false,
    );
    expect(matchesPickerFilters(switchRpg, filters({ genre: "RPG" }))).toBe(
      true,
    );
    expect(matchesPickerFilters(switchRpg, filters({ maxHours: 20 }))).toBe(
      false,
    );
    expect(matchesPickerFilters(switchRpg, filters({ maxPriority: 1 }))).toBe(
      false,
    );
    expect(matchesPickerFilters(switchRpg, filters({ maxPriority: 2 }))).toBe(
      true,
    );
  });

  it("finds a genre whichever provider named it", () => {
    // IGDB has no "Action" genre; Devil May Cry arrives as hack and slash
    const igdb = game("igdb", { tags: ["Hack and slash/Beat 'em up"] });
    const steam = game("steam", { tags: ["action"] });
    const rpg = game("rpg", { tags: ["Role-playing (RPG)"] });
    expect(matchesPickerFilters(igdb, filters({ genre: "Action" }))).toBe(true);
    expect(matchesPickerFilters(steam, filters({ genre: "Action" }))).toBe(
      true,
    );
    expect(matchesPickerFilters(rpg, filters({ genre: "RPG" }))).toBe(true);
    expect(matchesPickerFilters(rpg, filters({ genre: "Action" }))).toBe(false);
  });

  it("lets games with unknown length through a length limit only if asked", () => {
    const unknown = game("unknown");
    expect(matchesPickerFilters(unknown, filters({ maxHours: 10 }))).toBe(true);
    expect(
      matchesPickerFilters(
        unknown,
        filters({ maxHours: 10, includeUnknownLength: false }),
      ),
    ).toBe(false);
  });
});

describe("pickRandomGame", () => {
  it("returns null when nothing matches", () => {
    expect(
      pickRandomGame([game("done", { status: "mastered" })], filters()),
    ).toBeNull();
  });

  it("weights by priority: 1 is five times as likely as none", () => {
    const top = game("top", { priority: "1" });
    const none = game("none");
    expect(pickWeight(top, true)).toBe(5);
    expect(pickWeight(none, true)).toBe(1);
    expect(pickWeight(top, false)).toBe(1);
    // total weight 6: rolls below 5/6 land on `top`
    expect(pickRandomGame([top, none], filters(), () => 0.8)?.id).toBe("top");
    expect(pickRandomGame([top, none], filters(), () => 0.9)?.id).toBe("none");
  });

  it("doesn't pick the same game again when there's another choice", () => {
    const games = [game("a"), game("b")];
    for (let i = 0; i < 10; i++) {
      expect(pickRandomGame(games, filters(), Math.random, "a")?.id).toBe("b");
    }
    expect(pickRandomGame([game("a")], filters(), Math.random, "a")?.id).toBe(
      "a",
    );
  });
});

describe("parseMaxHours", () => {
  it("reads the number Vue hands over from the number input", () => {
    // v-model on type="number" casts the field's text to a number
    expect(parseMaxHours(10)).toBe(10);
    expect(parseMaxHours(2.5)).toBe(2.5);
  });

  it("still reads text, and treats empty or non-positive as no limit", () => {
    expect(parseMaxHours("12")).toBe(12);
    expect(parseMaxHours("")).toBeNull();
    expect(parseMaxHours("   ")).toBeNull();
    expect(parseMaxHours(0)).toBeNull();
    expect(parseMaxHours(-3)).toBeNull();
    expect(parseMaxHours(Number.NaN)).toBeNull();
  });
});
