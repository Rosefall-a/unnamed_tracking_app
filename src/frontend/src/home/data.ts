// What the Home widgets read. Each kind of data is fetched once, on first need,
// and shared, so ten widgets that list games cause one request. A widget says
// what it needs in the registry and the page loads it; a failed load is kept so
// the widget can say so and offer a retry.
import { computed, ref, shallowRef } from "vue";
import { fetchAchievementsFeed } from "../services/achievementsFeed";
import type { AchievementFeedEntry } from "../services/achievementsFeed";
import { fetchAchievementsSummary, fetchGames } from "../services/games";
import type { AchievementsSummaryEntry } from "../services/games";
import { fetchAnime, peekAllAnimes } from "../services/anime";
import { fetchMovies, peekAllMovies } from "../services/movies";
import { fetchTVShows, peekAllTVShows } from "../services/tvShows";
import { fetchCalendar } from "../services/mediaExtras";
import type { CalendarEntry } from "../services/mediaExtras";
import { fetchMediaNotifications } from "../services/notifications";
import type { MediaNotification } from "../services/notifications";
import { fetchStatsOverview, fetchWeeklyDigest } from "../services/stats";
import type { StatsOverview, WeeklyDigest } from "../services/stats";
import { fetchAllMedia } from "../services/media";
import type { MediaItem } from "../services/media";
import { animeFormatLabel } from "../utils/animeFormat";
import { sizedAssetUrl } from "../utils/gameImages";
import { displayTitle } from "../utils/displayTitle";
import { progressPercent } from "../utils/watchProgress";
import type { Anime } from "../types/anime";
import type { Game } from "../types/game";
import type { Movie } from "../types/movie";
import type { TVShow } from "../types/tv_show";

export type DataKey =
  | "games"
  | "movies"
  | "tv"
  | "anime"
  | "achievements"
  | "feed"
  | "calendar"
  | "notifications"
  | "digest"
  | "stats"
  | "screenshots";

export type TitleKind = "game" | "movie" | "tv" | "anime";

// "active" is being played or watched now, "queue" is waiting its turn
export type StatusGroup = "active" | "queue" | "wishlist" | "done" | "dropped";

// Any library entry, in the one shape the widgets draw from.
export interface HomeTitle {
  key: string;
  kind: TitleKind;
  id: string;
  title: string;
  art: string | null;
  wide: string | null;
  subtitle: string;
  // 0 to 1, or null when it has no measure of progress
  progress: number | null;
  // achievements unlocked out of those tracked, for games that have any
  ach: { unlocked: number; total: number } | null;
  to: string;
  status: string;
  group: StatusGroup;
  rating: number | null;
  favorite: boolean;
  addedAt: number;
  touchedAt: number;
  genres: string[];
  // when it comes out, or came out (ms), 0 when not known
  release: number;
  // the system a game is on
  platform: string;
  // how long it takes: time to beat for a game, running time for a film (hours)
  hours: number | null;
  // who made it: the developer of a game, the studios behind a film or show
  makers: string[];
}

// one title of each kind, for a label on a card
export const KIND_NOUN: Record<TitleKind, string> = {
  game: "Game",
  movie: "Movie",
  tv: "TV",
  anime: "Anime",
};

export const KIND_LABEL: Record<TitleKind, string> = {
  game: "Games",
  movie: "Movies",
  tv: "TV",
  anime: "Anime",
};

const games = shallowRef<Game[] | null>(null);
const movies = shallowRef<Movie[] | null>(null);
const tvShows = shallowRef<TVShow[] | null>(null);
const anime = shallowRef<Anime[] | null>(null);
const achSummary = shallowRef<Record<string, AchievementsSummaryEntry>>({});
const achFeed = shallowRef<{
  recent: AchievementFeedEntry[];
  rarest: AchievementFeedEntry[];
}>({ recent: [], rarest: [] });
const calendar = shallowRef<CalendarEntry[] | null>(null);
const notifications = shallowRef<{
  items: MediaNotification[];
  unread: number;
} | null>(null);
const digest = shallowRef<WeeklyDigest | null>(null);
const stats = shallowRef<StatsOverview | null>(null);
const screenshots = shallowRef<MediaItem[] | null>(null);

export const failed = ref<Partial<Record<DataKey, string>>>({});
const inflight = new Map<DataKey, Promise<void>>();
const loaded = new Set<DataKey>();
// what each widget waits on, as something the page can react to
const ready = ref<Partial<Record<DataKey, boolean>>>({});

async function load(key: DataKey): Promise<void> {
  switch (key) {
    case "games":
      games.value = await fetchGames();
      break;
    case "movies":
      movies.value = peekAllMovies() ?? (await fetchMovies());
      break;
    case "tv":
      tvShows.value = peekAllTVShows() ?? (await fetchTVShows());
      break;
    case "anime":
      anime.value = peekAllAnimes() ?? (await fetchAnime());
      break;
    case "achievements":
      achSummary.value = await fetchAchievementsSummary();
      break;
    case "feed":
      achFeed.value = await fetchAchievementsFeed(40);
      break;
    case "calendar":
      calendar.value = await fetchCalendar(45);
      break;
    case "notifications":
      notifications.value = await fetchMediaNotifications(12);
      break;
    case "digest":
      digest.value = await fetchWeeklyDigest();
      break;
    case "stats":
      stats.value = await fetchStatsOverview();
      break;
    case "screenshots":
      screenshots.value = await fetchAllMedia({ kind: "screenshot" });
      break;
  }
}

