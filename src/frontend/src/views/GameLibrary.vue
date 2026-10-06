<script setup lang="ts">
import { sizedAssetUrl } from "../utils/gameImages";
import HeartIcon from "../components/HeartIcon.vue";
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useWindowVirtualizer } from "@tanstack/vue-virtual";
import GameCard from "../components/GameCard.vue";
import CheckIcon from "../components/CheckIcon.vue";
import GameFormModal from "../components/GameFormModal.vue";
import BulkEditModal from "../components/BulkEditModal.vue";
import RandomGamePicker from "../components/RandomGamePicker.vue";
import { activePriority, priorityLabel } from "../utils/priority";
import { formatDisplayDate } from "../utils/dates";
import FilterCombobox from "../components/FilterCombobox.vue";
import {
  fetchGames,
  peekAllGames,
  deleteGame,
  setFavorite,
  fetchAchievementsSummary,
  addGameToCollection,
} from "../services/games";
import { setLibraryNavOrder } from "../state/libraryNav";
import { isCommandPaletteOpen } from "../state/commandPalette";
import CollectionPickerModal from "../components/CollectionPickerModal.vue";
import GameTopBar from "../components/GameTopBar.vue";
import SegmentedTabs from "../components/SegmentedTabs.vue";
import type { SegmentOption } from "../components/SegmentedTabs.vue";
import { computeScore } from "../utils/scoring";
import DOMPurify from "dompurify";
import {
  normalizePlatformFamily,
  PLATFORM_OPTIONS,
  RETRO_PLATFORM_OPTIONS,
} from "../utils/platforms";
import { GENRE_OPTIONS } from "../utils/genres";
import type { Game, GameStatus } from "../types/game";
import { usePrompt } from "../state/dialog";

const prompt = usePrompt();

type ViewMode = "cards" | "list" | "detail";
const SORT_KEYS = [
  "name",
  "name_desc",
  "recent",
  "rating",
  "playtime",
  "last_played",
  "neglected",
  "priority",
  "release",
  "length",
] as const;
type SortBy = (typeof SORT_KEYS)[number];
type AchievementsFilter = "all" | "has" | "none";
type MissingFilter = "none" | "playtime" | "rating" | "tags" | "description";
type CardDensity = "compact" | "cozy" | "large";

const router = useRouter();
const route = useRoute();

