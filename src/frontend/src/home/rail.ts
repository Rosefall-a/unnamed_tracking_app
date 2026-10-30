import type { RailItem } from "../components/home/ArtRail.vue";
import { airPhrase, countdown } from "./clock";
import { KIND_NOUN, nextAirByKey } from "./data";
import type { HomeTitle, TitleKind } from "./data";

export type RailShape = "poster" | "wide" | "square";

// A title as a card in a row. The kind goes on every card; the row decides
// whether to show it (always, never, or only when it mixes kinds).
export function toRail(t: HomeTitle, shape: RailShape): RailItem {
  return {
    key: t.key,
    title: t.title,
    art: shape === "wide" ? (t.wide ?? t.art) : t.art,
    subtitle: t.subtitle,
    progress: t.progress,
    to: t.to,
    tag: KIND_NOUN[t.kind],
    tagKind: t.kind,
  };
}

// The countdown to a show's next episode, when a provider has confirmed one
// ("2d 4h"). Null for anything that is not airing.
export function airBadge(
  key: string,
  now: number,
  precise = false,
): string | null {
  const next = nextAirByKey.value.get(key);
  return next ? airPhrase(countdown(next.airAt, now, precise)) : null;
}

export function asKinds(value: unknown): TitleKind[] {
  return Array.isArray(value) ? (value as TitleKind[]) : [];
}

const LIBRARY: Record<string, string> = {
  game: "/games",
  movie: "/movies",
  tv: "/tv",
  anime: "/anime",
};

// where a heading goes: the library of the one kind a widget is limited to, and
// nowhere when it mixes kinds
export function libraryLink(
  kinds: unknown,
): { to: string; label: string } | null {
  const list = asKinds(kinds);
  if (list.length !== 1) return null;
  const to = LIBRARY[list[0]];
  return to ? { to, label: "Open the library" } : null;
}