export function ensure(key: DataKey, force = false): Promise<void> {
  if (!force && loaded.has(key)) return Promise.resolve();
  const running = inflight.get(key);
  if (running) return running;
  const run = load(key)
    .then(() => {
      loaded.add(key);
      ready.value = { ...ready.value, [key]: true };
      const { [key]: _gone, ...rest } = failed.value;
      void _gone;
      failed.value = rest;
    })
    .catch((e) => {
      failed.value = {
        ...failed.value,
        [key]: e instanceof Error ? e.message : "Could not load this.",
      };
    })
    .finally(() => inflight.delete(key));
  inflight.set(key, run);
  return run;
}

export const isReady = (key: DataKey) => ready.value[key] === true;

// "in 3 hours", "in 2 days", for something that happens at a Unix time
export function until(seconds: number, now = Date.now()): string {
  const diff = seconds * 1000 - now;
  if (diff <= 0) return "now";
  const hours = Math.floor(diff / 3_600_000);
  if (hours < 1) return `in ${Math.max(1, Math.floor(diff / 60_000))} min`;
  if (hours < 24) return `in ${hours} h`;
  const days = Math.floor(hours / 24);
  return days === 1 ? "tomorrow" : `in ${days} days`;
}

// where a title of this kind opens
export function routeFor(mediaType: string, id: string): string {
  const base: Record<string, string> = {
    game: "/games",
    movie: "/movies",
    tv: "/tv",
    anime: "/anime",
  };
  return `${base[mediaType] ?? "/games"}/${id}`;
}

// ---- one shape for every kind of title ----

const DAY = 86_400_000;

function ms(value: string | null | undefined): number {
  if (!value) return 0;
  const t = new Date(value).getTime();
  return Number.isNaN(t) ? 0 : t;
}

// a date with no time ("2026-10-31") as that day at local midnight; 0 when missing
export function dayMs(value: string | null | undefined): number {
  if (!value) return 0;
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(value);
  if (m)
    return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])).getTime();
  return ms(value);
}

export function ago(time: number, now = Date.now()): string {
  if (!time) return "";
  const days = Math.floor((now - time) / DAY);
  if (days <= 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 30) return `${days} days ago`;
  if (days < 365) return `${Math.floor(days / 30)} mo ago`;
  return `${Math.floor(days / 365)} y ago`;
}

function mediaGroup(status: string): StatusGroup {
  if (status === "in progress" || status === "rewatch") return "active";
  if (status === "watched" || status === "favorite") return "done";
  if (status === "dropped") return "dropped";
  if (status === "wishlist") return "wishlist";
  return "queue";
}

function gameGroup(status: string): StatusGroup {
  if (status === "playing") return "active";
  if (status === "beaten" || status === "played" || status === "mastered")
    return "done";
  if (status === "dropped") return "dropped";
  if (status === "wishlist") return "wishlist";
  return "queue";
}

interface WithSeasons {
  seasons: {
    seasonNumber: number;
    episodesWatched: number;
    episodeCount: number | null;
  }[];
}

// "S2 E5" for the next unwatched episode, and how far through the whole show
function episodeProgress(show: WithSeasons): {
  subtitle: string;
  progress: number | null;
} {
  const seasons = [...show.seasons]
    .filter((s) => s.seasonNumber > 0)
    .sort((a, b) => a.seasonNumber - b.seasonNumber);
  let watched = 0;
  let total = 0;
  let next: string | null = null;
  for (const s of seasons) {
    watched += s.episodesWatched;
    total += s.episodeCount ?? 0;
    if (!next && s.episodeCount && s.episodesWatched < s.episodeCount)
      next = `S${s.seasonNumber} E${s.episodesWatched + 1}`;
  }
  return {
    subtitle: next ?? (total ? `${watched} / ${total} episodes` : ""),
    progress: total ? Math.min(1, watched / total) : null,
  };
}

// A game with no cover gets a generated one that has the game's name on it. On
// Home the card prints the name itself, so ask for it without.
function plainCover(url: string | null | undefined): string | null {
  if (!url) return null;
  if (!url.includes("/assets/key_art")) return url;
  return `${url}${url.includes("?") ? "&" : "?"}plain=1`;
}

