import { describe, expect, it } from "vitest";
import { mockGames } from "../data/mockGames";
import type { Game } from "../types/game";
import { matchesCustomTab } from "../state/gameTabs";
import { rowsToConditions } from "../utils/smartRuleFields";
import {
  describeCondition,
  renameCollectionInRules,
} from "../state/smartCollections";

const game = (over: Partial<Game>): Game => ({ ...mockGames[0], ...over });

describe("tabs you make", () => {
  it("holds the games you put in it, by collection name", () => {
    const tab = {
      id: "t1",
      name: "Online",
      rules: [{ field: "collection" as const, value: "online" }],
      match: "all" as const,
      hideElsewhere: true,
    };
    expect(matchesCustomTab(game({ collections: ["Online"] }), tab)).toBe(true);
    expect(matchesCustomTab(game({ collections: ["Cozy"] }), tab)).toBe(false);
  });

  it("can match on rules, every one or any one", () => {
    const rules = [
      { field: "status" as const, value: "backlog" },
      { field: "tag" as const, value: "Multiplayer" },
    ];
    const both = game({ status: "backlog", tags: ["Multiplayer"] });
    const one = game({ status: "backlog", tags: [] });
    const all = {
      id: "a",
      name: "A",
      rules,
      match: "all" as const,
      hideElsewhere: false,
    };
    expect(matchesCustomTab(both, all)).toBe(true);
    expect(matchesCustomTab(one, all)).toBe(false);
    expect(matchesCustomTab(one, { ...all, match: "any" })).toBe(true);
  });

  it("says what is missing before a rule tab is saved", () => {
    expect(rowsToConditions([{ field: "tag", value: "" }])).toBe(
      'Fill in "Tag is".',
    );
    expect(rowsToConditions([])).toBe("Add at least one rule.");
    expect(rowsToConditions([{ field: "priority", value: 9 }])).toContain(
      "from 1 to 5",
    );
  });
});

describe("rules that leave games out", () => {
  const tab = {
    id: "lo",
    name: "Owned",
    rules: [{ field: "status" as const, value: "wishlist,dropped", not: true }],
    match: "all" as const,
    hideElsewhere: false,
  };

  it("keeps every game except the statuses it names", () => {
    expect(matchesCustomTab(game({ status: "backlog" }), tab)).toBe(true);
    expect(matchesCustomTab(game({ status: "beaten" }), tab)).toBe(true);
    expect(matchesCustomTab(game({ status: "wishlist" }), tab)).toBe(false);
    expect(matchesCustomTab(game({ status: "dropped" }), tab)).toBe(false);
  });

  it("matches any of several statuses when included", () => {
    const either = { ...tab, rules: [{ ...tab.rules[0], not: false }] };
    expect(matchesCustomTab(game({ status: "dropped" }), either)).toBe(true);
    expect(matchesCustomTab(game({ status: "playing" }), either)).toBe(false);
  });

  it("works with other rules, like a tag and no wishlist", () => {
    const rpgs = {
      ...tab,
      rules: [
        { field: "tag" as const, value: "RPG" },
        { field: "status" as const, value: "wishlist", not: true },
      ],
    };
    expect(
      matchesCustomTab(game({ status: "backlog", tags: ["RPG"] }), rpgs),
    ).toBe(true);
    expect(
      matchesCustomTab(game({ status: "wishlist", tags: ["RPG"] }), rpgs),
    ).toBe(false);
  });

  it("keeps the leave-out choice when saved, and reads plainly", () => {
    const found = rowsToConditions([
      { field: "status", value: "wishlist,dropped", not: true },
    ]);
    expect(found).toEqual([
      { field: "status", value: "wishlist,dropped", not: true },
    ]);
    expect(describeCondition(tab.rules[0])).toBe(
      "Leaving out: Status is wishlist or dropped",
    );
  });
});

describe("statuses a tab shows", () => {
  const base = {
    id: "s1",
    name: "Active",
    rules: [],
    match: "all" as const,
    hideElsewhere: false,
  };

  it("shows only the statuses turned on", () => {
    const tab = {
      ...base,
      statuses: ["playing" as const, "mastered" as const],
    };
    expect(matchesCustomTab(game({ status: "playing" }), tab)).toBe(true);
    expect(matchesCustomTab(game({ status: "mastered" }), tab)).toBe(true);
    expect(matchesCustomTab(game({ status: "backlog" }), tab)).toBe(false);
    expect(matchesCustomTab(game({ status: "wishlist" }), tab)).toBe(false);
  });

  it("shows every status when none are picked out", () => {
    expect(matchesCustomTab(game({ status: "wishlist" }), base)).toBe(true);
  });

  it("checks statuses on top of the other rules", () => {
    const tab = {
      ...base,
      statuses: ["backlog" as const],
      rules: [{ field: "tag" as const, value: "RPG" }],
      match: "any" as const,
    };
    expect(
      matchesCustomTab(game({ status: "backlog", tags: ["RPG"] }), tab),
    ).toBe(true);
    expect(
      matchesCustomTab(game({ status: "beaten", tags: ["RPG"] }), tab),
    ).toBe(false);
  });
});

describe("renaming a collection", () => {
  it("moves rules that named it to the new name", () => {
    const rules = renameCollectionInRules(
      [
        { field: "collection", value: "online games" },
        { field: "collection", value: "Keep", not: true },
        { field: "tag", value: "Online Games" },
      ],
      "Online Games",
      "Live service",
    );
    expect(rules).toEqual([
      { field: "collection", value: "Live service" },
      { field: "collection", value: "Keep", not: true },
      { field: "tag", value: "Online Games" },
    ]);
  });
});
