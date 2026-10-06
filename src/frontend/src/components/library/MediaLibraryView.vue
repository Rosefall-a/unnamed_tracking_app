<script setup lang="ts">
import HeartIcon from "../HeartIcon.vue";
import {
  ref,
  computed,
  reactive,
  watch,
  onMounted,
  onActivated,
  onDeactivated,
  onBeforeUnmount,
} from "vue";
import { useRoute, useRouter } from "vue-router";
import CheckIcon from "../CheckIcon.vue";
import MediaTopBar from "../MediaTopBar.vue";
import UiModal from "../UiModal.vue";
import SegmentedTabs from "../SegmentedTabs.vue";
import type { SegmentOption } from "../SegmentedTabs.vue";
import { preferences } from "../../state/preferences";
import { matchesFilters } from "../../utils/libraryFilters";
import type { LibraryFilters } from "../../utils/libraryFilters";
import { blurOnLeave } from "../../utils/blurOnLeave";
import { PHONE_CARD_COLUMNS } from "../../utils/libraryLayout";
import { quickTourActive } from "../../state/quickTour";
import {
  STATUS_BUCKETS,
  statusBucket,
  statusBucketLabel,
  bucketToReal,
} from "../../utils/mediaStatus";

// A normalized view-model so this one component can drive Movies, TV
// Shows, and Anime without knowing about seasons, episode tables, or any
// other per-entity detail — each Library.vue page adapts its real
// entities into this shape and reacts to the events below.
import type {
  LibraryCardVM,
  SearchResultVM,
  QuickAddForm,
  EditForm,
} from "../../types/mediaLibrary";
export type {
  LibraryCardVM,
  SearchResultVM,
  QuickAddForm,
  EditForm,
} from "../../types/mediaLibrary";

// The pill/tab labels shown everywhere in this view come from the shared
// 5-value bucket set in utils/mediaStatus.ts — the pill's CSS modifier
// class is just the bucket key itself (see .pill.watching etc below).
const STATUSES = STATUS_BUCKETS;

const props = defineProps<{
  kind: "movie" | "tv" | "anime";
  addLabel: string;
  items: LibraryCardVM[];
  total: number;
  statusCounts: Record<string, number>;
  // library-wide leaderboard positions from the server
  scoreRanks?: Record<string, number>;
  loading: boolean;
  error: string | null;
  detailRoute: (id: string) => string;
  search: (
    query: string,
  ) => Promise<{ results: SearchResultVM[]; providerErrors: string[] }>;
  createFromResult: (
    result: SearchResultVM,
    form: QuickAddForm,
  ) => Promise<void>;
}>();

const emit = defineEmits<{
  (e: "toggle-favorite", id: string): void;
  (e: "advance-episode", id: string): void;
  (e: "save-note", id: string, note: string | null): void;
  (e: "save-edit", id: string, form: EditForm): void;
  (e: "bulk-set-status", ids: string[], status: string): void;
  (e: "bulk-favorite", ids: string[]): void;
  (e: "bulk-delete", ids: string[]): void;
  (e: "search", query: string): void;
  (
    e: "filters-change",
    filters: LibraryFilters & { statusBucket: string },
  ): void;
  (e: "load-more"): void;
}>();

const router = useRouter();
const route = useRoute();

function maybeLoadMore() {
  if (
    layout.value === "board" ||
    props.loading ||
    props.items.length >= props.total ||
    // what is already loaded is still being drawn a screenful at a time
    renderLimit.value < filteredItems.value.length
  )
    return;
  if (
    window.innerHeight + window.scrollY >=
    document.documentElement.scrollHeight - 1000
  ) {
    emit("load-more");
  }
}
onMounted(() =>
  window.addEventListener("scroll", maybeLoadMore, { passive: true }),
);
onBeforeUnmount(() => window.removeEventListener("scroll", maybeLoadMore));
watch(
  () => props.items.length,
  () => requestAnimationFrame(maybeLoadMore),
);

// The mockup's per-item "type" field (TV/Movie/OVA/Series/Anthology) has
// no real per-item equivalent — none of the three entities carry a
// sub-format string — so this renders a static per-page label instead,
// keeping the same element in the same place rather than dropping it.
const typeLabel = computed(() => {
  if (props.kind === "movie") return "Movie";
  if (props.kind === "tv") return "TV Series";
  return "Anime";
});

const LAYOUT_OPTIONS: SegmentOption[] = [
  {
    value: "list",
    label: "List",
    icon: '<line x1="8" y1="6" x2="21" y2="6" /><line x1="8" y1="12" x2="21" y2="12" /><line x1="8" y1="18" x2="21" y2="18" /><line x1="3" y1="6" x2="3.01" y2="6" /><line x1="3" y1="12" x2="3.01" y2="12" /><line x1="3" y1="18" x2="3.01" y2="18" />',
  },
  {
    value: "shelf",
    label: "Shelf",
    icon: '<rect x="3" y="3" width="7" height="18" rx="1" /><rect x="14" y="3" width="7" height="10" rx="1" />',
  },
  {
    value: "board",
    label: "Board",
    icon: '<rect x="3" y="4" width="6" height="16" rx="1" /><rect x="11" y="4" width="6" height="10" rx="1" /><rect x="19" y="4" width="2" height="7" rx="1" />',
  },
];

// ---- layout + filters ----
// List/Shelf/Board is a persisted, remembered choice — same idea as the
// Shelf card-size toggle below, so switching kinds or reloading doesn't
// reset it back to List every time. Stats is deliberately kept out of
// this persisted value: it's a separate lens on the data, not another
// layout choice, so opening it never overwrites what List/Shelf/Board
// was last set to, and leaving it returns to that remembered layout.
const layout = ref<"list" | "shelf" | "board">(
  (localStorage.getItem("libraryLayout") as "list" | "shelf" | "board") ||
    preferences.value.library_default_layout,
);
// the server default arrives a moment after the first render
watch(
  () => preferences.value.library_default_layout,
  (v) => {
    if (!localStorage.getItem("libraryLayout")) layout.value = v;
  },
);
watch(layout, (v) => localStorage.setItem("libraryLayout", v));
// Card size for the Shelf grid, same idea as Games' S/M/L density toggle
// — persisted so it doesn't reset every visit.
const shelfCardSize = ref<"compact" | "cozy" | "large">(
  (localStorage.getItem("libraryShelfCardSize") as
    "compact" | "cozy" | "large") || "cozy",
);
watch(shelfCardSize, (v) => localStorage.setItem("libraryShelfCardSize", v));
const shelfCardMinWidth = computed(() => {
  if (shelfCardSize.value === "compact") return "150px";
  if (shelfCardSize.value === "large") return "260px";
  return "200px";
});
const viewportWidth = ref(window.innerWidth);
const libraryToolsOpen = ref(false);
const compactControls = computed(
  () =>
    viewportWidth.value <= 760 &&
    !libraryToolsOpen.value &&
    !selectMode.value &&
    !quickTourActive.value,
);
const shelfGridColumns = computed(() =>
  viewportWidth.value <= 760
    ? `repeat(${PHONE_CARD_COLUMNS[shelfCardSize.value]}, minmax(0, 1fr))`
    : `repeat(auto-fill, minmax(${shelfCardMinWidth.value}, 1fr))`,
);
// Board's cards are fixed-width flex items (each status is its own
// horizontally-scrolling row) rather than a minmax grid, so the same S/M/L
// preference maps to an explicit width instead.
const boardCardWidth = computed(() => {
  if (viewportWidth.value <= 760) {
    const columns = PHONE_CARD_COLUMNS[shelfCardSize.value];
    return `calc((100% - ${(columns - 1) * 14}px) / ${columns})`;
  }
  if (shelfCardSize.value === "compact") return "150px";
  if (shelfCardSize.value === "large") return "260px";
  return "196px";
});
const activeStatus = ref<string>("all");
const searchQuery = ref("");
let filterTimer: ReturnType<typeof setTimeout> | null = null;
function emitFilters() {
  if (filterTimer !== null) clearTimeout(filterTimer);
  filterTimer = setTimeout(() => {
    emit("filters-change", {
      ...filters.value,
      statusBucket: activeStatus.value,
    });
  }, 250);
}
type SortKey =
  | "rank"
  | "score"
  | "title"
  | "title_desc"
  | "added"
  | "year_new"
  | "year_old"
  | "progress";
