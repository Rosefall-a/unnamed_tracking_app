<script setup lang="ts">
// A real month-grid calendar with three layers (episode airings, upcoming
// Plan to Watch releases, and what you actually watched), an agenda view
// for "what's next", and History folded in as a second tab. Grid cells hold
// small poster thumbnails instead of title text: text is what stretched
// the columns and warped the grid, and a library with dozens of airing
// shows can't fit names in a cell anyway. Names live in the hover tooltip
// and the day drawer that opens on click.
import { ref, reactive, computed, onMounted, watch } from "vue";
import { useRouter } from "vue-router";
import {
  fetchCalendar,
  fetchActivity,
  fetchCalendarFeedUrl,
  createActivityEntry,
  updateActivityEntry,
  deleteActivityEntry,
} from "../services/mediaExtras";
import type { ActivityEventType, CalendarEntry, ActivityEntry, MediaType } from "../services/mediaExtras";
import MediaTopBar from "../components/MediaTopBar.vue";
import { fetchMovies } from "../services/movies";
import { fetchTVShows } from "../services/tvShows";
import { fetchAnime } from "../services/anime";

const router = useRouter();
const tab = ref<"calendar" | "history">("calendar");
const calView = ref<"month" | "agenda">("month");

// ---- shared library lookup (posters for watched chips + title picker) ----
interface PickableMedia {
  mediaType: MediaType;
  mediaId: string;
  title: string;
  posterUrl: string | null;
}
const manualLibrary = ref<PickableMedia[]>([]);
const manualLibraryLoaded = ref(false);
const posterByMedia = computed(() => {
  const map = new Map<string, string | null>();
  for (const m of manualLibrary.value) map.set(`${m.mediaType}-${m.mediaId}`, m.posterUrl);
  return map;
});
async function loadManualLibrary() {
  if (manualLibraryLoaded.value) return;
  const [movies, shows, anime] = await Promise.all([fetchMovies(), fetchTVShows(), fetchAnime()]);
  manualLibrary.value = [
    ...movies.map((m) => ({ mediaType: "movie" as const, mediaId: m.id, title: m.title, posterUrl: m.posterUrl })),
    ...shows.map((s) => ({ mediaType: "tv" as const, mediaId: s.id, title: s.title, posterUrl: s.posterUrl })),
    ...anime.map((a) => ({ mediaType: "anime" as const, mediaId: a.id, title: a.title, posterUrl: a.posterUrl })),
  ];
  manualLibraryLoaded.value = true;
}

// ---- filters (remembered between visits) ----
const FILTER_KEY = "calendar-filters-v1";
const filters = reactive({
  movie: true,
  tv: true,
  anime: true,
  episode: true,
  release: true,
  watched: true,
  estimated: true,
});
try {
  const saved = JSON.parse(localStorage.getItem(FILTER_KEY) ?? "null");
  if (saved && typeof saved === "object") {
    for (const k of Object.keys(filters) as (keyof typeof filters)[]) {
      if (typeof saved[k] === "boolean") filters[k] = saved[k];
    }
  }
} catch {
  /* storage unavailable: defaults are fine */
}
watch(filters, () => {
  try {
    localStorage.setItem(FILTER_KEY, JSON.stringify(filters));
  } catch {
    /* ignore */
  }
});

// ---- calendar data ----
const entries = ref<CalendarEntry[]>([]);
const calLoading = ref(true);
const calError = ref<string | null>(null);

const today = new Date();
today.setHours(0, 0, 0, 0);
const viewYear = ref(today.getFullYear());
const viewMonth = ref(today.getMonth()); // 0-11

const isCurrentMonth = computed(
  () => viewYear.value === today.getFullYear() && viewMonth.value === today.getMonth(),
);
const CAL_MAX_DAYS = 90;
const monthsBack = computed(
  () => (today.getFullYear() - viewYear.value) * 12 + today.getMonth() - viewMonth.value,
);
const canGoPrev = computed(() => monthsBack.value < 12);
const canGoNext = computed(() => {
  const firstOfNext = new Date(viewYear.value, viewMonth.value + 1, 1);
  return firstOfNext.getTime() - today.getTime() < CAL_MAX_DAYS * 86_400_000;
});

async function loadCalendar() {
  calLoading.value = true;
  calError.value = null;
  try {
    // The backend only looks forward from today, so a wide window is
    // enough for every month the nav allows; past cells get their content
    // from the watched layer instead.
    entries.value = await fetchCalendar(CAL_MAX_DAYS);
  } catch (e) {
    calError.value = e instanceof Error ? e.message : "Failed to load the calendar.";
  } finally {
    calLoading.value = false;
  }
}

// ---- history data (also feeds the calendar's "watched" layer) ----
const historyEntries = ref<ActivityEntry[]>([]);
const historyLoading = ref(false);
const historyError = ref<string | null>(null);

async function loadHistory() {
  historyLoading.value = true;
  historyError.value = null;
  try {
    historyEntries.value = await fetchActivity(365);
  } catch (e) {
    historyError.value = e instanceof Error ? e.message : "Failed to load history.";
  } finally {
    historyLoading.value = false;
  }
}
async function refreshAll() {
  await Promise.all([loadCalendar(), loadHistory()]);
}
onMounted(() => {
  refreshAll();
  loadManualLibrary();
});

// ---- unify everything the grid/agenda draws ----
type Layer = "episode" | "release" | "watched";
interface CalItem {
  key: string;
  layer: Layer;
  mediaType: MediaType;
  mediaId: string;
  title: string;
  posterUrl: string | null;
  badge: string; // short text on the thumbnail: "12", "×3", ""
  detail: string; // longer line for tooltip/drawer
  projected: boolean;
  sortAt: number;
  dayKey: string;
}

