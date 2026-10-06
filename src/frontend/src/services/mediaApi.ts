// The calls every kind of media library makes the same way: one page of the
// list, the whole list, one title, create, update, delete, and the trash (see
// it, restore from it, empty it for good). Movies, TV shows and anime each
// plug in where their URLs live, how a raw backend record becomes theirs, and
// how their form values become a request body. Everything specific to one
// kind (seasons, episodes, metadata search, relations) stays in its service.
import { failedRequest } from "./apiError";
import type { EntityCache } from "../utils/entityCache";
import type { PaginatedResponse } from "../types/pagination";
import type { LibraryFilters } from "../utils/libraryFilters";

export async function handle<T>(
  response: Response,
  action: string,
): Promise<T> {
  if (!response.ok) {
    console.warn(`Failed to ${action}: ${response.status}`);
    throw await failedRequest(response);
  }
  return response.json();
}

// Pydantic can serialize a Decimal as either a JSON number or a string
// depending on config, handle both rather than assume one
export function toNumberOrNull(value: number | string | null): number | null {
  return value === null ? null : Number(value);
}

export function unixSecondsToIso(seconds: number): string {
  return new Date(seconds * 1000).toISOString();
}

export interface TrashedMedia {
  id: string;
  title: string;
  deleted_at: number;
}

export interface MediaPage<T> {
  items: T[];
  total: number;
  offset: number;
  limit: number;
  statusCounts: Record<string, number>;
  scoreRanks: Record<string, number>;
}

export function createMediaApi<
  Raw,
  Entity extends { id: string },
  Input,
>(options: {
  // "/api/movie", "/api/tv" or "/api/anime"
  base: string;
  // for error messages: "movie" and "movies"
  noun: string;
  plural: string;
  cache: EntityCache<Entity>;
  // turns a backend record into the entity and remembers it in the cache
  map: (raw: Raw) => Entity;
  toBody: (input: Input) => Record<string, unknown>;
}) {
  const { base, noun, plural, cache, map, toBody } = options;

  async function fetchPage(
    offset = 0,
    limit = 100,
    search: string | LibraryFilters = "",
  ): Promise<MediaPage<Entity>> {
    const params = new URLSearchParams({
      skip: String(offset),
      limit: String(limit),
    });
    const filters = typeof search === "string" ? null : search;
    const searchText = typeof search === "string" ? search : search.search;
    if (searchText.trim()) params.set("search", searchText.trim());
    if (filters?.onlyFavorites) params.set("favorite", "true");
    if (filters?.onlyUnrated) params.set("only_unrated", "true");
    if (filters?.onlyWithNote) params.set("only_with_note", "true");
    if (filters?.minScore !== null && filters?.minScore !== undefined)
      params.set("min_score", String(filters.minScore));
    if (filters?.yearFrom.trim())
      params.set("year_from", filters.yearFrom.trim());
    if (filters?.yearTo.trim()) params.set("year_to", filters.yearTo.trim());
    filters?.genres.forEach((genre) => params.append("genre", genre));
    if (filters?.genreMatchAll) params.set("genre_match_all", "true");
    filters?.formats.forEach((format) => params.append("format", format));
    if (filters?.statusBucket && filters.statusBucket !== "all")
      params.set("status_bucket", filters.statusBucket);
    const response = await fetch(`${base}/list?${params}`, {
      credentials: "include",
    });
    const page = await handle<PaginatedResponse<Raw>>(
      response,
      `fetch ${plural}`,
    );
    return {
      items: page.items.map(map),
      total: page.total,
      offset: page.offset,
      limit: page.limit,
      statusCounts: page.status_counts,
      scoreRanks: page.score_ranks ?? {},
    };
  }

  async function fetchAll(search = ""): Promise<Entity[]> {
    const all: Entity[] = [];
    let offset = 0;
    const limit = 100;
    while (true) {
      const page = await fetchPage(offset, limit, search);
      all.push(...page.items);
      if (all.length >= page.total || page.items.length === 0) break;
      offset += page.items.length;
    }
    cache.markListLoaded();
    return all;
  }

  async function get(id: string): Promise<Entity> {
    const response = await fetch(`${base}/get/${id}`, {
      credentials: "include",
    });
    return map(await handle<Raw>(response, `fetch ${noun} ${id}`));
  }

  async function create(input: Input): Promise<Entity> {
    const response = await fetch(`${base}/create`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(toBody(input)),
    });
    return map(await handle<Raw>(response, `create ${noun}`));
  }

  async function update(id: string, input: Input): Promise<Entity> {
    const response = await fetch(`${base}/update/${id}`, {
      method: "PATCH",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(toBody(input)),
    });
    return map(await handle<Raw>(response, `update ${noun} ${id}`));
  }

  async function remove(id: string): Promise<void> {
    cache.remove(id);
    const response = await fetch(`${base}/delete/${id}`, {
      method: "DELETE",
      credentials: "include",
    });
    if (!response.ok && response.status !== 204) {
      throw new Error(`Failed to delete ${noun} ${id}: ${response.status}`);
    }
  }

  async function fetchTrash(): Promise<TrashedMedia[]> {
    const response = await fetch(`${base}/trash`, { credentials: "include" });
    if (!response.ok) {
      throw new Error(`Failed to fetch deleted ${plural}: ${response.status}`);
    }
    return await response.json();
  }

  async function restore(id: string): Promise<Entity> {
    const response = await fetch(`${base}/${id}/restore`, {
      method: "POST",
      credentials: "include",
    });
    if (!response.ok) {
      throw new Error(`Failed to restore ${noun} ${id}: ${response.status}`);
    }
    return map(await response.json());
  }

  async function purge(id: string): Promise<void> {
    const response = await fetch(`${base}/${id}/purge`, {
      method: "DELETE",
      credentials: "include",
    });
    if (!response.ok && response.status !== 204) {
      throw new Error(`Failed to purge ${noun} ${id}: ${response.status}`);
    }
  }

  return {
    fetchPage,
    fetchAll,
    get,
    create,
    update,
    remove,
    fetchTrash,
    restore,
    purge,
  };
}