const games = ref<Game[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

const showFormModal = ref(false);
const editingGame = ref<Game | null>(null);

const deletingGame = ref<Game | null>(null);
const deleting = ref(false);
const deleteError = ref<string | null>(null);

const storedView = localStorage.getItem("gameLibraryViewMode");
// "shelves" used to be the by-source layout, since removed; "cards" is the
// grid, which is now what's labelled Shelves
const viewMode = ref<ViewMode>(
  storedView === "list" || storedView === "detail" ? storedView : "cards",
);
const selectedGame = ref<Game | null>(null);
// keyboard focus within the Cards grid (arrow keys + Enter), separate from
// selectedGame, which is only for the "List + preview" split view
const gridFocusIndex = ref<number | null>(null);

// bulk-edit selection, separate from `selectedGame` (the detail-view
// preview pick), this tracks a multi-game checkbox selection for the
// bulk-edit toolbar/modal
const selectMode = ref(false);
const selectedIds = ref<Set<string>>(new Set());
const showBulkEditModal = ref(false);
const showRandomPicker = ref(false);

// one-time nudge toward bulk edit, gone for good the first time it's
// dismissed or the feature is actually used, not re-shown once discovered
const BULK_EDIT_HINT_KEY = "seenBulkEditHint";
const showBulkEditHint = ref(
  localStorage.getItem(BULK_EDIT_HINT_KEY) !== "true",
);
function dismissBulkEditHint() {
  showBulkEditHint.value = false;
  try {
    localStorage.setItem(BULK_EDIT_HINT_KEY, "true");
  } catch {
    // worst case it just shows again next visit, not worth failing over
  }
}

function toggleSelectMode() {
  selectMode.value = !selectMode.value;
  if (!selectMode.value) selectedIds.value = new Set();
  // otherwise "Updated N games." from a previous bulk edit keeps showing
  // through an unrelated later selection
  bulkEditResultCount.value = null;
}

// shift-click extends from whichever card was last clicked, so selecting a
// long run doesn't mean toggling every card individually
let lastToggledId: string | null = null;
function toggleSelect(game: Game, shiftKey = false) {
  const next = new Set(selectedIds.value);
  if (shiftKey && lastToggledId) {
    const ids = filteredGames.value.map((g) => g.id);
    const from = ids.indexOf(lastToggledId);
    const to = ids.indexOf(game.id);
    if (from !== -1 && to !== -1) {
      const [start, end] = from < to ? [from, to] : [to, from];
      for (const id of ids.slice(start, end + 1)) next.add(id);
      selectedIds.value = next;
      lastToggledId = game.id;
      return;
    }
  }
  if (next.has(game.id)) next.delete(game.id);
  else next.add(game.id);
  selectedIds.value = next;
  lastToggledId = game.id;
}

function clearSelection() {
  selectedIds.value = new Set();
}

async function onBulkEditSaved(count: number) {
  showBulkEditModal.value = false;
  selectMode.value = false;
  selectedIds.value = new Set();
  bulkEditResultCount.value = count;
  await loadGames();
}
const bulkEditResultCount = ref<number | null>(null);

// bulk-add selected games to a collection, a keyboard/click alternative to
// dragging cards onto a collection, which this codebase has no drag-and-drop
// library to build (see the arrow-based reorder in CollectionDetail.vue for
// the same tradeoff elsewhere)
const bulkAddingToCollection = ref(false);
async function bulkAddToCollection() {
  if (!selectedIds.value.size) return;
  const name = await prompt({
    title: "Add to collection",
    message: `Add ${selectedIds.value.size} selected game(s) to which collection?`,
    confirmLabel: "Add",
  });
  if (!name || !name.trim()) return;
  const trimmed = name.trim();
  bulkAddingToCollection.value = true;
  try {
    await Promise.all(
      [...selectedIds.value].map((id) => addGameToCollection(id, trimmed)),
    );
    bulkEditResultCount.value = selectedIds.value.size;
    selectMode.value = false;
    selectedIds.value = new Set();
    await loadGames();
  } finally {
    bulkAddingToCollection.value = false;
  }
}

// Steam's "About This Game" section is rich HTML (headers, screenshots,
// gifs), sanitize it instead of dumping the raw tags as text
const selectedGameDescriptionHtml = computed(() => {
  if (!selectedGame.value?.description) return "";
  return DOMPurify.sanitize(selectedGame.value.description);
});

// filters persist across visits (localStorage) so they don't silently reset
// every time you navigate away and back
const FILTERS_KEY = "gameLibraryFilters";
interface PersistedFilters {
  searchQuery: string;
  statusFilter: GameStatus | "all";
  platformFilter: string;
  genreFilter: string;
  sortBy: SortBy;
  showAdvancedFilters: boolean;
  franchiseFilter: string;
  collectionFilter: string;
  companyFilter: string;
  ageRatingFilter: string;
  regionFilter: string;
  languageFilter: string;
  metadataProviderFilter: string;
  favoritesOnly: boolean;
  achievementsFilter: AchievementsFilter;
  retroAchievementsOnly: boolean;
  missingFilter: MissingFilter;
  tagsFilter: string[];
}
function loadPersistedFilters(): Partial<PersistedFilters> {
  try {
    const raw = localStorage.getItem(FILTERS_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}
const persisted = loadPersistedFilters();

const searchQuery = ref(persisted.searchQuery ?? "");
const statusFilter = ref<GameStatus | "all">(persisted.statusFilter ?? "all");
const platformFilter = ref<string>(persisted.platformFilter ?? "all");
const genreFilter = ref<string>(persisted.genreFilter ?? "all");
const sortBy = ref<SortBy>(
  persisted.sortBy ??
    (localStorage.getItem("gameLibraryDefaultSort") as SortBy) ??
    "name",
);

const showAdvancedFilters = ref(persisted.showAdvancedFilters ?? false);
const franchiseFilter = ref<string>(persisted.franchiseFilter ?? "all");
const collectionFilter = ref<string>(persisted.collectionFilter ?? "all");
const companyFilter = ref<string>(persisted.companyFilter ?? "all");
const ageRatingFilter = ref<string>(persisted.ageRatingFilter ?? "all");
const regionFilter = ref<string>(persisted.regionFilter ?? "all");
const languageFilter = ref<string>(persisted.languageFilter ?? "all");
const metadataProviderFilter = ref<string>(
  persisted.metadataProviderFilter ?? "all",
);
const favoritesOnly = ref(persisted.favoritesOnly ?? false);
const achievementsFilter = ref<AchievementsFilter>(
  persisted.achievementsFilter ?? "all",
);
const retroAchievementsOnly = ref(persisted.retroAchievementsOnly ?? false);
const missingFilter = ref<MissingFilter>(persisted.missingFilter ?? "none");
// multi-select, OR'd together, layered on top of the single-pick Genre
// combobox above rather than replacing it, so the common "just one genre"
// case stays a quick single click
const tagsFilter = ref<string[]>(persisted.tagsFilter ?? []);
function toggleTagFilter(tag: string) {
  tagsFilter.value = tagsFilter.value.includes(tag)
    ? tagsFilter.value.filter((t) => t !== tag)
    : [...tagsFilter.value, tag];
}

watch(
  [
    searchQuery,
    statusFilter,
    platformFilter,
    genreFilter,
    sortBy,
    showAdvancedFilters,
    franchiseFilter,
    collectionFilter,
    companyFilter,
    ageRatingFilter,
    regionFilter,
    languageFilter,
    metadataProviderFilter,
    favoritesOnly,
    achievementsFilter,
    retroAchievementsOnly,
    missingFilter,
    tagsFilter,
  ],
  () => {
    const toSave: PersistedFilters = {
      searchQuery: searchQuery.value,
      statusFilter: statusFilter.value,
      platformFilter: platformFilter.value,
      genreFilter: genreFilter.value,
      sortBy: sortBy.value,
      showAdvancedFilters: showAdvancedFilters.value,
      franchiseFilter: franchiseFilter.value,
      collectionFilter: collectionFilter.value,
      companyFilter: companyFilter.value,
      ageRatingFilter: ageRatingFilter.value,
      regionFilter: regionFilter.value,
      languageFilter: languageFilter.value,
      metadataProviderFilter: metadataProviderFilter.value,
      favoritesOnly: favoritesOnly.value,
      achievementsFilter: achievementsFilter.value,
      retroAchievementsOnly: retroAchievementsOnly.value,
      missingFilter: missingFilter.value,
      tagsFilter: tagsFilter.value,
    };
    localStorage.setItem(FILTERS_KEY, JSON.stringify(toSave));
  },
  { deep: true },
);

// recent searches, shown when the search box gets focus while empty, so
// getting back to a search you ran a minute ago doesn't mean retyping it
const RECENT_SEARCHES_KEY = "gameLibraryRecentSearches";
const MAX_RECENT_SEARCHES = 6;
function loadRecentSearches(): string[] {
  try {
    const raw = localStorage.getItem(RECENT_SEARCHES_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}
const recentSearches = ref<string[]>(loadRecentSearches());
const showRecentSearches = ref(false);
function commitSearchToRecent() {
  const q = searchQuery.value.trim();
  if (!q) return;
  const next = [
    q,
    ...recentSearches.value.filter((s) => s.toLowerCase() !== q.toLowerCase()),
  ].slice(0, MAX_RECENT_SEARCHES);
  recentSearches.value = next;
  try {
    localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(next));
  } catch {
    // best-effort, recent searches just don't persist, not worth failing over
  }
}
function pickRecentSearch(q: string) {
  searchQuery.value = q;
  showRecentSearches.value = false;
}
function removeRecentSearch(q: string) {
  recentSearches.value = recentSearches.value.filter((s) => s !== q);
  try {
    localStorage.setItem(
      RECENT_SEARCHES_KEY,
      JSON.stringify(recentSearches.value),
    );
  } catch {
    // same as above
  }
}

const advancedFilterCount = computed(() => {
  let count = 0;
  if (franchiseFilter.value !== "all") count++;
  if (collectionFilter.value !== "all") count++;
  if (companyFilter.value !== "all") count++;
  if (ageRatingFilter.value !== "all") count++;
  if (regionFilter.value !== "all") count++;
  if (languageFilter.value !== "all") count++;
  if (metadataProviderFilter.value !== "all") count++;
  if (favoritesOnly.value) count++;
  if (achievementsFilter.value !== "all") count++;
  if (retroAchievementsOnly.value) count++;
  if (missingFilter.value !== "none") count++;
  if (tagsFilter.value.length) count++;
  return count;
});

// every filter that narrows the list except the status tabs, which have
// their own row; platform and genre live in the Filters panel too
const filterCount = computed(
  () =>
    advancedFilterCount.value +
    (platformFilter.value !== "all" ? 1 : 0) +
    (genreFilter.value !== "all" ? 1 : 0),
);

function clearAdvancedFilters() {
  franchiseFilter.value = "all";
  collectionFilter.value = "all";
  companyFilter.value = "all";
  ageRatingFilter.value = "all";
  regionFilter.value = "all";
  languageFilter.value = "all";
  metadataProviderFilter.value = "all";
  favoritesOnly.value = false;
  achievementsFilter.value = "all";
  retroAchievementsOnly.value = false;
  missingFilter.value = "none";
  tagsFilter.value = [];
}

function clearAllFilters() {
  searchQuery.value = "";
  statusFilter.value = "all";
  platformFilter.value = "all";
  genreFilter.value = "all";
  clearAdvancedFilters();
}

// saved filter presets, a named snapshot of the filter *values*, not a
// snapshot of which games matched, so reapplying one always re-runs against
// whatever the library looks like right now (the same "Smart Collection"
// effect, with no separate live-updating machinery needed)
interface FilterPreset {
  name: string;
  filters: Omit<PersistedFilters, "searchQuery" | "showAdvancedFilters">;
}
const PRESETS_KEY = "gameLibraryFilterPresets";
function loadPresets(): FilterPreset[] {
  try {
    const raw = localStorage.getItem(PRESETS_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}
const filterPresets = ref<FilterPreset[]>(loadPresets());
const showPresetsMenu = ref(false);
function currentFilterValues(): FilterPreset["filters"] {
  return {
    statusFilter: statusFilter.value,
    platformFilter: platformFilter.value,
    genreFilter: genreFilter.value,
    sortBy: sortBy.value,
    franchiseFilter: franchiseFilter.value,
    collectionFilter: collectionFilter.value,
    companyFilter: companyFilter.value,
    ageRatingFilter: ageRatingFilter.value,
    regionFilter: regionFilter.value,
    languageFilter: languageFilter.value,
    metadataProviderFilter: metadataProviderFilter.value,
    favoritesOnly: favoritesOnly.value,
    achievementsFilter: achievementsFilter.value,
    retroAchievementsOnly: retroAchievementsOnly.value,
    missingFilter: missingFilter.value,
    tagsFilter: [...tagsFilter.value],
  };
}
async function saveCurrentAsPreset() {
  const name = await prompt({
    title: "Save filters",
    message: "Name this filter combo.",
    confirmLabel: "Save",
  });
  if (!name || !name.trim()) return;
  const trimmed = name.trim();
  const next = [
    ...filterPresets.value.filter((p) => p.name !== trimmed),
    { name: trimmed, filters: currentFilterValues() },
  ];
  filterPresets.value = next;
  try {
    localStorage.setItem(PRESETS_KEY, JSON.stringify(next));
  } catch {
    // best-effort, the preset just won't survive a reload
  }
  showPresetsMenu.value = false;
}
function applyPreset(preset: FilterPreset) {
  statusFilter.value = preset.filters.statusFilter;
  platformFilter.value = preset.filters.platformFilter;
  genreFilter.value = preset.filters.genreFilter;
  sortBy.value = preset.filters.sortBy;
  franchiseFilter.value = preset.filters.franchiseFilter;
  collectionFilter.value = preset.filters.collectionFilter;
  companyFilter.value = preset.filters.companyFilter;
  ageRatingFilter.value = preset.filters.ageRatingFilter;
  regionFilter.value = preset.filters.regionFilter;
  languageFilter.value = preset.filters.languageFilter;
  metadataProviderFilter.value = preset.filters.metadataProviderFilter;
  favoritesOnly.value = preset.filters.favoritesOnly;
  achievementsFilter.value = preset.filters.achievementsFilter;
  retroAchievementsOnly.value = preset.filters.retroAchievementsOnly;
  missingFilter.value = preset.filters.missingFilter;
  tagsFilter.value = [...(preset.filters.tagsFilter ?? [])];
  showAdvancedFilters.value = true;
  showPresetsMenu.value = false;
}
function deletePreset(name: string) {
  const next = filterPresets.value.filter((p) => p.name !== name);
  filterPresets.value = next;
  try {
    localStorage.setItem(PRESETS_KEY, JSON.stringify(next));
  } catch {
    // same as above
  }
}

// arriving from a Collections-page card click (?collection=Name),
// pre-apply that filter and surface the panel so it's clear why it's active
const queryCollection = route.query.collection;
if (typeof queryCollection === "string" && queryCollection) {
  collectionFilter.value = queryCollection;
  showAdvancedFilters.value = true;
}

const statusOptions: (GameStatus | "all")[] = [
  "all",
  "playing",
  "beaten",
  "mastered",
  "played",
  "on hold",
  "dropped",
  "backlog",
  "wishlist",
];

const VIEW_OPTIONS: SegmentOption[] = [
  {
    value: "list",
    label: "List",
    icon: '<line x1="8" y1="6" x2="21" y2="6" /><line x1="8" y1="12" x2="21" y2="12" /><line x1="8" y1="18" x2="21" y2="18" /><line x1="3" y1="6" x2="3.01" y2="6" /><line x1="3" y1="12" x2="3.01" y2="12" /><line x1="3" y1="18" x2="3.01" y2="18" />',
  },
  {
    value: "cards",
    label: "Shelves",
    icon: '<rect x="3" y="3" width="7" height="18" rx="1" /><rect x="14" y="3" width="7" height="10" rx="1" />',
  },
  {
    value: "detail",
    label: "Preview",
    title: "List + preview",
    icon: '<rect x="3" y="3" width="7" height="18" rx="1" /><rect x="13" y="3" width="8" height="18" rx="1" />',
  },
];

const statusCounts = computed(() => {
  const counts: Record<string, number> = { all: games.value.length };
  for (const g of games.value) counts[g.status] = (counts[g.status] ?? 0) + 1;
  return counts;
});

// arriving from a Home Hub row link (?status=playing, ?sort=recent)
const queryStatus = route.query.status;
if (
  typeof queryStatus === "string" &&
  statusOptions.includes(queryStatus as GameStatus | "all")
) {
  statusFilter.value = queryStatus as GameStatus | "all";
}
const querySort = route.query.sort;
if (
  typeof querySort === "string" &&
  (SORT_KEYS as readonly string[]).includes(querySort)
) {
  sortBy.value = querySort as SortBy;
}
// arriving from a link (Server Stats' tag chart, or a genre, developer,
// publisher, platform or series on a game's page): ?tag= ?company= ?platform=
// ?series=. It shows exactly that, not that on top of whatever filters were
// left on from last time.
function applyLinkedFilter() {
  if (route.path !== "/games") return;
  const pick = (key: string) => {
    const v = route.query[key];
    return typeof v === "string" && v ? v : null;
  };
  const tag = pick("tag");
  const company = pick("company");
  const platform = pick("platform");
  const series = pick("series");
  if (!tag && !company && !platform && !series) return;
  clearAllFilters();
  if (tag) genreFilter.value = tag;
  if (company) companyFilter.value = company;
  if (platform) platformFilter.value = platform;
  if (series) franchiseFilter.value = series;
  showAdvancedFilters.value = true;
}
applyLinkedFilter();
// the library is kept alive, so a link can arrive while it already exists
watch(() => route.fullPath, applyLinkedFilter);

const platformOptions = computed(() => {
  const set = new Set<string>(PLATFORM_OPTIONS);
  games.value.forEach((g) =>
    g.platforms.forEach((p) => {
      const family = normalizePlatformFamily(p.platform);
      if (PLATFORM_OPTIONS.includes(family)) set.add(family);
    }),
  );
  return Array.from(set).sort();
});

const platformExtraOptions = computed(() => {
  const set = new Set<string>(RETRO_PLATFORM_OPTIONS);
  games.value.forEach((g) =>
    g.platforms.forEach((p) => {
      const family = normalizePlatformFamily(p.platform);
      if (!PLATFORM_OPTIONS.includes(family)) set.add(family);
    }),
  );
  return Array.from(set).sort();
});

const genreOptions = computed(() => {
  const set = new Set<string>(GENRE_OPTIONS);
  games.value.forEach((g) => g.tags.forEach((t) => set.add(t)));
  return Array.from(set).sort();
});

function uniqueValues(pick: (g: Game) => string | null): string[] {
  const set = new Set<string>();
  games.value.forEach((g) => {
    const value = pick(g);
    if (value) set.add(value);
  });
  return Array.from(set).sort();
}

const franchiseOptions = computed(() => uniqueValues((g) => g.series));
const collectionOptions = computed(() => {
  const set = new Set<string>();
  games.value.forEach((g) => g.collections.forEach((c) => set.add(c)));
  return Array.from(set).sort();
});
const companyOptions = computed(() => {
  const set = new Set<string>();
  games.value.forEach((g) => {
    if (g.developer) set.add(g.developer);
    if (g.publisher) set.add(g.publisher);
  });
  return Array.from(set).sort();
});
const ageRatingOptions = computed(() => uniqueValues((g) => g.ageRating));
const regionOptions = computed(() => uniqueValues((g) => g.region));
const languageOptions = computed(() => uniqueValues((g) => g.language));
const metadataProviderOptions = computed(() => uniqueValues((g) => g.source));

function setView(mode: ViewMode) {
  viewMode.value = mode;
  localStorage.setItem("gameLibraryViewMode", mode);
  if (mode === "detail" && !selectedGame.value && games.value.length) {
    selectedGame.value = games.value[0];
  }
}

// guards against a slower, earlier loadGames() call overwriting a newer
// one's result, loadGames is re-triggered from many places (save, delete,
// collection changes) that can overlap
let loadGamesToken = 0;

function selectFirstForDetailView() {
  if (viewMode.value === "detail" && !selectedGame.value && games.value.length)
    selectedGame.value = games.value[0];
}

async function loadGames() {
  const token = ++loadGamesToken;
  // A library seen earlier in this visit is drawn at once and refreshed
  // behind it, instead of a "Loading…" screen on every return to the page.
  const seen = games.value.length ? null : peekAllGames();
  if (seen) {
    games.value = seen;
    selectFirstForDetailView();
    loading.value = false;
  } else if (!games.value.length) {
    loading.value = true;
  }
  try {
    // the completion numbers are best-effort, a failed summary fetch just
    // means no completion badges, not a broken library page, and it is asked
    // for alongside the games rather than after them
    const [fetched, summary] = await Promise.all([
      fetchGames(),
      fetchAchievementsSummary().catch(() => null),
    ]);
    if (token !== loadGamesToken) return;
    games.value = fetched;
    if (summary) {
      for (const game of games.value) {
        const entry = summary[game.id];
        if (!entry) continue;
        game.achievementTotal = entry.total;
        game.achievementPercent = entry.total
          ? Math.round((entry.unlocked / entry.total) * 100)
          : 0;
      }
    }
    selectFirstForDetailView();
  } catch (err) {
    if (token !== loadGamesToken) return;
    error.value = err instanceof Error ? err.message : "Failed to load games";
  } finally {
    if (token === loadGamesToken) loading.value = false;
  }
}

onMounted(loadGames);

// filters are only remembered while you stay on this page, leaving it
// (any other route) wipes them so the next visit starts from a clean slate
onUnmounted(() => {
  localStorage.removeItem(FILTERS_KEY);
});

// --- Keyboard shortcuts ------------------------------------------------
// "/" focuses search (common convention, GitHub, Linear, etc.), "n" opens
// Add Game, Escape backs out of whatever's active. All disabled while
// typing in a field or while a modal/dialog is open, so they never hijack
// normal typing or double-fire on top of a dialog's own Escape handling.
const searchInputRef = ref<HTMLInputElement | null>(null);
function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  return (
    tag === "INPUT" ||
    tag === "TEXTAREA" ||
    tag === "SELECT" ||
    target.isContentEditable
  );
}
function anyModalOpen(): boolean {
  return (
    showFormModal.value ||
    !!deletingGame.value ||
    showBulkEditModal.value ||
    !!collectionPickerGame.value ||
    isCommandPaletteOpen.value
  );
}
function onGlobalKeydown(e: KeyboardEvent) {
  if (anyModalOpen()) return;
  if (e.key === "Escape") {
    if (
      isTypingTarget(e.target) &&
      (e.target as HTMLElement) === searchInputRef.value
    ) {
      searchQuery.value = "";
      searchInputRef.value?.blur();
    } else if (showAdvancedFilters.value) {
      showAdvancedFilters.value = false;
    } else if (selectMode.value) {
      toggleSelectMode();
    }
    return;
  }
  if (isTypingTarget(e.target)) return;
  if (e.key === "/") {
    e.preventDefault();
    searchInputRef.value?.focus();
  } else if (e.key === "n") {
    e.preventDefault();
    openAddModal();
  } else if (
    (e.key === "j" || e.key === "ArrowDown") &&
    viewMode.value === "detail"
  ) {
    e.preventDefault();
    const idx = selectedGame.value
      ? filteredGames.value.findIndex((g) => g.id === selectedGame.value?.id)
      : -1;
    if (idx < filteredGames.value.length - 1)
      selectedGame.value = filteredGames.value[idx + 1];
  } else if (
    (e.key === "k" || e.key === "ArrowUp") &&
    viewMode.value === "detail"
  ) {
    e.preventDefault();
    const idx = selectedGame.value
      ? filteredGames.value.findIndex((g) => g.id === selectedGame.value?.id)
      : -1;
    if (idx > 0) selectedGame.value = filteredGames.value[idx - 1];
  } else if (/^[a-z]$/i.test(e.key) && viewMode.value === "cards") {
    // 'n' is already claimed by "Add Game" above
    if (e.key.toLowerCase() === "n") return;
    const letter = e.key.toLowerCase();
    const index = filteredGames.value.findIndex(
      (g) => g.title.trim()[0]?.toLowerCase() === letter,
    );
    if (index !== -1) {
      e.preventDefault();
      gridFocusIndex.value = index;
      rowVirtualizer.value.scrollToIndex(
        Math.floor(index / CARD_COLUMNS.value),
        { align: "start" },
      );
    }
  } else if (
    viewMode.value === "cards" &&
    !selectMode.value &&
    ["ArrowRight", "ArrowLeft", "ArrowUp", "ArrowDown"].includes(e.key)
  ) {
    const count = filteredGames.value.length;
    if (!count) return;
    e.preventDefault();
    let idx = gridFocusIndex.value ?? 0;
    if (e.key === "ArrowRight") idx = Math.min(idx + 1, count - 1);
    else if (e.key === "ArrowLeft") idx = Math.max(idx - 1, 0);
    else if (e.key === "ArrowDown")
      idx = Math.min(idx + CARD_COLUMNS.value, count - 1);
    else if (e.key === "ArrowUp") idx = Math.max(idx - CARD_COLUMNS.value, 0);
    gridFocusIndex.value = idx;
    rowVirtualizer.value.scrollToIndex(Math.floor(idx / CARD_COLUMNS.value), {
      align: "auto",
    });
  } else if (
    e.key === "Enter" &&
    viewMode.value === "cards" &&
    gridFocusIndex.value !== null
  ) {
    const game = filteredGames.value[gridFocusIndex.value];
    if (game) {
      e.preventDefault();
      router.push(`/games/${game.id}`);
    }
  }
}
onMounted(() => window.addEventListener("keydown", onGlobalKeydown));
onUnmounted(() => window.removeEventListener("keydown", onGlobalKeydown));

function openAddModal() {
  editingGame.value = null;
  showFormModal.value = true;
}

function openEditModal(game: Game) {
  editingGame.value = game;
  showFormModal.value = true;
}

async function onGameSaved() {
  showFormModal.value = false;
  editingGame.value = null;
  await loadGames();
}

function onDeleteFromModal(gameId: string) {
  const game = games.value.find((g) => g.id === gameId);
  showFormModal.value = false;
  editingGame.value = null;
  if (game) requestDelete(game);
}

function requestDelete(game: Game) {
  deletingGame.value = game;
  deleteError.value = null;
}

async function toggleFavorite(game: Game) {
  const next = !game.favorite;
  game.favorite = next;
  try {
    await setFavorite(game.id, next);
  } catch {
    game.favorite = !next;
  }
}

const collectionPickerGame = ref<Game | null>(null);

function handleAddToCollection(game: Game) {
  collectionPickerGame.value = game;
}

async function onCollectionAdded() {
  await loadGames();
}

async function confirmDelete() {
  if (!deletingGame.value) return;
  deleting.value = true;
  deleteError.value = null;
  try {
    await deleteGame(deletingGame.value.id);
    if (selectedGame.value?.id === deletingGame.value.id)
      selectedGame.value = null;
    deletingGame.value = null;
    await loadGames();
  } catch (err) {
    deleteError.value =
      err instanceof Error ? err.message : "Failed to delete game";
  } finally {
    deleting.value = false;
  }
}

function gameTotalMinutes(game: Game): number {
  return game.platforms.reduce((sum, p) => sum + p.playtimeMinutes, 0);
}

function totalPlaytime(game: Game): string {
  const minutes = gameTotalMinutes(game);
  if (minutes === 0) return "N/A";
  const hours = Math.floor(minutes / 60);
  return `${hours}h`;
}

function gameLastPlayed(game: Game): string | null {
  const dates = game.platforms
    .map((p) => p.lastPlayedAt)
    .filter((d): d is string => d !== null);
  return dates.length
    ? dates.reduce((latest, d) => (d > latest ? d : latest))
    : null;
}

function openGame(game: Game) {
  router.push(`/games/${game.id}`);
}

const filteredGames = computed(() => {
  let result = games.value;

  if (statusFilter.value !== "all") {
    result = result.filter((g) => g.status === statusFilter.value);
  }
  if (platformFilter.value !== "all") {
    result = result.filter((g) =>
      g.platforms.some(
        (p) => normalizePlatformFamily(p.platform) === platformFilter.value,
      ),
    );
  }
  if (genreFilter.value !== "all") {
    result = result.filter((g) => g.tags.includes(genreFilter.value));
  }
  if (franchiseFilter.value !== "all") {
    result = result.filter((g) => g.series === franchiseFilter.value);
  }
  if (collectionFilter.value !== "all") {
    result = result.filter((g) =>
      g.collections.includes(collectionFilter.value),
    );
  }
  if (companyFilter.value !== "all") {
    result = result.filter(
      (g) =>
        g.developer === companyFilter.value ||
        g.publisher === companyFilter.value,
    );
  }
  if (ageRatingFilter.value !== "all") {
    result = result.filter((g) => g.ageRating === ageRatingFilter.value);
  }
  if (regionFilter.value !== "all") {
    result = result.filter((g) => g.region === regionFilter.value);
  }
  if (languageFilter.value !== "all") {
    result = result.filter((g) => g.language === languageFilter.value);
  }
  if (metadataProviderFilter.value !== "all") {
    result = result.filter((g) => g.source === metadataProviderFilter.value);
  }
  if (favoritesOnly.value) {
    result = result.filter((g) => g.favorite);
  }
  if (achievementsFilter.value === "has") {
    result = result.filter((g) => g.achievementTotal > 0);
  } else if (achievementsFilter.value === "none") {
    result = result.filter((g) => g.achievementTotal === 0);
  }
  if (retroAchievementsOnly.value) {
    result = result.filter(
      (g) => g.achievementsProvider === "retroachievements",
    );
  }
  if (missingFilter.value === "playtime") {
    result = result.filter((g) => gameTotalMinutes(g) === 0);
  } else if (missingFilter.value === "rating") {
    result = result.filter((g) => g.ratingOverall === null);
  } else if (missingFilter.value === "tags") {
    result = result.filter((g) => g.tags.length === 0);
  } else if (missingFilter.value === "description") {
    result = result.filter((g) => !g.description);
  }
  if (tagsFilter.value.length) {
    result = result.filter((g) =>
      g.tags.some((t) => tagsFilter.value.includes(t)),
    );
  }

  const q = searchQuery.value.trim().toLowerCase();
  if (q) {
    result = result.filter((g) => fuzzyTitleMatch(g.title, q));
  }

  // missing values always sort last, whichever way the sort runs
  const lastIfNull = <T,>(
    x: T | null,
    y: T | null,
    compare: (x: T, y: T) => number,
  ): number => {
    if (x === null && y === null) return 0;
    if (x === null) return 1;
    if (y === null) return -1;
    return compare(x, y);
  };
  result = [...result].sort((a, b) => {
    if (sortBy.value === "name") return a.title.localeCompare(b.title);
    if (sortBy.value === "name_desc") return b.title.localeCompare(a.title);
    if (sortBy.value === "recent")
      return (b.dateAdded ?? "").localeCompare(a.dateAdded ?? "");
    if (sortBy.value === "rating") {
      const scoreA = computeScore(a)?.sum ?? -1;
      const scoreB = computeScore(b)?.sum ?? -1;
      return scoreB - scoreA;
    }
    if (sortBy.value === "playtime")
      return gameTotalMinutes(b) - gameTotalMinutes(a);
    if (sortBy.value === "last_played")
      return lastIfNull(gameLastPlayed(a), gameLastPlayed(b), (x, y) =>
        y.localeCompare(x),
      );
    // never-played games sort first (most neglected), then oldest-last-played first
    if (sortBy.value === "neglected")
      return (gameLastPlayed(a) ?? "").localeCompare(gameLastPlayed(b) ?? "");
    // 1 (highest) first; finished games have no priority, so they go last
    if (sortBy.value === "priority")
      return (
        lastIfNull(activePriority(a), activePriority(b), (x, y) => x - y) ||
        a.title.localeCompare(b.title)
      );
    if (sortBy.value === "release")
      return lastIfNull(a.releaseDate, b.releaseDate, (x, y) =>
        y.localeCompare(x),
      );
    // shortest first, for "something I can finish this weekend"
    if (sortBy.value === "length")
      return lastIfNull(a.timeToBeatHours, b.timeToBeatHours, (x, y) => x - y);
    return 0;
  });

  return result;
});

// keeps GameDetail.vue's J/K next/prev shortcut in sync with whatever
// order the library is actually showing right now (filters + sort applied)
watch(filteredGames, (list) => setLibraryNavOrder(list.map((g) => g.id)), {
  immediate: true,
});
// stale keyboard focus (pointing at a game that scrolled out of the
// filtered results) is worse than none, drop it whenever the list changes
watch(filteredGames, () => {
  gridFocusIndex.value = null;
});

const hasAnyGames = computed(() => games.value.length > 0);
const isEmpty = computed(
  () => !loading.value && !error.value && filteredGames.value.length === 0,
);

// zero-result search suggestions, a cheap edit-distance check against
// every known title, not a real fuzzy-search index, but enough to catch
// the common case of a typo
function levenshtein(a: string, b: string): number {
  const dp: number[][] = Array.from({ length: a.length + 1 }, (_, i) => [
    i,
    ...Array(b.length).fill(0),
  ]);
  for (let j = 0; j <= b.length; j++) dp[0][j] = j;
  for (let i = 1; i <= a.length; i++) {
    for (let j = 1; j <= b.length; j++) {
      dp[i][j] =
        a[i - 1] === b[j - 1]
          ? dp[i - 1][j - 1]
          : 1 + Math.min(dp[i - 1][j - 1], dp[i - 1][j], dp[i][j - 1]);
    }
  }
  return dp[a.length][b.length];
}

// exact substring always wins first (cheap, predictable); only falls back to
// edit-distance against individual title words for queries long enough that
// a couple of typos won't produce false positives against short titles
function fuzzyTitleMatch(title: string, q: string): boolean {
  const lowerTitle = title.toLowerCase();
  if (lowerTitle.includes(q)) return true;
  if (q.length < 4) return false;
  const threshold = Math.max(1, Math.floor(q.length * 0.34));
  return lowerTitle
    .split(/\s+/)
    .some((word) => levenshtein(q, word) <= threshold);
}

const searchSuggestions = computed(() => {
  const q = searchQuery.value.trim().toLowerCase();
  if (!q || filteredGames.value.length > 0 || games.value.length === 0)
    return [];
  return (
    games.value
      .map((g) => ({
        title: g.title,
        distance: levenshtein(q, g.title.toLowerCase()),
      }))
      // scaled to query length, a short typo-prone query needs a tighter
      // tolerance than a long title, or everything "matches"
      .filter((g) => g.distance <= Math.max(2, Math.ceil(q.length * 0.4)))
      .sort((a, b) => a.distance - b.distance)
      .slice(0, 3)
      .map((g) => g.title)
  );
});

// active-filter pills shown above the grid, each entry's clear() resets
// just that one filter, so the whole set doesn't have to be visible only
// inside the dropdowns to know (or undo) what's currently applied. Status
// isn't one: the status tabs already show it, as in Media
const activeFilterPills = computed(() => {
  const pills: { key: string; label: string; clear: () => void }[] = [];
  if (platformFilter.value !== "all")
    pills.push({
      key: "platform",
      label: platformFilter.value,
      clear: () => (platformFilter.value = "all"),
    });
  if (genreFilter.value !== "all")
    pills.push({
      key: "genre",
      label: genreFilter.value,
      clear: () => (genreFilter.value = "all"),
    });
  if (franchiseFilter.value !== "all")
    pills.push({
      key: "franchise",
      label: franchiseFilter.value,
      clear: () => (franchiseFilter.value = "all"),
    });
  if (collectionFilter.value !== "all")
    pills.push({
      key: "collection",
      label: collectionFilter.value,
      clear: () => (collectionFilter.value = "all"),
    });
  if (companyFilter.value !== "all")
    pills.push({
      key: "company",
      label: companyFilter.value,
      clear: () => (companyFilter.value = "all"),
    });
  if (ageRatingFilter.value !== "all")
    pills.push({
      key: "age",
      label: ageRatingFilter.value,
      clear: () => (ageRatingFilter.value = "all"),
    });
  if (regionFilter.value !== "all")
    pills.push({
      key: "region",
      label: regionFilter.value,
      clear: () => (regionFilter.value = "all"),
    });
  if (languageFilter.value !== "all")
    pills.push({
      key: "language",
      label: languageFilter.value,
      clear: () => (languageFilter.value = "all"),
    });
  if (metadataProviderFilter.value !== "all")
    pills.push({
      key: "provider",
      label: metadataProviderFilter.value,
      clear: () => (metadataProviderFilter.value = "all"),
    });
  if (favoritesOnly.value)
    pills.push({
      key: "favorites",
      label: "★ Favorites",
      clear: () => (favoritesOnly.value = false),
    });
  if (achievementsFilter.value !== "all") {
    pills.push({
      key: "achievements",
      label:
        achievementsFilter.value === "has"
          ? "Has achievements"
          : "No achievements",
      clear: () => (achievementsFilter.value = "all"),
    });
  }
  if (retroAchievementsOnly.value)
    pills.push({
      key: "retro",
      label: "RetroAchievements tracked",
      clear: () => (retroAchievementsOnly.value = false),
    });
  if (missingFilter.value !== "none") {
    const labels: Record<Exclude<MissingFilter, "none">, string> = {
      playtime: "No playtime logged",
      rating: "No rating",
      tags: "No tags",
      description: "No description",
    };
    pills.push({
      key: "missing",
      label: labels[missingFilter.value],
      clear: () => (missingFilter.value = "none"),
    });
  }
  for (const tag of tagsFilter.value) {
    pills.push({
      key: "tag:" + tag,
      label: tag,
      clear: () => toggleTagFilter(tag),
    });
  }
  return pills;
});

// card density, a coarse 3-step alternative to CARD_COLUMNS' fixed
// viewport breakpoints, layered on top rather than replacing them so the
// grid still adapts sensibly across screen sizes at every density
const cardDensity = ref<CardDensity>(
  (localStorage.getItem("gameLibraryDensity") as CardDensity) || "cozy",
);
watch(cardDensity, (d) => localStorage.setItem("gameLibraryDensity", d));

// virtualized cards grid, with 150+ games each rendering a real <img> plus
// hover/transform effects, mounting every card at once was the actual
// source of the reported lag, so virtualizing by row is exact: each virtual
// "item" is one row of up to CARD_COLUMNS cards, positioned with a single
// translateY rather than scrolling real DOM. estimateSize is a rough guess
// corrected immediately per-row by measureElement (actual row height
// depends on container width via the aspect-ratio cover, so it can't be
// hardcoded). CARD_COLUMNS itself tracks viewport width, a fixed column
// count regardless of screen size used to crush every card into an
// unreadable ~35px sliver on a phone; the grid's inline
// grid-template-columns reads this same computed value, so the JS slicing
// and the CSS layout can never disagree about how many cards are per row.
const viewportWidth = ref(window.innerWidth);
function onResize() {
  viewportWidth.value = window.innerWidth;
}
onMounted(() => window.addEventListener("resize", onResize));
onUnmounted(() => window.removeEventListener("resize", onResize));

// Same card widths as the Media shelf (150 / 200 / 260px, 14px gap): the
// column count is what an auto-fill grid of that minimum width would give
// for the width the page actually has, so a "small" card is the same size
// on both pages.
const MIN_CARD_WIDTH: Record<CardDensity, number> = {
  compact: 150,
  cozy: 200,
  large: 260,
};
const GRID_GAP = 14;
const contentEl = ref<HTMLElement | null>(null);
const gridWidth = ref(document.documentElement.clientWidth - 72);
let contentObserver: ResizeObserver | null = null;
onMounted(() => {
  if (!contentEl.value) return;
  contentObserver = new ResizeObserver((entries) => {
    gridWidth.value = entries[0].contentRect.width;
  });
  contentObserver.observe(contentEl.value);
});
onUnmounted(() => contentObserver?.disconnect());

const CARD_COLUMNS = computed(() => {
  const min = MIN_CARD_WIDTH[cardDensity.value];
  return Math.max(
    1,
    Math.floor((gridWidth.value + GRID_GAP) / (min + GRID_GAP)),
  );
});
const cardRowCount = computed(() =>
  Math.ceil(filteredGames.value.length / CARD_COLUMNS.value),
);
// Same as Media: a leaderboard position among everything that has a rating,
// highest first, generated rather than assigned
const rankByGameId = computed(() => {
  const rated = games.value
    .map((g) => ({ id: g.id, sum: computeScore(g)?.sum ?? null }))
    .filter((g): g is { id: string; sum: number } => g.sum !== null)
    .sort((a, b) => b.sum - a.sum);
  return new Map(rated.map((g, i) => [g.id, i + 1]));
});
const rowVirtualizer = useWindowVirtualizer(
  computed(() => ({
    count: cardRowCount.value,
    estimateSize: () => 330,
    overscan: 3,
  })),
);
// The list sits below the header, toolbar and tabs, which the window
// virtualizer doesn't know about. As each row is measured and replaces its
// 330px estimate it "corrects" the page scroll to compensate, which pushed
// the page a third of the way down the moment it loaded. (An instance
// property in this version, not a constructor option.)
rowVirtualizer.value.shouldAdjustScrollPositionOnItemSizeChange = () => false;
function cardsInRow(rowIndex: number): Game[] {
  const start = rowIndex * CARD_COLUMNS.value;
  return filteredGames.value.slice(start, start + CARD_COLUMNS.value);
}
</script>

<template>
  <main class="library" :class="{ locked: viewMode === 'detail' }">
    <GameTopBar active="games">
      <template #actions>
        <SegmentedTabs
          :options="VIEW_OPTIONS"
          :model-value="viewMode"
          aria-label="View"
          @update:model-value="setView($event as ViewMode)"
        />
      </template>
    </GameTopBar>

    <div ref="contentEl" class="content">
      <div class="page-head">
        <div>
          <h1>Games</h1>
          <div class="sub">
            {{ games.length }} {{ games.length === 1 ? "game" : "games" }}
          </div>
        </div>
        <div class="head-actions">
          <div class="select-button-wrap">
            <button
              type="button"
              class="select-btn"
              :class="{ on: selectMode }"
              @click="
                toggleSelectMode();
                dismissBulkEditHint();
              "
            >
              {{ selectMode ? "Done" : "Select" }}
            </button>
            <div v-if="showBulkEditHint" class="first-use-hint">
              <span
                >Select games, then bulk-edit their status, tags, or collections
                all at once.</span
              >
              <button
                type="button"
                class="first-use-hint-dismiss"
                @click="dismissBulkEditHint"
              >
                Got it
              </button>
            </div>
          </div>
          <button
            type="button"
            class="select-btn"
            :disabled="!games.length"
            title="Pick a game to play, filtered by status, platform, genre, length and priority"
            @click="showRandomPicker = true"
          >
            Random
          </button>
          <button type="button" class="add-btn" @click="openAddModal">
            + Add Game
          </button>
        </div>
      </div>

      <div v-if="selectMode" class="bulk-toolbar">
        <span class="count">{{ selectedIds.size }} selected</span>
        <button
          type="button"
          class="btn-outline"
          :disabled="filteredGames.length === 0"
          @click="selectedIds = new Set(filteredGames.map((g) => g.id))"
        >
          Select all ({{ filteredGames.length }})
        </button>
        <button
          type="button"
          class="btn-outline"
          :disabled="!selectedIds.size"
          @click="clearSelection"
        >
          Clear
        </button>
        <button
          type="button"
          class="btn-outline"
          :disabled="!selectedIds.size || bulkAddingToCollection"
          @click="bulkAddToCollection"
        >
          {{ bulkAddingToCollection ? "Adding…" : "Add to Collection" }}
        </button>
        <button
          type="button"
          class="btn-solid"
          :disabled="!selectedIds.size"
          @click="showBulkEditModal = true"
        >
          Bulk Edit
        </button>
      </div>
      <div
        v-if="bulkEditResultCount !== null"
        class="form-success bulk-success"
      >
        Updated {{ bulkEditResultCount }} game{{
          bulkEditResultCount === 1 ? "" : "s"
        }}.
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
            ref="searchInputRef"
            v-model="searchQuery"
            type="text"
            class="search-input"
            placeholder="Search your library… (/)"
            aria-label="Search games"
            @focus="showRecentSearches = true"
            @blur="
              showRecentSearches = false;
              commitSearchToRecent();
            "
            @keydown.enter="commitSearchToRecent"
          />
          <div
            v-if="
              showRecentSearches && !searchQuery.trim() && recentSearches.length
            "
            class="recent-searches-dropdown"
          >
            <div class="recent-searches-label">Recent searches</div>
            <button
              v-for="q in recentSearches"
              :key="q"
              type="button"
              class="recent-search-item"
              @mousedown.prevent="pickRecentSearch(q)"
            >
              <span>{{ q }}</span>
              <span
                class="recent-search-remove"
                @mousedown.prevent.stop="removeRecentSearch(q)"
                >✕</span
              >
            </button>
          </div>
        </div>
        <select v-model="sortBy" class="sort-select" aria-label="Sort by">
          <option value="name">Name (A–Z)</option>
          <option value="name_desc">Name (Z–A)</option>
          <option value="recent">Recently added</option>
          <option value="rating">Rating</option>
          <option value="playtime">Most Played</option>
          <option value="last_played">Recently played</option>
          <option value="neglected">Neglected (least recently played)</option>
          <option value="priority">Priority</option>
          <option value="release">Release date (newest)</option>
          <option value="length">Time to beat (shortest)</option>
        </select>
        <button
          type="button"
          class="filter-btn"
          :class="{ 'active-filter': filterCount }"
          @click="showAdvancedFilters = !showAdvancedFilters"
        >
          Filters
          <span v-if="filterCount" class="count">{{ filterCount }}</span>
        </button>
        <div class="presets-wrap">
          <button
            type="button"
            class="filter-btn"
            @click="showPresetsMenu = !showPresetsMenu"
          >
            Presets
          </button>
          <div v-if="showPresetsMenu" class="presets-dropdown">
            <button
              v-for="p in filterPresets"
              :key="p.name"
              type="button"
              class="preset-item"
              @click="applyPreset(p)"
            >
              <span>{{ p.name }}</span>
              <span class="preset-remove" @click.stop="deletePreset(p.name)"
                >✕</span
              >
            </button>
            <p v-if="!filterPresets.length" class="preset-empty">
              No saved presets yet.
            </p>
            <button
              type="button"
              class="preset-save"
              @click="saveCurrentAsPreset"
            >
              + Save current filters
            </button>
          </div>
        </div>
        <div
          v-if="viewMode === 'cards'"
          class="density-toggle"
          title="Card size"
        >
          <button
            v-for="d in ['compact', 'cozy', 'large'] as CardDensity[]"
            :key="d"
            type="button"
            class="density-button"
            :class="{ active: cardDensity === d }"
            :title="d"
            @click="cardDensity = d"
          >
            {{ d === "compact" ? "S" : d === "cozy" ? "M" : "L" }}
          </button>
        </div>
      </div>

      <div v-if="showAdvancedFilters" class="advanced-panel">
        <div class="filter-group platform-genre-group">
          <FilterCombobox
            v-model="platformFilter"
            :options="platformOptions"
            :extra-options="platformExtraOptions"
            extra-label="Retro"
            placeholder="Platform"
            all-label="All platforms"
          />
          <FilterCombobox
            v-model="genreFilter"
            :options="genreOptions"
            placeholder="Genre"
            all-label="All genres"
          />
        </div>
        <div class="advanced-field">
          <label>Franchise</label>
          <FilterCombobox
            v-model="franchiseFilter"
            :options="franchiseOptions"
            placeholder="Franchise"
            all-label="All franchises"
          />
        </div>
        <div class="advanced-field">
          <label>Collection</label>
          <FilterCombobox
            v-model="collectionFilter"
            :options="collectionOptions"
            placeholder="Collection"
            all-label="All collections"
          />
        </div>
        <div class="advanced-field">
          <label>Company</label>
          <FilterCombobox
            v-model="companyFilter"
            :options="companyOptions"
            placeholder="Company"
            all-label="All companies"
          />
        </div>
        <div class="advanced-field">
          <label>Age Rating</label>
          <FilterCombobox
            v-model="ageRatingFilter"
            :options="ageRatingOptions"
            placeholder="Age rating"
            all-label="All ratings"
          />
        </div>
        <div class="advanced-field">
          <label>Region</label>
          <FilterCombobox
            v-model="regionFilter"
            :options="regionOptions"
            placeholder="Region"
            all-label="All regions"
          />
        </div>
        <div class="advanced-field">
          <label>Language</label>
          <FilterCombobox
            v-model="languageFilter"
            :options="languageOptions"
            placeholder="Language"
            all-label="All languages"
          />
        </div>
        <div class="advanced-field">
          <label>Metadata Provider</label>
          <FilterCombobox
            v-model="metadataProviderFilter"
            :options="metadataProviderOptions"
            placeholder="Provider"
            all-label="All providers"
          />
        </div>
        <div class="advanced-field">
          <label>Achievements</label>
          <select
            v-model="achievementsFilter"
            class="filter-select"
            aria-label="Achievements"
          >
            <option value="all">All games</option>
            <option value="has">Has achievements</option>
            <option value="none">No achievements</option>
          </select>
        </div>
        <div class="advanced-field">
          <label>What's missing</label>
          <select
            v-model="missingFilter"
            class="filter-select"
            aria-label="What's missing"
          >
            <option value="none">Nothing, show everything</option>
            <option value="playtime">No playtime logged</option>
            <option value="rating">No rating</option>
            <option value="tags">No tags</option>
            <option value="description">No description</option>
          </select>
        </div>
        <div class="advanced-field advanced-field-wide">
          <label>Tags (any of)</label>
          <div class="tags-multiselect">
            <button
              v-for="tag in genreOptions"
              :key="tag"
              type="button"
              class="tag-chip"
              :class="{ active: tagsFilter.includes(tag) }"
              @click="toggleTagFilter(tag)"
            >
              {{ tag }}
            </button>
          </div>
        </div>
        <div class="advanced-toggles">
          <button
            type="button"
            class="toggle-chip"
            :class="{ active: favoritesOnly }"
            @click="favoritesOnly = !favoritesOnly"
          >
            ★ Favorites only
          </button>
          <button
            type="button"
            class="toggle-chip"
            :class="{ active: retroAchievementsOnly }"
            @click="retroAchievementsOnly = !retroAchievementsOnly"
          >
            Has RetroAchievements tracking
          </button>
          <button
            type="button"
            class="clear-advanced"
            :disabled="!advancedFilterCount"
            @click="clearAdvancedFilters"
          >
            Clear advanced filters
          </button>
        </div>
      </div>

      <div class="status-tabs">
        <button
          v-for="s in statusOptions"
          :key="s"
          type="button"
          class="status-tab"
          :class="{ active: statusFilter === s }"
          @click="statusFilter = s"
        >
          {{ s === "all" ? "All" : s }}
          <span class="n">{{ statusCounts[s] }}</span>
        </button>
      </div>

      <div v-if="activeFilterPills.length" class="active-filter-pills">
        <button
          v-for="pill in activeFilterPills"
          :key="pill.key"
          type="button"
          class="filter-pill"
          :title="`Remove ${pill.label} filter`"
          @click="pill.clear()"
        >
          {{ pill.label }} <span class="filter-pill-x">✕</span>
        </button>
        <button
          type="button"
          class="filter-pill-clear-all"
          @click="clearAllFilters"
        >
          Clear all
        </button>
      </div>

      <p v-if="loading" class="empty-state">Loading…</p>
      <p v-else-if="error" class="empty-state error">{{ error }}</p>

      <div v-else-if="isEmpty" class="empty-state rich">
        <svg
          v-if="!hasAnyGames"
          viewBox="0 0 24 24"
          width="48"
          height="48"
          fill="none"
          stroke="currentColor"
          stroke-width="1.4"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <rect x="3" y="5" width="18" height="14" rx="2" />
          <path d="M3 9h18" />
          <path d="M8 13h.01M12 13h.01M16 13h.01" />
        </svg>
        <h3 v-if="!hasAnyGames">Your library is empty</h3>
        <p>
          {{
            hasAnyGames
              ? "Nothing matches. Try a different filter or search."
              : "Add your first game to get started."
          }}
        </p>
        <div v-if="searchSuggestions.length" class="search-suggestions">
          <span>Did you mean:</span>
          <button
            v-for="s in searchSuggestions"
            :key="s"
            type="button"
            class="search-suggestion-item"
            @click="searchQuery = s"
          >
            {{ s }}
          </button>
        </div>
        <button
          v-if="hasAnyGames"
          type="button"
          class="btn-outline"
          @click="clearAllFilters"
        >
          Clear filters
        </button>
        <template v-else>
          <button type="button" class="btn-solid" @click="openAddModal">
            + Add Game
          </button>
          <ul class="empty-hint-list">
            <li>
              Add a game manually, or connect Steam/GOG/PlayStation in Settings
              to sync a library
            </li>
            <li>
              Drop screenshots or files into Upload and assign them to a game
              later
            </li>
          </ul>
        </template>
      </div>

      <template v-else>
        <div
          v-if="viewMode === 'cards'"
          class="grid-virtual-container"
          :style="{ height: rowVirtualizer.getTotalSize() + 'px' }"
        >
          <div
            v-for="virtualRow in rowVirtualizer.getVirtualItems()"
            :key="virtualRow.index"
            :ref="(el) => rowVirtualizer.measureElement(el as HTMLElement)"
            :data-index="virtualRow.index"
            class="grid-row"
            :style="{
              transform: `translateY(${virtualRow.start}px)`,
              gridTemplateColumns: `repeat(${CARD_COLUMNS}, 1fr)`,
            }"
          >
            <GameCard
              v-for="(game, colIndex) in cardsInRow(virtualRow.index)"
              :key="game.id"
              :game="game"
              :rank="rankByGameId.get(game.id) ?? null"
              :select-mode="selectMode"
              :selected="selectedIds.has(game.id)"
              :keyboard-focused="
                gridFocusIndex === virtualRow.index * CARD_COLUMNS + colIndex
              "
              @edit="openEditModal"
              @add-to-collection="handleAddToCollection"
              @toggle-select="toggleSelect"
            />
          </div>
        </div>

        <div v-else-if="viewMode === 'list'" class="list-view">
          <div v-if="filteredGames.length" class="list-header">
            <span></span>
            <button
              type="button"
              class="sortable left"
              :class="{ active: sortBy === 'name' }"
              @click="sortBy = 'name'"
            >
              Name
            </button>
            <span></span>
            <button
              type="button"
              class="sortable"
              :class="{ active: sortBy === 'playtime' }"
              @click="sortBy = 'playtime'"
            >
              Playtime
            </button>
            <button
              type="button"
              class="sortable"
              :class="{ active: sortBy === 'rating' }"
              @click="sortBy = 'rating'"
            >
              Rating
            </button>
            <span>Rank</span>
            <button
              type="button"
              class="sortable"
              :class="{ active: sortBy === 'neglected' }"
              @click="sortBy = 'neglected'"
            >
              Last played
            </button>
            <span>Released</span>
            <span>Status</span>
          </div>
          <div
            v-for="game in filteredGames"
            :key="game.id"
            class="list-row"
            @click="selectMode ? toggleSelect(game) : openGame(game)"
          >
            <div class="list-thumb-wrap">
              <img
                class="list-cover"
                :src="game.coverImageUrl"
                alt=""
                loading="lazy"
                decoding="async"
              />
              <div
                v-if="selectMode"
                class="select-checkbox"
                :class="{ checked: selectedIds.has(game.id) }"
                @click.stop="toggleSelect(game)"
              >
                <CheckIcon v-if="selectedIds.has(game.id)" />
              </div>
            </div>
            <div class="list-title-col">
              <div class="list-title">{{ game.title }}</div>
              <div class="list-sub">
                {{ game.tags[0] ?? "No genre"
                }}<template v-if="game.platforms[0]">
                  · {{ game.platforms[0].platform }}</template
                >
              </div>
            </div>
            <div class="icon-cluster">
              <button
                type="button"
                class="icon-btn"
                :class="{ active: game.favorite }"
                :title="
                  game.favorite ? 'Remove from favorites' : 'Add to favorites'
                "
                @click.stop="toggleFavorite(game)"
              >
                <HeartIcon :filled="game.favorite" />
              </button>
              <button
                type="button"
                class="icon-btn"
                title="Add to collection"
                @click.stop="handleAddToCollection(game)"
              >
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
                </svg>
              </button>
              <button
                type="button"
                class="icon-btn"
                title="Edit"
                @click.stop="openEditModal(game)"
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
            <div class="stat-cell strong">
              {{ totalPlaytime(game) === "N/A" ? "–" : totalPlaytime(game) }}
            </div>
            <div class="score-cell" :class="{ empty: !computeScore(game) }">
              {{
                computeScore(game)
                  ? `★ ${computeScore(game)!.sum.toFixed(1)}`
                  : "–"
              }}
            </div>
            <div class="rank-cell">
              <span v-if="rankByGameId.get(game.id)" class="rank-badge"
                >#{{ rankByGameId.get(game.id) }}</span
              >
              <span v-else class="rank-empty">–</span>
            </div>
            <div class="stat-cell">
              {{
                gameLastPlayed(game)
                  ? new Date(gameLastPlayed(game)!).toLocaleDateString()
                  : "–"
              }}
            </div>
            <div class="stat-cell">
              {{ game.releaseDate ? formatDisplayDate(game.releaseDate) : "–" }}
            </div>
            <div class="status-cell">
              <span
                class="status-pill"
                :class="`st-${game.status.replace(' ', '-')}`"
                >{{ game.status }}</span
              >
            </div>
          </div>
        </div>

        <div v-else class="detail-view">
          <div class="detail-list">
            <button
              v-for="game in filteredGames"
              :key="game.id"
              type="button"
              class="detail-list-item"
              :class="{ active: selectedGame?.id === game.id }"
              @click="selectedGame = game"
            >
              <img
                class="detail-list-thumb"
                :src="game.coverImageUrl"
                alt=""
                loading="lazy"
                decoding="async"
              />
              <span>{{ game.title }}</span>
            </button>
          </div>

          <Transition name="preview-fade" mode="out-in">
            <div
              v-if="selectedGame"
              :key="selectedGame.id"
              class="detail-preview"
            >
              <div
                class="preview-banner"
                :style="{
                  backgroundImage: `url(${sizedAssetUrl(selectedGame.bannerImageUrl, 800)})`,
                }"
              >
                <div class="preview-banner-overlay"></div>
              </div>
              <div class="preview-info">
                <h2>{{ selectedGame.title }}</h2>
                <div class="preview-meta">
                  <span class="preview-badge">{{ selectedGame.status }}</span>
                  <span
                    v-if="computeScore(selectedGame)"
                    class="preview-badge score"
                  >
                    ★ {{ computeScore(selectedGame)!.sum.toFixed(1) }}
                  </span>
                  <span class="preview-badge">{{
                    totalPlaytime(selectedGame)
                  }}</span>
                </div>
                <div class="preview-details">
                  <div v-if="selectedGame.developer" class="preview-detail-row">
                    <span class="preview-detail-label">Developer</span>
                    <span>{{ selectedGame.developer }}</span>
                  </div>
                  <div v-if="selectedGame.publisher" class="preview-detail-row">
                    <span class="preview-detail-label">Publisher</span>
                    <span>{{ selectedGame.publisher }}</span>
                  </div>
                  <div v-if="selectedGame.series" class="preview-detail-row">
                    <span class="preview-detail-label">Series</span>
                    <span>{{ selectedGame.series }}</span>
                  </div>
                  <div v-if="selectedGame.source" class="preview-detail-row">
                    <span class="preview-detail-label">Source</span>
                    <span>{{ selectedGame.source }}</span>
                  </div>
                  <div v-if="selectedGame.ageRating" class="preview-detail-row">
                    <span class="preview-detail-label">Age Rating</span>
                    <span>{{ selectedGame.ageRating }}</span>
                  </div>
                  <div
                    v-if="selectedGame.releaseDate"
                    class="preview-detail-row"
                  >
                    <span class="preview-detail-label">Released</span>
                    <span>{{
                      formatDisplayDate(selectedGame.releaseDate)
                    }}</span>
                  </div>
                  <div
                    v-if="activePriority(selectedGame) !== null"
                    class="preview-detail-row"
                  >
                    <span class="preview-detail-label">Priority</span>
                    <span>{{
                      priorityLabel(activePriority(selectedGame)!)
                    }}</span>
                  </div>
                  <div v-if="selectedGame.dateAdded" class="preview-detail-row">
                    <span class="preview-detail-label">Added</span>
                    <span>{{
                      new Date(selectedGame.dateAdded).toLocaleDateString()
                    }}</span>
                  </div>
                  <div
                    v-if="selectedGame.platforms.length"
                    class="preview-detail-row"
                  >
                    <span class="preview-detail-label">Platforms</span>
                    <div class="preview-platforms">
                      <div
                        v-for="p in selectedGame.platforms"
                        :key="p.platform"
                      >
                        {{ p.platform }}:
                        {{ Math.round(p.playtimeMinutes / 60) }}h
                        <span v-if="p.completionPercent !== null"
                          >· {{ p.completionPercent }}%</span
                        >
                      </div>
                    </div>
                  </div>
                  <div
                    v-if="selectedGame.tags.length"
                    class="preview-detail-row"
                  >
                    <span class="preview-detail-label">Tags</span>
                    <span class="preview-pills">
                      <span
                        v-for="tag in selectedGame.tags"
                        :key="tag"
                        class="preview-pill"
                        >{{ tag }}</span
                      >
                    </span>
                  </div>
                  <div
                    v-if="selectedGame.features.length"
                    class="preview-detail-row"
                  >
                    <span class="preview-detail-label">Features</span>
                    <span class="preview-pills">
                      <span
                        v-for="f in selectedGame.features"
                        :key="f"
                        class="preview-pill"
                        >{{ f }}</span
                      >
                    </span>
                  </div>
                  <div
                    v-if="selectedGame.links.length"
                    class="preview-detail-row"
                  >
                    <span class="preview-detail-label">Links</span>
                    <div class="preview-links">
                      <a
                        v-for="link in selectedGame.links"
                        :key="link.url"
                        :href="link.url"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {{ link.label }}
                      </a>
                    </div>
                  </div>
                  <div
                    v-if="
                      selectedGame.ownership.format ||
                      selectedGame.ownership.price !== null
                    "
                    class="preview-detail-row"
                  >
                    <span class="preview-detail-label">Ownership</span>
                    <span>
                      {{ selectedGame.ownership.format ?? "N/A" }}
                      <span v-if="selectedGame.ownership.price !== null">
                        · {{ selectedGame.ownership.priceCurrency ?? "USD" }}
                        {{ selectedGame.ownership.price.toFixed(2) }}
                      </span>
                    </span>
                  </div>
                  <div
                    v-if="selectedGame.folderLocation"
                    class="preview-detail-row"
                  >
                    <span class="preview-detail-label">Folder</span>
                    <span>{{ selectedGame.folderLocation }}</span>
                  </div>
                </div>
                <div
                  v-if="selectedGameDescriptionHtml"
                  class="preview-description-html"
                  v-html="selectedGameDescriptionHtml"
                ></div>
                <div class="preview-actions">
                  <button
                    type="button"
                    class="primary-button"
                    @click="openGame(selectedGame)"
                  >
                    Open Full Page
                  </button>
                  <button
                    type="button"
                    class="secondary-button"
                    @click="openEditModal(selectedGame)"
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    class="icon-button"
                    title="Add to collection"
                    @click="handleAddToCollection(selectedGame)"
                  >
                    <svg
                      viewBox="0 0 24 24"
                      width="16"
                      height="16"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    >
                      <path
                        d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"
                      />
                    </svg>
                  </button>
                  <button
                    type="button"
                    class="icon-button"
                    :class="{ active: selectedGame.favorite }"
                    :title="
                      selectedGame.favorite
                        ? 'Remove from favorites'
                        : 'Add to favorites'
                    "
                    @click="toggleFavorite(selectedGame)"
                  >
                    <HeartIcon :filled="selectedGame.favorite" />
                  </button>
                </div>
              </div>
            </div>
          </Transition>
          <p v-if="!selectedGame" class="empty-row">
            Select a game to preview it.
          </p>
        </div>
      </template>

      <GameFormModal
        v-if="showFormModal"
        :game="editingGame"
        @close="showFormModal = false"
        @saved="onGameSaved"
        @delete="onDeleteFromModal"
      />

      <CollectionPickerModal
        v-if="collectionPickerGame"
        :game="collectionPickerGame"
        @close="collectionPickerGame = null"
        @added="onCollectionAdded"
      />

      <BulkEditModal
        v-if="showBulkEditModal"
        :game-ids="Array.from(selectedIds)"
        @close="showBulkEditModal = false"
        @saved="onBulkEditSaved"
      />

      <RandomGamePicker
        v-if="showRandomPicker"
        :games="games"
        @close="showRandomPicker = false"
      />

      <div
        v-if="deletingGame"
        class="confirm-backdrop"
        @click.self="deletingGame = null"
      >
        <div class="confirm-dialog">
          <h3>Delete {{ deletingGame.title }}?</h3>
          <p>
            Moved to trash, recoverable for 7 days from Settings, then purged
            for good.
          </p>
          <div v-if="deleteError" class="confirm-error">{{ deleteError }}</div>
          <div class="confirm-actions">
            <button
              type="button"
              class="secondary-button"
              @click="deletingGame = null"
            >
              Cancel
            </button>
            <button
              type="button"
              class="danger-button"
              :disabled="deleting"
              @click="confirmDelete"
            >
              {{ deleting ? "Deleting…" : "Delete" }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </main>
</template>

<style scoped>
.library {
  position: relative;
  font-family: system-ui, sans-serif;
  background: #0d0d0d;
  min-height: 100vh;
  color: #fff;
  overflow-x: hidden;
}
/* List + preview mode: the page itself doesn't scroll, only the list and
   preview panes do, via their own overflow-y (see .detail-list/.detail-preview) */
.library.locked {
  height: 100vh;
  overflow-y: hidden;
  box-sizing: border-box;
}
/* let the panels stretch to fill whatever room is actually left below the
   header/filters, instead of guessing that height with a fixed calc() */
.library.locked .content {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.library.locked .detail-view {
  flex: 1;
  height: auto;
  min-height: 0;
}
.content {
  position: relative;
  z-index: 1;
  padding: 24px 24px 24px 48px;
  box-sizing: border-box;
}
@media (max-width: 720px) {
  .content {
    padding: 16px 14px 24px;
  }
}
.library {
  --bg: #0d0d0d;
  --surface: #1a1a1a;
  --surface-2: #222222;
  --border: #2b2b2b;
  --border-soft: #202020;
  --accent: #d68a34;
  --accent-soft: rgba(214, 138, 52, 0.16);
  --accent-line: rgba(214, 138, 52, 0.4);
  --text: #f2f2f2;
  --text-dim: #9c9c9c;
  --text-faint: #666;
  --good: #6fbf73;
  --good-soft: rgba(111, 191, 115, 0.16);
  --hold: #7ba7d9;
  --hold-soft: rgba(123, 167, 217, 0.16);
  --dropped: #d96f6f;
  --dropped-soft: rgba(217, 111, 111, 0.16);
  --plan: #9d8cd9;
  --plan-soft: rgba(157, 140, 217, 0.16);
}
.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
.page-head h1 {
  font-weight: 800;
  font-size: 1.7rem;
  margin: 0;
}
.page-head .sub {
  color: var(--text-faint);
  font-size: 0.85rem;
  margin-top: 4px;
}
.head-actions {
  display: flex;
  gap: 8px;
}
.add-btn {
  background: var(--accent);
  border: none;
  color: #14100a;
  border-radius: 8px;
  padding: 0 18px;
  height: 38px;
  font-family: inherit;
  font-size: 0.85rem;
  font-weight: 700;
  cursor: pointer;
}
.select-btn {
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--text-dim);
  border-radius: 8px;
  padding: 0 16px;
  height: 38px;
  font-family: inherit;
  font-size: 0.85rem;
  font-weight: 700;
  cursor: pointer;
}
.select-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.select-btn.on {
  background: var(--accent-soft);
  border-color: var(--accent-line);
  color: var(--accent);
}
.toolbar {
  margin-top: 16px;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.search-wrap {
  position: relative;
  flex: 1;
  min-width: 140px;
  max-width: 340px;
}
.search-wrap > svg {
  position: absolute;
  left: 11px;
  top: 50%;
  transform: translateY(-50%);
  width: 15px;
  height: 15px;
  color: var(--text-faint);
  pointer-events: none;
}
.search-input {
  box-sizing: border-box;
  height: 38px;
  width: 100%;
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--text);
  border-radius: 8px;
  padding: 0 12px 0 34px;
  font-family: inherit;
  font-size: 0.85rem;
}
.search-input:focus {
  outline: none;
  border-color: var(--accent-line);
}
.sort-select,
.filter-select {
  box-sizing: border-box;
  height: 38px;
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--text);
  border-radius: 8px;
  padding: 0 12px;
  font-family: inherit;
  font-size: 0.85rem;
  cursor: pointer;
}
.sort-select:focus,
.filter-select:focus {
  outline: none;
  border-color: var(--accent-line);
}
.filter-btn {
  box-sizing: border-box;
  height: 38px;
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--text-dim);
  border-radius: 8px;
  padding: 0 14px;
  font-family: inherit;
  font-size: 0.85rem;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
}
.filter-btn.active-filter {
  border-color: var(--accent-line);
  color: var(--accent);
}
.filter-btn .count {
  background: var(--accent);
  color: #14100a;
  border-radius: 999px;
  font-size: 0.66rem;
  font-weight: 800;
  padding: 1px 6px;
}
.status-tabs {
  margin-top: 14px;
  margin-bottom: 20px;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  border-bottom: 1px solid var(--border-soft);
}
.status-tab {
  background: transparent;
  border: none;
  color: var(--text-dim);
  font-family: inherit;
  font-size: 0.82rem;
  font-weight: 600;
  padding: 10px 14px;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  display: flex;
  align-items: center;
  gap: 7px;
  text-transform: capitalize;
}
.status-tab.active {
  color: var(--text);
  border-bottom-color: var(--accent);
}
.status-tab .n {
  font-variant-numeric: tabular-nums;
  color: var(--text-faint);
  font-weight: 500;
}
.status-tab.active .n {
  color: var(--text-dim);
}
.platform-genre-group {
  grid-column: 1 / -1;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.recent-searches-dropdown {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  width: 220px;
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  border-radius: 8px;
  padding: 6px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.45);
  z-index: 20;
}
.recent-searches-label {
  color: #777;
  font-size: 10.5px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 4px 8px 6px;
}
.recent-search-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  background: none;
  border: none;
  color: #eee;
  font-size: 13px;
  text-align: left;
  padding: 7px 8px;
  border-radius: 6px;
  cursor: pointer;
}
.recent-search-item:hover {
  background: rgba(255, 255, 255, 0.06);
}
.recent-search-remove {
  color: #666;
  font-size: 11px;
  padding: 2px 4px;
  border-radius: 4px;
}
.recent-search-remove:hover {
  color: #fca5a5;
}
.select-button-wrap,
.presets-wrap {
  position: relative;
}
.presets-dropdown {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  width: 220px;
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  border-radius: 8px;
  padding: 6px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.45);
  z-index: 20;
}
.preset-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  background: none;
  border: none;
  color: #eee;
  font-size: 13px;
  text-align: left;
  padding: 8px;
  border-radius: 6px;
  cursor: pointer;
}
.preset-item:hover {
  background: rgba(255, 255, 255, 0.06);
}
.preset-remove {
  color: #666;
  font-size: 11px;
  padding: 2px 4px;
  border-radius: 4px;
}
.preset-remove:hover {
  color: #fca5a5;
}
.preset-empty {
  color: #666;
  font-size: 12px;
  padding: 8px;
  margin: 0;
}
.preset-save {
  display: block;
  width: 100%;
  background: rgba(214, 138, 52, 0.12);
  border: none;
  color: #d68a34;
  font-size: 12.5px;
  font-weight: 600;
  text-align: left;
  padding: 8px;
  border-radius: 6px;
  cursor: pointer;
  margin-top: 4px;
}
.preset-save:hover {
  background: rgba(214, 138, 52, 0.2);
}
.first-use-hint {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  width: 240px;
  background: var(--surface);
  border: 1px solid var(--accent-line);
  border-radius: 10px;
  padding: 12px 14px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.45);
  z-index: 20;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.first-use-hint span {
  color: var(--text);
  font-size: 0.82rem;
  line-height: 1.5;
}
.first-use-hint-dismiss {
  align-self: flex-end;
  background: var(--accent-soft);
  border: 1px solid var(--accent-line);
  color: var(--accent);
  border-radius: 7px;
  padding: 5px 10px;
  font-family: inherit;
  font-size: 0.75rem;
  font-weight: 700;
  cursor: pointer;
}
/* anchored to Select, the tip ran off a phone screen */
@media (max-width: 600px) {
  .first-use-hint {
    position: fixed;
    top: auto;
    left: 16px;
    right: 16px;
    bottom: 16px;
    width: auto;
  }
}
.density-toggle {
  display: flex;
  gap: 2px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 3px;
  box-sizing: border-box;
}
.density-button {
  background: none;
  border: none;
  color: var(--text-faint);
  width: 26px;
  height: 26px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.7rem;
  font-weight: 700;
}
.density-button:hover {
  color: var(--text);
  background: rgba(255, 255, 255, 0.06);
}
.density-button.active {
  color: #14100a;
  background: var(--accent);
}
.active-filter-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin: -6px 0 16px;
}
.filter-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(214, 138, 52, 0.12);
  border: 1px solid rgba(214, 138, 52, 0.35);
  color: #f0c896;
  border-radius: 999px;
  padding: 5px 10px 5px 12px;
  font-size: 12px;
  cursor: pointer;
}
.filter-pill:hover {
  background: rgba(214, 138, 52, 0.2);
}
.filter-pill-x {
  color: #d68a34;
  font-size: 10px;
}
.filter-pill-clear-all {
  background: none;
  border: none;
  color: #777;
  font-size: 12px;
  text-decoration: underline;
  cursor: pointer;
  padding: 5px 4px;
}
.filter-pill-clear-all:hover {
  color: #ccc;
}
.search-suggestions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  color: var(--text-dim);
  font-size: 0.82rem;
  margin-top: -8px;
}
.search-suggestion-item {
  background: var(--surface-2);
  border: 1px solid var(--border);
  color: var(--text);
  border-radius: 999px;
  padding: 5px 12px;
  font-family: inherit;
  font-size: 0.78rem;
  cursor: pointer;
}
.search-suggestion-item:hover {
  border-color: var(--accent-line);
  color: var(--accent);
}
.empty-hint-list {
  list-style: none;
  margin: 8px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  text-align: left;
  max-width: 420px;
}
.empty-hint-list li {
  color: var(--text-dim);
  font-size: 0.78rem;
  line-height: 1.5;
  background: var(--surface);
  border: 1px solid var(--border-soft);
  border-radius: 8px;
  padding: 8px 12px;
}
.filter-select:hover {
  border-color: #4a4a4a;
}
.filter-select {
  appearance: none;
  -webkit-appearance: none;
  padding-right: 34px;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'><path d='M1 1l4 4 4-4' stroke='%23999' stroke-width='1.5' fill='none' stroke-linecap='round' stroke-linejoin='round'/></svg>");
  background-repeat: no-repeat;
  background-position: right 16px center;
}
/* fixed 10-per-row grid, column width only depends on the container, never
   on how many games there are, so adding one more game just starts filling
   the next row instead of resizing every existing card */
