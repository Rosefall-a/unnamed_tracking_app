import type { Anime, AnimeSeason, AnimeStatus } from "../types/anime";

const SHOWS_PAGE_SIZE = 50;

// The exact shape FastAPI sends, snake_case, matching the Python model
// field-for-field. Nothing outside this file should ever see raw backend
// data directly.
interface BackendSeason {
  id: string;
  show_id: string;
  season_number: number;
  name: string | null;
  episode_count: number | null;
  episodes_watched: number;
  status: string;
  air_date: string | null;
  poster_url: string | null;
  created_at: number;
  updated_at: number;
}

export interface BackendAnime {
  id: string;
  user_id: string;
  title: string;
  sort_title: string;
  description: string | null;
  first_air_date: string | null;
  episode_runtime_minutes: number | null;
  studios: string[];
  countries: string[];
  languages: string[];
  genres: string[];
  tags: string[];
  features: string[];
  age_rating: string | null;
  anilist_score: number | string | null;
  mal_score: number | string | null;
  source: string | null;
  poster_url: string | null;
  status: string;
  priority: string | null;
  favorite: boolean;
  rewatches: number;
  rating_story: number | string | null;
  rating_performance: number | string | null;
  rating_soundtrack: number | string | null;
  rating_overall: number | string | null;
  personal_rank: number | null;
  seasons: BackendSeason[];
  // unix timestamps in seconds, not ISO strings
  created_at: number;
  updated_at: number;
}

// Pydantic can serialize a Decimal as either a JSON number or a string
// depending on config, handle both rather than assume one
function toNumberOrNull(value: number | string | null): number | null {
  return value === null ? null : Number(value);
}

function unixSecondsToIso(seconds: number): string {
  return new Date(seconds * 1000).toISOString();
}

// backend sends "IN_PROGRESS", "WISHLIST", etc., frontend expects
// 'in progress', 'wishlist' (lowercase, spaces not underscores)
function normalizeStatus(raw: string): AnimeStatus {
  return raw.toLowerCase().replace(/_/g, " ") as AnimeStatus;
}
// inverse of normalizeStatus, 'in progress' -> 'IN_PROGRESS'
function denormalizeStatus(status: AnimeStatus): string {
  return status.toUpperCase().replace(/ /g, "_");
}

function mapBackendSeason(raw: BackendSeason): AnimeSeason {
  return {
    id: raw.id,
    showId: raw.show_id,
    seasonNumber: raw.season_number,
    name: raw.name,
    episodeCount: raw.episode_count,
    episodesWatched: raw.episodes_watched,
    status: normalizeStatus(raw.status),
    airDate: raw.air_date,
    posterUrl: raw.poster_url,
    createdAt: unixSecondsToIso(raw.created_at),
    updatedAt: unixSecondsToIso(raw.updated_at),
  };
}

export function mapBackendAnime(raw: BackendAnime): Anime {
  return {
    id: raw.id,
    userId: raw.user_id,
    title: raw.title,
    sortTitle: raw.sort_title,
    description: raw.description,
    firstAirDate: raw.first_air_date,
    episodeRuntimeMinutes: raw.episode_runtime_minutes,
    studios: raw.studios,
    countries: raw.countries,
    languages: raw.languages,
    genres: raw.genres,
    tags: raw.tags,
    features: raw.features,
    ageRating: raw.age_rating,
    anilistScore: toNumberOrNull(raw.anilist_score),
    malScore: toNumberOrNull(raw.mal_score),
    source: raw.source,
    posterUrl: raw.poster_url,
    status: normalizeStatus(raw.status),
    priority: raw.priority,
    favorite: raw.favorite,
    rewatches: raw.rewatches,
    ratingStory: toNumberOrNull(raw.rating_story),
    ratingPerformance: toNumberOrNull(raw.rating_performance),
    ratingSoundtrack: toNumberOrNull(raw.rating_soundtrack),
    ratingOverall: toNumberOrNull(raw.rating_overall),
    personalRank: raw.personal_rank,
    seasons: raw.seasons.map(mapBackendSeason),
    createdAt: unixSecondsToIso(raw.created_at),
    updatedAt: unixSecondsToIso(raw.updated_at),
  };
}

async function handle<T>(response: Response, action: string): Promise<T> {
  if (!response.ok) {
    const message = await response.text();
    throw new Error(`Failed to ${action}: ${response.status} ${message}`);
  }
  return response.json();
}

export async function fetchAnime(): Promise<Anime[]> {
  const all: BackendAnime[] = [];
  let skip = 0;
  while (true) {
    const response = await fetch(
      `/api/anime/list?skip=${skip}&limit=${SHOWS_PAGE_SIZE}`,
      { credentials: "include" },
    );
    const page = await handle<BackendAnime[]>(response, "fetch anime");
    all.push(...page);
    if (page.length < SHOWS_PAGE_SIZE) break;
    skip += SHOWS_PAGE_SIZE;
  }
  return all.map(mapBackendAnime);
}

