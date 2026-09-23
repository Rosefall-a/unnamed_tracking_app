// Library statistics (see backend api/routes/media_stats.py). Everything
// is exact or absent: watch time is the sum of real runtimes, and titles
// or episodes with no runtime on record are counted separately, never
// filled in with a guess.

export interface NamedCount {
  name: string;
  count: number;
  average?: number | null;
}
export interface YearCount {
  year: number;
  count: number;
}
export interface MonthCount {
  month: string;
  count: number;
}
export interface TopTitle {
  id: string;
  title: string;
  score: number;
  posterUrl: string | null;
  kind: "movie" | "tv" | "anime" | "game";
}
export interface Rewatched {
  id: string;
  title: string;
  count: number;
}
export interface ProgressRow {
  id: string;
  title: string;
  kind: "anime" | "tv" | "game";
  watched: number;
  total: number;
  posterUrl: string | null;
  // set for games, which have no episode count: the exact playtime text
  label?: string;
}
export interface StatusCounts {
  plan: number;
  hold: number;
  watching: number;
  completed: number;
  dropped: number;
}
export interface ScoreStats {
  rated: number;
  average: number | null;
  distribution: Record<string, number>;
}

interface Common {
  titles: number;
  by_status: StatusCounts;
  favorites: number;
  score: ScoreStats;
  by_release_year: YearCount[];
  top_rated: TopTitle[];
  added_per_month: MonthCount[];
}

export interface MovieStats extends Common {
  genres: NamedCount[];
  studios: NamedCount[];
  directors: NamedCount[];
  movies_watched: number;
  minutes_watched: number;
  minutes_first: number;
  minutes_rewatch: number;
  movies_without_runtime: number;
  rewatches: number;
  most_rewatched: Rewatched[];
  rewatch_logs: number;
}

export interface EpisodicStats extends Common {
  genres: NamedCount[];
  studios: NamedCount[];
  formats: NamedCount[];
  rewatch_logs: number;
  most_rewatched: Rewatched[];
  // an episode counts when its row is flagged or it is within the season
  // progress counter; only episodes marked watched count; a rewatch adds that title's
  // watched episodes again; a season is completed only when every one of
  // its episodes is watched
  seasons_completed: number;
  seasons_in_progress: number;
  episodes_watched: number;
  episodes_rewatched: number;
  episodes_known: number;
  minutes_first: number;
  minutes_rewatch: number;
  minutes_watched: number;
  episodes_without_runtime: number;
  most_watched: {
    id: string;
    title: string;
    minutes: number;
    episodes: number;
  }[];
}

export interface GameStats extends Common {
  playtime_seconds: number;
  games_with_playtime: number;
  most_played: { id: string; title: string; seconds: number }[];
  achievements_unlocked: number;
  achievements_total: number;
  sources: NamedCount[];
  developers: NamedCount[];
  tags: NamedCount[];
  finished_per_year: YearCount[];
  spent: { currency: string; amount: number }[];
  insights: GameInsights;
}

// What a game library tool like Playnite would show, computed exactly:
// "no playtime recorded" means the platform reported none, backlog hours
// only add games that have a time-to-beat (the rest are counted apart),
// and cost per hour only uses games with both a price and playtime.
export interface GameInsights {
  owned: number;
  with_playtime: number;
  unplayed: { count: number; spent: { currency: string; amount: number }[] };
  average_seconds: number | null;
  median_seconds: number | null;
  playtime_buckets: { label: string; count: number }[];
  played_last_30_days: number;
  recently_played: {
    id: string;
    title: string;
    last_played_at: number;
    seconds: number;
  }[];
  finished_this_year: number;
  seconds_by_source: { name: string; seconds: number }[];
  seconds_by_developer: { name: string; seconds: number }[];
  seconds_by_series: { name: string; seconds: number }[];
  backlog: { count: number; hours: number; without_estimate: number };
  cost_per_hour: {
    currency: string;
    per_hour: number;
    hours: number;
    games: number;
  }[];
  closest_to_full: {
    id: string;
    title: string;
    unlocked: number;
    total: number;
  }[];
  fully_unlocked: number;
  decades: { decade: number; count: number }[];
  age_ratings: NamedCount[];
  features: NamedCount[];
}

export interface OverviewStats {
  kinds: {
    kind: "movie" | "tv" | "anime" | "game";
    titles: number;
    completed: number;
    minutes: number;
  }[];
  media_minutes: number;
  game_seconds: number;
  media_titles: number;
  media_completed: number;
  media_favorites: number;
  top_rated: TopTitle[];
  in_progress: ProgressRow[];
  backlog: {
    kind: "movie" | "tv" | "anime" | "game";
    waiting: number;
    on_hold: number;
  }[];
  game_backlog: { count: number; hours: number; without_estimate: number };
  games_finished_this_year: number;
  score_by_type: {
    kind: "movie" | "tv" | "anime" | "game";
    average: number | null;
    rated: number;
  }[];
  needs_score: {
    count: number;
    items: {
      id: string;
      title: string;
      kind: "movie" | "tv" | "anime";
      posterUrl: string | null;
    }[];
  };
  activity: {
    per_day: {
      date: string;
      count: number;
      episodes: number;
      achievements: number;
    }[];
    active_days_total: number;
    current_streak: number;
    longest_streak: number;
    busiest_day: {
      date: string;
      count: number;
      episodes: number;
      achievements: number;
    } | null;
  };
}

export interface MediaStats {
  overview: OverviewStats;
  games: GameStats;
  movie: MovieStats;
  tv: EpisodicStats;
  anime: EpisodicStats;
}

// Kept in memory so opening the page again shows the last numbers at once
// while fresh ones load behind them.
let cached: MediaStats | null = null;

export function peekMediaStats(): MediaStats | null {
  return cached;
}

export async function fetchMediaStats(): Promise<MediaStats> {
  const response = await fetch("/api/media-stats", { credentials: "include" });
  if (!response.ok)
    throw new Error(`Failed to load statistics: ${response.status}`);
  const raw = (await response.json()) as MediaStats;
  // the server names it poster_url; the rest of the app says posterUrl
  const fix = (
    list: { poster_url?: string | null; posterUrl?: string | null }[],
  ) => list.forEach((t) => (t.posterUrl = t.posterUrl ?? t.poster_url ?? null));
  fix(raw.overview.top_rated);
  fix(raw.overview.in_progress);
  fix(raw.overview.needs_score.items);
  fix(raw.games.top_rated);
  fix(raw.movie.top_rated);
  fix(raw.tv.top_rated);
  fix(raw.anime.top_rated);
  cached = raw;
  return cached;
}
