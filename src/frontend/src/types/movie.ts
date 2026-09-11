export type MovieStatus =
  | "dropped"
  | "wishlist"
  | "watchlist"
  | "backlog"
  | "in progress"
  | "watched"
  | "favorite"
  | "rewatch";

export interface Movie {
  id: string;
  userId: string;
  title: string;
  sortTitle: string;
  description: string | null;
  releaseDate: string | null;
  runtimeMinutes: number | null;
  director: string | null;
  writer: string | null;
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
  status: MovieStatus;
  priority: string | null;
  favorite: boolean;
  rewatches: number;
  ratingStory: number | null;
  ratingPerformance: number | null;
  ratingSoundtrack: number | null;
  ratingOverall: number | null;
  personalRank: number | null;
  createdAt: string;
  updatedAt: string;
}