export async function getAnime(id: string): Promise<Anime> {
  const response = await fetch(`/api/anime/get/${id}`, {
    credentials: "include",
  });
  const raw = await handle<BackendAnime>(response, `fetch anime ${id}`);
  return mapBackendAnime(raw);
}

export interface SeasonInput {
  seasonNumber: number;
  name?: string | null;
  episodeCount?: number | null;
  airDate?: string | null;
  posterUrl?: string | null;
}

function seasonInputToBody(input: SeasonInput): Record<string, unknown> {
  return {
    season_number: input.seasonNumber,
    name: input.name ?? null,
    episode_count: input.episodeCount ?? null,
    air_date: input.airDate ?? null,
    poster_url: input.posterUrl ?? null,
  };
}

export interface AnimeInput {
  title: string;
  description?: string | null;
  firstAirDate?: string | null;
  episodeRuntimeMinutes?: number | null;
  studios?: string[];
  countries?: string[];
  languages?: string[];
  genres?: string[];
  tags?: string[];
  features?: string[];
  ageRating?: string | null;
  anilistScore?: number | null;
  malScore?: number | null;
  source?: string | null;
  posterUrl?: string | null;
  status?: AnimeStatus;
  priority?: string | null;
  favorite?: boolean;
  rewatches?: number;
  ratingStory?: number | null;
  ratingPerformance?: number | null;
  ratingSoundtrack?: number | null;
  ratingOverall?: number | null;
  personalRank?: number | null;
  // omitted entirely (not just an empty array) means "auto-create a
  // default Season 1" — see create_anime on the backend
  seasons?: SeasonInput[];
}

// Round-trips a loaded Anime back into AnimeInput shape — used when a
// caller needs to change one field (e.g. toggling favorite from the
// detail page) without reopening the full edit form, since updateAnime
// always sends every field rather than a true partial patch.
export function animeToInput(show: Anime): AnimeInput {
  return {
    title: show.title,
    description: show.description,
    firstAirDate: show.firstAirDate,
    episodeRuntimeMinutes: show.episodeRuntimeMinutes,
    studios: show.studios,
    countries: show.countries,
    languages: show.languages,
    genres: show.genres,
    tags: show.tags,
    features: show.features,
    ageRating: show.ageRating,
    anilistScore: show.anilistScore,
    malScore: show.malScore,
    source: show.source,
    posterUrl: show.posterUrl,
    status: show.status,
    priority: show.priority,
    favorite: show.favorite,
    rewatches: show.rewatches,
    ratingStory: show.ratingStory,
    ratingPerformance: show.ratingPerformance,
    ratingSoundtrack: show.ratingSoundtrack,
    ratingOverall: show.ratingOverall,
    personalRank: show.personalRank,
  };
}

function inputToBody(input: AnimeInput): Record<string, unknown> {
  const body: Record<string, unknown> = {
    title: input.title,
    description: input.description ?? null,
    first_air_date: input.firstAirDate ?? null,
    episode_runtime_minutes: input.episodeRuntimeMinutes ?? null,
    studios: input.studios ?? [],
    countries: input.countries ?? [],
    languages: input.languages ?? [],
    genres: input.genres ?? [],
    tags: input.tags ?? [],
    features: input.features ?? [],
    age_rating: input.ageRating ?? null,
    anilist_score: input.anilistScore ?? null,
    mal_score: input.malScore ?? null,
    source: input.source ?? null,
    poster_url: input.posterUrl ?? null,
    priority: input.priority ?? null,
    favorite: input.favorite ?? false,
    rewatches: input.rewatches ?? 0,
    rating_story: input.ratingStory ?? null,
    rating_performance: input.ratingPerformance ?? null,
    rating_soundtrack: input.ratingSoundtrack ?? null,
    rating_overall: input.ratingOverall ?? null,
    personal_rank: input.personalRank ?? null,
  };
  if (input.status) body.status = denormalizeStatus(input.status);
  if (input.seasons) body.seasons = input.seasons.map(seasonInputToBody);
  return body;
}

export async function createAnime(input: AnimeInput): Promise<Anime> {
  const response = await fetch("/api/anime/create", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(inputToBody(input)),
  });
  const raw = await handle<BackendAnime>(response, "create anime");
  return mapBackendAnime(raw);
}

export async function updateAnime(
  id: string,
  input: AnimeInput,
): Promise<Anime> {
  const response = await fetch(`/api/anime/update/${id}`, {
    method: "PATCH",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(inputToBody(input)),
  });
  const raw = await handle<BackendAnime>(response, `update anime ${id}`);
  return mapBackendAnime(raw);
}

