import type { SegmentOption } from "../components/SegmentedTabs.vue";

// A real month-grid calendar with three layers (episode airings, upcoming
// Plan to Watch releases, and what you actually watched), an agenda view
// for "what's next", and History folded in as a second tab. Grid cells hold
// small poster thumbnails instead of title text: text is what stretched
// the columns and warped the grid, and a library with dozens of airing
// shows can't fit names in a cell anyway. Names live in the hover tooltip
// and the day drawer that opens on click.
import {
  ref,
  reactive,
  computed,
  onMounted,
  onActivated,
  onDeactivated,
  watch,
} from "vue";
import { useRoute, useRouter } from "vue-router";
import { blurOnLeave } from "../utils/blurOnLeave";

import {
  fetchCalendar,
  fetchActivity,
  fetchCalendarFeedUrl,
  fetchCalendarGames,
  fetchCalendarEvents,
  createCalendarEvent,
  updateCalendarEvent,
  deleteCalendarEvent,
  createActivityEntry,
  updateActivityEntry,
  deleteActivityEntry,
} from "../services/mediaExtras";
import type {
  ActivityEventType,
  CalendarEntry,
  CalendarGameEntry,
  CalendarEventEntry,
  ActivityEntry,
  MediaType,
} from "../services/mediaExtras";

