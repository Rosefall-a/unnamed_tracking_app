// Cross-media-type features — rewatch history, custom lists, the
// activity feed, and the airing calendar — all span movies/TV/anime,
// so this is one shared service file rather than duplicated three ways.

export type MediaType = "movie" | "tv" | "anime";

async function handle<T>(response: Response, action: string): Promise<T> {
  if (!response.ok) {
    const message = await response.text();
    throw new Error(`Failed to ${action}: ${response.status} ${message}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

export interface Rewatch {
  id: string;
  mediaType: MediaType;
  mediaId: string;
  finishedOn: string;
  note: string | null;
  createdAt: number;
}

interface BackendRewatch {
  id: string;
  media_type: MediaType;
  media_id: string;
  finished_on: string;
  note: string | null;
  created_at: number;
}

function mapRewatch(r: BackendRewatch): Rewatch {
  return {
    id: r.id,
    mediaType: r.media_type,
    mediaId: r.media_id,
    finishedOn: r.finished_on,
    note: r.note,
    createdAt: r.created_at,
  };
}

export async function fetchRewatches(
  mediaType: MediaType,
  mediaId: string,
): Promise<Rewatch[]> {
  const params = new URLSearchParams({
    media_type: mediaType,
    media_id: mediaId,
  });
  const response = await fetch(`/api/rewatches?${params}`, {
    credentials: "include",
  });
  const raw = await handle<BackendRewatch[]>(response, "load rewatch history");
  return raw.map(mapRewatch);
}

export async function addRewatch(
  mediaType: MediaType,
  mediaId: string,
  finishedOn?: string,
  note?: string | null,
): Promise<Rewatch> {
  const response = await fetch("/api/rewatches", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      media_type: mediaType,
      media_id: mediaId,
      finished_on: finishedOn ?? null,
      note: note ?? null,
    }),
  });
  const raw = await handle<BackendRewatch>(response, "log rewatch");
  return mapRewatch(raw);
}

export async function deleteRewatch(rewatchId: string): Promise<void> {
  const response = await fetch(`/api/rewatches/${rewatchId}`, {
    method: "DELETE",
    credentials: "include",
  });
  await handle<void>(response, "delete rewatch");
}

// A smart list's saved filter — every field that is set must match.
// Evaluated against the whole library by the backend on every read.
export interface SmartRule {
  mediaTypes?: MediaType[];
  // Plan / Hold / Watching / Completed / Dropped, same buckets as the
  // rest of the media UI (utils/mediaStatus.ts)
  statusBuckets?: string[];
  genre?: string;
  minScore?: number;
  favorite?: boolean;
}

export interface MediaListSummary {
  id: string;
  name: string;
  description: string | null;
  itemCount: number;
  isSmart: boolean;
  // kept by the app (Favorites): can't be renamed, re-ruled or deleted
  isSystem: boolean;
  // pinned lists sit first; position is the user's own order
  pinned: boolean;
  position: number;
  // titles per type, so the overview can filter lists by what they hold
  typeCounts: Partial<Record<MediaType, number>>;
  smartRule: SmartRule | null;
  coverMediaId: string | null;
  // up to 4 posters (cover first) so the overview grid needs no
  // per-list detail request
  previewPosters: (string | null)[];
  createdAt: number;
  updatedAt: number;
}

export interface MediaListItemVM {
  id: string;
  mediaType: MediaType;
  mediaId: string;
  title: string;
  posterUrl: string | null;
  status: string;
  addedAt: number;
}

export interface MediaListDetail extends MediaListSummary {
  items: MediaListItemVM[];
}

interface BackendSmartRule {
  media_types?: MediaType[] | null;
  status_buckets?: string[] | null;
  genre?: string | null;
  min_score?: number | null;
  favorite?: boolean | null;
}

interface BackendMediaListSummary {
  id: string;
  name: string;
  description: string | null;
  item_count: number;
  is_smart: boolean;
  is_system?: boolean;
  pinned?: boolean;
  position?: number;
  type_counts?: Partial<Record<MediaType, number>>;
  smart_rule: BackendSmartRule | null;
  cover_media_id: string | null;
  preview_posters: (string | null)[];
  created_at: number;
  updated_at: number;
}

function mapSmartRule(r: BackendSmartRule | null): SmartRule | null {
  if (!r) return null;
  const rule: SmartRule = {};
  if (r.media_types?.length) rule.mediaTypes = r.media_types;
  if (r.status_buckets?.length) rule.statusBuckets = r.status_buckets;
  if (r.genre) rule.genre = r.genre;
  if (r.min_score != null) rule.minScore = r.min_score;
  if (r.favorite != null) rule.favorite = r.favorite;
  return rule;
}

function smartRuleToBody(
  r: SmartRule | null | undefined,
): BackendSmartRule | null {
  if (!r) return null;
  return {
    media_types: r.mediaTypes?.length ? r.mediaTypes : null,
    status_buckets: r.statusBuckets?.length ? r.statusBuckets : null,
    genre: r.genre?.trim() ? r.genre.trim() : null,
    min_score: r.minScore ?? null,
    favorite: r.favorite ?? null,
  };
}

interface BackendMediaListItem {
  id: string;
  media_type: MediaType;
  media_id: string;
  title: string;
  poster_url: string | null;
  status: string;
  added_at: number;
}

function mapListSummary(l: BackendMediaListSummary): MediaListSummary {
  return {
    id: l.id,
    name: l.name,
    description: l.description,
    itemCount: l.item_count,
    isSmart: l.is_smart,
    isSystem: l.is_system ?? false,
    pinned: l.pinned ?? false,
    position: l.position ?? 0,
    typeCounts: l.type_counts ?? {},
    smartRule: mapSmartRule(l.smart_rule),
    coverMediaId: l.cover_media_id,
    previewPosters: l.preview_posters,
    createdAt: l.created_at,
    updatedAt: l.updated_at,
  };
}

// backend sends "IN_PROGRESS", "WISHLIST", etc., same convention as
// services/anime.ts's/tvShows.ts's/movies.ts's own normalizeStatus
function mapListItem(i: BackendMediaListItem): MediaListItemVM {
  return {
    id: i.id,
    mediaType: i.media_type,
    mediaId: i.media_id,
    title: i.title,
    posterUrl: i.poster_url,
    status: i.status.toLowerCase().replace(/_/g, " "),
    addedAt: i.added_at,
  };
}

export async function fetchMediaLists(): Promise<MediaListSummary[]> {
  const response = await fetch("/api/lists", { credentials: "include" });
  const raw = await handle<BackendMediaListSummary[]>(response, "load lists");
  return raw.map(mapListSummary);
}

export async function createMediaList(
  name: string,
  description?: string | null,
  smartRule?: SmartRule | null,
): Promise<MediaListSummary> {
  const response = await fetch("/api/lists", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name,
      description: description ?? null,
      smart_rule: smartRuleToBody(smartRule),
    }),
  });
  const raw = await handle<BackendMediaListSummary>(response, "create list");
  return mapListSummary(raw);
}

// Saves the user's own order of their lists (first id is shown first).
export async function saveListOrder(listIds: string[]): Promise<void> {
  const response = await fetch("/api/lists/order", {
    method: "PUT",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ list_ids: listIds }),
  });
  if (!response.ok)
    throw new Error(`Failed to save the list order: ${response.status}`);
}

export async function updateMediaList(
  listId: string,
  input: {
    name?: string;
    description?: string | null;
    smartRule?: SmartRule | null;
    coverMediaId?: string | null;
    pinned?: boolean;
  },
): Promise<MediaListSummary> {
  const body: Record<string, unknown> = {};
  if (input.pinned !== undefined) body.pinned = input.pinned;
  if (input.name !== undefined) body.name = input.name;
  if (input.description !== undefined) body.description = input.description;
  if (input.smartRule !== undefined)
    body.smart_rule = smartRuleToBody(input.smartRule);
  if (input.coverMediaId !== undefined)
    body.cover_media_id = input.coverMediaId;
  const response = await fetch(`/api/lists/${listId}`, {
    method: "PATCH",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const raw = await handle<BackendMediaListSummary>(response, "update list");
  return mapListSummary(raw);
}

export async function deleteMediaList(listId: string): Promise<void> {
  const response = await fetch(`/api/lists/${listId}`, {
    method: "DELETE",
    credentials: "include",
  });
  await handle<void>(response, "delete list");
}

export async function fetchMediaListDetail(
  listId: string,
): Promise<MediaListDetail> {
  const response = await fetch(`/api/lists/${listId}`, {
    credentials: "include",
  });
  const raw = await handle<
    BackendMediaListSummary & { items: BackendMediaListItem[] }
  >(response, "load list");
  return { ...mapListSummary(raw), items: raw.items.map(mapListItem) };
}

export async function addToMediaList(
  listId: string,
  mediaType: MediaType,
  mediaId: string,
): Promise<MediaListItemVM> {
  const response = await fetch(`/api/lists/${listId}/items`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ media_type: mediaType, media_id: mediaId }),
  });
  const raw = await handle<BackendMediaListItem>(response, "add to list");
  return mapListItem(raw);
}

// `itemIds` is the full desired sequence of the list's item rows
export async function reorderMediaList(
  listId: string,
  itemIds: string[],
): Promise<void> {
  const response = await fetch(`/api/lists/${listId}/order`, {
    method: "PUT",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ item_ids: itemIds }),
  });
  await handle<void>(response, "save list order");
}

export interface ListMembership {
  listId: string;
  itemId: string;
}

interface BackendListMembership {
  list_id: string;
  item_id: string;
}

export async function fetchListMembership(
  mediaType: MediaType,
  mediaId: string,
): Promise<ListMembership[]> {
  const params = new URLSearchParams({
    media_type: mediaType,
    media_id: mediaId,
  });
  const response = await fetch(`/api/lists/membership?${params}`, {
    credentials: "include",
  });
  const raw = await handle<BackendListMembership[]>(
    response,
    "load list membership",
  );
  return raw.map((m) => ({ listId: m.list_id, itemId: m.item_id }));
}

export async function removeFromMediaList(
  listId: string,
  itemId: string,
): Promise<void> {
  const response = await fetch(`/api/lists/${listId}/items/${itemId}`, {
    method: "DELETE",
    credentials: "include",
  });
  await handle<void>(response, "remove from list");
}

export type ActivityEventType =
  "episodes_watched" | "status_changed" | "rated" | "rewatched";

export interface ActivityEntry {
  id: string;
  mediaType: MediaType;
  mediaId: string;
  mediaTitle: string;
  eventType: ActivityEventType;
  eventDate: string;
  count: number;
  detail: string | null;
}

interface BackendActivityEntry {
  id: string;
  media_type: MediaType;
  media_id: string;
  media_title: string;
  event_type: ActivityEventType;
  event_date: string;
  count: number;
  detail: string | null;
}

function mapActivityEntry(a: BackendActivityEntry): ActivityEntry {
  return {
    id: a.id,
    mediaType: a.media_type,
    mediaId: a.media_id,
    mediaTitle: a.media_title,
    eventType: a.event_type,
    eventDate: a.event_date,
    count: a.count,
    detail: a.detail,
  };
}

export async function fetchActivity(days = 30): Promise<ActivityEntry[]> {
  const response = await fetch(`/api/activity?days=${days}`, {
    credentials: "include",
  });
  const raw = await handle<BackendActivityEntry[]>(response, "load activity");
  return raw.map(mapActivityEntry);
}

export async function createActivityEntry(input: {
  mediaType: MediaType;
  mediaId: string;
  eventType: ActivityEventType;
  eventDate: string;
  count?: number;
  detail?: string | null;
}): Promise<ActivityEntry> {
  const response = await fetch("/api/activity", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      media_type: input.mediaType,
      media_id: input.mediaId,
      event_type: input.eventType,
      event_date: input.eventDate,
      count: input.count ?? 1,
      detail: input.detail ?? null,
    }),
  });
  const raw = await handle<BackendActivityEntry>(
    response,
    "log activity entry",
  );
  return mapActivityEntry(raw);
}

export async function updateActivityEntry(
  id: string,
  input: {
    mediaType?: MediaType;
    mediaId?: string;
    eventType?: ActivityEventType;
    eventDate?: string;
    count?: number;
    detail?: string | null;
  },
): Promise<ActivityEntry> {
  const body: Record<string, unknown> = {};
  if (input.mediaType !== undefined) body.media_type = input.mediaType;
  if (input.mediaId !== undefined) body.media_id = input.mediaId;
  if (input.eventType !== undefined) body.event_type = input.eventType;
  if (input.eventDate !== undefined) body.event_date = input.eventDate;
  if (input.count !== undefined) body.count = input.count;
  if (input.detail !== undefined) body.detail = input.detail;
  const response = await fetch(`/api/activity/${id}`, {
    method: "PATCH",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const raw = await handle<BackendActivityEntry>(
    response,
    "update activity entry",
  );
  return mapActivityEntry(raw);
}

export async function deleteActivityEntry(id: string): Promise<void> {
  const response = await fetch(`/api/activity/${id}`, {
    method: "DELETE",
    credentials: "include",
  });
  await handle<void>(response, "delete activity entry");
}

export interface CalendarEntry {
  // "game" only appears when game releases are switched on in Settings
  mediaType: MediaType | "game";
  mediaId: string;
  title: string;
  posterUrl: string | null;
  nextEpisodeNumber: number | null;
  airAt: number;
  // "episode" = next-airing-episode countdown for something being
  // watched; "release" = an upcoming release/premiere date for
  // something still on Plan to Watch
  kind: "episode" | "release";
  // false only for the one real, provider-confirmed next-episode date —
  // every later episode entry for the same show is a weekly-cadence
  // guess, since no provider hands over a full future schedule
  isProjected: boolean;
}

interface BackendCalendarEntry {
  media_type: MediaType | "game";
  media_id: string;
  title: string;
  poster_url: string | null;
  next_episode_number: number | null;
  air_at: number;
  kind: "episode" | "release";
  is_projected: boolean;
}

export async function fetchCalendar(days = 14): Promise<CalendarEntry[]> {
  const response = await fetch(`/api/calendar?days=${days}`, {
    credentials: "include",
  });
  const raw = await handle<BackendCalendarEntry[]>(response, "load calendar");
  return raw.map((c) => ({
    mediaType: c.media_type,
    mediaId: c.media_id,
    title: c.title,
    posterUrl: c.poster_url,
    nextEpisodeNumber: c.next_episode_number,
    airAt: c.air_at,
    kind: c.kind,
    isProjected: c.is_projected,
  }));
}

// The secret .ics feed URL for this user — created on first ask, and
// replaceable if it ever leaks. Calendar apps can't send a login cookie,
// so the URL itself is the credential.
export async function fetchCalendarFeedUrl(
  regenerate = false,
): Promise<string> {
  const response = await fetch(
    regenerate
      ? "/api/calendar/feed-token/regenerate"
      : "/api/calendar/feed-token",
    { method: regenerate ? "POST" : "GET", credentials: "include" },
  );
  const raw = await handle<{ path: string }>(
    response,
    "load the calendar feed link",
  );
  return `${window.location.origin}${raw.path}`;
}

// The past side of Games on the calendar: release dates (Settings > Game
// releases), and the day a game was finished or bought and how many
// achievements were unlocked on a day (Settings > Games history).
export interface CalendarGameEntry {
  kind:
    "game_released" | "game_finished" | "game_achievements" | "game_purchased";
  gameId: string;
  title: string;
  date: string;
  count: number;
  posterUrl: string | null;
}

export async function fetchCalendarGames(): Promise<CalendarGameEntry[]> {
  const response = await fetch("/api/calendar/games", {
    credentials: "include",
  });
  const raw = await handle<
    {
      kind: CalendarGameEntry["kind"];
      game_id: string;
      title: string;
      date: string;
      count: number;
      poster_url?: string | null;
    }[]
  >(response, "load games history");
  return raw.map((g) => ({
    kind: g.kind,
    gameId: g.game_id,
    title: g.title,
    date: g.date,
    count: g.count,
    posterUrl: g.poster_url ?? null,
  }));
}

// Entries the user put on the calendar by hand.
export interface CalendarEventEntry {
  id: string;
  title: string;
  eventDate: string; // YYYY-MM-DD
  eventTime: string | null; // HH:MM, or null for all day
  note: string | null;
  mediaType: MediaType | "game" | null;
  mediaId: string | null;
}
export interface CalendarEventInput {
  title: string;
  eventDate: string;
  eventTime: string | null;
  note: string | null;
  mediaType: MediaType | "game" | null;
  mediaId: string | null;
}
interface BackendCalendarEvent {
  id: string;
  title: string;
  event_date: string;
  event_time: string | null;
  note: string | null;
  media_type: MediaType | "game" | null;
  media_id: string | null;
}
function mapCalendarEvent(e: BackendCalendarEvent): CalendarEventEntry {
  return {
    id: e.id,
    title: e.title,
    eventDate: e.event_date,
    eventTime: e.event_time,
    note: e.note,
    mediaType: e.media_type,
    mediaId: e.media_id,
  };
}
function eventBody(input: CalendarEventInput) {
  return {
    title: input.title,
    event_date: input.eventDate,
    event_time: input.eventTime || null,
    note: input.note || null,
    media_type: input.mediaType,
    media_id: input.mediaId,
  };
}
export async function fetchCalendarEvents(): Promise<CalendarEventEntry[]> {
  const response = await fetch("/api/calendar/events", {
    credentials: "include",
  });
  const raw = await handle<BackendCalendarEvent[]>(
    response,
    "load calendar entries",
  );
  return raw.map(mapCalendarEvent);
}
export async function createCalendarEvent(
  input: CalendarEventInput,
): Promise<CalendarEventEntry> {
  const response = await fetch("/api/calendar/events", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(eventBody(input)),
  });
  return mapCalendarEvent(
    await handle<BackendCalendarEvent>(response, "add the calendar entry"),
  );
}
export async function updateCalendarEvent(
  id: string,
  input: CalendarEventInput,
): Promise<CalendarEventEntry> {
  const response = await fetch(`/api/calendar/events/${id}`, {
    method: "PATCH",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(eventBody(input)),
  });
  return mapCalendarEvent(
    await handle<BackendCalendarEvent>(response, "save the calendar entry"),
  );
}
export async function deleteCalendarEvent(id: string): Promise<void> {
  const response = await fetch(`/api/calendar/events/${id}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!response.ok)
    throw new Error(`Failed to delete the calendar entry: ${response.status}`);
}