export async function deleteAnime(id: string): Promise<void> {
  const response = await fetch(`/api/anime/delete/${id}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!response.ok && response.status !== 204) {
    throw new Error(`Failed to delete anime ${id}: ${response.status}`);
  }
}

export async function createSeason(
  showId: string,
  input: SeasonInput,
): Promise<Anime> {
  const response = await fetch(`/api/anime/${showId}/seasons`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(seasonInputToBody(input)),
  });
  const raw = await handle<BackendAnime>(response, "create season");
  return mapBackendAnime(raw);
}

export interface SeasonUpdateInput {
  seasonNumber?: number;
  name?: string | null;
  episodeCount?: number | null;
  episodesWatched?: number;
  airDate?: string | null;
  posterUrl?: string | null;
  status?: AnimeStatus;
}

export async function updateSeason(
  showId: string,
  seasonId: string,
  input: SeasonUpdateInput,
): Promise<Anime> {
  const body: Record<string, unknown> = {};
  if ("seasonNumber" in input) body.season_number = input.seasonNumber;
  if ("name" in input) body.name = input.name;
  if ("episodeCount" in input) body.episode_count = input.episodeCount;
  if ("episodesWatched" in input) body.episodes_watched = input.episodesWatched;
  if ("airDate" in input) body.air_date = input.airDate;
  if ("posterUrl" in input) body.poster_url = input.posterUrl;
  if (input.status) body.status = denormalizeStatus(input.status);

  const response = await fetch(`/api/anime/${showId}/seasons/${seasonId}`, {
    method: "PATCH",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const raw = await handle<BackendAnime>(response, "update season");
  return mapBackendAnime(raw);
}

export async function deleteSeason(
  showId: string,
  seasonId: string,
): Promise<Anime> {
  const response = await fetch(`/api/anime/${showId}/seasons/${seasonId}`, {
    method: "DELETE",
    credentials: "include",
  });
  const raw = await handle<BackendAnime>(response, "delete season");
  return mapBackendAnime(raw);
}

// A raw metadata search result, straight from whichever provider
// (AniList or MyAnimeList) found it — already snake_case-to-camelCase
// mapped here since these never round-trip back to the backend the way
// BackendAnime does. No `seasons` field: unlike TMDB for TV, neither
// AniList nor Jikan returns a season breakdown, so a new anime always
// gets the backend's auto-created default season instead.
export interface AnimeMetadataResult {
  provider: string;
  providerId: string;
  title: string;
  description: string | null;
  firstAirDate: string | null;
  episodeRuntimeMinutes: number | null;
  episodeCount: number | null;
  studios: string[];
  countries: string[];
  genres: string[];
  posterUrl: string | null;
  anilistScore: number | null;
  malScore: number | null;
  url: string | null;
}

export interface AnimeMetadataSearchResponse {
  query: string;
  providers: string[];
  providerErrors: string[];
  results: AnimeMetadataResult[];
}

interface BackendAnimeMetadataResult {
  provider: string;
  provider_id: string;
  title: string;
  description: string | null;
  first_air_date: string | null;
  episode_runtime_minutes: number | null;
  episode_count: number | null;
  studios: string[];
  countries: string[];
  genres: string[];
  poster_url: string | null;
  anilist_score: number | string | null;
  mal_score: number | string | null;
  url: string | null;
}

interface BackendAnimeMetadataSearchResponse {
  query: string;
  providers: string[];
  provider_errors: string[];
  results: BackendAnimeMetadataResult[];
}

export async function searchAnimeMetadata(
  query: string,
  limit = 8,
): Promise<AnimeMetadataSearchResponse> {
  const params = new URLSearchParams({ query, limit: String(limit) });
  const response = await fetch(`/api/anime/metadata/search?${params}`, {
    credentials: "include",
  });
  const raw = await handle<BackendAnimeMetadataSearchResponse>(
    response,
    "search anime metadata",
  );
  return {
    query: raw.query,
    providers: raw.providers,
    providerErrors: raw.provider_errors,
    results: raw.results.map((r) => ({
      provider: r.provider,
      providerId: r.provider_id,
      title: r.title,
      description: r.description,
      firstAirDate: r.first_air_date,
      episodeRuntimeMinutes: r.episode_runtime_minutes,
      episodeCount: r.episode_count,
      studios: r.studios,
      countries: r.countries,
      genres: r.genres,
      posterUrl: r.poster_url,
      anilistScore: toNumberOrNull(r.anilist_score),
      malScore: toNumberOrNull(r.mal_score),
      url: r.url,
    })),
  };
}
