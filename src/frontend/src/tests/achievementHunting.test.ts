import { describe, expect, it } from "vitest";

import { mockGames } from "../data/mockGames";
import { applyAchievementSummary } from "../services/games";
import {
  matchesCondition,
  matchesSmartCollection,
} from "../state/smartCollections";
import type {
  SmartCollection,
  SmartCondition,
} from "../state/smartCollections";
import type { Game } from "../types/game";

function game(total: number, unlocked: number): Game {
  const g: Game = { ...mockGames[0], id: crypto.randomUUID() };
  applyAchievementSummary([g], { [g.id]: { total, unlocked } });
  return g;
}

const almost: SmartCollection = {
  id: "x",
  name: "Almost there",
  field: "achievement_percent",
  value: "80",
};

describe("achievement counts", () => {
  it("only shows 100% when every achievement is unlocked", () => {
    expect(game(200, 199).achievementPercent).toBe(99);
    expect(game(200, 200).achievementPercent).toBe(100);
    expect(game(0, 0).achievementPercent).toBe(0);
    expect(game(3, 1).achievementUnlocked).toBe(1);
  });

  it("an almost there rule takes games at the share or above, not finished ones", () => {
    expect(matchesSmartCollection(game(10, 8), almost)).toBe(true);
    expect(matchesSmartCollection(game(10, 7), almost)).toBe(false);
    expect(matchesSmartCollection(game(10, 10), almost)).toBe(false);
    expect(matchesSmartCollection(game(0, 0), almost)).toBe(false);
  });
});

describe("smart collection rules", () => {
  const DAY = 86_400_000;
  const now = Date.now();

  function make(patch: Partial<Game>): Game {
    return { ...mockGames[0], id: crypto.randomUUID(), ...patch };
  }

  it("can need every rule or any one of them", () => {
    const backlogRpg = make({ status: "backlog", tags: ["RPG"] });
    const backlogOther = make({ status: "backlog", tags: ["Racing"] });
    const rules = [
      { field: "status" as const, value: "backlog" },
      { field: "tag" as const, value: "rpg" },
    ];
    const all: SmartCollection = {
      id: "a",
      name: "a",
      ...rules[0],
      rules,
      match: "all",
    };
    expect(matchesSmartCollection(backlogRpg, all)).toBe(true);
    expect(matchesSmartCollection(backlogOther, all)).toBe(false);
    expect(matchesSmartCollection(backlogOther, { ...all, match: "any" })).toBe(
      true,
    );
  });

  it("reads dates, activity, platform, series and priority", () => {
    const g = make({
      completionDate: "2026-03-01",
      releaseDate: "2012-05-01",
      dateAdded: new Date(now - 3 * DAY).toISOString(),
      lastPlayedAt: new Date(now - 200 * DAY).toISOString(),
      platforms: [],
      platform: "PC",
      series: "Dark Souls",
      priority: "2",
    });
    const is = (field: SmartCondition["field"], value: string) =>
      matchesCondition(g, { field, value }, now);
    expect(is("finished_year", "2026")).toBe(true);
    expect(is("finished_year", "2025")).toBe(false);
    expect(is("released_from", "2010")).toBe(true);
    expect(is("released_to", "2011")).toBe(false);
    expect(is("added_within_days", "7")).toBe(true);
    expect(is("played_within_days", "30")).toBe(false);
    expect(is("not_played_days", "180")).toBe(true);
    expect(is("platform", "pc")).toBe(true);
    expect(is("series", "dark souls")).toBe(true);
    expect(is("priority", "3")).toBe(true);
    expect(is("priority", "1")).toBe(false);
  });

  it("an old one-rule collection still reads the same", () => {
    const old: SmartCollection = {
      id: "o",
      name: "o",
      field: "favorite",
      value: "",
    };
    expect(matchesSmartCollection(make({ favorite: true }), old)).toBe(true);
    expect(matchesSmartCollection(make({ favorite: false }), old)).toBe(false);
  });
});