function keyOfDate(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
function timeLabel(airAt: number): string {
  return new Date(airAt * 1000).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

function fromEntry(e: CalendarEntry): CalItem {
  const layer: Layer = e.kind === "release" ? "release" : "episode";
  const ep = e.nextEpisodeNumber ? `Episode ${e.nextEpisodeNumber}` : "";
  // a release/premiere date has no real time-of-day (see _date_to_unix's
  // noon-UTC encoding, a placeholder to keep the date right across
  // timezones, not an actual airing time)
  const when = layer === "release" ? "Release date" : timeLabel(e.airAt);
  const estimate = e.isProjected ? "estimated" : "";
  return {
    key: `${e.mediaType}-${e.mediaId}-${e.kind}-${e.nextEpisodeNumber ?? 0}`,
    layer,
    mediaType: e.mediaType,
    mediaId: e.mediaId,
    title: e.title,
    posterUrl: e.posterUrl,
    badge: e.nextEpisodeNumber ? String(e.nextEpisodeNumber) : "",
    detail: [ep, when, estimate].filter(Boolean).join(" · "),
    projected: e.isProjected,
    sortAt: e.airAt,
    dayKey: keyOfDate(new Date(e.airAt * 1000)),
  };
}
function fromActivity(a: ActivityEntry): CalItem | null {
  if (a.eventType !== "episodes_watched" && a.eventType !== "rewatched") return null;
  const isRewatch = a.eventType === "rewatched";
  return {
    key: `watched-${a.id}`,
    layer: "watched",
    mediaType: a.mediaType,
    mediaId: a.mediaId,
    title: a.mediaTitle,
    posterUrl: posterByMedia.value.get(`${a.mediaType}-${a.mediaId}`) ?? null,
    badge: isRewatch ? "↻" : a.count > 1 ? `×${a.count}` : "",
    detail: isRewatch
      ? "Rewatched"
      : `Watched ${a.count} episode${a.count === 1 ? "" : "s"}`,
    projected: false,
    sortAt: new Date(`${a.eventDate}T12:00:00`).getTime() / 1000,
    dayKey: a.eventDate,
  };
}

const allItems = computed<CalItem[]>(() => {
  const items = entries.value.map(fromEntry);
  for (const a of historyEntries.value) {
    const item = fromActivity(a);
    if (item) items.push(item);
  }
  return items;
});
const visibleItems = computed(() =>
  allItems.value.filter((i) => {
    if (!filters[i.mediaType] || !filters[i.layer]) return false;
    if (i.projected && !filters.estimated) return false;
    return true;
  }),
);
const itemsByDay = computed(() => {
  const map = new Map<string, CalItem[]>();
  for (const i of visibleItems.value) {
    const list = map.get(i.dayKey);
    if (list) list.push(i);
    else map.set(i.dayKey, [i]);
  }
  for (const list of map.values()) list.sort((a, b) => a.sortAt - b.sortAt);
  return map;
});

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];
const WEEKDAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

interface DayCell {
  day: number;
  inMonth: boolean;
  key: string;
  isToday: boolean;
  isPast: boolean;
  items: CalItem[];
}

const todayKey = keyOfDate(today);
const gridCells = computed<DayCell[]>(() => {
  const y = viewYear.value;
  const m = viewMonth.value;
  const firstWeekday = new Date(y, m, 1).getDay();
  const daysInMonth = new Date(y, m + 1, 0).getDate();
  // Always a full 6 rows would leave a blank final week most months, so
  // pad only to the end of the week the month actually reaches.
  const total = Math.ceil((firstWeekday + daysInMonth) / 7) * 7;
  const cells: DayCell[] = [];
  for (let i = 0; i < total; i++) {
    const d = new Date(y, m, 1 - firstWeekday + i);
    const key = keyOfDate(d);
    cells.push({
      day: d.getDate(),
      inMonth: d.getMonth() === m,
      key,
      isToday: key === todayKey,
      isPast: key < todayKey,
      items: itemsByDay.value.get(key) ?? [],
    });
  }
  return cells;
});

function prevMonth() {
  if (!canGoPrev.value) return;
  if (viewMonth.value === 0) {
    viewMonth.value = 11;
    viewYear.value -= 1;
  } else {
    viewMonth.value -= 1;
  }
}
function nextMonth() {
  if (!canGoNext.value) return;
  if (viewMonth.value === 11) {
    viewMonth.value = 0;
    viewYear.value += 1;
  } else {
    viewMonth.value += 1;
  }
}
function goToday() {
  viewYear.value = today.getFullYear();
  viewMonth.value = today.getMonth();
}

// Grid chips: up to 6 slots; past that the last slot becomes "+N"
const CHIP_SLOTS = 6;
function chipsFor(cell: DayCell): { shown: CalItem[]; more: number } {
  if (cell.items.length <= CHIP_SLOTS) return { shown: cell.items, more: 0 };
  return { shown: cell.items.slice(0, CHIP_SLOTS - 1), more: cell.items.length - (CHIP_SLOTS - 1) };
}
function itemTooltip(i: CalItem): string {
  return `${i.title}${i.detail ? ` — ${i.detail}` : ""}`;
}
function openItem(i: { mediaType: MediaType; mediaId: string }) {
  const base = i.mediaType === "movie" ? "/movies" : i.mediaType === "anime" ? "/anime" : "/tv";
  router.push(`${base}/${i.mediaId}`);
}

// ---- agenda: what's coming, day by day ----
const agendaGroups = computed(() => {
  const upcoming = visibleItems.value.filter((i) => i.layer !== "watched" && i.dayKey >= todayKey);
  const map = new Map<string, CalItem[]>();
  for (const i of upcoming) {
    const list = map.get(i.dayKey);
    if (list) list.push(i);
    else map.set(i.dayKey, [i]);
  }
  return [...map.entries()]
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([key, list]) => ({ key, items: list.sort((a, b) => a.sortAt - b.sortAt) }));
});
function longDayLabel(key: string): string {
  const yesterday = keyOfDate(new Date(today.getTime() - 86_400_000));
  const tomorrow = keyOfDate(new Date(today.getTime() + 86_400_000));
  const base = new Date(`${key}T00:00:00`).toLocaleDateString(undefined, {
    weekday: "long", month: "short", day: "numeric",
  });
  if (key === todayKey) return `Today · ${base}`;
  if (key === tomorrow) return `Tomorrow · ${base}`;
  if (key === yesterday) return `Yesterday · ${base}`;
  return base;
}

// ---- day drawer (opens on click, holds the full list for that day) ----
const drawerKey = ref<string | null>(null);
const drawerItems = computed(() => (drawerKey.value ? itemsByDay.value.get(drawerKey.value) ?? [] : []));
function openDrawer(cell: DayCell) {
  drawerKey.value = cell.key;
}
function closeDrawer() {
  drawerKey.value = null;
}
const LAYER_LABEL: Record<Layer, string> = {
  episode: "Airing",
  release: "Release",
  watched: "Watched",
};

