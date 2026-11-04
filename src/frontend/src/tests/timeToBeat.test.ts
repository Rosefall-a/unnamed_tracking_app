import { afterEach, describe, expect, it } from "vitest";

import { DEFAULT_PREFERENCES } from "../services/preferences";
import type { TimeToBeatStyle } from "../services/preferences";
import { preferences } from "../state/preferences";
import type { Game, GameStatus } from "../types/game";
import {
  DEFAULT_PICKER_FILTERS,
  matchesPickerFilters,
} from "../utils/randomPicker";
import { chosenHours, chosenTimeLabel, hoursFor } from "../utils/timeToBeat";

function use(style: TimeToBeatStyle) {
  preferences.value = { ...DEFAULT_PREFERENCES, time_to_beat_style: style };
}

const game = (times: Partial<Game>): Game =>
  ({
    id: "a",
    title: "a",
    status: "backlog" as GameStatus,
    tags: [],
    priority: null,
    platforms: [],
    timeToBeatHours: 10,
    timeToBeatExtrasHours: 20,
    timeToBeatCompletionistHours: 40,
    timeToBeatAllHours: 15,
    ...times,
  }) as Game;

afterEach(() => use("main"));

describe("the chosen time to beat", () => {
  it("defaults to the main story", () => {
    expect(chosenHours(game({}))).toBe(10);
    expect(chosenTimeLabel()).toBe("Main story");
  });

  it("reads each figure", () => {
    expect(hoursFor(game({}), "extras")).toBe(20);
    expect(hoursFor(game({}), "completionist")).toBe(40);
    expect(hoursFor(game({}), "all")).toBe(15);
  });

  it("is unknown when the game lacks that figure, never another figure", () => {
    use("completionist");
    expect(
      chosenHours(game({ timeToBeatCompletionistHours: null })),
    ).toBeNull();
    expect(
      chosenHours(game({ timeToBeatCompletionistHours: undefined })),
    ).toBeNull();
    expect(chosenTimeLabel()).toBe("Completionist");
  });

  it("drives the random picker's length limit", () => {
    const limit = { ...DEFAULT_PICKER_FILTERS, maxHours: 30 };
    expect(matchesPickerFilters(game({}), limit)).toBe(true);
    use("completionist");
    expect(matchesPickerFilters(game({}), limit)).toBe(false);
  });
});