const SORT_KEYS: SortKey[] = [
  "rank",
  "score",
  "title",
  "title_desc",
  "added",
  "year_new",
  "year_old",
  "progress",
];
function savedSort(): SortKey {
  try {
    const v = localStorage.getItem(`librarySort:${props.kind}`) as SortKey;
    return SORT_KEYS.includes(v) ? v : "rank";
  } catch {
    return "rank";
  }
}
const sortKey = ref<SortKey>(savedSort());
watch(sortKey, (v) => {
  try {
    localStorage.setItem(`librarySort:${props.kind}`, v);
  } catch {
    /* remembering the sort is optional */
  }
});
const selectedGenres = ref<Set<string>>(new Set());
const genreMatchAll = ref(false);
const selectedFormats = ref<Set<string>>(new Set());
const onlyFavorites = ref(false);
const onlyUnrated = ref(false);
const onlyWithNote = ref(false);
const minScore = ref<number | null>(null);
// kept as text: v-model on a number input would hand back a Number
const yearFrom = ref("");
const yearTo = ref("");
const filtersOpen = ref(false);
const SCORE_OPTIONS = [6, 7, 8, 9];

const allGenres = computed(() => {
  const set = new Set<string>();
  props.items.forEach((it) => it.genres.forEach((g) => set.add(g)));
  return [...set].sort();
});

const allFormats = computed(() => {
  const set = new Set<string>();
  props.items.forEach((it) => it.format && set.add(it.format));
  return [...set].sort();
});

// the number of separate filters in use, shown on the Filters button
const activeFilterCount = computed(
  () =>
    [
      selectedGenres.value.size > 0,
      selectedFormats.value.size > 0,
      onlyFavorites.value,
      onlyUnrated.value,
      onlyWithNote.value,
      minScore.value !== null,
      yearFrom.value.trim() !== "" || yearTo.value.trim() !== "",
    ].filter(Boolean).length,
);
// A genre chip on a title's page links here as ?genre=Action. It shows exactly
// that, not that on top of whatever filters were left on from last time.
const BASE_PATH: Record<string, string> = {
  movie: "/movies",
  tv: "/tv",
  anime: "/anime",
};
function applyLinkedFilter() {
  if (route.path !== BASE_PATH[props.kind]) return;
  const genre = route.query.genre;
  if (typeof genre !== "string" || !genre) return;
  clearFilters();
  selectedGenres.value = new Set([genre]);
  filtersOpen.value = true;
}
function clearFilters() {
  selectedGenres.value = new Set();
  selectedFormats.value = new Set();
  genreMatchAll.value = false;
  onlyFavorites.value = false;
  onlyUnrated.value = false;
  onlyWithNote.value = false;
  minScore.value = null;
  yearFrom.value = "";
  yearTo.value = "";
}

applyLinkedFilter();
// the library is kept alive, so a link can arrive while it already exists
watch(() => route.fullPath, applyLinkedFilter);

// ---- drawing a long library a screenful at a time ----
// A shelf or list of hundreds of cards is slow to open if every one is drawn
// at once, so the first screenfuls are drawn and a marker below them draws the
// next batch as it nears the screen. Search, sort and filters start over.
const RENDER_STEP = 48;
const renderLimit = ref(RENDER_STEP);
const moreSentinel = ref<HTMLElement | null>(null);
const sentinelObserver =
  typeof IntersectionObserver === "undefined"
    ? null
    : new IntersectionObserver(
        (entries) => {
          if (!entries.some((e) => e.isIntersecting)) return;
          renderLimit.value += RENDER_STEP;
          // asked again, so a marker still in view after the batch draws more
          const el = moreSentinel.value;
          if (el) {
            sentinelObserver?.unobserve(el);
            sentinelObserver?.observe(el);
          }
        },
        { rootMargin: "800px" },
      );
watch(moreSentinel, (el, old) => {
  if (old) sentinelObserver?.unobserve(old);
  if (el) sentinelObserver?.observe(el);
});
onBeforeUnmount(() => sentinelObserver?.disconnect());

// Every filter except the status tab (the Board shows the tabs as rows).
const filters = computed<LibraryFilters>(() => ({
  search: searchQuery.value,
  genres: [...selectedGenres.value],
  genreMatchAll: genreMatchAll.value,
  formats: [...selectedFormats.value],
  onlyFavorites: onlyFavorites.value,
  onlyUnrated: onlyUnrated.value,
  onlyWithNote: onlyWithNote.value,
  minScore: minScore.value,
  yearFrom: yearFrom.value,
  yearTo: yearTo.value,
}));
function matchesFilterState(it: LibraryCardVM): boolean {
  return matchesFilters(it, filters.value);
}

// Rank is generated, not manually assigned — a leaderboard position among
// everything that's been rated, highest score first. Nothing without a
// score participates, so there's no ranking to show for it yet.
const rankByItemId = computed(() => {
  // The server ranks the whole library; the loaded items alone would give
  // a title the wrong rank whenever it is paginated or searched.
  if (props.scoreRanks && Object.keys(props.scoreRanks).length) {
    return new Map(Object.entries(props.scoreRanks));
  }
  const ranked = props.items
    .filter((it) => it.score !== null)
    .slice()
    .sort((a, b) => (b.score as number) - (a.score as number));
  const map = new Map<string, number>();
  ranked.forEach((it, idx) => map.set(it.id, idx + 1));
  return map;
});
function computedRank(it: LibraryCardVM): number | null {
  return rankByItemId.value.get(it.id) ?? null;
}

const statusCounts = computed<Record<string, number>>(() => ({
  all: props.total,
  ...props.statusCounts,
}));

function progressPct(it: LibraryCardVM): number {
  if (!it.isEpisodic) return it.watched > 0 ? 100 : 0;
  return it.total ? (it.watched / it.total) * 100 : 0;
}