.grid-virtual-container {
  position: relative;
  width: 100%;
}
.grid-row {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  display: grid;
  grid-template-columns: repeat(10, 1fr);
  gap: 14px;
  padding-bottom: 14px;
}
.grid-row :deep(.game-card-wrap) {
  width: auto;
  min-width: 0;
}

/* Advanced filters */
.bulk-toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 12px;
  padding: 10px 16px;
  background: var(--accent-soft);
  border: 1px solid var(--accent-line);
  border-radius: 10px;
}
.bulk-toolbar .count {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--accent);
  white-space: nowrap;
}
.bulk-toolbar .btn-solid {
  margin-left: auto;
}
.btn-outline {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text-dim);
  border-radius: 8px;
  padding: 0 16px;
  height: 36px;
  font-family: inherit;
  font-size: 0.82rem;
  font-weight: 700;
  cursor: pointer;
}
.btn-solid {
  background: var(--accent);
  border: none;
  color: #14100a;
  border-radius: 8px;
  padding: 0 16px;
  height: 36px;
  font-family: inherit;
  font-size: 0.82rem;
  font-weight: 700;
  cursor: pointer;
}
.btn-outline:disabled,
.btn-solid:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.form-success.bulk-success {
  color: #86efac;
  font-size: 13px;
  background: rgba(34, 197, 94, 0.1);
  border: 1px solid rgba(34, 197, 94, 0.3);
  border-radius: 8px;
  padding: 8px 12px;
  margin-bottom: 20px;
}
.select-checkbox {
  width: 26px;
  height: 26px;
  border-radius: 7px;
  background: rgba(10, 10, 10, 0.8);
  border: 1.5px solid rgba(255, 255, 255, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--accent, #d68a34);
  font-size: 0.85rem;
  font-weight: 800;
  position: absolute;
  top: 6px;
  left: 6px;
  z-index: 4;
}
.select-checkbox.checked {
  background: var(--accent, #d68a34);
  border-color: var(--accent, #d68a34);
  color: #14100a;
}
.advanced-panel {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 14px;
  margin-top: 10px;
  padding: 14px 16px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
}
.advanced-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.advanced-field-wide {
  grid-column: 1 / -1;
}
.tags-multiselect {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.tag-chip {
  box-sizing: border-box;
  height: 28px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  color: var(--text-dim);
  border-radius: 999px;
  padding: 0 12px;
  font-size: 0.76rem;
  font-weight: 700;
  cursor: pointer;
}
.tag-chip:hover {
  border-color: #4a4a4a;
}
.tag-chip.active {
  background: var(--accent-soft);
  border-color: var(--accent-line);
  color: var(--accent);
}
.advanced-field label {
  color: var(--text-dim);
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.advanced-field .combobox,
.advanced-field .filter-select {
  width: 100%;
}
.advanced-toggles {
  grid-column: 1 / -1;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  padding-top: 6px;
  border-top: 1px solid #232323;
  margin-top: 4px;
}
.toggle-chip {
  box-sizing: border-box;
  height: 28px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  color: var(--text-dim);
  border-radius: 999px;
  padding: 0 12px;
  font-size: 0.76rem;
  font-weight: 700;
  cursor: pointer;
}
.toggle-chip:hover {
  border-color: #4a4a4a;
}
.toggle-chip.active {
  color: var(--accent);
  border-color: var(--accent-line);
  background: var(--accent-soft);
}
.clear-advanced {
  margin-left: auto;
  background: none;
  border: none;
  color: #999;
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
  text-decoration: underline;
}
.clear-advanced:hover:not(:disabled) {
  color: #fff;
}
.clear-advanced:disabled {
  color: #555;
  cursor: not-allowed;
  text-decoration: none;
}

.empty-state {
  color: var(--text-faint);
  font-size: 0.9rem;
  padding: 40px 0;
  text-align: center;
}
.empty-state.error {
  color: #e57373;
}
/* the first-run "library is empty" guide, which Media has no equivalent of */
.empty-state.rich {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 80px 20px;
}
.empty-state.rich svg {
  color: var(--border);
  margin-bottom: 10px;
}
.empty-state.rich h3 {
  margin: 0;
  color: var(--text);
  font-size: 1.05rem;
}
.empty-state.rich p {
  margin: 0 0 10px;
}

/* List view */
.list-view {
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow-x: auto;
}
.list-header,
.list-row {
  display: grid;
  grid-template-columns:
    76px minmax(200px, 1fr)
    100px 84px 64px 46px 104px 104px 128px;
  align-items: center;
  gap: 20px;
  min-width: 1066px;
}
.list-header {
  padding: 0 16px 8px;
}
.list-header span,
.list-header .sortable {
  color: var(--text-faint);
  font-size: 0.66rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 700;
  text-align: center;
}
.list-header .sortable {
  background: none;
  border: none;
  padding: 0;
  font-family: inherit;
  cursor: pointer;
}
.list-header .sortable.left {
  text-align: left;
}
.list-header .sortable:hover,
.list-header .sortable.active {
  color: var(--accent);
}
.list-row {
  /* a row below the fold is not drawn until it is near, which keeps a long
     list quick to open */
  content-visibility: auto;
  contain-intrinsic-size: auto 76px;
  padding: 10px 16px;
  background: var(--surface);
  border: 1px solid var(--border-soft);
  border-radius: 10px;
  cursor: pointer;
  transition: border-color 0.15s ease;
}
.list-row:hover {
  border-color: var(--accent-line);
}
.list-thumb-wrap {
  position: relative;
  width: 76px;
}
.list-cover {
  display: block;
  width: 76px;
  aspect-ratio: 2 / 3;
  object-fit: cover;
  border-radius: 6px;
  background: var(--surface-2);
}
.list-title-col {
  min-width: 0;
}
.list-title {
  font-weight: 700;
  font-size: 1.02rem;
  line-height: 1.3;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.list-sub {
  font-size: 0.72rem;
  color: var(--text-faint);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.icon-cluster {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.icon-btn {
  background: var(--surface-2);
  border: 1px solid var(--border);
  color: var(--text-faint);
  width: 28px;
  height: 28px;
  border-radius: 7px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
}
.icon-btn svg {
  width: 12px;
  height: 12px;
}
.icon-btn:hover {
  border-color: var(--accent-line);
  color: var(--text);
}
.icon-btn.active {
  color: var(--accent);
  border-color: var(--accent-line);
  background: var(--accent-soft);
}
.rank-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 20px;
  padding: 0 5px;
  border-radius: 5px;
  background: var(--accent-soft);
  color: var(--accent);
  border: 1px solid var(--accent-line);
  font-size: 0.68rem;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}
.rank-cell {
  display: flex;
  align-items: center;
  justify-content: center;
}
.rank-empty {
  color: var(--text-faint);
  font-size: 0.75rem;
}
.status-cell,
.stat-cell,
.score-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  font-variant-numeric: tabular-nums;
}
.stat-cell {
  font-size: 0.8rem;
  color: var(--text-dim);
}
.stat-cell.strong {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--text);
}
.score-cell {
  font-size: 0.82rem;
  font-weight: 700;
  color: var(--accent);
  white-space: nowrap;
}
.score-cell.empty {
  justify-self: center;
  min-width: 20px;
  height: 20px;
  padding: 0 5px;
  border-radius: 5px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  color: var(--text-faint);
  font-weight: 600;
}
.status-pill {
  display: inline-block;
  width: 128px;
  text-align: center;
  background: var(--surface-2);
  color: var(--text-dim);
  padding: 5px 10px;
  border-radius: 999px;
  font-size: 0.6875rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.01em;
  white-space: nowrap;
}
.status-pill.st-playing {
  background: var(--accent-soft);
  color: var(--accent);
}
.status-pill.st-beaten,
.status-pill.st-mastered,
.status-pill.st-played {
  background: var(--good-soft);
  color: var(--good);
}
.status-pill.st-on-hold {
  background: var(--hold-soft);
  color: var(--hold);
}
.status-pill.st-dropped {
  background: var(--dropped-soft);
  color: var(--dropped);
}
.status-pill.st-backlog,
.status-pill.st-wishlist {
  background: var(--plan-soft);
  color: var(--plan);
}
.list-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 130px;
  flex-shrink: 0;
}
.icon-button {
  background: var(--surface-2);
  color: var(--text-faint);
  border: 1px solid var(--border);
  border-radius: 7px;
  width: 30px;
  height: 30px;
  flex-shrink: 0;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition:
    background 0.15s ease,
    color 0.15s ease,
    border-color 0.15s ease;
}
.icon-button svg {
  width: 16px;
  height: 16px;
}
.icon-button:hover {
  border-color: var(--accent-line);
  color: var(--text);
}
.icon-button.active {
  color: var(--accent);
  border-color: var(--accent-line);
  background: var(--accent-soft);
}

/* Detail (list + preview) view, a bounded-height split panel so the list
   and the preview each get their own scrollbar instead of the whole page
   scrolling as one long column */
.detail-view {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 20px;
  align-items: start;
  height: calc(100vh - 262px);
  min-height: 420px;
}
.detail-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
}
.detail-list-item {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--surface);
  border: 1px solid var(--border-soft);
  border-radius: 10px;
  padding: 8px 12px 8px 8px;
  cursor: pointer;
  color: var(--text);
  font-family: inherit;
  font-size: 0.85rem;
  font-weight: 700;
  text-align: left;
  transition: border-color 0.15s ease;
}
.detail-list-item:hover {
  border-color: var(--accent-line);
}
.detail-list-item.active {
  background: var(--accent-soft);
  border-color: var(--accent-line);
}
.detail-list-thumb {
  width: 40px;
  aspect-ratio: 2 / 3;
  object-fit: cover;
  border-radius: 6px;
  background: var(--surface-2);
  flex-shrink: 0;
}
.detail-preview {
  border: 1px solid var(--border-soft);
  border-radius: 10px;
  background: var(--surface);
  height: 100%;
  overflow-y: auto;
}
.preview-banner {
  position: relative;
  height: 260px;
  background-color: var(--surface-2);
  background-size: cover;
  background-repeat: no-repeat;
  background-position: center;
}
.preview-banner-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, transparent 40%, var(--surface) 100%);
}
.preview-info {
  padding: 20px;
}
.preview-info h2 {
  margin: 0 0 10px;
  font-size: 1.7rem;
  font-weight: 800;
  color: var(--text);
}
.preview-meta {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
}
.preview-badge {
  background: var(--surface-2);
  border: 1px solid var(--border);
  padding: 5px 12px;
  border-radius: 999px;
  font-size: 0.6875rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.01em;
  color: var(--text-dim);
  font-variant-numeric: tabular-nums;
}
.preview-details {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 18px;
  padding-top: 14px;
  border-top: 1px solid var(--border-soft);
}
.preview-platforms {
  display: flex;
  flex-direction: column;
  gap: 2px;
  color: var(--text);
  font-size: 0.82rem;
}
.preview-links {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.preview-links a {
  color: var(--accent);
  font-size: 0.82rem;
  text-decoration: none;
}
.preview-links a:hover {
  text-decoration: underline;
}
.preview-detail-row {
  display: flex;
  gap: 10px;
  font-size: 0.82rem;
  color: var(--text);
  align-items: baseline;
}
.preview-detail-label {
  color: var(--text-faint);
  font-size: 0.66rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  min-width: 80px;
  flex-shrink: 0;
}
.preview-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.preview-pill {
  background: var(--surface-2);
  border: 1px solid var(--border);
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 0.7rem;
  color: var(--text-dim);
}
.preview-fade-enter-active,
.preview-fade-leave-active {
  transition: opacity 0.2s ease;
}
.preview-fade-enter-from,
.preview-fade-leave-to {
  opacity: 0;
}
.preview-badge.score {
  color: var(--accent);
}
.preview-description-html {
  color: var(--text-dim);
  line-height: 1.6;
  margin: 0 0 18px;
  max-width: 100%;
  overflow-wrap: break-word;
}
.preview-description-html :deep(img),
.preview-description-html :deep(video) {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  margin: 10px 0;
  display: block;
}
.preview-description-html :deep(h1),
.preview-description-html :deep(h2),
.preview-description-html :deep(h3) {
  margin: 18px 0 6px;
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
}
.preview-description-html :deep(p) {
  margin: 0 0 12px;
}
.preview-description-html :deep(a) {
  color: var(--accent);
}
.preview-description-html :deep(ul) {
  padding-left: 20px;
  margin: 0 0 12px;
}
.preview-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
/* same buttons as the page header's Add game / Select */
.preview-actions .primary-button,
.preview-actions .secondary-button {
  height: 38px;
  padding: 0 18px;
  border-radius: 8px;
  font-family: inherit;
  font-size: 0.85rem;
  font-weight: 700;
}
.preview-actions .primary-button {
  background: var(--accent);
  color: #14100a;
}
.preview-actions .secondary-button {
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--text-dim);
}
.empty-row {
  color: #777;
  font-size: 14px;
}

