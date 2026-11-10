// Which HowLongToBeat figure the person goes by. Sorting, length limits, Home
// widgets and the game page's headline all read it from here.
import { preferences } from "../state/preferences";
import type { TimeToBeatStyle } from "../services/preferences";
import type { Game } from "../types/game";

type GameTimes = Pick<
  Game,
  | "timeToBeatHours"
  | "timeToBeatExtrasHours"
  | "timeToBeatCompletionistHours"
  | "timeToBeatAllHours"
>;

export const TIME_TO_BEAT_STYLES: { value: TimeToBeatStyle; label: string }[] =
  [
    { value: "main", label: "Main story" },
    { value: "extras", label: "Main story and extras" },
    { value: "completionist", label: "Completionist" },
    { value: "all", label: "All play styles" },
  ];

// A game missing the chosen figure counts as unknown. Another figure is never
// put in its place: a main story time passed off as completionist would be wrong.
export function hoursFor(
  game: GameTimes,
  style: TimeToBeatStyle,
): number | null {
  if (style === "extras") return game.timeToBeatExtrasHours ?? null;
  if (style === "completionist")
    return game.timeToBeatCompletionistHours ?? null;
  if (style === "all") return game.timeToBeatAllHours ?? null;
  return game.timeToBeatHours ?? null;
}

export function chosenHours(game: GameTimes): number | null {
  return hoursFor(game, preferences.value.time_to_beat_style);
}

export function chosenTimeLabel(): string {
  const style = preferences.value.time_to_beat_style;
  return (
    TIME_TO_BEAT_STYLES.find((s) => s.value === style)?.label ?? "Main story"
  );
}