const filteredItems = computed(() => {
  let list = props.items;
  if (activeStatus.value !== "all") {
    list = list.filter((it) => statusBucket(it.status) === activeStatus.value);
  }
  list = list.filter(matchesFilterState);
  const sorted = [...list];
  const year = (it: LibraryCardVM) =>
    it.releaseYear ? parseInt(it.releaseYear, 10) : null;
  // titles missing the sorted value always go last, whichever direction
  const byNullable = (
    value: (it: LibraryCardVM) => number | null,
    direction: 1 | -1,
  ) =>
    sorted.sort((a, b) => {
      const va = value(a);
      const vb = value(b);
      if (va === null && vb === null) return a.title.localeCompare(b.title);
      if (va === null) return 1;
      if (vb === null) return -1;
      return (va - vb) * direction || a.title.localeCompare(b.title);
    });
  if (sortKey.value === "title") {
    sorted.sort((a, b) => a.title.localeCompare(b.title));
  } else if (sortKey.value === "title_desc") {
    sorted.sort((a, b) => b.title.localeCompare(a.title));
  } else if (sortKey.value === "progress") {
    sorted.sort((a, b) => progressPct(b) - progressPct(a));
  } else if (sortKey.value === "score") {
    byNullable((it) => it.score, -1);
  } else if (sortKey.value === "added") {
    byNullable((it) => it.addedAt ?? null, -1);
  } else if (sortKey.value === "year_new") {
    byNullable(year, -1);
  } else if (sortKey.value === "year_old") {
    byNullable(year, 1);
  } else {
    sorted.sort((a, b) => {
      const ra = computedRank(a) ?? 999999;
      const rb = computedRank(b) ?? 999999;
      return ra - rb || a.title.localeCompare(b.title);
    });
  }
  return sorted;
});
const renderedItems = computed(() =>
  filteredItems.value.slice(0, renderLimit.value),
);
watch([searchQuery, sortKey, activeStatus, filters, layout], () => {
  renderLimit.value = RENDER_STEP;
});

const boardPageStarts = reactive<Record<string, number>>({});
const boardViewportWidth = ref(0);
const libraryContainer = ref<HTMLElement | null>(null);
const boardVisibleCount = computed(() => {
  if (viewportWidth.value <= 760)
    return PHONE_CARD_COLUMNS[shelfCardSize.value];
  const cardWidth =
    shelfCardSize.value === "compact"
      ? 150
      : shelfCardSize.value === "large"
        ? 260
        : 196;
  return Math.max(
    1,
    Math.floor((boardViewportWidth.value + 14) / (cardWidth + 14)) || 1,
  );
});
function resetBoardPages() {
  Object.keys(boardPageStarts).forEach((key) => delete boardPageStarts[key]);
}
function moveBoard(status: string, direction: -1 | 1, available: number) {
  const current = boardPageStarts[status] ?? 0;
  if (direction < 0) {
    boardPageStarts[status] = Math.max(0, current - available);
    return;
  }
  if (
    current + available >= props.items.length &&
    props.items.length < props.total
  ) {
    emit("load-more");
  }
  boardPageStarts[status] = current + available;
}
watch([activeStatus, filters], () => {
  resetBoardPages();
  emitFilters();
});
watch(boardViewportWidth, resetBoardPages);
function updateBoardViewport() {
  viewportWidth.value = window.innerWidth;
  const element = libraryContainer.value;
  if (!element) return;
  const style = getComputedStyle(element);
  boardViewportWidth.value =
    element.clientWidth -
    parseFloat(style.paddingLeft) -
    parseFloat(style.paddingRight);
}
let measureFrame = 0;
const libraryObserver = new ResizeObserver(() => {
  cancelAnimationFrame(measureFrame);
  measureFrame = requestAnimationFrame(updateBoardViewport);
});
onMounted(() => {
  updateBoardViewport();
  if (libraryContainer.value) libraryObserver.observe(libraryContainer.value);
});
onActivated(() => {
  updateBoardViewport();
  window.addEventListener("resize", updateBoardViewport);
  if (libraryContainer.value) libraryObserver.observe(libraryContainer.value);
});
onDeactivated(() => {
  window.removeEventListener("resize", updateBoardViewport);
  libraryObserver.disconnect();
  cancelAnimationFrame(measureFrame);
});
watch(shelfCardSize, () => requestAnimationFrame(updateBoardViewport));
onBeforeUnmount(() => {
  window.removeEventListener("resize", updateBoardViewport);
  libraryObserver.disconnect();
  cancelAnimationFrame(measureFrame);
});

const boardGroups = computed(() => {
  const statuses =
    activeStatus.value === "all"
      ? STATUSES
      : STATUSES.filter((s) => s.key === activeStatus.value);
  return statuses
    .map((s) => {
      let rowItems = props.items.filter(
        (it) => statusBucket(it.status) === s.key,
      );
      rowItems = rowItems.filter(matchesFilterState);
      const start = boardPageStarts[s.key] ?? 0;
      return {
        status: s,
        rowItems,
        visibleItems: rowItems.slice(start, start + boardVisibleCount.value),
        start,
      };
    })
    .filter((g) => g.rowItems.length > 0);
});

function toggleFormat(f: string) {
  const next = new Set(selectedFormats.value);
  if (next.has(f)) next.delete(f);
  else next.add(f);
  selectedFormats.value = next;
}

function toggleGenre(g: string) {
  const next = new Set(selectedGenres.value);
  if (next.has(g)) next.delete(g);
  else next.add(g);
  selectedGenres.value = next;
}

// ---- select / bulk edit ----
const selectMode = ref(false);
const selectedIds = ref<Set<string>>(new Set());
const bulkStatusValue = ref("");

function toggleSelectMode() {
  selectMode.value = !selectMode.value;
  if (!selectMode.value) selectedIds.value = new Set();
}
function toggleSelectItem(id: string) {
  const next = new Set(selectedIds.value);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  selectedIds.value = next;
}
function clearSelection() {
  selectedIds.value = new Set();
}
function bulkApplyStatus() {
  if (!bulkStatusValue.value) return;
  emit(
    "bulk-set-status",
    [...selectedIds.value],
    bucketToReal(bulkStatusValue.value),
  );
  bulkStatusValue.value = "";
}
function bulkFavorite() {
  emit("bulk-favorite", [...selectedIds.value]);
}
function bulkDelete() {
  emit("bulk-delete", [...selectedIds.value]);
  selectedIds.value = new Set();
}

function handleCardClick(it: LibraryCardVM) {
  if (selectMode.value) {
    toggleSelectItem(it.id);
    return;
  }
  router.push(props.detailRoute(it.id));
}

// ---- notes modal ----
const cardActionsOpen = ref(false);
const cardActionsTarget = ref<LibraryCardVM | null>(null);
function openCardActions(it: LibraryCardVM) {
  cardActionsTarget.value = it;
  cardActionsOpen.value = true;
}

const noteOpen = ref(false);
const noteTargetId = ref<string | null>(null);
const noteText = ref("");
function openNote(it: LibraryCardVM) {
  noteTargetId.value = it.id;
  noteText.value = it.note ?? "";
  noteOpen.value = true;
}
function closeNote() {
  noteOpen.value = false;
  noteTargetId.value = null;
}
function saveNote() {
  if (!noteTargetId.value) return;
  emit("save-note", noteTargetId.value, noteText.value.trim() || null);
  closeNote();
}

// ---- episode advance ----
// No cap on how far watched can go past the known total — metadata's
// episode count is often wrong or stale, and a rewatch can outrun it too.
function advanceEpisode(it: LibraryCardVM) {
  if (!it.canAdvance) return;
  emit("advance-episode", it.id);
  const nowWatched = it.watched + 1;
  const justFinished = it.total !== null && nowWatched >= it.total;
  if (justFinished && it.score === null) {
    openFinishRating(it, statusBucket(it.status), nowWatched, it.total);
  }
}

