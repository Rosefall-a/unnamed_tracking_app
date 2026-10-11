import { describe, expect, it } from "vitest";
import { bucketCounts } from "../utils/mediaStatus";

describe("bucketCounts", () => {
  it("folds the server's real statuses into the five tabs", () => {
    const counts = bucketCounts({
      WISHLIST: 7,
      WATCHLIST: 66,
      BACKLOG: 15,
      IN_PROGRESS: 3,
      REWATCH: 1,
      WATCHED: 128,
      FAVORITE: 2,
      DROPPED: 3,
    });
    expect(counts).toMatchObject({
      plan: 73,
      hold: 15,
      watching: 4,
      completed: 130,
      dropped: 3,
    });
  });

  it("makes All the sum of the tabs", () => {
    expect(bucketCounts({ WATCHED: 4, DROPPED: 1 }).all).toBe(5);
  });

  it("keeps a key that already is a tab", () => {
    expect(bucketCounts({ watching: 2, completed: 3 })).toMatchObject({
      watching: 2,
      completed: 3,
      all: 5,
    });
  });
});
