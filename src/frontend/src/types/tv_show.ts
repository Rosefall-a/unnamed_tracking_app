export type TVShowStatus =
  | "dropped"
  | "wishlist"
  | "watchlist"
  | "backlog"
  | "in progress"
  | "watched"
  | "favorite"
  | "rewatch";

export interface Episode {
  id: string;
  seasonId: string;
  episodeNumber: number;
  title: string | null;
  description: string | null;
  airDate: string | null;
  runtimeMinutes: number | null;
  stillUrl: string | null;
  watched: boolean;
  rating: number | null;
  createdAt: string;
  updatedAt: string;
}

export interface Season {
  id: string;
  showId: string;
  seasonNumber: number;
  name: string | null;
  episodeCount: number | null;
  episodesWatched: number;
  status: TVShowStatus;
  airDate: string | null;
  posterUrl: string | null;
  episodes: Episode[];
  createdAt: string;
  updatedAt: string;
}

export interface TVShow {
  id: string;
  userId: string;
  title: string;
  sortTitle: string;
  description: string | null;
  firstAirDate: string | null;
  episodeRuntimeMinutes: number | null;
  creators: string[];
  studios: string[];
  countries: string[];
  languages: string[];
  genres: string[];
  tags: string[];
  features: string[];
  ageRating: string | null;
  tmdbScore: number | null;
  source: string | null;
  externalId: string | null;
  posterUrl: string | null;
  backdropUrl: string | null;
  status: TVShowStatus;
  priority: string | null;
  favorite: boolean;
  rewatches: number;
  note: string | null;
  startDate: string | null;
  endDate: string | null;
  ratingStory: number | null;
  ratingPerformance: number | null;
  ratingSoundtrack: number | null;
  ratingOverall: number | null;
  personalRank: number | null;
  // backend field names (e.g. "poster_url") an admin has manually
  // changed — "Apply metadata" skips re-filling these
  lockedFields: string[];
  seasons: Season[];
  createdAt: string;
  updatedAt: string;
}