// ---- "you finished it" rating prompt ----
// Only appears once something is actually complete (episodes caught up to
// the known total, or the status is edited to Completed) rather than on
// every single episode tick — a rating is worth asking for once, not
// nagging for every checkbox click.
const finishOpen = ref(false);
const finishTargetId = ref<string | null>(null);
const finishTitle = ref("");
const finishPoster = ref<string | null>(null);
const finishScore = ref<number | null>(null);
const finishBucket = ref("completed");
const finishWatched = ref(0);
const finishTotalEpisodes = ref<number | null>(null);
function openFinishRating(
  it: LibraryCardVM,
  bucket: string,
  watched: number,
  totalEpisodes: number | null,
) {
  finishTargetId.value = it.id;
  finishTitle.value = it.title;
  finishPoster.value = it.poster;
  finishScore.value = null;
  finishBucket.value = bucket;
  finishWatched.value = watched;
  finishTotalEpisodes.value = totalEpisodes;
  finishOpen.value = true;
}
function closeFinish() {
  finishOpen.value = false;
  finishTargetId.value = null;
}
function stepFinishScore(delta: number) {
  const base = finishScore.value ?? 0;
  finishScore.value = Math.max(
    0,
    Math.min(10, Math.round((base + delta) * 10) / 10),
  );
}
function finishSave() {
  if (!finishTargetId.value) return;
  emit("save-edit", finishTargetId.value, {
    status: bucketToReal(finishBucket.value),
    score: finishScore.value,
    watched: finishWatched.value,
    totalEpisodes: finishTotalEpisodes.value,
    seen: finishWatched.value > 0,
  });
  closeFinish();
}

// ---- small edit modal ----
const editOpen = ref(false);
const editTargetId = ref<string | null>(null);
const editForm = reactive<EditForm>({
  status: "plan",
  score: null,
  watched: 0,
  totalEpisodes: null,
  seen: false,
});
function openEdit(it: LibraryCardVM) {
  editTargetId.value = it.id;
  editForm.status = statusBucket(it.status);
  editForm.score = it.score;
  editForm.watched = it.watched;
  editForm.totalEpisodes = it.total;
  editForm.seen = it.watched > 0;
  editOpen.value = true;
}
function closeEdit() {
  editOpen.value = false;
  editTargetId.value = null;
}
function saveEdit() {
  if (!editTargetId.value) return;
  const target = props.items.find((i) => i.id === editTargetId.value);
  const wasCompleted = target
    ? statusBucket(target.status) === "completed"
    : false;
  const justCompleted = editForm.status === "completed" && !wasCompleted;
  const id = editTargetId.value;
  const totalEpisodes = editForm.totalEpisodes;
  // Setting status to Completed catches episodes watched up to the known
  // total automatically — no reason to make someone type in the number
  // themselves when the app already knows it.
  const watched =
    editForm.status === "completed" && totalEpisodes !== null
      ? totalEpisodes
      : editForm.watched;
  const scoreAlreadySet = editForm.score !== null;
  emit("save-edit", id, {
    ...editForm,
    watched,
    status: bucketToReal(editForm.status),
  });
  closeEdit();
  if (target && justCompleted && !scoreAlreadySet) {
    openFinishRating(target, "completed", watched, totalEpisodes);
  }
}

// ---- quick add (two-step: search -> fill-out form) ----
const quickAddOpen = ref(false);
const quickAddStep = ref<"search" | "form">("search");
const quickAddQuery = ref("");
const quickAddResults = ref<SearchResultVM[]>([]);
const quickAddProviderErrors = ref<string[]>([]);
const quickAddSearching = ref(false);
const quickAddPick = ref<SearchResultVM | null>(null);
const quickAddForm = reactive<QuickAddForm>({
  status: "plan",
  watched: 0,
  seen: false,
  score: null,
  startDate: null,
  endDate: null,
});
const quickAddSaving = ref(false);

function openQuickAdd() {
  quickAddStep.value = "search";
  quickAddQuery.value = "";
  quickAddResults.value = [];
  quickAddProviderErrors.value = [];
  quickAddOpen.value = true;
}
function onEscape(e: KeyboardEvent) {
  if (e.key === "Escape" && quickAddOpen.value) closeQuickAdd();
}
onMounted(() => window.addEventListener("keydown", onEscape));
onBeforeUnmount(() => window.removeEventListener("keydown", onEscape));
function closeQuickAdd() {
  quickAddOpen.value = false;
  quickAddPick.value = null;
}
async function runQuickAddSearch() {
  if (!quickAddQuery.value.trim()) {
    quickAddResults.value = [];
    return;
  }
  quickAddSearching.value = true;
  try {
    const { results, providerErrors } = await props.search(quickAddQuery.value);
    quickAddResults.value = results;
    quickAddProviderErrors.value = providerErrors;
  } finally {
    quickAddSearching.value = false;
  }
}
function pickQuickAddResult(result: SearchResultVM) {
  quickAddPick.value = result;
  quickAddForm.status = "plan";
  quickAddForm.watched = 0;
  quickAddForm.seen = false;
  quickAddForm.score = null;
  quickAddForm.startDate = null;
  quickAddForm.endDate = null;
  quickAddStep.value = "form";
}
function quickAddBackToSearch() {
  quickAddStep.value = "search";
}
// The max attribute alone doesn't stop someone from typing past it — a
// fresh add has no legitimate reason to start above the known total
// (unlike the ongoing rewatch case, where advancing past it is allowed).
function clampQuickAddWatched() {
  const max = quickAddPick.value?.episodeTotal;
  if (max !== null && max !== undefined && quickAddForm.watched > max) {
    quickAddForm.watched = max;
  }
}
async function saveQuickAdd() {
  if (!quickAddPick.value) return;
  quickAddSaving.value = true;
  // Same as the edit modal: picking Completed catches episodes watched up
  // to the known total automatically instead of leaving it at 0.
  const watched =
    quickAddForm.status === "completed" &&
    quickAddPick.value.episodeTotal !== null
      ? quickAddPick.value.episodeTotal
      : quickAddForm.watched;
  try {
    await props.createFromResult(quickAddPick.value, {
      ...quickAddForm,
      watched,
      status: bucketToReal(quickAddForm.status),
    });
    closeQuickAdd();
  } finally {
    quickAddSaving.value = false;
  }
}

defineExpose({ openQuickAdd });
</script>