import {
  fetchPreferences,
  queuePreferences,
  DEFAULT_PREFERENCES,
} from "../services/preferences";
import type { Preferences } from "../services/preferences";
import { useKeptAlive } from "../utils/useKeptAlive";
import { useConfirm } from "../state/dialog";
import { fetchMovies } from "../services/movies";
import { fetchTVShows } from "../services/tvShows";
import { fetchAnime } from "../services/anime";
import { displayTitle } from "../utils/displayTitle";
export function useCalendar() {
  const router = useRouter();
  const route = useRoute();
  const tab = ref<"calendar" | "history">("calendar");
  const calView = ref<"month" | "week" | "agenda">("month");
  const TAB_OPTIONS: SegmentOption[] = [
    { value: "calendar", label: "Calendar" },
    { value: "history", label: "History" },
  ];
  const VIEW_OPTIONS: SegmentOption[] = [
    { value: "month", label: "Month" },
    { value: "week", label: "Week" },
    { value: "agenda", label: "Agenda" },
  ];

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
    for (const m of manualLibrary.value)
      map.set(`${m.mediaType}-${m.mediaId}`, m.posterUrl);
    return map;
  });
  async function loadManualLibrary() {
    if (manualLibraryLoaded.value) return;
    const [movies, shows, anime] = await Promise.all([
      fetchMovies(),
      fetchTVShows(),
      fetchAnime(),
    ]);
    manualLibrary.value = [
      ...movies.map((m) => ({
        mediaType: "movie" as const,
        mediaId: m.id,
        title: m.title,
        posterUrl: m.posterUrl,
      })),
      ...shows.map((s) => ({
        mediaType: "tv" as const,
        mediaId: s.id,
        title: s.title,
        posterUrl: s.posterUrl,
      })),
      ...anime.map((a) => ({
        mediaType: "anime" as const,
        mediaId: a.id,
        title: displayTitle(a),
        posterUrl: a.posterUrl,
      })),
    ];
    manualLibraryLoaded.value = true;
  }

  // ---- filters (remembered between visits) ----
  const FILTER_KEY = "calendar-filters-v1";
  const filters = reactive({
    movie: true,
    tv: true,
    anime: true,
    game: true,
    episode: true,
    release: true,
    watched: true,
    event: true,
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

  // ---- preferences (Settings > Calendar) ----
  const prefs = ref<Preferences>({ ...DEFAULT_PREFERENCES });
  const showGamesFilter = computed(
    () =>
      !prefs.value.calendar_hide_games &&
      (prefs.value.calendar_game_releases || prefs.value.calendar_game_history),
  );
  const weekStart = computed(() => prefs.value.calendar_week_start);
  async function loadPreferences() {
    try {
      prefs.value = await fetchPreferences();
    } catch {
      // defaults are fine
    }
  }

  // which airing shows appear, by where they sit in the library: saved with the
  // other calendar settings, so it holds on every device
  type AiringStatus = Preferences["calendar_airing_statuses"][number];
  const AIRING_STATUS_CHIPS: { key: AiringStatus; label: string }[] = [
    { key: "watching", label: "Watching" },
    { key: "plan", label: "Plan to Watch" },
    { key: "hold", label: "On Hold" },
  ];
  async function toggleAiringStatus(key: AiringStatus) {
    const previous = prefs.value.calendar_airing_statuses;
    const next = previous.includes(key)
      ? previous.filter((s) => s !== key)
      : [...previous, key];
    prefs.value = { ...prefs.value, calendar_airing_statuses: next };
    try {
      const { latest } = await queuePreferences({
        calendar_airing_statuses: next,
      });
      if (latest) await loadCalendar();
    } catch {
      prefs.value = { ...prefs.value, calendar_airing_statuses: previous };
    }
  }

  // ---- calendar data ----
  const gameEntries = ref<CalendarGameEntry[]>([]);
  async function loadGameHistory() {
    try {
      // the server sends nothing unless Games history is switched on
      gameEntries.value = await fetchCalendarGames();
    } catch {
      gameEntries.value = [];
    }
  }
  const eventEntries = ref<CalendarEventEntry[]>([]);
  async function loadEvents() {
    try {
      eventEntries.value = await fetchCalendarEvents();
    } catch {
      // the rest of the calendar still works without them
    }
  }
  const entries = ref<CalendarEntry[]>([]);
  const calLoading = ref(true);
  const calError = ref<string | null>(null);

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const viewYear = ref(today.getFullYear());
  const viewMonth = ref(today.getMonth()); // 0-11

  const isCurrentMonth = computed(
    () =>
      viewYear.value === today.getFullYear() &&
      viewMonth.value === today.getMonth(),
  );
  const CAL_MAX_DAYS = 90;
  // Back as far as the oldest entry of any kind (watch history, game history and
  // release dates, your own entries), never earlier than the current month, so a
  // brand-new account still has somewhere sensible to stand; forward as far as
  // the backend projects airings.
  const earliestMonth = computed(() => {
    let min = "";
    for (const a of historyEntries.value)
      if (!min || a.eventDate < min) min = a.eventDate;
    for (const g of gameEntries.value) if (!min || g.date < min) min = g.date;
    for (const e of eventEntries.value)
      if (!min || e.eventDate < min) min = e.eventDate;
    if (!min) return today.getFullYear() * 12 + today.getMonth();
    const d = new Date(`${min}T00:00:00`);
    return Math.min(
      d.getFullYear() * 12 + d.getMonth(),
      today.getFullYear() * 12 + today.getMonth(),
    );
  });
  const canGoPrev = computed(
    () => viewYear.value * 12 + viewMonth.value > earliestMonth.value,
  );
  const canGoNext = computed(() => {
    const firstOfNext = new Date(viewYear.value, viewMonth.value + 1, 1);
    return firstOfNext.getTime() - today.getTime() < CAL_MAX_DAYS * 86_400_000;
  });
  const jumpMonthValue = computed(
    () => `${viewYear.value}-${String(viewMonth.value + 1).padStart(2, "0")}`,
  );
  function jumpToMonth(event: Event) {
    const value = (event.target as HTMLInputElement).value;
    if (!/^\d{4}-\d{2}$/.test(value)) return;
    const [y, m] = value.split("-").map(Number);
    const index = y * 12 + (m - 1);
    const max =
      today.getFullYear() * 12 +
      today.getMonth() +
      Math.ceil(CAL_MAX_DAYS / 30);
    if (index < earliestMonth.value || index > max) return;
    viewYear.value = y;
    viewMonth.value = m - 1;
  }

  // Only a first load (nothing on screen yet) shows the loading state; later
  // refreshes swap data in quietly.
  async function loadCalendar() {
    if (!entries.value.length) calLoading.value = true;
    calError.value = null;
    try {
      // The backend only looks forward from today, so a wide window is
      // enough for every month the nav allows; past cells get their content
      // from the watched layer instead.
      entries.value = await fetchCalendar(CAL_MAX_DAYS);
    } catch (e) {
      calError.value =
        e instanceof Error ? e.message : "Failed to load the calendar.";
    } finally {
      calLoading.value = false;
    }
  }

  // ---- history data (also feeds the calendar's "watched" layer) ----
  const historyEntries = ref<ActivityEntry[]>([]);
  const historyLoading = ref(false);
  const historyError = ref<string | null>(null);

  async function loadHistory() {
    if (!historyEntries.value.length) historyLoading.value = true;
    historyError.value = null;
    try {
      // every entry there is, not a fixed window
      historyEntries.value = await fetchActivity(36500);
    } catch (e) {
      historyError.value =
        e instanceof Error ? e.message : "Failed to load history.";
    } finally {
      historyLoading.value = false;
    }
  }
  const refreshing = ref(false);
  async function refreshAll() {
    refreshing.value = true;
    try {
      await loadPreferences();
      await Promise.all([
        loadCalendar(),
        loadHistory(),
        loadGameHistory(),
        loadEvents(),
      ]);
    } finally {
      refreshing.value = false;
    }
  }
  let appliedDefaultView = false;
  onMounted(async () => {
    await refreshAll();
    if (!appliedDefaultView) {
      appliedDefaultView = true;
      calView.value = prefs.value.calendar_default_view;
    }
    loadManualLibrary();
  });
  useKeptAlive(refreshAll);

  // ---- unify everything the grid/agenda draws ----
  type Layer = "episode" | "release" | "watched" | "event";
  type CalMediaType = MediaType | "game" | "custom";
  interface CalItem {
    key: string;
    layer: Layer;
    mediaType: CalMediaType;
    mediaId: string;
    title: string;
    posterUrl: string | null;
    badge: string; // short text on the thumbnail: "12", "×3", ""
    detail: string; // longer line for tooltip/drawer
    projected: boolean;
    sortAt: number;
    dayKey: string;
    eventId?: string;
  }

  function keyOfDate(d: Date): string {
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  }
  function timeLabel(airAt: number): string {
    return new Date(airAt * 1000).toLocaleTimeString(undefined, {
      hour: "numeric",
      minute: "2-digit",
    });
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
  function fromGame(g: CalendarGameEntry): CalItem {
    const detail =
      g.kind === "game_released"
        ? "Release date"
        : g.kind === "game_finished"
          ? "Finished"
          : g.kind === "game_purchased"
            ? "Bought"
            : `${g.count} achievement${g.count === 1 ? "" : "s"} unlocked`;
    return {
      key: `${g.kind}-${g.gameId}-${g.date}`,
      // a release date belongs with the other releases, the rest with what you did
      layer: g.kind === "game_released" ? "release" : "watched",
      mediaType: "game",
      mediaId: g.gameId,
      title: g.title,
      posterUrl: g.posterUrl,
      badge:
        g.kind === "game_released"
          ? ""
          : g.kind === "game_finished"
            ? "✓"
            : g.kind === "game_purchased"
              ? "$"
              : String(g.count),
      detail,
      projected: false,
      sortAt: new Date(`${g.date}T12:00:00`).getTime() / 1000,
      dayKey: g.date,
    };
  }
  function fromEvent(e: CalendarEventEntry): CalItem {
    const linked =
      e.mediaType && e.mediaId
        ? (posterByMedia.value.get(`${e.mediaType}-${e.mediaId}`) ?? null)
        : null;
    return {
      key: `event-${e.id}`,
      layer: "event",
      mediaType: "custom",
      mediaId: e.mediaId ?? "",
      title: e.title,
      posterUrl: linked,
      badge: "",
      detail: [e.eventTime ? e.eventTime : "All day", e.note]
        .filter(Boolean)
        .join(" · "),
      projected: false,
      sortAt:
        new Date(`${e.eventDate}T${e.eventTime ?? "00:00"}:00`).getTime() /
        1000,
      dayKey: e.eventDate,
      eventId: e.id,
    };
  }
  function fromActivity(a: ActivityEntry): CalItem | null {
    if (a.eventType !== "episodes_watched" && a.eventType !== "rewatched")
      return null;
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

  // Indexed by day once, when the underlying data changes, so drawing a
  // month only looks up its ~42 days instead of filtering everything ever
  // logged on every filter click or navigation.
  function indexByDay(items: CalItem[]): Map<string, CalItem[]> {
    const map = new Map<string, CalItem[]>();
    for (const i of items) {
      const list = map.get(i.dayKey);
      if (list) list.push(i);
      else map.set(i.dayKey, [i]);
    }
    return map;
  }
  const upcomingByDay = computed(() =>
    indexByDay([
      ...entries.value.map(fromEntry),
      ...eventEntries.value.map(fromEvent),
    ]),
  );
  const watchedByDay = computed(() => {
    const items: CalItem[] = [];
    for (const a of historyEntries.value) {
      const item = fromActivity(a);
      if (item) items.push(item);
    }
    for (const g of gameEntries.value) items.push(fromGame(g));
    return indexByDay(items);
  });
  function passesFilters(i: CalItem): boolean {
    if (i.mediaType !== "custom" && !filters[i.mediaType]) return false;
    if (!filters[i.layer]) return false;
    if (i.mediaType === "game" && prefs.value.calendar_hide_games) return false;
    return !(
      i.projected &&
      (!filters.estimated || !prefs.value.calendar_show_estimated)
    );
  }
  function itemsForDay(key: string): CalItem[] {
    const a = upcomingByDay.value.get(key);
    const b = watchedByDay.value.get(key);
    if (!a && !b) return [];
    return [...(a ?? []), ...(b ?? [])]
      .filter(passesFilters)
      .sort((x, y) => x.sortAt - y.sortAt);
  }

  const MONTH_NAMES = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
  ];
  const ALL_WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  const WEEKDAY_LABELS = computed(() => [
    ...ALL_WEEKDAYS.slice(weekStart.value),
    ...ALL_WEEKDAYS.slice(0, weekStart.value),
  ]);

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
    const firstWeekday = (new Date(y, m, 1).getDay() - weekStart.value + 7) % 7;
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
        items: itemsForDay(key),
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
  function startOfWeek(d: Date): Date {
    const start = new Date(d.getFullYear(), d.getMonth(), d.getDate());
    start.setDate(
      start.getDate() - ((start.getDay() - weekStart.value + 7) % 7),
    );
    return start;
  }
  const weekAnchor = ref(startOfWeek(today));
  watch(weekStart, () => (weekAnchor.value = startOfWeek(weekAnchor.value)));
  interface WeekDay {
    key: string;
    label: string;
    isToday: boolean;
    isPast: boolean;
    items: CalItem[];
  }
  const weekDays = computed<WeekDay[]>(() =>
    Array.from({ length: 7 }, (_, i) => {
      const d = new Date(weekAnchor.value);
      d.setDate(d.getDate() + i);
      const key = keyOfDate(d);
      return {
        key,
        label: d.toLocaleDateString(undefined, {
          weekday: "short",
          month: "short",
          day: "numeric",
        }),
        isToday: key === todayKey,
        isPast: key < todayKey,
        items: itemsForDay(key),
      };
    }),
  );
  const weekLabel = computed(() => {
    const end = new Date(weekAnchor.value);
    end.setDate(end.getDate() + 6);
    const fmt = (d: Date, year: boolean) =>
      d.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        ...(year ? { year: "numeric" } : {}),
      });
    return `${fmt(weekAnchor.value, false)} to ${fmt(end, true)}`;
  });
  const isCurrentWeek = computed(
    () => keyOfDate(weekAnchor.value) === keyOfDate(startOfWeek(today)),
  );
  const canWeekNext = computed(
    () =>
      weekAnchor.value.getTime() + 7 * 86_400_000 - today.getTime() <
      CAL_MAX_DAYS * 86_400_000,
  );
  const canWeekPrev = computed(() => {
    const first = new Date(
      Math.floor(earliestMonth.value / 12),
      earliestMonth.value % 12,
      1,
    );
    return weekAnchor.value.getTime() > first.getTime();
  });
  function shiftWeek(weeks: number) {
    const next = new Date(weekAnchor.value);
    next.setDate(next.getDate() + weeks * 7);
    weekAnchor.value = next;
  }
  function goToday() {
    viewYear.value = today.getFullYear();
    viewMonth.value = today.getMonth();
    weekAnchor.value = startOfWeek(today);
  }

  // Grid chips: up to 6 slots; past that the last slot becomes "+N"
  const CHIP_SLOTS = 6;
  function chipsFor(cell: DayCell): { shown: CalItem[]; more: number } {
    if (cell.items.length <= CHIP_SLOTS) return { shown: cell.items, more: 0 };
    return {
      shown: cell.items.slice(0, CHIP_SLOTS - 1),
      more: cell.items.length - (CHIP_SLOTS - 1),
    };
  }
  function itemTooltip(i: CalItem): string {
    return `${i.title}${i.detail ? ` · ${i.detail}` : ""}`;
  }
  function activate(i: CalItem) {
    if (i.eventId) openEventEditor(i.eventId);
    else openItem(i);
  }
  function openItem(i: { mediaType: CalMediaType; mediaId: string }) {
    if (i.mediaType === "custom") return;
    const base =
      i.mediaType === "movie"
        ? "/movies"
        : i.mediaType === "anime"
          ? "/anime"
          : i.mediaType === "game"
            ? "/games"
            : "/tv";
    router.push(`${base}/${i.mediaId}`);
  }

  // ---- agenda: what's coming, day by day ----
  const agendaGroups = computed(() =>
    [...upcomingByDay.value.keys()]
      .filter((key) => key >= todayKey)
      .sort()
      .map((key) => ({
        key,
        items: itemsForDay(key).filter((i) => i.layer !== "watched"),
      }))
      .filter((g) => g.items.length),
  );
  function longDayLabel(key: string): string {
    const yesterday = keyOfDate(new Date(today.getTime() - 86_400_000));
    const tomorrow = keyOfDate(new Date(today.getTime() + 86_400_000));
    const base = new Date(`${key}T00:00:00`).toLocaleDateString(undefined, {
      weekday: "long",
      month: "short",
      day: "numeric",
    });
    if (key === todayKey) return `Today · ${base}`;
    if (key === tomorrow) return `Tomorrow · ${base}`;
    if (key === yesterday) return `Yesterday · ${base}`;
    return base;
  }

  // ---- day drawer (opens on click, holds the full list for that day) ----
  const drawerKey = ref<string | null>(null);
  const drawerItems = computed(() =>
    drawerKey.value ? itemsForDay(drawerKey.value) : [],
  );
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
    event: "Mine",
  };

  // ---- entries you add by hand ----
  const showEventForm = ref(false);
  const eventId = ref<string | null>(null);
  const eventTitle = ref("");
  const eventDate = ref(keyOfDate(new Date()));
  const eventTime = ref("");
  const eventNote = ref("");
  const eventLink = ref<PickableMedia | null>(null);
  const eventLinkSearch = ref("");
  const eventError = ref<string | null>(null);
  const eventSaving = ref(false);

  async function openEventForm(date?: string) {
    eventId.value = null;
    eventTitle.value = "";
    eventDate.value = date ?? keyOfDate(new Date());
    eventTime.value = "";
    eventNote.value = "";
    eventLink.value = null;
    eventLinkSearch.value = "";
    eventError.value = null;
    showEventForm.value = true;
    if (!manualLibraryLoaded.value) await loadManualLibrary();
  }
  async function openEventEditor(id: string) {
    const e = eventEntries.value.find((x) => x.id === id);
    if (!e) return;
    if (!manualLibraryLoaded.value) await loadManualLibrary();
    eventId.value = e.id;
    eventTitle.value = e.title;
    eventDate.value = e.eventDate;
    eventTime.value = e.eventTime ?? "";
    eventNote.value = e.note ?? "";
    eventLink.value =
      manualLibrary.value.find(
        (m) => m.mediaType === e.mediaType && m.mediaId === e.mediaId,
      ) ?? null;
    eventLinkSearch.value = eventLink.value?.title ?? "";
    eventError.value = null;
    closeDrawer();
    showEventForm.value = true;
  }
  function closeEventForm() {
    showEventForm.value = false;
  }
  const eventLinkResults = computed(() => {
    const q = eventLinkSearch.value.trim().toLowerCase();
    if (!q || eventLink.value) return [];
    return manualLibrary.value
      .filter((m) => m.title.toLowerCase().includes(q))
      .slice(0, 6);
  });
  function pickEventLink(m: PickableMedia) {
    eventLink.value = m;
    eventLinkSearch.value = m.title;
  }
  async function saveEvent() {
    if (eventSaving.value) return; // a fast double click must not save twice
    if (!eventTitle.value.trim()) {
      eventError.value = "Give the entry a title.";
      return;
    }
    if (!eventDate.value) {
      eventError.value = "Pick a date.";
      return;
    }
    eventSaving.value = true;
    eventError.value = null;
    const input = {
      title: eventTitle.value.trim(),
      eventDate: eventDate.value,
      eventTime: eventTime.value || null,
      note: eventNote.value.trim() || null,
      mediaType: eventLink.value?.mediaType ?? null,
      mediaId: eventLink.value?.mediaId ?? null,
    };
    try {
      if (eventId.value) await updateCalendarEvent(eventId.value, input);
      else await createCalendarEvent(input);
      await loadEvents();
      closeEventForm();
    } catch (e) {
      eventError.value = e instanceof Error ? e.message : "Failed to save.";
    } finally {
      eventSaving.value = false;
    }
  }
  async function removeEvent() {
    if (!eventId.value) return;
    const ok = await confirm({
      title: "Delete entry",
      message: "Delete this calendar entry?",
      confirmLabel: "Delete",
      danger: true,
    });
    if (!ok) return;
    try {
      await deleteCalendarEvent(eventId.value);
      await loadEvents();
      closeEventForm();
    } catch (e) {
      eventError.value = e instanceof Error ? e.message : "Failed to delete.";
    }
  }
  function openLinkedTitle() {
    if (eventLink.value) openItem(eventLink.value);
  }

  // ---- keyboard: left and right change month or week, T goes to today ----
  function onKey(e: KeyboardEvent) {
    if (
      route.path !== "/calendar" ||
      e.defaultPrevented ||
      document.querySelector("dialog[open]")
    )
      return;
    if (tab.value !== "calendar" || calView.value === "agenda") return;
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    const target = e.target as HTMLElement | null;
    if (target && /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName)) return;
    if (
      drawerKey.value ||
      showEventForm.value ||
      showManualForm.value ||
      showFeed.value
    )
      return;
    if (e.key === "ArrowLeft") {
      if (calView.value === "month") prevMonth();
      else if (canWeekPrev.value) shiftWeek(-1);
    } else if (e.key === "ArrowRight") {
      if (calView.value === "month") nextMonth();
      else if (canWeekNext.value) shiftWeek(1);
    } else if (e.key.toLowerCase() === "t") {
      goToday();
    }
  }
  // Escape closes whichever dialog is open, like every other dialog in the app
  function onEscape(e: KeyboardEvent) {
    if (e.key !== "Escape") return;
    if (showEventForm.value && !eventSaving.value) closeEventForm();
    else if (showManualForm.value && !manualSaving.value) closeManualForm();
    else if (showFeed.value) showFeed.value = false;
  }
  function listen() {
    window.addEventListener("keydown", onKey);
    window.addEventListener("keydown", onEscape);
  }
  function unlisten() {
    window.removeEventListener("keydown", onKey);
    window.removeEventListener("keydown", onEscape);
  }
  onActivated(listen);
  onDeactivated(unlisten);
  onMounted(listen);

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
      feedError.value =
        e instanceof Error ? e.message : "Couldn't load the feed link.";
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
  const confirm = useConfirm();
  async function regenerateFeed() {
    const ok = await confirm({
      message:
        "Make a new link? Anything subscribed to the old one stops updating.",
      confirmLabel: "Make new link",
    });
    if (!ok) return;
    feedBusy.value = true;
    try {
      feedUrl.value = await fetchCalendarFeedUrl(true);
      feedCopied.value = false;
    } catch (e) {
      feedError.value =
        e instanceof Error ? e.message : "Couldn't make a new link.";
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
        return `${e.mediaTitle}${e.detail ? `: ${e.detail}` : " status changed"}`;
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
      if (historyType.value !== "all" && e.eventType !== historyType.value)
        return false;
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
    return manualLibrary.value
      .filter((m) => m.title.toLowerCase().includes(q))
      .slice(0, 8);
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
          const targetIdx = historyEntries.value.findIndex(
            (h) => h.id === updated.id,
          );
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
    const ok = await confirm({
      message: "Delete this history entry? This can't be undone.",
      confirmLabel: "Delete",
      danger: true,
    });
    if (!ok) return;
    try {
      await deleteActivityEntry(e.id);
      historyEntries.value = historyEntries.value.filter((h) => h.id !== e.id);
    } catch (err) {
      historyError.value =
        err instanceof Error ? err.message : "Failed to delete entry.";
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
  function addEventForDrawerDay() {
    const key = drawerKey.value;
    closeDrawer();
    void openEventForm(key ?? undefined);
  }
  function logForDrawerDay() {
    const key = drawerKey.value ?? undefined;
    closeDrawer();
    openManualForm(key);
  }
  const manualSearchResults = computed(() => {
    const q = manualSearch.value.trim().toLowerCase();
    if (!q) return [];
    return manualLibrary.value
      .filter((m) => m.title.toLowerCase().includes(q))
      .slice(0, 8);
  });
  function pickManualMedia(m: PickableMedia) {
    manualPicked.value = m;
    manualSearch.value = m.title;
  }
  async function submitManualEntry() {
    if (manualSaving.value) return;
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
      manualError.value =
        err instanceof Error ? err.message : "Failed to log entry.";
    } finally {
      manualSaving.value = false;
    }
  }

  return {
    blurOnLeave,
    tab,
    calView,
    TAB_OPTIONS,
    VIEW_OPTIONS,
    loadManualLibrary,
    filters,
    prefs,
    showGamesFilter,
    AIRING_STATUS_CHIPS,
    toggleAiringStatus,
    entries,
    calLoading,
    calError,
    today,
    viewYear,
    viewMonth,
    isCurrentMonth,
    CAL_MAX_DAYS,
    canGoPrev,
    canGoNext,
    jumpMonthValue,
    jumpToMonth,
    historyEntries,
    historyLoading,
    historyError,
    refreshing,
    refreshAll,
    MONTH_NAMES,
    WEEKDAY_LABELS,
    gridCells,
    prevMonth,
    nextMonth,
    weekDays,
    weekLabel,
    isCurrentWeek,
    canWeekNext,
    canWeekPrev,
    shiftWeek,
    goToday,
    chipsFor,
    itemTooltip,
    activate,
    agendaGroups,
    longDayLabel,
    drawerKey,
    drawerItems,
    openDrawer,
    closeDrawer,
    LAYER_LABEL,
    showEventForm,
    eventId,
    eventTitle,
    eventDate,
    eventTime,
    eventNote,
    eventLink,
    eventLinkSearch,
    eventError,
    eventSaving,
    openEventForm,
    closeEventForm,
    eventLinkResults,
    pickEventLink,
    saveEvent,
    removeEvent,
    openLinkedTitle,
    showFeed,
    feedUrl,
    feedError,
    feedCopied,
    feedBusy,
    openFeed,
    copyFeed,
    regenerateFeed,
    historySearch,
    historyType,
    historyWindowDays,
    historyDayLabel,
    describeActivity,
    HISTORY_ICONS,
    groupedHistory,
    hasOlderHistory,
    openHistoryEntry,
    editingId,
    editDate,
    editCount,
    editDetail,
    editEventType,
    editMediaSearch,
    editMediaPicked,
    editChangingMedia,
    editError,
    startEdit,
    cancelEdit,
    editSearchResults,
    pickEditMedia,
    saveEdit,
    removeHistoryEntry,
    showManualForm,
    manualSearch,
    manualPicked,
    manualEventType,
    manualDate,
    manualCount,
    manualDetail,
    manualError,
    manualSaving,
    EVENT_TYPE_LABELS,
    openManualForm,
    closeManualForm,
    addEventForDrawerDay,
    logForDrawerDay,
    manualSearchResults,
    pickManualMedia,
    submitManualEntry,
  };
}
