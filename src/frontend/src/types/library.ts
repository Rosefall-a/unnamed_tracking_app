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
  airing?: boolean;
  format?: string | null;
  releaseYear: string | null;
  addedAt?: number | null;
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