function gameTitle(g: Game): HomeTitle {
  const touched = ms(g.lastPlayedAt);
  const summary = achSummary.value[g.id];
  return {
    key: `game:${g.id}`,
    kind: "game",
    id: g.id,
    title: g.title,
    art: plainCover(g.coverImageUrl),
    wide: g.bannerImageUrl ? sizedAssetUrl(g.bannerImageUrl, 1200) : null,
    subtitle: touched
      ? `Played ${ago(touched)}`
      : g.platform || g.status.charAt(0).toUpperCase() + g.status.slice(1),
    progress: null,
    ach: summary?.total
      ? { unlocked: summary.unlocked, total: summary.total }
      : null,
    to: `/games/${g.id}`,
    status: g.status,
    group: gameGroup(g.status),
    rating: g.ratingOverall,
    favorite: g.favorite,
    addedAt: ms(g.dateAdded),
    touchedAt: touched,
    genres: g.tags ?? [],
    release: dayMs(g.releaseDate),
    platform: g.platform || g.source || "",
    hours: g.timeToBeatHours,
    makers: g.developer ? [g.developer] : [],
  };
}

function movieTitle(m: Movie): HomeTitle {
  const percent = progressPercent(m.progressMinutes, m.runtimeMinutes);
  return {
    key: `movie:${m.id}`,
    kind: "movie",
    id: m.id,
    title: m.title,
    art: m.posterUrl,
    wide: m.backdropUrl,
    subtitle: m.releaseDate ? m.releaseDate.slice(0, 4) : "Movie",
    progress: percent === null ? null : percent / 100,
    ach: null,
    to: `/movies/${m.id}`,
    status: m.status,
    group: mediaGroup(m.status),
    rating: m.ratingOverall,
    favorite: m.favorite,
    addedAt: ms(m.createdAt),
    touchedAt: ms(m.updatedAt),
    genres: m.genres,
    release: dayMs(m.releaseDate),
    platform: "",
    hours: m.runtimeMinutes ? m.runtimeMinutes / 60 : null,
    makers: m.studios ?? [],
  };
}

function showTitle(s: TVShow): HomeTitle {
  const { subtitle, progress } = episodeProgress(s);
  return {
    key: `tv:${s.id}`,
    kind: "tv",
    id: s.id,
    title: s.title,
    art: s.posterUrl,
    wide: s.backdropUrl,
    subtitle: subtitle || "TV show",
    progress,
    ach: null,
    to: `/tv/${s.id}`,
    status: s.status,
    group: mediaGroup(s.status),
    rating: s.ratingOverall,
    favorite: s.favorite,
    addedAt: ms(s.createdAt),
    touchedAt: ms(s.updatedAt),
    genres: s.genres,
    release: dayMs(s.firstAirDate),
    platform: "",
    hours: null,
    makers: s.studios ?? [],
  };
}

function animeTitle(a: Anime): HomeTitle {
  const { subtitle: episodes, progress } = episodeProgress(a);
  // a film or an OVA is called that, not "S1 E1"
  const format = a.seasons.length <= 1 ? animeFormatLabel(a.format) : null;
  const year = a.firstAirDate ? a.firstAirDate.slice(0, 4) : "";
  const subtitle = format ? (year ? `${format} · ${year}` : format) : episodes;
  return {
    key: `anime:${a.id}`,
    kind: "anime",
    id: a.id,
    title: displayTitle(a),
    art: a.posterUrl,
    wide: a.backdropUrl,
    subtitle: subtitle || "Anime",
    progress,
    ach: null,
    to: `/anime/${a.id}`,
    status: a.status,
    group: mediaGroup(a.status),
    rating: a.ratingOverall,
    favorite: a.favorite,
    addedAt: ms(a.createdAt),
    touchedAt: ms(a.updatedAt),
    genres: a.genres,
    release: dayMs(a.firstAirDate),
    platform: "",
    hours: null,
    makers: a.studios ?? [],
  };
}

export const titlesByKind = computed<Record<TitleKind, HomeTitle[]>>(() => ({
  game: (games.value ?? []).map(gameTitle),
  movie: (movies.value ?? []).map(movieTitle),
  tv: (tvShows.value ?? []).map(showTitle),
  anime: (anime.value ?? []).map(animeTitle),
}));

export const allTitles = computed(() => [
  ...titlesByKind.value.game,
  ...titlesByKind.value.movie,
  ...titlesByKind.value.tv,
  ...titlesByKind.value.anime,
]);

// The kinds a widget was told to include; an empty or missing choice is all.
export function titlesOf(kinds: unknown): HomeTitle[] {
  const wanted = Array.isArray(kinds) ? (kinds as TitleKind[]) : [];
  if (!wanted.length) return allTitles.value;
  return wanted.flatMap((k) => titlesByKind.value[k] ?? []);
}

// The next confirmed episode of each show, by title key. Weekly guesses for later
// episodes are left out: a countdown to a guess would be a made-up number.
export const nextAirByKey = computed(() => {
  const next = new Map<string, CalendarEntry>();
  for (const e of calendar.value ?? []) {
    if (e.isProjected || e.kind !== "episode") continue;
    const key = `${e.mediaType}:${e.mediaId}`;
    const have = next.get(key);
    if (!have || e.airAt < have.airAt) next.set(key, e);
  }
  return next;
});

export const homeData = {
  games,
  movies,
  tvShows,
  anime,
  achSummary,
  achFeed,
  calendar,
  notifications,
  digest,
  stats,
  screenshots,
};
