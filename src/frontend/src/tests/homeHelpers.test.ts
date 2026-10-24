import { describe, expect, it } from "vitest";
import { chromeFrom } from "../home/chrome";
import { nearestAnniversary } from "../home/anniversary";
import { countdown } from "../home/clock";
import { inCollection, isUnfinished, narrow, sortTitles } from "../home/select";
import type { HomeTitle } from "../home/data";

function title(over: Partial<HomeTitle>): HomeTitle {
  return {
    key: over.title ?? "t",
    kind: "game",
    id: "1",
    title: "T",
    art: null,
    wide: null,
    subtitle: "",
    progress: null,
    ach: null,
    to: "",
    status: "",
    group: "queue",
    rating: null,
    favorite: false,
    addedAt: 0,
    touchedAt: 0,
    genres: [],
    release: 0,
    platform: "",
    hours: null,
    makers: [],
    collections: [],
    playedHours: null,
    ...over,
  };
}

describe("countdown", () => {
  const now = Date.UTC(2026, 9, 14, 12, 0, 0);
  const at = (seconds: number) => now / 1000 + seconds;

  it("shows the two biggest units", () => {
    expect(countdown(at(2 * 86_400 + 4 * 3600 + 59), now, false)).toBe("2d 4h");
    expect(countdown(at(3 * 3600 + 12 * 60), now, false)).toBe("3h 12m");
  });

  it("counts seconds when asked, and in the last minutes regardless", () => {
    expect(countdown(at(3600 + 5 * 60 + 7), now, true)).toBe("1h 05m 07s");
    expect(countdown(at(3 * 60 + 9), now, false)).toBe("3m 09s");
    expect(countdown(at(12 * 60), now, false)).toBe("12m");
  });

  it("says Now once it has passed", () => {
    expect(countdown(at(-5), now, false)).toBe("Now");
  });
});

describe("chromeFrom", () => {
  it("falls back for anything missing or unknown", () => {
    expect(chromeFrom({})).toEqual({
      heading: "",
      showHeading: true,
      panel: "auto",
      cardSize: "medium",
      cardText: "always",
      cardTag: "auto",
    });
    expect(chromeFrom({ _panel: "weird", _cardSize: 3 }).panel).toBe("auto");
    expect(chromeFrom({ _showHeading: false }).showHeading).toBe(false);
  });
});

describe("sortTitles", () => {
  const list = [
    title({ title: "B", addedAt: 1, touchedAt: 9, rating: 5 }),
    title({ title: "A", addedAt: 3, touchedAt: 1, rating: 9 }),
    title({ title: "C", addedAt: 2, touchedAt: 5, rating: null }),
  ];
  const names = (l: HomeTitle[]) => l.map((t) => t.title).join("");

  it("orders by each choice without changing the list it was given", () => {
    expect(names(sortTitles(list, "added"))).toBe("ACB");
    expect(names(sortTitles(list, "updated"))).toBe("BCA");
    expect(names(sortTitles(list, "title"))).toBe("ABC");
    expect(names(sortTitles(list, "rating"))).toBe("ABC");
    expect(names(list)).toBe("BAC");
  });

  it("uses the shelf's own order for default", () => {
    expect(names(sortTitles(list, "default", "updated"))).toBe("BCA");
  });

  it("keeps every title when shuffling", () => {
    expect(names(sortTitles(list, "random")).split("").sort().join("")).toBe(
      "ABC",
    );
  });
});

describe("narrow", () => {
  const list = [
    title({ title: "A", genres: ["Horror", "Action"], rating: 8 }),
    title({ title: "B", genres: ["Comedy"], rating: 9 }),
    title({ title: "C", genres: ["horror"], rating: null }),
  ];

  it("matches a genre without minding case", () => {
    expect(narrow(list, { genre: "HORROR" }).map((t) => t.title)).toEqual([
      "A",
      "C",
    ]);
  });

  it("drops unrated titles when a lowest rating is set", () => {
    expect(narrow(list, { minRating: 8 }).map((t) => t.title)).toEqual([
      "A",
      "B",
    ]);
  });

  it("does nothing with blank options", () => {
    expect(narrow(list, { genre: "", minRating: 0 })).toHaveLength(3);
  });
});

describe("nearestAnniversary", () => {
  it("finds last year's date across New Year", () => {
    const r = nearestAnniversary(new Date(2024, 11, 30), new Date(2026, 0, 2));
    expect(r).toEqual({ days: -3, years: 1 });
  });
  it("does not call something added three days ago a throwback", () => {
    const r = nearestAnniversary(new Date(2025, 11, 30), new Date(2026, 0, 2));
    expect(r.years).toBe(0);
  });
  it("puts Feb 29 on Feb 28 in a year without one", () => {
    const r = nearestAnniversary(new Date(2024, 1, 29), new Date(2026, 1, 28));
    expect(r).toEqual({ days: 0, years: 2 });
  });
});

describe("isUnfinished", () => {
  const now = Date.UTC(2026, 9, 23);
  const longAgo = now - 60 * 86_400_000;
  const settings = { staleDays: 30, minHours: 3 };

  it("takes a game with real playtime that is not finished and left alone", () => {
    const game = title({
      kind: "game",
      group: "queue",
      playedHours: 12,
      touchedAt: longAgo,
    });
    expect(isUnfinished(game, settings, now)).toBe(true);
  });
  it("leaves out games barely played, finished, or touched recently", () => {
    expect(
      isUnfinished(
        title({ playedHours: 1, touchedAt: longAgo }),
        settings,
        now,
      ),
    ).toBe(false);
    expect(
      isUnfinished(
        title({ playedHours: 12, group: "done", touchedAt: longAgo }),
        settings,
        now,
      ),
    ).toBe(false);
    expect(
      isUnfinished(
        title({ playedHours: 12, touchedAt: now - 86_400_000 }),
        settings,
        now,
      ),
    ).toBe(false);
  });
  it("takes a show partway through, not one not started or finished", () => {
    const show = (progress: number | null) =>
      title({ kind: "tv", progress, touchedAt: longAgo, playedHours: null });
    expect(isUnfinished(show(0.4), settings, now)).toBe(true);
    expect(isUnfinished(show(0), settings, now)).toBe(false);
    expect(isUnfinished(show(1), settings, now)).toBe(false);
    expect(isUnfinished(show(null), settings, now)).toBe(false);
  });
});

describe("inCollection", () => {
  it("matches a game collection by name and a list by its members", () => {
    const g = title({
      key: "game:1",
      kind: "game",
      collections: ["Soulslikes"],
    });
    expect(inCollection(g, "game:Soulslikes", undefined)).toBe(true);
    expect(inCollection(g, "game:Other", undefined)).toBe(false);
    const show = title({ key: "tv:9", kind: "tv" });
    expect(inCollection(show, "list:abc", ["tv:9"])).toBe(true);
    expect(inCollection(show, "list:abc", undefined)).toBe(false);
  });
});
