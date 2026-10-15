// Picking, filtering and ordering titles for the widgets that list them, so a
// shelf, a continue row and the random picker all mean the same by "highest
// rated" or "this genre".
import type { HomeTitle } from "./data";

export function sortTitles(
  list: HomeTitle[],
  sort: unknown,
  fallback: "added" | "updated" | "title" | "rating" = "added",
): HomeTitle[] {
  const mode = sort === "default" || !sort ? fallback : String(sort);
  const copy = [...list];
  switch (mode) {
    case "updated":
      return copy.sort((a, b) => b.touchedAt - a.touchedAt);
    case "title":
      return copy.sort((a, b) => a.title.localeCompare(b.title));
    case "rating":
      return copy.sort((a, b) => (b.rating ?? -1) - (a.rating ?? -1));
    case "random":
      return shuffle(copy);
    default:
      return copy.sort((a, b) => b.addedAt - a.addedAt);
  }
}

export function shuffle<T>(list: T[]): T[] {
  for (let i = list.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [list[i], list[j]] = [list[j], list[i]];
  }
  return list;
}

// the genre, rating, platform and length options shared by shelves and the picker
export function narrow(
  list: HomeTitle[],
  settings: Record<string, unknown>,
): HomeTitle[] {
  const genre = String(settings.genre ?? "")
    .trim()
    .toLowerCase();
  const min = Number(settings.minRating) || 0;
  const platform = String(settings.platform ?? "")
    .trim()
    .toLowerCase();
  const maxHours = Number(settings.maxHours) || 0;
  return list.filter(
    (t) =>
      (!genre || t.genres.some((g) => g.toLowerCase().includes(genre))) &&
      (min <= 0 || (t.rating !== null && t.rating >= min)) &&
      (!platform || t.platform.toLowerCase().includes(platform)) &&
      (maxHours <= 0 || (t.hours !== null && t.hours <= maxHours)),
  );
}
