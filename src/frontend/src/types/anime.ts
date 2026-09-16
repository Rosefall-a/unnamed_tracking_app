export type AnimeStatus =
  | "dropped"
  | "wishlist"
  | "watchlist"
  | "backlog"
  | "in progress"
  | "watched"
  | "favorite"
  | "rewatch";

export interface AnimeEpisode {
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

export interface AnimeSeason {
  id: string;
  showId: string;
  seasonNumber: number;
  name: string | null;
  episodeCount: number | null;
  episodesWatched: number;
  status: AnimeStatus;
  airDate: string | null;
  posterUrl: string | null;
  episodes: AnimeEpisode[];
  createdAt: string;
  updatedAt: string;
}

export interface Anime {
  id: string;
  userId: string;
  title: string;
  sortTitle: string;
  description: string | null;
  firstAirDate: string | null;
  episodeRuntimeMinutes: number | null;
  studios: string[];
  countries: string[];
  languages: string[];
  genres: string[];
  tags: string[];
  features: string[];
  ageRating: string | null;
  format: string | null;
  anilistScore: number | null;
  malScore: number | null;
  source: string | null;
  externalId: string | null;
  anilistId: string | null;
  posterUrl: string | null;
  backdropUrl: string | null;
  status: AnimeStatus;
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
  seasons: AnimeSeason[];
  createdAt: string;
  updatedAt: string;
}
