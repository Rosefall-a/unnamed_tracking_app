import { describe, expect, it } from "vitest";

import { computeScore } from "../utils/scoring";
import type { Game } from "../types/game";

const baseGame = {
  id: "game-1",
  title: "Test Game",
  coverColor: "#000000",
  coverImageUrl: "",
  bannerImageUrl: "",
  status: "played",
  lastPlayedAt: null,
  staleSince: null,
  profilesEnabled: false,
  osrsStatsEnabled: false,
  completionDate: null,
  parentGameId: null,
  relationshipType: null,
  achievementPercent: 0,
  achievementTotal: 0,
  achievements: [],
  description: null,
  developer: null,
  publisher: null,
  series: null,
  dateAdded: null,
  resumeNote: null,
  folderLocation: null,
  releaseDate: null,
  source: null,
  ageRating: null,
  timeToBeatHours: null,
  region: null,
  language: null,
  achievementsProvider: null,
  links: [],
  ownership: {
    format: null,
    purchaseDate: null,
    price: null,
    priceCurrency: null,
    condition: null,
  },
  favorite: false,
  collections: [],
  tags: [],
  features: [],
  platforms: [],
} satisfies Omit<
  Game,
  "ratingOverall" | "ratingStory" | "ratingGameplay" | "ratingSound"
>;

describe("computeScore", () => {
  it("sums only ratings that are present", () => {
    const game = {
      ...baseGame,
      ratingOverall: 8,
      ratingStory: null,
      ratingGameplay: 7,
      ratingSound: 9,
    } satisfies Game;

    expect(computeScore(game)).toEqual({ sum: 24, max: 30 });
  });

  it("returns null when a game has no ratings", () => {
    const game = {
      ...baseGame,
      ratingOverall: null,
      ratingStory: null,
      ratingGameplay: null,
      ratingSound: null,
    } satisfies Game;

    expect(computeScore(game)).toBeNull();
  });

  it("allows a zero rating", () => {
    const game = {
      ...baseGame,
      ratingOverall: 0,
      ratingStory: null,
      ratingGameplay: null,
      ratingSound: null,
    } satisfies Game;

    expect(computeScore(game)).toEqual({ sum: 0, max: 10 });
  });
});