<template>
  <div class="lib-root" :class="{ 'compact-controls': compactControls }">
    <MediaTopBar :active="kind">
      <template #actions>
        <SegmentedTabs
          :options="LAYOUT_OPTIONS"
          :model-value="layout"
          aria-label="Layout"
          @update:model-value="layout = $event as 'list' | 'shelf' | 'board'"
        />
      </template>
    </MediaTopBar>

    <div ref="libraryContainer" class="lib-inner">
      <div class="page-head">
        <div>
          <h1>
            {{
              kind === "movie" ? "Movies" : kind === "tv" ? "TV Shows" : "Anime"
            }}
          </h1>
          <div class="sub">
            {{ total }} {{ total === 1 ? "title" : "titles" }}
          </div>
        </div>
        <button
          v-if="viewportWidth <= 760"
          type="button"
          class="btn-outline library-tools-toggle"
          :aria-expanded="!compactControls"
          :aria-label="compactControls ? 'Library controls' : 'Hide controls'"
          @click="libraryToolsOpen = !libraryToolsOpen"
        >
          {{ compactControls ? "Controls" : "Hide controls" }}
        </button>
        <div class="head-actions" style="display: flex; gap: 8px">
          <button
            type="button"
            class="select-btn"
            :class="{ on: selectMode }"
            @click="toggleSelectMode"
          >
            {{ selectMode ? "Done" : "Select" }}
          </button>
          <button
            type="button"
            class="add-btn"
            :disabled="selectMode"
            @click="openQuickAdd"
            data-shortcut="create"
          >
            {{ addLabel }}
          </button>
          <slot name="actions"></slot>
        </div>
      </div>

      <div v-if="selectedIds.size" class="bulk-bar">
        <span class="count">{{ selectedIds.size }} selected</span>
        <select v-model="bulkStatusValue" @change="bulkApplyStatus">
          <option value="">Set status to...</option>
          <option v-for="s in STATUSES" :key="s.key" :value="s.key">
            {{ s.label }}
          </option>
        </select>
        <button type="button" class="btn-outline" @click="bulkFavorite">
          Toggle Favorite
        </button>
        <div class="spacer"></div>
        <button type="button" class="btn-outline" @click="bulkDelete">
          Remove from library
        </button>
        <button type="button" class="btn-outline" @click="clearSelection">
          Clear
        </button>
      </div>

      <div class="toolbar">
        <div class="search-wrap">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
          >
            <circle cx="11" cy="11" r="7" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            v-model="searchQuery"
            data-shortcut="search"
            placeholder="Search your library..."
            aria-label="Search your library"
          />
        </div>
        <select v-model="sortKey" class="sort-select" aria-label="Sort by">
          <option value="rank">Sort: Rank</option>
          <option value="score">Sort: Score, highest first</option>
          <option value="title">Sort: Title A–Z</option>
          <option value="title_desc">Sort: Title Z–A</option>
          <option value="added">Sort: Recently added</option>
          <option value="year_new">Sort: Release year, newest</option>
          <option value="year_old">Sort: Release year, oldest</option>
          <option value="progress">Sort: Progress</option>
        </select>
        <button
          type="button"
          class="filter-btn"
          :class="{ 'active-filter': activeFilterCount }"
          @click="filtersOpen = !filtersOpen"
        >
          Filters
          <span v-if="activeFilterCount" class="count">{{
            activeFilterCount
          }}</span>
        </button>
        <div
          v-if="layout === 'shelf' || layout === 'board'"
          class="card-size-toggle"
          title="Card size"
        >
          <button
            v-for="s in ['compact', 'cozy', 'large']"
            :key="s"
            type="button"
            class="card-size-button"
            :class="{ active: shelfCardSize === s }"
            :title="s"
            @click="shelfCardSize = s as typeof shelfCardSize"
          >
            {{ s === "compact" ? "S" : s === "cozy" ? "M" : "L" }}
          </button>
        </div>
      </div>
      <div v-if="filtersOpen" class="filter-panel">
        <div class="filter-group">
          <span class="filter-label">Show</span>
          <button
            type="button"
            class="genre-chip"
            :class="{ selected: onlyFavorites }"
            @click="onlyFavorites = !onlyFavorites"
          >
            Favorites
          </button>
          <button
            type="button"
            class="genre-chip"
            :class="{ selected: onlyUnrated }"
            @click="onlyUnrated = !onlyUnrated"
          >
            Not scored yet
          </button>
          <button
            type="button"
            class="genre-chip"
            :class="{ selected: onlyWithNote }"
            @click="onlyWithNote = !onlyWithNote"
          >
            Has a note
          </button>
        </div>
        <div class="filter-group">
          <span class="filter-label">Score</span>
          <button
            v-for="s in SCORE_OPTIONS"
            :key="s"
            type="button"
            class="genre-chip"
            :class="{ selected: minScore === s }"
            @click="minScore = minScore === s ? null : s"
          >
            {{ s }}+
          </button>
        </div>
        <div class="filter-group">
          <span class="filter-label">Year</span>
          <input
            :value="yearFrom"
            type="number"
            class="year-input"
            placeholder="From"
            aria-label="Released from year"
            @input="yearFrom = ($event.target as HTMLInputElement).value"
          />
          <span class="filter-dash">to</span>
          <input
            :value="yearTo"
            type="number"
            class="year-input"
            placeholder="To"
            aria-label="Released up to year"
            @input="yearTo = ($event.target as HTMLInputElement).value"
          />
        </div>
        <div v-if="allFormats.length > 1" class="filter-group">
          <span class="filter-label">Format</span>
          <button
            v-for="f in allFormats"
            :key="f"
            type="button"
            class="genre-chip"
            :class="{ selected: selectedFormats.has(f) }"
            @click="toggleFormat(f)"
          >
            {{ f }}
          </button>
        </div>
        <div v-if="allGenres.length" class="filter-group">
          <span class="filter-label">Genre</span>
          <button
            v-for="g in allGenres"
            :key="g"
            type="button"
            class="genre-chip"
            :class="{ selected: selectedGenres.has(g) }"
            @click="toggleGenre(g)"
          >
            {{ g }}
          </button>
          <button
            v-if="selectedGenres.size > 1"
            type="button"
            class="genre-chip match-mode"
            :class="{ selected: genreMatchAll }"
            title="Require every selected genre instead of any of them"
            @click="genreMatchAll = !genreMatchAll"
          >
            {{ genreMatchAll ? "Match all" : "Match any" }}
          </button>
        </div>
        <div class="filter-foot">
          <span class="filter-result"
            >{{ filteredItems.length }} of {{ total }} loaded/matching</span
          >
          <button
            v-if="activeFilterCount"
            type="button"
            class="filter-clear"
            @click="clearFilters"
          >
            Clear filters
          </button>
        </div>
      </div>

      <div class="status-tabs">
        <button
          type="button"
          class="status-tab"
          :class="{ active: activeStatus === 'all' }"
          @click="activeStatus = 'all'"
        >
          All <span class="n">{{ statusCounts.all }}</span>
        </button>
        <button
          v-for="s in STATUSES"
          :key="s.key"
          type="button"
          class="status-tab"
          :class="{ active: activeStatus === s.key }"
          @click="activeStatus = s.key"
        >
          {{ s.label }} <span class="n">{{ statusCounts[s.key] }}</span>
        </button>
      </div>

      <div class="body">
        <p v-if="loading" class="empty-state">Loading…</p>
        <p v-else-if="error" class="empty-state error">{{ error }}</p>

        <!-- ===== STATS ===== -->
        <!-- ===== LIST ===== -->
        <template v-else-if="layout === 'list'">
          <p v-if="!filteredItems.length" class="empty-state">
            Nothing matches. Try a different filter or search.
          </p>
          <div v-else class="list-scroll">
            <div class="list-row-header">
              <span></span><span>Title</span><span></span><span>Progress</span
              ><span>Score</span><span>Rank</span><span>Status</span>
            </div>
            <div class="list-rows">
              <div
                v-for="it in renderedItems"
                :key="it.id"
                class="list-row"
                @click="handleCardClick(it)"
              >
                <div class="list-thumb-wrap">
                  <div class="list-thumb">
                    <img
                      v-if="it.poster"
                      :src="it.poster"
                      :alt="it.title"
                      loading="lazy"
                      decoding="async"
                    />
                  </div>
                  <div
                    v-if="selectMode"
                    class="select-checkbox"
                    :class="{ checked: selectedIds.has(it.id) }"
                    @click.stop="toggleSelectItem(it.id)"
                  >
                    <CheckIcon v-if="selectedIds.has(it.id)" />
                  </div>
                </div>
                <div class="list-title-col">
                  <div class="list-title">{{ it.title }}</div>
                  <div class="list-type">
                    {{ it.format ?? typeLabel
                    }}<template v-if="it.releaseYear">
                      · {{ it.releaseYear }}</template
                    >
                  </div>
                  <div class="airing-tag" :class="{ invisible: !it.airing }">
                    <span class="dot"></span>Airing
                  </div>
                </div>
                <div class="icon-cluster no-card-click">
                  <button
                    type="button"
                    class="icon-btn"
                    :class="{ active: it.favorite }"
                    title="Favorite"
                    @click.stop="emit('toggle-favorite', it.id)"
                  >
                    <HeartIcon :filled="it.favorite" />
                  </button>
                  <button
                    type="button"
                    class="icon-btn"
                    :class="{ active: it.note }"
                    :title="it.note ? 'Edit note' : 'Add note'"
                    @click.stop="openNote(it)"
                  >
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    >
                      <path d="M14 3v4a1 1 0 0 0 1 1h4" />
                      <path
                        d="M17 21H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7l5 5v11a2 2 0 0 1-2 2z"
                      />
                      <line x1="8" y1="13" x2="16" y2="13" />
                      <line x1="8" y1="17" x2="13" y2="17" />
                    </svg>
                  </button>
                  <button
                    type="button"
                    class="icon-btn"
                    title="Edit"
                    @click.stop="openEdit(it)"
                  >
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    >
                      <path d="M12 20h9" />
                      <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" />
                    </svg>
                  </button>
                </div>
                <div class="list-progress">
                  <div class="list-progress-label">{{ it.progressLabel }}</div>
                  <button
                    v-if="it.canAdvance"
                    type="button"
                    class="plus-btn no-card-click"
                    title="Mark next episode watched"
                    @click.stop="advanceEpisode(it)"
                  >
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2.5"
                      stroke-linecap="round"
                    >
                      <line x1="12" y1="5" x2="12" y2="19" />
                      <line x1="5" y1="12" x2="19" y2="12" />
                    </svg>
                  </button>
                  <div v-else class="plus-btn-spacer"></div>
                </div>
                <div class="score-tag" :class="{ empty: !it.score }">
                  {{ it.score ? `★ ${it.score}` : "–" }}
                </div>
                <div class="rank-cell">
                  <span v-if="computedRank(it)" class="rank-badge"
                    >#{{ computedRank(it) }}</span
                  >
                  <span v-else class="rank-empty">–</span>
                </div>
                <div class="status-cell">
                  <span class="pill" :class="statusBucket(it.status)">{{
                    statusBucketLabel(it.status)
                  }}</span>
                </div>
              </div>
            </div>
          </div>
          <div
            v-if="renderLimit < filteredItems.length"
            ref="moreSentinel"
            class="render-sentinel"
          ></div>
          <div v-if="items.length < total" class="load-more-indicator">
            {{ loading ? "Loading more…" : "Scroll for more" }}
          </div>
        </template>

        <!-- ===== SHELF ===== -->
        <template v-else-if="layout === 'shelf'">
          <p v-if="!filteredItems.length" class="empty-state">
            Nothing matches. Try a different filter or search.
          </p>
          <div
            v-else
            class="shelf-grid"
            :style="{
              gridTemplateColumns: shelfGridColumns,
            }"
          >
            <div
              v-for="it in renderedItems"
              :key="it.id"
              class="shelf-card"
              @click="handleCardClick(it)"
              @mouseleave="blurOnLeave"
            >
              <div class="shelf-art-wrap">
                <div class="shelf-art">
                  <img
                    v-if="it.poster"
                    :src="it.poster"
                    :alt="it.title"
                    loading="lazy"
                    decoding="async"
                  />
                </div>
                <div
                  v-if="selectMode"
                  class="select-checkbox"
                  :class="{ checked: selectedIds.has(it.id) }"
                  @click.stop="toggleSelectItem(it.id)"
                >
                  <CheckIcon v-if="selectedIds.has(it.id)" />
                </div>
                <span v-if="computedRank(it)" class="shelf-rank rank-badge"
                  >#{{ computedRank(it) }}</span
                >

                <div v-if="!selectMode" class="sc-actions no-card-click">
                  <button
                    type="button"
                    class="sc-action sc-more"
                    :aria-label="`Actions for ${it.title}`"
                    @click.stop="openCardActions(it)"
                  >
                    <svg
                      viewBox="0 0 24 24"
                      fill="currentColor"
                      aria-hidden="true"
                    >
                      <circle cx="5" cy="12" r="2" />
                      <circle cx="12" cy="12" r="2" />
                      <circle cx="19" cy="12" r="2" />
                    </svg>
                  </button>
                  <button
                    v-if="it.canAdvance"
                    type="button"
                    class="sc-action"
                    title="Mark next episode watched"
                    @click.stop="advanceEpisode(it)"
                  >
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2.5"
                      stroke-linecap="round"
                    >
                      <line x1="12" y1="5" x2="12" y2="19" />
                      <line x1="5" y1="12" x2="19" y2="12" />
                    </svg>
                  </button>
                  <button
                    type="button"
                    class="sc-action"
                    :class="{ active: it.favorite }"
                    title="Favorite"
                    @click.stop="emit('toggle-favorite', it.id)"
                  >
                    <HeartIcon :filled="it.favorite" />
                  </button>
                  <button
                    type="button"
                    class="sc-action"
                    :class="{ active: it.note }"
                    :title="it.note ? 'Edit note' : 'Add note'"
                    @click.stop="openNote(it)"
                  >
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    >
                      <path d="M14 3v4a1 1 0 0 0 1 1h4" />
                      <path
                        d="M17 21H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7l5 5v11a2 2 0 0 1-2 2z"
                      />
                      <line x1="8" y1="13" x2="16" y2="13" />
                      <line x1="8" y1="17" x2="13" y2="17" />
                    </svg>
                  </button>
                  <button
                    type="button"
                    class="sc-action"
                    title="Edit"
                    @click.stop="openEdit(it)"
                  >
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    >
                      <path d="M12 20h9" />
                      <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" />
                    </svg>
                  </button>
                </div>
              </div>
              <div class="shelf-body">
                <div class="shelf-title-row">
                  <div class="shelf-title">{{ it.title }}</div>
                  <div class="score-tag" :class="{ empty: !it.score }">
                    {{ it.score ? `★ ${it.score}` : "–" }}
                  </div>
                </div>
                <div class="shelf-meta-row">
                  <span class="shelf-type">{{ it.format ?? typeLabel }}</span>
                  <span class="shelf-sub">{{ it.progressLabel }}</span>
                </div>
                <div class="shelf-progress-row">
                  <div class="list-progress-track">
                    <div
                      class="list-progress-fill"
                      :style="{ width: progressPct(it) + '%' }"
                    ></div>
                  </div>
                  <div v-if="it.airing" class="airing-tag">
                    <span class="dot"></span>Airing
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div
            v-if="renderLimit < filteredItems.length"
            ref="moreSentinel"
            class="render-sentinel"
          ></div>
          <div v-if="items.length < total" class="load-more-indicator">
            {{ loading ? "Loading more…" : "Scroll for more" }}
          </div>
        </template>

        <!-- ===== BOARD ===== -->
        <template v-else-if="layout === 'board'">
          <p v-if="!boardGroups.length" class="empty-state">
            Nothing matches. Try a different filter or search.
          </p>
          <div
            v-for="group in boardGroups"
            :key="group.status.key"
            class="board-section"
          >
            <div class="board-heading">
              <h2>{{ group.status.label }}</h2>
              <span class="n">{{ group.rowItems.length }}</span>
              <div class="board-nav">
                <button
                  type="button"
                  :disabled="group.start === 0"
                  @click="moveBoard(group.status.key, -1, boardVisibleCount)"
                >
                  ‹
                </button>
                <button
                  type="button"
                  :disabled="
                    group.start + boardVisibleCount >= group.rowItems.length &&
                    items.length >= total
                  "
                  @click="moveBoard(group.status.key, 1, boardVisibleCount)"
                >
                  ›
                </button>
              </div>
            </div>
            <div class="board-shelf">
              <div
                v-for="it in group.visibleItems"
                :key="it.id"
                class="board-card"
                :style="{ width: boardCardWidth }"
                @click="handleCardClick(it)"
              >
                <div class="board-art-wrap">
                  <div class="board-art">
                    <img
                      v-if="it.poster"
                      :src="it.poster"
                      :alt="it.title"
                      loading="lazy"
                      decoding="async"
                    />
                  </div>
                  <div
                    v-if="selectMode"
                    class="select-checkbox"
                    :class="{ checked: selectedIds.has(it.id) }"
                    @click.stop="toggleSelectItem(it.id)"
                  >
                    <CheckIcon v-if="selectedIds.has(it.id)" />
                  </div>
                  <span v-if="computedRank(it)" class="board-rank rank-badge"
                    >#{{ computedRank(it) }}</span
                  >
                  <div v-if="!selectMode" class="sc-actions no-card-click">
                    <button
                      type="button"
                      class="sc-action sc-more"
                      :aria-label="`Actions for ${it.title}`"
                      @click.stop="openCardActions(it)"
                    >
                      <svg
                        viewBox="0 0 24 24"
                        fill="currentColor"
                        aria-hidden="true"
                      >
                        <circle cx="5" cy="12" r="2" />
                        <circle cx="12" cy="12" r="2" />
                        <circle cx="19" cy="12" r="2" />
                      </svg>
                    </button>
                  </div>
                </div>
                <div class="board-title-row">
                  <div class="board-title">{{ it.title }}</div>
                  <span class="score-tag" :class="{ empty: !it.score }">{{
                    it.score ? `★ ${it.score}` : "–"
                  }}</span>
                </div>
                <div class="shelf-type">{{ it.format ?? typeLabel }}</div>
                <div v-if="it.releaseYear" class="shelf-year">
                  {{ it.releaseYear }}
                </div>
                <div class="board-progress-row">
                  <div class="list-progress-track">
                    <div
                      class="list-progress-fill"
                      :style="{ width: progressPct(it) + '%' }"
                    ></div>
                  </div>
                  <div class="board-progress-info">
                    <span class="shelf-sub">{{ it.progressLabel }}</span>
                    <button
                      v-if="it.canAdvance"
                      type="button"
                      class="plus-btn no-card-click"
                      title="Mark next episode watched"
                      @click.stop="advanceEpisode(it)"
                    >
                      <svg
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2.5"
                        stroke-linecap="round"
                      >
                        <line x1="12" y1="5" x2="12" y2="19" />
                        <line x1="5" y1="12" x2="19" y2="12" />
                      </svg>
                    </button>
                  </div>
                  <div v-if="it.airing" class="airing-tag">
                    <span class="dot"></span>Airing
                  </div>
                </div>
                <div class="board-footer-row">
                  <div class="icon-cluster shelf-icon-cluster no-card-click">
                    <button
                      type="button"
                      class="icon-btn"
                      :class="{ active: it.favorite }"
                      title="Favorite"
                      @click.stop="emit('toggle-favorite', it.id)"
                    >
                      <HeartIcon :filled="it.favorite" />
                    </button>
                    <button
                      type="button"
                      class="icon-btn"
                      :class="{ active: it.note }"
                      :title="it.note ? 'Edit note' : 'Add note'"
                      @click.stop="openNote(it)"
                    >
                      <svg
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      >
                        <path d="M14 3v4a1 1 0 0 0 1 1h4" />
                        <path
                          d="M17 21H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7l5 5v11a2 2 0 0 1-2 2z"
                        />
                        <line x1="8" y1="13" x2="16" y2="13" />
                        <line x1="8" y1="17" x2="13" y2="17" />
                      </svg>
                    </button>
                    <button
                      type="button"
                      class="icon-btn"
                      title="Edit"
                      @click.stop="openEdit(it)"
                    >
                      <svg
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      >
                        <path d="M12 20h9" />
                        <path
                          d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"
                        />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </template>
      </div>
    </div>

    <!-- ===== Notes modal ===== -->
    <UiModal
      v-if="cardActionsOpen"
      @close="cardActionsOpen = false"
      :title="`Actions for ${cardActionsTarget?.title ?? 'media'}`"
    >
      <div v-if="cardActionsTarget" class="compact-card-actions">
        <button
          v-if="cardActionsTarget.canAdvance"
          type="button"
          class="btn-outline"
          @click="
            cardActionsOpen = false;
            advanceEpisode(cardActionsTarget);
          "
        >
          Mark next episode watched
        </button>
        <button
          type="button"
          class="btn-outline"
          @click="
            cardActionsOpen = false;
            emit('toggle-favorite', cardActionsTarget.id);
          "
        >
          {{ cardActionsTarget.favorite ? "Remove favorite" : "Add favorite" }}
        </button>
        <button
          type="button"
          class="btn-outline"
          @click="
            cardActionsOpen = false;
            openNote(cardActionsTarget);
          "
        >
          {{ cardActionsTarget.note ? "Edit note" : "Add note" }}
        </button>
        <button
          type="button"
          class="btn-outline"
          @click="
            cardActionsOpen = false;
            openEdit(cardActionsTarget);
          "
        >
          Edit media
        </button>
      </div>
    </UiModal>

    <UiModal
      v-if="noteOpen"
      title="Notes"
      description="Only visible to you."
      @close="closeNote"
    >
      <div class="media-modal-content">
        <textarea
          v-model="noteText"
          aria-label="Personal media notes"
          placeholder="Nothing written yet: first impressions, things to remember, why you dropped it..."
        ></textarea>
        <div class="modal-actions">
          <button type="button" class="btn-outline" @click="closeNote">
            Cancel
          </button>
          <button type="button" class="btn-solid" @click="saveNote">
            Save
          </button>
        </div>
      </div>
    </UiModal>

    <!-- ===== "You finished it" rating prompt ===== -->
    <UiModal
      v-if="finishOpen"
      title="Rating"
      description="Give it a rating, or skip for now."
      @close="closeFinish"
    >
      <div class="media-modal-content finish-card">
        <div
          v-if="finishPoster"
          class="finish-poster"
          :style="{ backgroundImage: `url(${finishPoster})` }"
        ></div>
        <div class="finish-body">
          <div class="finish-eyebrow">You finished it</div>
          <h3>{{ finishTitle }}</h3>

          <div class="decimal-rate finish-rate">
            <button
              type="button"
              aria-label="Decrease rating"
              @click="stepFinishScore(-0.5)"
            >
              −
            </button>
            <input
              v-model.number="finishScore"
              aria-label="Completion rating"
              type="number"
              min="0"
              max="10"
              step="0.1"
              placeholder="–"
            />
            <span class="of10">/ 10</span>
            <button
              type="button"
              aria-label="Increase rating"
              @click="stepFinishScore(0.5)"
            >
              +
            </button>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn-outline" @click="closeFinish">
              Skip
            </button>
            <button type="button" class="btn-solid" @click="finishSave">
              Save rating
            </button>
          </div>
        </div>
      </div>
    </UiModal>

    <!-- ===== Small edit modal ===== -->
    <UiModal
      v-if="editOpen"
      title="Quick edit"
      description="Update status, rating and progress."
      @close="closeEdit"
    >
      <div class="media-modal-content">
        <div class="qa-field-grid">
          <label class="qa-field">
            <span>Status</span>
            <select v-model="editForm.status">
              <option v-for="s in STATUSES" :key="s.key" :value="s.key">
                {{ s.label }}
              </option>
            </select>
          </label>
          <label
            v-if="items.find((i) => i.id === editTargetId)?.isEpisodic"
            class="qa-field"
          >
            <span>Episodes watched</span>
            <input v-model.number="editForm.watched" type="number" min="0" />
          </label>
          <label
            v-if="items.find((i) => i.id === editTargetId)?.isEpisodic"
            class="qa-field"
          >
            <span>Total episodes</span>
            <input
              v-model.number="editForm.totalEpisodes"
              type="number"
              min="0"
              placeholder="Unknown"
            />
          </label>
          <label class="qa-field">
            <span>Your rating (0–10)</span>
            <input
              v-model.number="editForm.score"
              type="number"
              min="0"
              max="10"
              step="0.1"
              placeholder="–"
            />
          </label>
        </div>
        <div class="modal-actions">
          <button type="button" class="btn-outline" @click="closeEdit">
            Cancel
          </button>
          <button type="button" class="btn-solid" @click="saveEdit">
            Save
          </button>
        </div>
      </div>
    </UiModal>

    <!-- ===== Quick Add ===== -->
    <UiModal
      v-if="quickAddOpen"
      :title="addLabel.replace('+ ', '')"
      description="Search, then pick the right result."
      size="wide"
      @close="closeQuickAdd"
    >
      <div class="media-modal-content qa-card">
        <div v-if="quickAddStep === 'search'">
          <div class="qa-body">
            <div class="qa-search-row">
              <input
                v-model="quickAddQuery"
                aria-label="Search media by title"
                autofocus
                placeholder="Search by title..."
                @keyup.enter="runQuickAddSearch"
              />
              <button
                type="button"
                class="qa-add-btn"
                @click="runQuickAddSearch"
              >
                Search
              </button>
            </div>
            <p
              v-if="quickAddProviderErrors.length"
              class="empty-state error"
              style="padding: 8px 0; font-size: 0.78rem"
            >
              {{ quickAddProviderErrors.join(" · ") }}
            </p>
            <p v-if="quickAddSearching" class="empty-state">Searching…</p>
            <p v-else-if="!quickAddResults.length" class="empty-state">
              No results yet. Search above.
            </p>
            <div v-else class="qa-results">
              <div v-for="(r, i) in quickAddResults" :key="i" class="qa-result">
                <div
                  class="qa-result-art"
                  :style="
                    r.poster ? { backgroundImage: `url(${r.poster})` } : {}
                  "
                ></div>
                <div class="qa-result-titles">
                  <div class="qa-result-english">{{ r.title }}</div>
                  <div
                    v-if="r.releaseYear || r.episodeTotal"
                    class="qa-result-meta"
                  >
                    <span v-if="r.releaseYear">{{ r.releaseYear }}</span>
                    <span v-if="r.episodeTotal"
                      >{{ r.episodeTotal }} episode{{
                        r.episodeTotal === 1 ? "" : "s"
                      }}</span
                    >
                  </div>
                  <div v-if="r.description" class="qa-result-desc">
                    {{ r.description }}
                  </div>
                </div>
                <button
                  type="button"
                  class="qa-add-btn"
                  @click="pickQuickAddResult(r)"
                >
                  + Add
                </button>
              </div>
            </div>
            <div class="qa-search-foot">
              <button type="button" class="btn-outline" @click="closeQuickAdd">
                Cancel
              </button>
            </div>
          </div>
        </div>

        <div v-else>
          <div class="qa-body">
            <button
              type="button"
              class="qa-back-link"
              @click="quickAddBackToSearch"
            >
              &larr; Back to results
            </button>
            <div class="qa-form-header">
              <div
                class="qa-form-art"
                :style="
                  quickAddPick?.poster
                    ? { backgroundImage: `url(${quickAddPick.poster})` }
                    : {}
                "
              ></div>
              <div class="qa-form-titles">
                <div class="qa-result-english">{{ quickAddPick?.title }}</div>
                <div
                  v-if="quickAddPick?.releaseYear || quickAddPick?.episodeTotal"
                  class="qa-result-meta"
                >
                  <span v-if="quickAddPick?.releaseYear">{{
                    quickAddPick.releaseYear
                  }}</span>
                  <span v-if="quickAddPick?.episodeTotal"
                    >{{ quickAddPick.episodeTotal }} episode{{
                      quickAddPick.episodeTotal === 1 ? "" : "s"
                    }}</span
                  >
                </div>
              </div>
            </div>
            <p class="qa-section-label">Your progress</p>
            <div class="qa-field-grid">
              <label class="qa-field">
                <span>Status</span>
                <select v-model="quickAddForm.status">
                  <option v-for="s in STATUSES" :key="s.key" :value="s.key">
                    {{ s.label }}
                  </option>
                </select>
              </label>
              <label v-if="kind !== 'movie'" class="qa-field">
                <span
                  >Episodes watched<template v-if="quickAddPick?.episodeTotal">
                    of {{ quickAddPick.episodeTotal }}</template
                  ></span
                >
                <input
                  v-model.number="quickAddForm.watched"
                  type="number"
                  min="0"
                  :max="quickAddPick?.episodeTotal ?? undefined"
                  @change="clampQuickAddWatched"
                />
              </label>
              <label class="qa-field">
                <span>Your rating (0–10)</span>
                <input
                  v-model.number="quickAddForm.score"
                  type="number"
                  min="0"
                  max="10"
                  step="0.1"
                  placeholder="–"
                />
              </label>
              <label class="qa-field">
                <span>Start date</span>
                <input v-model="quickAddForm.startDate" type="date" />
              </label>
              <label class="qa-field">
                <span>End date</span>
                <input v-model="quickAddForm.endDate" type="date" />
              </label>
            </div>
            <div class="modal-actions">
              <button type="button" class="btn-outline" @click="closeQuickAdd">
                Cancel
              </button>
              <button
                type="button"
                class="btn-solid"
                :disabled="quickAddSaving"
                @click="saveQuickAdd"
              >
                {{ quickAddSaving ? "Adding…" : "Add to Library" }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </UiModal>
  </div>
</template>

<style scoped src="../../styles/pages/media-library.css" />
