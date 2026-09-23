// Which spelling of an anime's title to show, from the user's title
// language setting (English, romaji or Japanese). `title` stays the
// canonical one; if the preferred spelling is not known for a title the next
// best is used, and finally `title`, so a title is never blank.
import { preferences } from "../state/preferences";
import type { Anime } from "../types/anime";

const ORDER = {
  english: ["titleEnglish", "titleRomaji", "titleNative"],
  romaji: ["titleRomaji", "titleEnglish", "titleNative"],
  native: ["titleNative", "titleRomaji", "titleEnglish"],
} as const;

export function displayTitle(
  show: Pick<Anime, "title" | "titleEnglish" | "titleRomaji" | "titleNative">,
): string {
  for (const key of ORDER[preferences.value.title_language] ?? ORDER.english) {
    const value = show[key];
    if (value) return value;
  }
  return show.title;
}
