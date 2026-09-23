import { describe, expect, it } from "vitest";
import { matchesFilters } from "../utils/libraryFilters";
import type { Filterable, LibraryFilters } from "../utils/libraryFilters";

const none: LibraryFilters = {
  search: "",
  genres: [],
  genreMatchAll: false,
  formats: [],
  onlyFavorites: false,
  onlyUnrated: false,
  onlyWithNote: false,
  minScore: null,
  yearFrom: "",
  yearTo: "",
};

function title(over: Partial<Filterable> = {}): Filterable {
  return {
    title: "Attack on Titan",
    altTitles: ["Shingeki no Kyojin", "進撃の巨人"],
    genres: ["Action", "Drama"],
    format: "TV",
    favorite: false,
    score: 9,
    note: null,
    releaseYear: "2013",
    ...over,
  };
}

describe("library filters", () => {
  it("shows everything when nothing is set", () => {
    expect(matchesFilters(title(), none)).toBe(true);
  });

  it("search finds any spelling of the title", () => {
    expect(matchesFilters(title(), { ...none, search: "shingeki" })).toBe(true);
    expect(matchesFilters(title(), { ...none, search: "巨人" })).toBe(true);
    expect(matchesFilters(title(), { ...none, search: "naruto" })).toBe(false);
  });

  it("genres match any by default and every one on request", () => {
    const two = { ...none, genres: ["Action", "Comedy"] };
    expect(matchesFilters(title(), two)).toBe(true);
    expect(matchesFilters(title(), { ...two, genreMatchAll: true })).toBe(
      false,
    );
    expect(
      matchesFilters(title(), {
        ...none,
        genres: ["Action", "Drama"],
        genreMatchAll: true,
      }),
    ).toBe(true);
  });

  it("a minimum score never matches an unscored title", () => {
    expect(matchesFilters(title({ score: 8 }), { ...none, minScore: 8 })).toBe(
      true,
    );
    expect(
      matchesFilters(title({ score: 7.5 }), { ...none, minScore: 8 }),
    ).toBe(false);
    expect(
      matchesFilters(title({ score: null }), { ...none, minScore: 6 }),
    ).toBe(false);
    expect(
      matchesFilters(title({ score: null }), { ...none, onlyUnrated: true }),
    ).toBe(true);
    expect(matchesFilters(title(), { ...none, onlyUnrated: true })).toBe(false);
  });

  it("a year range is inclusive and excludes titles with no known year", () => {
    const range = { ...none, yearFrom: "2010", yearTo: "2013" };
    expect(matchesFilters(title({ releaseYear: "2013" }), range)).toBe(true);
    expect(matchesFilters(title({ releaseYear: "2010" }), range)).toBe(true);
    expect(matchesFilters(title({ releaseYear: "2014" }), range)).toBe(false);
    expect(matchesFilters(title({ releaseYear: null }), range)).toBe(false);
    // only one end given
    expect(
      matchesFilters(title({ releaseYear: "1999" }), {
        ...none,
        yearTo: "2000",
      }),
    ).toBe(true);
    // a half-typed year is ignored rather than hiding everything
    expect(matchesFilters(title(), { ...none, yearFrom: "abc" })).toBe(true);
  });

  it("format, favorites and notes narrow the list", () => {
    expect(matchesFilters(title(), { ...none, formats: ["Movie"] })).toBe(
      false,
    );
    expect(matchesFilters(title(), { ...none, formats: ["TV", "OVA"] })).toBe(
      true,
    );
    expect(matchesFilters(title(), { ...none, onlyFavorites: true })).toBe(
      false,
    );
    expect(
      matchesFilters(title({ favorite: true }), {
        ...none,
        onlyFavorites: true,
      }),
    ).toBe(true);
    expect(
      matchesFilters(title({ note: "   " }), { ...none, onlyWithNote: true }),
    ).toBe(false);
    expect(
      matchesFilters(title({ note: "rewatch soon" }), {
        ...none,
        onlyWithNote: true,
      }),
    ).toBe(true);
  });
});