// ---- subscribe (iCal feed) ----
const showFeed = ref(false);
const feedUrl = ref("");
const feedError = ref<string | null>(null);
const feedCopied = ref(false);
const feedBusy = ref(false);
async function openFeed() {
  showFeed.value = true;
  feedError.value = null;
  feedCopied.value = false;
  if (feedUrl.value) return;
  try {
    feedUrl.value = await fetchCalendarFeedUrl();
  } catch (e) {
    feedError.value = e instanceof Error ? e.message : "Couldn't load the feed link.";
  }
}
async function copyFeed() {
  try {
    await navigator.clipboard.writeText(feedUrl.value);
    feedCopied.value = true;
    setTimeout(() => (feedCopied.value = false), 1800);
  } catch {
    feedError.value = "Copy failed. Select the link and copy it by hand.";
  }
}
async function regenerateFeed() {
  if (!window.confirm("Make a new link? Anything subscribed to the old one stops updating.")) return;
  feedBusy.value = true;
  try {
    feedUrl.value = await fetchCalendarFeedUrl(true);
    feedCopied.value = false;
  } catch (e) {
    feedError.value = e instanceof Error ? e.message : "Couldn't make a new link.";
  } finally {
    feedBusy.value = false;
  }
}

// ---- history (folded in as a second tab) ----
const historySearch = ref("");
const historyType = ref<"all" | ActivityEventType>("all");
const historyWindowDays = ref(60);

function historyDayLabel(key: string): string {
  return longDayLabel(key);
}
function describeActivity(e: ActivityEntry): string {
  switch (e.eventType) {
    case "episodes_watched":
      return `Watched ${e.count} episode${e.count === 1 ? "" : "s"} of ${e.mediaTitle}`;
    case "status_changed":
      return `${e.mediaTitle}${e.detail ? ` — ${e.detail}` : " status changed"}`;
    case "rewatched":
      return `Rewatched ${e.mediaTitle}${e.count > 1 ? ` (${e.count} times)` : ""}`;
    case "rated":
      return `Rated ${e.mediaTitle}`;
    default:
      return e.mediaTitle;
  }
}
const HISTORY_ICONS: Record<ActivityEntry["eventType"], string> = {
  episodes_watched: "▶",
  status_changed: "↻",
  rewatched: "⟲",
  rated: "★",
};
const filteredHistory = computed(() => {
  const q = historySearch.value.trim().toLowerCase();
  return historyEntries.value.filter((e) => {
    if (historyType.value !== "all" && e.eventType !== historyType.value) return false;
    if (q && !e.mediaTitle.toLowerCase().includes(q)) return false;
    return true;
  });
});
const historyCutoff = computed(() =>
  keyOfDate(new Date(today.getTime() - historyWindowDays.value * 86_400_000)),
);
const groupedHistory = computed(() => {
  const map = new Map<string, ActivityEntry[]>();
  for (const e of filteredHistory.value) {
    if (e.eventDate < historyCutoff.value) continue;
    const list = map.get(e.eventDate);
    if (list) list.push(e);
    else map.set(e.eventDate, [e]);
  }
  return [...map.entries()].sort((a, b) => b[0].localeCompare(a[0]));
});
const hasOlderHistory = computed(() =>
  filteredHistory.value.some((e) => e.eventDate < historyCutoff.value),
);
function openHistoryEntry(e: ActivityEntry) {
  openItem(e);
}

// ---- editing a history entry: every field, including which title and
// event type it's attached to ----
const editingId = ref<string | null>(null);
const editDate = ref("");
const editCount = ref(1);
const editDetail = ref("");
const editEventType = ref<ActivityEventType>("episodes_watched");
const editMediaSearch = ref("");
const editMediaPicked = ref<PickableMedia | null>(null);
const editChangingMedia = ref(false);
const editError = ref<string | null>(null);

function startEdit(e: ActivityEntry) {
  editingId.value = e.id;
  editDate.value = e.eventDate;
  editCount.value = e.count;
  editDetail.value = e.detail ?? "";
  editEventType.value = e.eventType;
  editMediaPicked.value = {
    mediaType: e.mediaType,
    mediaId: e.mediaId,
    title: e.mediaTitle,
    posterUrl: posterByMedia.value.get(`${e.mediaType}-${e.mediaId}`) ?? null,
  };
  editMediaSearch.value = e.mediaTitle;
  editChangingMedia.value = false;
  editError.value = null;
}
function cancelEdit() {
  editingId.value = null;
}
const editSearchResults = computed(() => {
  const q = editMediaSearch.value.trim().toLowerCase();
  if (!q) return [];
  return manualLibrary.value.filter((m) => m.title.toLowerCase().includes(q)).slice(0, 8);
});
function pickEditMedia(m: PickableMedia) {
  editMediaPicked.value = m;
  editMediaSearch.value = m.title;
  editChangingMedia.value = false;
}
async function saveEdit(e: ActivityEntry) {
  if (!editMediaPicked.value) {
    editError.value = "Pick a title.";
    return;
  }
  editError.value = null;
  try {
    const updated = await updateActivityEntry(e.id, {
      mediaType: editMediaPicked.value.mediaType,
      mediaId: editMediaPicked.value.mediaId,
      eventType: editEventType.value,
      eventDate: editDate.value,
      count: editCount.value,
      detail: editDetail.value || null,
    });
    const idx = historyEntries.value.findIndex((h) => h.id === e.id);
    if (idx !== -1) {
      if (updated.id === e.id) {
        historyEntries.value[idx] = updated;
      } else {
        // moved onto a day that already had a bucket — merged server
        // side into that row, so this one is gone and the target
        // needs its own count/detail refreshed
        historyEntries.value.splice(idx, 1);
        const targetIdx = historyEntries.value.findIndex((h) => h.id === updated.id);
        if (targetIdx !== -1) historyEntries.value[targetIdx] = updated;
        else historyEntries.value.push(updated);
      }
    }
    editingId.value = null;
  } catch (err) {
    editError.value = err instanceof Error ? err.message : "Failed to save.";
  }
}
async function removeHistoryEntry(e: ActivityEntry) {
  if (!window.confirm("Delete this history entry? This can't be undone.")) return;
  try {
    await deleteActivityEntry(e.id);
    historyEntries.value = historyEntries.value.filter((h) => h.id !== e.id);
  } catch (err) {
    historyError.value = err instanceof Error ? err.message : "Failed to delete entry.";
  }
}

