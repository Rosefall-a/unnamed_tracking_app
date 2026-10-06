export interface LibraryCardVM {
  id: string;
  title: string;
  poster: string | null;
  status: string;
  favorite: boolean;
  score: number | null;
  personalRank: number | null;
  note: string | null;
  genres: string[];
  isEpisodic: boolean;
  watched: number;
  total: number | null;
  progressLabel: string;
  canAdvance: boolean;
  // No real "currently airing" data source is wired up for any of the
  // three entities yet (would need extending the TVmaze/AniList/TMDB
  // clients) — the field and its always-rendered-but-invisible tag stay
  // here so the capability and layout are ready the moment that data
  // exists, matching the mockup exactly rather than dropping the feature.
  airing?: boolean;
  // The real sub-format (e.g. "TV", "Movie", "OVA") when the entity
  // carries one — currently only Anime does (from AniList/Jikan). Falls
  // back to the generic per-kind typeLabel below when absent.
  format?: string | null;
  // Release/first-air year, shown right under the format label — null
  // when the underlying date is unknown.
  releaseYear: string | null;
  // when it was added to the library (ms), for sorting by recently added
  addedAt?: number | null;
  // other spellings of the title, so search finds any of them
  altTitles?: string[];
}

export interface SearchResultVM {
  title: string;
  poster: string | null;
  description: string | null;
  episodeTotal: number | null;
  releaseYear: string | null;
}

export interface QuickAddForm {
  status: string;
  watched: number;
  seen: boolean;
  score: number | null;
  startDate: string | null;
  endDate: string | null;
}

export interface EditForm {
  status: string;
  score: number | null;
  watched: number;
  totalEpisodes: number | null;
  seen: boolean;
}
