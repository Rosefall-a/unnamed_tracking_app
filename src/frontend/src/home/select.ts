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
      // shuffled once a day, so Home looks the same every visit until tomorrow
      return dailyShuffle(copy, (t) => t.key);
    default:
      return copy.sort((a, b) => b.addedAt - a.addedAt);
  }
}

// The local day ("2026-11-10"): what "today" means for anything picked daily
export function todayKey(now: number | Date = Date.now()): string {
  const d = new Date(now);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

// FNV-1a: a small, stable number for a piece of text
function hash(text: string): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return h >>> 0;
}

/** A shuffle that stays the same all day and changes tomorrow. Each item is
 * placed by its own key and the day, so the order does not depend on the order
 * the list came in, and a title added or removed leaves the rest where they
 * were. `salt` lets two widgets shuffle the same titles differently. */
export function dailyShuffle<T>(
  list: T[],
  keyOf: (item: T) => string,
  salt = "",
  day = todayKey(),
): T[] {
  const placed = list.map((item) => ({
    item,
    key: keyOf(item),
    rank: hash(`${day}|${salt}|${keyOf(item)}`),
  }));
  placed.sort((a, b) => a.rank - b.rank || a.key.localeCompare(b.key));
  return placed.map((p) => p.item);
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

const DAY = 86_400_000;

/** Started and not finished, and left alone for a while: a game with real
 * playtime that is not done, or a show or film partway through. Only recorded
 * playtime and episodes count; nothing is estimated. */
export function isUnfinished(
  t: HomeTitle,
  settings: Record<string, unknown>,
  now = Date.now(),
): boolean {
  if (t.group === "done" || t.group === "dropped" || t.group === "wishlist")
    return false;
  const started =
    t.kind === "game"
      ? (t.playedHours ?? 0) > 0 &&
        (t.playedHours ?? 0) >= (Number(settings.minHours) || 0)
      : t.progress !== null && t.progress > 0 && t.progress < 1;
  if (!started) return false;
  const staleDays = Number(settings.staleDays) || 0;
  return !staleDays || !t.touchedAt || now - t.touchedAt >= staleDays * DAY;
}

/** Whether a title is in the collection a shelf shows: "game:<name>" for a game
 * collection, "list:<id>" for a media list (its members as title keys). */
export function inCollection(
  t: HomeTitle,
  collection: string,
  listMembers: string[] | undefined,
): boolean {
  if (collection.startsWith("game:"))
    return t.kind === "game" && t.collections.includes(collection.slice(5));
  if (collection.startsWith("list:"))
    return (listMembers ?? []).includes(t.key);
  return false;
}