/* Shared buttons */
.primary-button,
.secondary-button,
.small-button,
.danger-button {
  border: none;
  border-radius: 8px;
  padding: 9px 16px;
  font-weight: 600;
  cursor: pointer;
  font-size: 13px;
}
.primary-button {
  background: #d68a34;
  color: #111;
}
.secondary-button,
.small-button {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}
.danger-button {
  background: rgba(220, 38, 38, 0.18);
  color: #fca5a5;
}
.danger-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Confirm dialog */
.confirm-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.65);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 60;
}
.confirm-dialog {
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  border-radius: 12px;
  padding: 22px;
  width: 100%;
  max-width: 360px;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.6);
}
.confirm-dialog h3 {
  margin: 0 0 8px;
}
.confirm-dialog p {
  margin: 0 0 16px;
  color: #aaa;
  font-size: 14px;
}
.confirm-error {
  color: #fca5a5;
  font-size: 13px;
  margin-bottom: 12px;
}
.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

/* Mobile, the list view's per-column widths and the detail view's fixed
   260px/1fr split were both designed against a desktop-width container and
   had never been checked below it: list rows squeezed the title (the one
   thing you actually need to read) to zero width, and the detail split
   crushed the preview pane to an unreadable sliver. List scrolls
   horizontally instead of losing the title; detail stacks into one column
   with a shorter, horizontally-scrolling game strip above the preview. */