// ---- manually logging a new history entry ----
const showManualForm = ref(false);
const manualSearch = ref("");
const manualPicked = ref<PickableMedia | null>(null);
const manualEventType = ref<ActivityEventType>("episodes_watched");
const manualDate = ref(keyOfDate(new Date()));
const manualCount = ref(1);
const manualDetail = ref("");
const manualError = ref<string | null>(null);
const manualSaving = ref(false);

const EVENT_TYPE_LABELS: Record<ActivityEventType, string> = {
  episodes_watched: "Episodes watched",
  status_changed: "Status changed",
  rewatched: "Rewatched",
  rated: "Rated",
};

async function openManualForm(date?: string) {
  showManualForm.value = true;
  manualPicked.value = null;
  manualSearch.value = "";
  manualError.value = null;
  manualDate.value = date ?? keyOfDate(new Date());
  await loadManualLibrary();
}
function closeManualForm() {
  showManualForm.value = false;
}
function logForDrawerDay() {
  const key = drawerKey.value ?? undefined;
  closeDrawer();
  openManualForm(key);
}
const manualSearchResults = computed(() => {
  const q = manualSearch.value.trim().toLowerCase();
  if (!q) return [];
  return manualLibrary.value.filter((m) => m.title.toLowerCase().includes(q)).slice(0, 8);
});
function pickManualMedia(m: PickableMedia) {
  manualPicked.value = m;
  manualSearch.value = m.title;
}
async function submitManualEntry() {
  if (!manualPicked.value) {
    manualError.value = "Pick a title first.";
    return;
  }
  manualSaving.value = true;
  manualError.value = null;
  try {
    const created = await createActivityEntry({
      mediaType: manualPicked.value.mediaType,
      mediaId: manualPicked.value.mediaId,
      eventType: manualEventType.value,
      eventDate: manualDate.value,
      count: manualCount.value,
      detail: manualDetail.value || null,
    });
    // Same upsert semantics as the backend's automatic logging — if a
    // bucket for this exact (media, event type, day) already existed,
    // `created` is that same row with the count bumped, not a new one.
    const idx = historyEntries.value.findIndex((h) => h.id === created.id);
    if (idx !== -1) historyEntries.value[idx] = created;
    else historyEntries.value.push(created);
    showManualForm.value = false;
  } catch (err) {
    manualError.value = err instanceof Error ? err.message : "Failed to log entry.";
  } finally {
    manualSaving.value = false;
  }
}
</script>

