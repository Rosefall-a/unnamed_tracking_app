// The rules behind the library's Filters panel, kept apart from the page so
// they can be tested. A title with no known value for a filter that needs one
// (no year for a year range, no score for a minimum score) never matches it.

export interface Filterable {
  title: string;
  altTitles?: string[];
  genres: string[];
  format?: string | null;
  favorite: boolean;
  score: number | null;
  note: string | null;
  releaseYear: string | null;
}

export interface LibraryFilters {
  search: string;
  genres: string[];
  genreMatchAll: boolean;
  formats: string[];
  onlyFavorites: boolean;
  onlyUnrated: boolean;
  onlyWithNote: boolean;
  minScore: number | null;
  yearFrom: string;
  yearTo: string;
}

export function matchesFilters(it: Filterable, f: LibraryFilters): boolean {
  const q = f.search.trim().toLowerCase();
  if (q) {
    const spellings = [it.title, ...(it.altTitles ?? [])];
    if (!spellings.some((t) => t.toLowerCase().includes(q))) return false;
  }
  if (f.genres.length) {
    const has = (g: string) => it.genres.includes(g);
    if (!(f.genreMatchAll ? f.genres.every(has) : f.genres.some(has)))
      return false;
  }
  if (f.formats.length && !f.formats.includes(it.format ?? "")) return false;
  if (f.onlyFavorites && !it.favorite) return false;
  if (f.onlyUnrated && it.score !== null) return false;
  if (f.onlyWithNote && !(it.note && it.note.trim())) return false;
  if (f.minScore !== null && !(it.score !== null && it.score >= f.minScore))
    return false;
  const from = parseInt(f.yearFrom, 10);
  const to = parseInt(f.yearTo, 10);
  if (!Number.isNaN(from) || !Number.isNaN(to)) {
    const year = it.releaseYear ? parseInt(it.releaseYear, 10) : NaN;
    if (Number.isNaN(year)) return false;
    if (!Number.isNaN(from) && year < from) return false;
    if (!Number.isNaN(to) && year > to) return false;
  }
  return true;
}
