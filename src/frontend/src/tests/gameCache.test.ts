import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchGames, peekAllGames, peekGame } from "../services/games";
import type { BackendGame } from "../services/games";

function raw(id: string, title: string): BackendGame {
  return {
    id,
    title,
    sort_title: title.toLowerCase(),
    source: "Steam",
    platform: "PC",
    status: "BACKLOG",
    playtime_seconds: 0,
    created_at: 0,
    updated_at: 0,
    last_played_at: null,
    stale_since: null,
    completion_date: null,
    purchase_date: null,
    purchase_price: null,
    purchase_price_currency_code: null,
    physical_condition: null,
    rating_overall: null,
    rating_story: null,
    rating_gameplay: null,
    rating_soundtrack: null,
    time_to_beat_hours: null,
    tags: [],
    features: [],
    collections: [],
    links: [],
  } as unknown as BackendGame;
}

function serve(games: BackendGame[]) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({ ok: true, json: async () => games })),
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("the game cache", () => {
  it("has no full list until one has been fetched, then has every game", async () => {
    expect(peekAllGames()).toBeNull();
    serve([raw("a", "Alpha"), raw("b", "Beta")]);
    await fetchGames();
    expect(peekAllGames()?.map((g) => g.title)).toEqual(["Alpha", "Beta"]);
    expect(peekGame("a")?.title).toBe("Alpha");
  });

  it("keeps the completion numbers a library filled in across a refresh", async () => {
    serve([raw("c", "Gamma")]);
    const [first] = await fetchGames();
    // the library fills these in from its achievements summary
    first.achievementTotal = 20;
    first.achievementPercent = 45;

    serve([raw("c", "Gamma")]);
    const [again] = await fetchGames();
    expect(again).not.toBe(first);
    expect(again.achievementTotal).toBe(20);
    expect(again.achievementPercent).toBe(45);
  });
});