<template>
  <main class="page">
    <MediaTopBar active="calendar" />

    <div class="content">
      <div class="page-head">
        <h1>Calendar</h1>
        <div class="tab-toggle">
          <button
            type="button"
            :class="{ active: tab === 'calendar' }"
            @click="tab = 'calendar'"
          >
            Calendar
          </button>
          <button
            type="button"
            :class="{ active: tab === 'history' }"
            @click="tab = 'history'"
          >
            History
          </button>
        </div>
        <div class="head-actions">
          <button v-if="tab === 'calendar'" type="button" class="secondary-button" @click="openFeed">
            Subscribe
          </button>
          <button type="button" class="add-button" @click="openManualForm()">+ Log entry</button>
        </div>
      </div>

      <template v-if="tab === 'calendar'">
        <div class="month-bar">
          <div v-if="calView === 'month'" class="month-nav">
            <button type="button" class="nav-btn" :disabled="!canGoPrev" @click="prevMonth">‹</button>
            <span class="month-label">{{ MONTH_NAMES[viewMonth] }} {{ viewYear }}</span>
            <button type="button" class="nav-btn" :disabled="!canGoNext" @click="nextMonth">›</button>
          </div>
          <div v-else class="month-nav">
            <span class="month-label agenda-label">Next {{ CAL_MAX_DAYS }} days</span>
          </div>
          <div class="month-bar-actions">
            <div class="view-toggle">
              <button type="button" :class="{ active: calView === 'month' }" @click="calView = 'month'">
                Month
              </button>
              <button type="button" :class="{ active: calView === 'agenda' }" @click="calView = 'agenda'">
                Agenda
              </button>
            </div>
            <button
              type="button"
              class="refresh-btn"
              :class="{ spinning: calLoading || historyLoading }"
              title="Refresh"
              :disabled="calLoading"
              @click="refreshAll"
            >
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 12a9 9 0 1 1-2.64-6.36" />
                <polyline points="21 4 21 10 15 10" />
              </svg>
            </button>
            <button
              v-if="calView === 'month'"
              type="button"
              class="today-btn"
              :disabled="isCurrentMonth"
              @click="goToday"
            >
              Today
            </button>
          </div>
        </div>

        <div class="filter-row">
          <div class="filter-group">
            <button type="button" class="fchip" :class="{ on: filters.movie }" @click="filters.movie = !filters.movie">Movies</button>
            <button type="button" class="fchip" :class="{ on: filters.tv }" @click="filters.tv = !filters.tv">TV</button>
            <button type="button" class="fchip" :class="{ on: filters.anime }" @click="filters.anime = !filters.anime">Anime</button>
          </div>
          <div class="filter-group">
            <button type="button" class="fchip layer-episode" :class="{ on: filters.episode }" @click="filters.episode = !filters.episode">
              <span class="swatch"></span>Airing
            </button>
            <button type="button" class="fchip layer-release" :class="{ on: filters.release }" @click="filters.release = !filters.release">
              <span class="swatch"></span>Releases
            </button>
            <button type="button" class="fchip layer-watched" :class="{ on: filters.watched }" @click="filters.watched = !filters.watched">
              <span class="swatch"></span>Watched
            </button>
            <button
              type="button"
              class="fchip layer-estimated"
              :class="{ on: filters.estimated }"
              title="Episodes projected from the weekly airing pattern, not confirmed dates"
              @click="filters.estimated = !filters.estimated"
            >
              <span class="swatch"></span>Estimated
            </button>
          </div>
        </div>

        <p v-if="calError" class="state error">{{ calError }}</p>

        <template v-if="calView === 'month'">
          <div class="weekday-row">
            <span v-for="w in WEEKDAY_LABELS" :key="w">{{ w }}</span>
          </div>
          <div class="month-grid" :class="{ loading: calLoading }">
            <button
              v-for="cell in gridCells"
              :key="cell.key"
              type="button"
              class="day-cell"
              :class="{ 'out-of-month': !cell.inMonth, today: cell.isToday, past: cell.isPast }"
              @click="openDrawer(cell)"
            >
              <span class="day-number">{{ cell.day }}</span>
              <span class="day-chips">
                <span
                  v-for="i in chipsFor(cell).shown"
                  :key="i.key"
                  class="chip"
                  :class="[`layer-${i.layer}`, { projected: i.projected }]"
                  :title="itemTooltip(i)"
                >
                  <img v-if="i.posterUrl" :src="i.posterUrl" alt="" loading="lazy" />
                  <span v-else class="chip-fallback">{{ i.title.slice(0, 1) }}</span>
                  <span v-if="i.badge" class="chip-badge">{{ i.badge }}</span>
                </span>
                <span v-if="chipsFor(cell).more" class="chip chip-more">+{{ chipsFor(cell).more }}</span>
              </span>
            </button>
          </div>
        </template>

        <template v-else>
          <p v-if="!agendaGroups.length && !calLoading" class="state">
            Nothing scheduled in the next {{ CAL_MAX_DAYS }} days with these filters.
          </p>
          <div v-else class="agenda">
            <div v-for="g in agendaGroups" :key="g.key" class="agenda-day">
              <div class="day-heading">{{ longDayLabel(g.key) }}</div>
              <button
                v-for="i in g.items"
                :key="i.key"
                type="button"
                class="agenda-row"
                :class="[`layer-${i.layer}`, { projected: i.projected }]"
                @click="openItem(i)"
              >
                <span class="agenda-thumb">
                  <img v-if="i.posterUrl" :src="i.posterUrl" alt="" loading="lazy" />
                </span>
                <span class="agenda-main">
                  <span class="agenda-title">{{ i.title }}</span>
                  <span class="agenda-detail">{{ i.detail }}</span>
                </span>
                <span class="agenda-tag">{{ LAYER_LABEL[i.layer] }}</span>
              </button>
            </div>
          </div>
        </template>
      </template>

      <template v-else>
        <div class="history-filters">
          <input v-model="historySearch" type="text" class="history-search" placeholder="Search history…" />
          <select v-model="historyType" class="history-type">
            <option value="all">Everything</option>
            <option v-for="(label, key) in EVENT_TYPE_LABELS" :key="key" :value="key">{{ label }}</option>
          </select>
        </div>
        <p v-if="historyLoading" class="state">Loading…</p>
        <p v-else-if="historyError" class="state error">{{ historyError }}</p>
        <p v-else-if="!groupedHistory.length" class="state">
          Nothing logged yet — checking off episodes or changing a status will show up here.
        </p>
        <div v-else class="days">
          <div v-for="[key, dayEntries] in groupedHistory" :key="key" class="day-group">
            <div class="day-heading">{{ historyDayLabel(key) }}</div>
            <template v-for="entry in dayEntries" :key="entry.id">
              <div v-if="editingId === entry.id" class="entry-edit-row">
                <div class="entry-edit-title-row">
                  <template v-if="editChangingMedia">
                    <div class="entry-edit-title-search">
                      <input
                        v-model="editMediaSearch"
                        type="text"
                        placeholder="Search your library…"
                        class="entry-edit-detail"
                        @input="editMediaPicked = null"
                      />
                      <div v-if="editSearchResults.length" class="modal-search-results">
                        <button
                          v-for="m in editSearchResults"
                          :key="`${m.mediaType}-${m.mediaId}`"
                          type="button"
                          class="modal-search-result"
                          @click="pickEditMedia(m)"
                        >
                          {{ m.title }} <span class="modal-search-kind">{{ m.mediaType }}</span>
                        </button>
                      </div>
                    </div>
                  </template>
                  <template v-else>
                    <span class="entry-edit-title">{{ editMediaPicked?.title }}</span>
                    <button type="button" class="entry-change-title-btn" @click="editChangingMedia = true; loadManualLibrary()">
                      Change title
                    </button>
                  </template>
                </div>
                <div class="entry-edit-fields">
                  <select v-model="editEventType" class="entry-edit-type">
                    <option v-for="(label, key) in EVENT_TYPE_LABELS" :key="key" :value="key">{{ label }}</option>
                  </select>
                  <input v-model="editDate" type="date" class="entry-edit-date" />
                  <input v-model.number="editCount" type="number" min="1" class="entry-edit-count" />
                  <input v-model="editDetail" type="text" placeholder="Note (optional)" class="entry-edit-detail" />
                </div>
                <p v-if="editError" class="modal-error">{{ editError }}</p>
                <div class="entry-edit-actions">
                  <button type="button" class="entry-save-btn" @click="saveEdit(entry)">Save</button>
                  <button type="button" class="entry-cancel-btn" @click="cancelEdit">Cancel</button>
                </div>
              </div>
              <div v-else class="entry-row" :class="entry.eventType" @click="openHistoryEntry(entry)">
                <span class="entry-icon">{{ HISTORY_ICONS[entry.eventType] }}</span>
                <span class="entry-text">{{ describeActivity(entry) }}</span>
                <span class="entry-actions">
                  <button type="button" class="entry-action-btn" title="Edit" @click.stop="startEdit(entry)">✎</button>
                  <button type="button" class="entry-action-btn" title="Delete" @click.stop="removeHistoryEntry(entry)">×</button>
                </span>
              </div>
            </template>
          </div>
          <button v-if="hasOlderHistory" type="button" class="secondary-button older-btn" @click="historyWindowDays += 90">
            Show older
          </button>
        </div>
      </template>
    </div>

    <Teleport to="body">
      <div v-if="drawerKey" class="drawer-backdrop" @click.self="closeDrawer">
        <aside class="drawer" role="dialog" aria-label="Day details">
          <div class="drawer-head">
            <h3>{{ longDayLabel(drawerKey) }}</h3>
            <button type="button" class="drawer-close" title="Close" @click="closeDrawer">×</button>
          </div>
          <p v-if="!drawerItems.length" class="drawer-empty">Nothing on this day with the current filters.</p>
          <div v-else class="drawer-list">
            <button
              v-for="i in drawerItems"
              :key="i.key"
              type="button"
              class="agenda-row"
              :class="[`layer-${i.layer}`, { projected: i.projected }]"
              @click="openItem(i)"
            >
              <span class="agenda-thumb">
                <img v-if="i.posterUrl" :src="i.posterUrl" alt="" loading="lazy" />
              </span>
              <span class="agenda-main">
                <span class="agenda-title">{{ i.title }}</span>
                <span class="agenda-detail">{{ i.detail }}</span>
              </span>
              <span class="agenda-tag">{{ LAYER_LABEL[i.layer] }}</span>
            </button>
          </div>
          <div class="drawer-foot">
            <button type="button" class="secondary-button" @click="logForDrawerDay">Log something on this day</button>
          </div>
        </aside>
      </div>
    </Teleport>

    <div v-if="showFeed" class="modal-backdrop" @click.self="showFeed = false">
      <div class="modal-card">
        <h3>Subscribe in your calendar app</h3>
        <p class="modal-hint">
          Paste this link into Google Calendar (Other calendars, From URL), Apple Calendar or
          Outlook and every airing episode and release shows up there, kept up to date. Anyone
          with the link can see your schedule, so treat it like a password. The app has to be
          reachable from the internet for Google Calendar to fetch it.
        </p>
        <input class="modal-input" type="text" readonly :value="feedUrl" placeholder="Loading…" @focus="($event.target as HTMLInputElement).select()" />
        <p v-if="feedError" class="modal-error feed-error">{{ feedError }}</p>
        <div class="modal-actions">
          <button type="button" class="secondary-button" :disabled="feedBusy" @click="regenerateFeed">
            New link
          </button>
          <button type="button" class="add-button" :disabled="!feedUrl" @click="copyFeed">
            {{ feedCopied ? "Copied" : "Copy link" }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="showManualForm" class="modal-backdrop" @click.self="closeManualForm">
      <div class="modal-card">
        <h3>Log a history entry</h3>
        <p class="modal-hint">
          For anything the app didn't catch automatically — watch history from before you added
          this title, or an import.
        </p>

        <label class="modal-field">
          <span>Title</span>
          <input
            v-model="manualSearch"
            type="text"
            placeholder="Search your library…"
            class="modal-input"
            @input="manualPicked = null"
          />
          <div v-if="manualSearchResults.length && !manualPicked" class="modal-search-results">
            <button
              v-for="m in manualSearchResults"
              :key="`${m.mediaType}-${m.mediaId}`"
              type="button"
              class="modal-search-result"
              @click="pickManualMedia(m)"
            >
              {{ m.title }} <span class="modal-search-kind">{{ m.mediaType }}</span>
            </button>
          </div>
        </label>

        <label class="modal-field">
          <span>What happened</span>
          <select v-model="manualEventType" class="modal-input">
            <option v-for="(label, key) in EVENT_TYPE_LABELS" :key="key" :value="key">{{ label }}</option>
          </select>
        </label>

        <div class="modal-field-row">
          <label class="modal-field">
            <span>Date</span>
            <input v-model="manualDate" type="date" class="modal-input" />
          </label>
          <label v-if="manualEventType === 'episodes_watched'" class="modal-field">
            <span>Episodes</span>
            <input v-model.number="manualCount" type="number" min="1" class="modal-input" />
          </label>
        </div>

        <label class="modal-field">
          <span>Note (optional)</span>
          <input v-model="manualDetail" type="text" class="modal-input" placeholder="e.g. rewatched with friends" />
        </label>

        <p v-if="manualError" class="modal-error">{{ manualError }}</p>

        <div class="modal-actions">
          <button type="button" class="secondary-button" @click="closeManualForm">Cancel</button>
          <button type="button" class="add-button" :disabled="manualSaving" @click="submitManualEntry">
            {{ manualSaving ? "Logging…" : "Log entry" }}
          </button>
        </div>
      </div>
    </div>
  </main>
</template>

<style scoped>
.page {
  position: relative;
  font-family: system-ui, sans-serif;
  background: #121212;
  min-height: 100vh;
  color: #fff;
}
.content {
  max-width: 1100px;
  margin: 0 auto;
  padding: 24px 24px 60px;
}
.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 20px;
}
.page-head h1 {
  margin: 0;
  font-size: 1.6rem;
  font-weight: 700;
}
.tab-toggle {
  display: inline-flex;
  gap: 4px;
  background: #1a1a1a;
  border-radius: 10px;
  padding: 4px;
}
.tab-toggle button {
  background: transparent;
  border: none;
  color: #9c9c9c;
  height: 30px;
  font-family: inherit;
  font-size: 0.8rem;
  font-weight: 700;
  padding: 0 16px;
  border-radius: 7px;
  cursor: pointer;
}
.tab-toggle button.active {
  background: #d68a34;
  color: #14100a;
}
.state {
  color: #999;
  font-size: 0.88rem;
  padding: 24px 0;
}
.state.error {
  color: #e57373;
}

