import { describe, expect, it } from "vitest";
import { isFullyWatched } from "../utils/completion";

const season = (watched: number, count: number | null, ticked = 0) => ({
  episodeCount: count,
  episodesWatched: watched,
  episodes: Array.from({ length: count ?? 0 }, (_, i) => ({ watched: i < ticked })),
});
const show = (seasons: ReturnType<typeof season>[], extra = {}) => ({
  id: "s1",
  status: "in progress",
  seasons,
  ...extra,
});

describe("isFullyWatched", () => {
  it("is true when every season's watched count reaches its length (the + button)", () => {
    expect(isFullyWatched(show([season(12, 12), season(24, 24)]))).toBe(true);
  });

  it("is true when every episode is ticked, even with a count of zero (the Episodes tab)", () => {
    expect(isFullyWatched(show([season(0, 3, 3)]))).toBe(true);
  });

  it("is false while any season has episodes left", () => {
    expect(isFullyWatched(show([season(12, 12), season(10, 24)]))).toBe(false);
  });

  it("is false when a season's length is unknown", () => {
    expect(isFullyWatched(show([season(12, null)]))).toBe(false);
  });

  it("is false while another episode is on the way", () => {
    expect(isFullyWatched(show([season(12, 12)], { nextEpisodeAirAt: "2026-11-01" }))).toBe(false);
  });

  it("is false for a show with no seasons", () => {
    expect(isFullyWatched(show([]))).toBe(false);
  });
});
