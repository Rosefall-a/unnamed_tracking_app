export type TVShowStatus =
  | "dropped"
  | "wishlist"
  | "watchlist"
  | "backlog"
  | "in progress"
  | "watched"
  | "favorite"
  | "rewatch";

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
  posterUrl: string | null;
  status: TVShowStatus;
  priority: string | null;
  favorite: boolean;
  rewatches: number;
  ratingStory: number | null;
  ratingPerformance: number | null;
  ratingSoundtrack: number | null;
  ratingOverall: number | null;
  personalRank: number | null;
  seasons: Season[];
  createdAt: string;
  updatedAt: string;
}