/* month calendar grid */
.month-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 10px;
}
.month-nav {
  display: flex;
  align-items: center;
  gap: 14px;
}
.month-label {
  font-size: 1.1rem;
  font-weight: 700;
  min-width: 160px;
  text-align: center;
}
.nav-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: #1a1a1a;
  border: 1px solid #2b2b2b;
  color: #eee;
  font-size: 1rem;
  cursor: pointer;
}
.nav-btn:hover:not(:disabled) {
  border-color: rgba(214, 138, 52, 0.4);
  color: #d68a34;
}
.nav-btn:disabled {
  opacity: 0.3;
  cursor: default;
}
.add-button {
  height: 40px;
  box-sizing: border-box;
  background: #d68a34;
  color: #111;
  border: none;
  border-radius: 8px;
  padding: 0 18px;
  font-weight: 600;
  font-size: 0.84rem;
  cursor: pointer;
  font-family: inherit;
  white-space: nowrap;
}
.month-bar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.refresh-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid #2b2b2b;
  color: #ccc;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}
.refresh-btn:hover:not(:disabled) {
  border-color: rgba(214, 138, 52, 0.4);
  color: #d68a34;
}
.refresh-btn:disabled {
  opacity: 0.6;
  cursor: default;
}
.refresh-btn.spinning svg {
  animation: refresh-spin 0.7s linear infinite;
}
@keyframes refresh-spin {
  to {
    transform: rotate(360deg);
  }
}
.today-btn {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid #2b2b2b;
  color: #ccc;
  border-radius: 8px;
  padding: 0 14px;
  height: 32px;
  font-size: 0.78rem;
  font-weight: 700;
  cursor: pointer;
  font-family: inherit;
}
.today-btn:hover:not(:disabled) {
  border-color: rgba(214, 138, 52, 0.4);
  color: #d68a34;
}
.today-btn:disabled {
  opacity: 0.4;
  cursor: default;
}
.head-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.view-toggle {
  display: inline-flex;
  gap: 2px;
  background: #1a1a1a;
  border-radius: 8px;
  padding: 3px;
}
.view-toggle button {
  background: transparent;
  border: none;
  color: #9c9c9c;
  height: 26px;
  padding: 0 12px;
  border-radius: 6px;
  font-family: inherit;
  font-size: 0.74rem;
  font-weight: 700;
  cursor: pointer;
}
.view-toggle button.active {
  background: rgba(214, 138, 52, 0.22);
  color: #d68a34;
}
.agenda-label {
  min-width: 0;
  text-align: left;
}