@media (max-width: 760px) {
  /* Media's phone list: no header, cover and title side by side, every
     other cell stacked under the title. The two dates are dropped here
     since, stacked without their column headers, they'd be unlabeled. */
  .list-view {
    overflow-x: visible;
  }
  .list-header {
    display: none;
  }
  .list-header,
  .list-row {
    min-width: 0;
  }
  .list-row {
    grid-template-columns: 56px minmax(0, 1fr);
    gap: 6px 12px;
  }
  .list-row > *:nth-child(n + 3) {
    grid-column: 2;
    justify-self: start;
  }
  .list-row > *:nth-child(7),
  .list-row > *:nth-child(8) {
    display: none;
  }
  .list-thumb-wrap {
    width: 56px;
  }
  .list-cover {
    width: 100%;
  }
  .detail-view {
    grid-template-columns: 1fr;
    grid-template-rows: auto 1fr;
    height: auto;
  }
  .detail-list {
    flex-direction: row;
    overflow-x: auto;
    overflow-y: hidden;
    height: auto;
    padding-bottom: 6px;
  }
  .detail-list-item {
    flex-direction: column;
    text-align: center;
    width: 84px;
    flex-shrink: 0;
  }
  .detail-list-item span {
    font-size: 11px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    width: 100%;
  }
  .library.locked {
    height: auto;
    overflow-y: visible;
  }
  .library.locked .content {
    height: auto;
  }
}
</style>
