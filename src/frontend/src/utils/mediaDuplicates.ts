// Before a film, show or anime is added: is it already in the library? The
// library is loaded a page at a time, so this asks the server (one small search
// by name) instead of looking only at what happens to be loaded.
import { fetchMoviesPage } from "../services/movies";
import { fetchTVShowsPage } from "../services/tvShows";
import { fetchAnimePage } from "../services/anime";
import { statusBucketLabel } from "./mediaStatus";

export interface LibraryMatch {
  id: string;
  title: string;
  year: string | null;
  status: string;
  to: string;
}

const plain = (text: string) =>
  text.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, "");

// The same name, and the same year when both have one: a remake with the same
// name ("Resident Evil" 2002 and 2026) is not the same title.
export function sameTitle(
  a: { title: string; year: string | null },
  b: { title: string; year: string | null },
): boolean {
  if (plain(a.title) !== plain(b.title)) return false;
  return !a.year || !b.year || a.year === b.year;
}

export async function findInLibrary(
  kind: "movie" | "tv" | "anime",
  title: string,
  year: string | null,
): Promise<LibraryMatch | null> {
  const query = title.trim();
  if (!query) return null;
  let found: LibraryMatch[];
  if (kind === "movie") {
    const page = await fetchMoviesPage(0, 10, query);
    found = page.items.map((m) => ({
      id: m.id,
      title: m.title,
      year: m.releaseDate?.slice(0, 4) ?? null,
      status: statusBucketLabel(m.status),
      to: `/movies/${m.id}`,
    }));
  } else if (kind === "tv") {
    const page = await fetchTVShowsPage(0, 10, query);
    found = page.items.map((s) => ({
      id: s.id,
      title: s.title,
      year: s.firstAirDate?.slice(0, 4) ?? null,
      status: statusBucketLabel(s.status),
      to: `/tv/${s.id}`,
    }));
  } else {
    const page = await fetchAnimePage(0, 10, query);
    found = page.items.map((a) => ({
      id: a.id,
      title: a.title,
      year: a.firstAirDate?.slice(0, 4) ?? null,
      status: statusBucketLabel(a.status),
      to: `/anime/${a.id}`,
    }));
  }
  return found.find((m) => sameTitle(m, { title: query, year })) ?? null;
}