/* filters */
.filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 22px;
  margin-bottom: 16px;
}
.filter-group {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.fchip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 28px;
  padding: 0 12px;
  border-radius: 999px;
  background: transparent;
  border: 1px solid #2b2b2b;
  color: #777;
  font-family: inherit;
  font-size: 0.74rem;
  font-weight: 700;
  cursor: pointer;
  transition: border-color 0.15s ease, color 0.15s ease, background 0.15s ease;
}
.fchip:hover {
  color: #ccc;
}
.fchip.on {
  color: #eee;
  background: rgba(255, 255, 255, 0.07);
  border-color: #3a3a3a;
}
.swatch {
  width: 10px;
  height: 10px;
  border-radius: 3px;
  border: 2px solid var(--layer, #888);
  box-sizing: border-box;
}
.fchip:not(.on) .swatch {
  opacity: 0.4;
}
.layer-episode {
  --layer: #d68a34;
}
.layer-release {
  --layer: #7ba7d9;
}
.layer-watched {
  --layer: #6fbf73;
}
.layer-estimated {
  --layer: #d68a34;
}
.layer-estimated .swatch {
  border-style: dashed;
}

/* month grid: minmax(0, 1fr) is what stops long content from stretching
   a column, and cells have a fixed height so a busy day can't make its
   whole row taller than the rest */
.weekday-row {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 6px;
  margin-bottom: 6px;
}
.weekday-row span {
  text-align: center;
  font-size: 0.72rem;
  font-weight: 700;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.month-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  grid-auto-rows: 112px;
  gap: 6px;
  transition: opacity 0.15s ease;
}
.month-grid.loading {
  opacity: 0.5;
}
.day-cell {
  min-width: 0;
  overflow: hidden;
  background: #171717;
  border: 1px solid #202020;
  border-radius: 8px;
  padding: 6px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  text-align: left;
  font-family: inherit;
  color: inherit;
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
}
.day-cell:hover {
  border-color: rgba(214, 138, 52, 0.45);
  background: #1b1b1b;
}
.day-cell:focus-visible {
  outline: 2px solid #d68a34;
  outline-offset: 1px;
}
.day-cell.out-of-month {
  opacity: 0.35;
}
.day-cell.today {
  border-color: rgba(214, 138, 52, 0.55);
  background: rgba(214, 138, 52, 0.07);
}
.day-number {
  font-size: 0.74rem;
  font-weight: 700;
  color: #999;
  font-variant-numeric: tabular-nums;
}
.day-cell.today .day-number {
  color: #d68a34;
}
.day-chips {
  display: flex;
  flex-wrap: wrap;
  align-content: flex-start;
  gap: 3px;
  min-width: 0;
}
.chip {
  position: relative;
  width: 27px;
  height: 39px;
  border-radius: 4px;
  overflow: hidden;
  flex-shrink: 0;
  background: #262626;
  border: 2px solid var(--layer, #888);
  box-sizing: border-box;
}
.chip img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.chip-fallback {
  display: flex;
  width: 100%;
  height: 100%;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
  font-weight: 700;
  color: #888;
}
.chip.projected {
  border-style: dashed;
  opacity: 0.75;
}
.chip-badge {
  position: absolute;
  right: 0;
  bottom: 0;
  min-width: 12px;
  padding: 0 2px;
  background: rgba(0, 0, 0, 0.82);
  color: #fff;
  font-size: 0.58rem;
  font-weight: 800;
  line-height: 13px;
  text-align: center;
  border-top-left-radius: 3px;
  font-variant-numeric: tabular-nums;
}
.chip-more {
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #333;
  background: transparent;
  color: #999;
  font-size: 0.68rem;
  font-weight: 700;
}

/* agenda + day drawer rows */
.agenda {
  display: flex;
  flex-direction: column;
  gap: 22px;
}
.agenda-day .day-heading {
  margin-bottom: 8px;
}
.agenda-row {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  box-sizing: border-box;
  background: #171717;
  border: 1px solid #202020;
  border-left: 3px solid var(--layer, #888);
  border-radius: 8px;
  padding: 8px 12px 8px 8px;
  margin-bottom: 6px;
  text-align: left;
  color: #ddd;
  font-family: inherit;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease;
}
.agenda-row:hover {
  background: #1c1c1c;
  border-color: rgba(214, 138, 52, 0.4);
  border-left-color: var(--layer, #888);
}
.agenda-row.projected {
  border-left-style: dashed;
}
.agenda-thumb {
  width: 34px;
  height: 50px;
  border-radius: 4px;
  overflow: hidden;
  background: #262626;
  flex-shrink: 0;
}
.agenda-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.agenda-main {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
  flex: 1;
}
.agenda-title {
  font-size: 0.86rem;
  font-weight: 700;
  color: #fff;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.agenda-detail {
  font-size: 0.75rem;
  color: #999;
}
.agenda-tag {
  font-size: 0.66rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--layer, #888);
  flex-shrink: 0;
}

.drawer-backdrop {
  position: fixed;
  inset: 0;
  z-index: 150;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: flex-end;
}
.drawer {
  width: min(400px, 100%);
  height: 100%;
  box-sizing: border-box;
  background: #141414;
  border-left: 1px solid #262626;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  overflow-y: auto;
  color: #fff;
  box-shadow: -24px 0 64px rgba(0, 0, 0, 0.5);
}
.drawer-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.drawer-head h3 {
  margin: 0;
  font-size: 1.05rem;
}
.drawer-close {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  border: 1px solid #2b2b2b;
  background: rgba(255, 255, 255, 0.06);
  color: #ccc;
  font-size: 1.1rem;
  cursor: pointer;
}
.drawer-empty {
  color: #888;
  font-size: 0.84rem;
}
.drawer-list {
  flex: 1;
}
.drawer-foot {
  border-top: 1px solid #202020;
  padding-top: 14px;
}

.history-filters {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}
.history-search,
.history-type {
  background: #0d0d0d;
  border: 1px solid #2a2a2a;
  border-radius: 8px;
  color: #eee;
  padding: 0 12px;
  height: 34px;
  font-size: 0.82rem;
  font-family: inherit;
  box-sizing: border-box;
}
.history-search {
  flex: 1;
  min-width: 180px;
}
.history-search:focus,
.history-type:focus {
  outline: none;
  border-color: #d68a34;
}
.older-btn {
  align-self: center;
}
.feed-error {
  margin-top: 10px;
}

/* history list */
.days {
  display: flex;
  flex-direction: column;
  gap: 26px;
  margin-top: 8px;
}
.day-heading {
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 700;
  color: #d68a34;
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid #202020;
}
.entry-row {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #171717;
  border: 1px solid #202020;
  border-left: 3px solid #3a3a3a;
  border-radius: 8px;
  padding: 11px 14px;
  margin-bottom: 8px;
  font-size: 0.86rem;
  color: #ddd;
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease, transform 0.1s ease;
}
.entry-row:hover {
  border-color: rgba(214, 138, 52, 0.4);
  border-left-color: #d68a34;
  background: #1c1c1c;
  transform: translateX(2px);
}
.entry-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.06);
  font-size: 0.78rem;
  flex-shrink: 0;
}
.entry-row.episodes_watched {
  border-left-color: #6fbf73;
}
.entry-row.episodes_watched .entry-icon {
  color: #6fbf73;
  background: rgba(111, 191, 115, 0.14);
}
.entry-row.status_changed {
  border-left-color: #7ba7d9;
}
.entry-row.status_changed .entry-icon {
  color: #7ba7d9;
  background: rgba(123, 167, 217, 0.14);
}
.entry-row.rewatched {
  border-left-color: #d68a34;
}
.entry-row.rewatched .entry-icon {
  color: #d68a34;
  background: rgba(214, 138, 52, 0.14);
}
.entry-row.rated {
  border-left-color: #d9c86f;
}
.entry-row.rated .entry-icon {
  color: #d9c86f;
  background: rgba(217, 200, 111, 0.14);
}
.entry-text {
  min-width: 0;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.entry-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.15s ease;
  flex-shrink: 0;
}
.entry-row:hover .entry-actions {
  opacity: 1;
}
.entry-action-btn {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid #2b2b2b;
  color: #ccc;
  border-radius: 6px;
  width: 24px;
  height: 24px;
  font-size: 0.78rem;
  cursor: pointer;
  font-family: inherit;
}
.entry-action-btn:hover {
  border-color: rgba(214, 138, 52, 0.4);
  color: #d68a34;
}

/* history inline edit row */
.entry-edit-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: #171717;
  border: 1px solid rgba(214, 138, 52, 0.4);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 8px;
}
.entry-edit-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.entry-edit-title {
  font-weight: 700;
  font-size: 0.86rem;
  color: #fff;
}
.entry-edit-title-search {
  position: relative;
  flex: 1;
}
.entry-change-title-btn {
  background: none;
  border: none;
  color: #d68a34;
  font-size: 0.74rem;
  font-weight: 700;
  cursor: pointer;
  font-family: inherit;
  padding: 0;
}
.entry-edit-fields {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.entry-edit-type {
  background: #0d0d0d;
  border: 1px solid #2a2a2a;
  border-radius: 6px;
  color: #eee;
  padding: 6px 8px;
  font-size: 0.8rem;
  font-family: inherit;
}
.entry-edit-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.entry-edit-date,
.entry-edit-count,
.entry-edit-detail {
  background: #0d0d0d;
  border: 1px solid #2a2a2a;
  border-radius: 6px;
  color: #eee;
  padding: 6px 8px;
  font-size: 0.8rem;
  font-family: inherit;
}
.entry-edit-count {
  width: 64px;
}
.entry-edit-detail {
  flex: 1;
  min-width: 120px;
}
.entry-save-btn,
.entry-cancel-btn {
  border: none;
  border-radius: 6px;
  padding: 6px 12px;
  font-size: 0.78rem;
  font-weight: 700;
  cursor: pointer;
  font-family: inherit;
}
.entry-save-btn {
  background: #d68a34;
  color: #14100a;
}
.entry-cancel-btn {
  background: rgba(255, 255, 255, 0.08);
  color: #ccc;
}

/* manual log-entry modal */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.65);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
  padding: 24px;
}
.modal-card {
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  border-radius: 12px;
  padding: 22px;
  width: 100%;
  max-width: 420px;
  max-height: 85vh;
  overflow-y: auto;
  box-sizing: border-box;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.6);
}
.modal-card h3 {
  margin: 0 0 6px;
  color: #fff;
}
.modal-hint {
  color: #999;
  font-size: 0.78rem;
  margin: 0 0 16px;
  line-height: 1.5;
}
.modal-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 0.82rem;
  color: #ccc;
  margin-bottom: 14px;
  position: relative;
}
.modal-field-row {
  display: flex;
  gap: 12px;
}
.modal-field-row .modal-field {
  flex: 1;
}
.modal-input {
  background: #111;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  color: #fff;
  padding: 9px 12px;
  font: inherit;
  font-size: 13px;
  box-sizing: border-box;
  width: 100%;
}
.modal-input:focus {
  outline: none;
  border-color: #d68a34;
}
.modal-search-results {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  z-index: 10;
  background: #171717;
  border: 1px solid #2a2a2a;
  border-radius: 8px;
  margin-top: 4px;
  max-height: 200px;
  overflow-y: auto;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.5);
}
.modal-search-result {
  display: flex;
  justify-content: space-between;
  width: 100%;
  text-align: left;
  background: none;
  border: none;
  color: #ddd;
  padding: 8px 10px;
  cursor: pointer;
  font-size: 0.82rem;
  font-family: inherit;
}
.modal-search-result:hover {
  background: rgba(255, 255, 255, 0.06);
}
.modal-search-kind {
  color: #777;
  font-size: 0.7rem;
  text-transform: uppercase;
}
.modal-error {
  color: #fca5a5;
  font-size: 13px;
  background: rgba(220, 38, 38, 0.1);
  border: 1px solid rgba(220, 38, 38, 0.3);
  border-radius: 8px;
  padding: 8px 10px;
  margin-bottom: 12px;
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 6px;
}
.secondary-button {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 10px 18px;
  font-weight: 600;
  font-size: 0.84rem;
  cursor: pointer;
  font-family: inherit;
}
</style>
