import { describe, expect, it } from "vitest";
import { chromeFrom } from "../home/chrome";
import { countdown } from "../home/clock";
import { narrow, sortTitles } from "../home/select";
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
