<script setup lang="ts">
import UiModal from "../components/UiModal.vue";
import {
  ref,
  computed,
  onMounted,
  onUnmounted,
  onActivated,
  onDeactivated,
  nextTick,
  watch,
} from "vue";
import { useKeptAlive } from "../utils/useKeptAlive";
import { useRoute, useRouter } from "vue-router";
import { useWindowVirtualizer } from "@tanstack/vue-virtual";
import GameCard from "../components/GameCard.vue";
import SkeletonBlock from "../components/SkeletonBlock.vue";
import GameFormModal from "../components/GameFormModal.vue";
import BulkEditModal from "../components/BulkEditModal.vue";
import RandomGamePicker from "../components/RandomGamePicker.vue";
import { activePriority, priorityLabel } from "../utils/priority";
import { formatDisplayDate } from "../utils/dates";
import FilterCombobox from "../components/FilterCombobox.vue";
import {
  fetchGames,
  deleteGame,
  setFavorite,
  fetchAchievementsSummary,
  addGameToCollection,
} from "../services/games";
import { takeLibraryScroll } from "../state/libraryScroll";
import { setLibraryNavOrder } from "../state/libraryNav";
import { isCommandPaletteOpen } from "../state/commandPalette";
import CollectionPickerModal from "../components/CollectionPickerModal.vue";
import AccountChip from "../components/AccountChip.vue";
import PageHeader from "../components/PageHeader.vue";
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

type ViewMode = "cards" | "list" | "detail" | "shelves";
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
const isLibraryActive = ref(true);
const error = ref<string | null>(null);

const showFormModal = ref(false);
const editingGame = ref<Game | null>(null);

const deletingGame = ref<Game | null>(null);
const deleting = ref(false);
const deleteError = ref<string | null>(null);

const viewMode = ref<ViewMode>(
  (localStorage.getItem("gameLibraryViewMode") as ViewMode) || "cards",
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
// arriving from Server Stats' tag chart (?tag=Name)
const queryTag = route.query.tag;
if (typeof queryTag === "string" && queryTag) {
  genreFilter.value = queryTag;
}

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

async function loadGames() {
  const token = ++loadGamesToken;
  if (!games.value.length) loading.value = true;
  try {
    const fetched = await fetchGames();
    if (token !== loadGamesToken) return;
    games.value = fetched;
    error.value = null;
    if (selectedGame.value)
      selectedGame.value =
        fetched.find((game) => game.id === selectedGame.value?.id) ?? null;
    // best-effort, a failed summary fetch just means no completion badges,
    // not a broken library page
    try {
      const summary = await fetchAchievementsSummary();
      if (token !== loadGamesToken) return;
      for (const game of games.value) {
        const entry = summary[game.id];
        if (!entry) continue;
        game.achievementTotal = entry.total;
        game.achievementPercent = entry.total
          ? Math.round((entry.unlocked / entry.total) * 100)
          : 0;
      }
    } catch {
      // ignore
    }
    if (
      viewMode.value === "detail" &&
      !selectedGame.value &&
      games.value.length
    ) {
      selectedGame.value = games.value[0];
    }
  } catch (err) {
    if (token !== loadGamesToken) return;
    error.value = err instanceof Error ? err.message : "Failed to load games";
  } finally {
    if (token === loadGamesToken) loading.value = false;
  }
}

async function restoreLibraryScroll() {
  await nextTick();
  if (route.path !== "/games") return;
  const y = takeLibraryScroll();
  if (y > 0) window.scrollTo(0, y);
}
onMounted(async () => {
  await loadGames();
  // the page has no real height until games render, so restoring scroll
  // before that just gets clamped back to ~0, wait for the grid/list to
  // actually paint, then scroll for real. The position itself was captured
  // by a router guard (state/libraryScroll.ts), not onUnmounted here,
  // that runs before any DOM change from the navigation, so it's reliably
  // the position the user was actually looking at when they left.
  await restoreLibraryScroll();
});
useKeptAlive(() => {
  void loadGames();
  void restoreLibraryScroll();
});

// filters are only remembered while you stay on this page, leaving it
// (any other route) wipes them so the next visit starts from a clean slate
onDeactivated(() => {
  clearAllFilters();
  showAdvancedFilters.value = false;
  selectMode.value = false;
  selectedIds.value.clear();
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
  if (
    route.path !== "/games" ||
    e.ctrlKey ||
    e.metaKey ||
    e.altKey ||
    e.defaultPrevented ||
    anyModalOpen() ||
    document.querySelector("dialog[open]")
  )
    return;
  if (
    e.key === "Enter" &&
    e.target instanceof HTMLElement &&
    e.target.closest("button, a, [role='combobox']")
  )
    return;
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
onActivated(() => window.addEventListener("keydown", onGlobalKeydown));
onDeactivated(() => window.removeEventListener("keydown", onGlobalKeydown));
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
// inside the dropdowns to know (or undo) what's currently applied
const activeFilterPills = computed(() => {
  const pills: { key: string; label: string; clear: () => void }[] = [];
  if (statusFilter.value !== "all")
    pills.push({
      key: "status",
      label: statusFilter.value,
      clear: () => (statusFilter.value = "all"),
    });
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
  if (viewMode.value === "shelves") updateAllShelfArrows();
}
onActivated(() => {
  isLibraryActive.value = true;
  onResize();
  window.addEventListener("resize", onResize);
  if (contentEl.value) contentObserver?.observe(contentEl.value);
});
onDeactivated(() => {
  isLibraryActive.value = false;
  window.removeEventListener("resize", onResize);
  contentObserver?.disconnect();
});
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
const rowVirtualizer = useWindowVirtualizer(
  computed(() => ({
    count: cardRowCount.value,
    enabled: isLibraryActive.value,
    estimateSize: () => 330,
    overscan: 3,
  })),
);
function cardsInRow(rowIndex: number): Game[] {
  const start = rowIndex * CARD_COLUMNS.value;
  return filteredGames.value.slice(start, start + CARD_COLUMNS.value);
}

// "Shelves" view, Home Hub's grouped-row layout, applied to the whole
// (filtered) library instead of just Continue Playing/Recently Added
const sourceShelves = computed(() => {
  const map = new Map<string, Game[]>();
  for (const g of filteredGames.value) {
    const key = g.source || "Other";
    if (!map.has(key)) map.set(key, []);
    map.get(key)!.push(g);
  }
  return [...map.entries()]
    .sort((a, b) => b[1].length - a[1].length)
    .map(([name, list]) => ({ name, games: list }));
});
function scrollShelf(e: MouseEvent, dir: 1 | -1) {
  const wrap = (e.currentTarget as HTMLElement).closest(".shelf-wrap");
  const shelf = wrap?.querySelector(".shelf") as HTMLElement | null;
  if (!shelf) return;
  shelf.scrollBy({ left: dir * shelf.clientWidth * 0.9, behavior: "smooth" });
}
// same arrow-visibility pattern as Home Hub's shelves, only shown once
// there's actually somewhere left to scroll
function updateShelfArrows(shelf: HTMLElement) {
  const wrap = shelf.closest(".shelf-wrap");
  if (!wrap) return;
  const left = wrap.querySelector(".shelf-arrow.left");
  const right = wrap.querySelector(".shelf-arrow.right");
  const maxScroll = shelf.scrollWidth - shelf.clientWidth;
  left?.classList.toggle("can-scroll", shelf.scrollLeft > 4);
  right?.classList.toggle("can-scroll", shelf.scrollLeft < maxScroll - 4);
}
function updateAllShelfArrows() {
  document
    .querySelectorAll<HTMLElement>(".shelves-view .shelf")
    .forEach(updateShelfArrows);
}
watch(viewMode, (mode) => {
  if (mode === "shelves") nextTick(updateAllShelfArrows);
});
</script>

<template>
  <main class="library" :class="{ locked: viewMode === 'detail' }">
    <AccountChip fixed />

    <div ref="contentEl" class="content">
      <PageHeader
        title="Games"
        :description="`${games.length} ${games.length === 1 ? 'game' : 'games'}`"
      >
        <template #actions>
          <button
            type="button"
            class="ui-btn ui-btn-ghost"
            :disabled="!games.length"
            title="Pick a game to play, filtered by status, platform, genre, length and priority"
            @click="showRandomPicker = true"
          >
            Random
          </button>
          <button
            type="button"
            class="ui-btn ui-btn-primary"
            @click="openAddModal"
          >
            Add game
          </button>
        </template>
      </PageHeader>
      <div class="header-row">
        <div class="header-actions">
          <div class="search-wrap">
            <input
              ref="searchInputRef"
              data-shortcut="search"
              v-model="searchQuery"
              type="text"
              class="search-input"
              placeholder="Search games… (/)"
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
                showRecentSearches &&
                !searchQuery.trim() &&
                recentSearches.length
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
          <select
            v-model="statusFilter"
            class="filter-select"
            aria-label="Filter by status"
          >
            <option v-for="s in statusOptions" :key="s" :value="s">
              {{ s === "all" ? "All statuses" : s }}
            </option>
          </select>
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
          <select v-model="sortBy" class="filter-select" aria-label="Sort by">
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
              :aria-label="`${d} game cards`"
              :aria-pressed="cardDensity === d"
              @click="cardDensity = d"
            >
              {{ d === "compact" ? "S" : d === "cozy" ? "M" : "L" }}
            </button>
          </div>

          <div class="view-toggle">
            <button
              type="button"
              class="view-toggle-button"
              :class="{ active: viewMode === 'cards' }"
              title="Cards"
              aria-label="Cards view"
              :aria-pressed="viewMode === 'cards'"
              @click="setView('cards')"
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
                <rect x="3" y="3" width="8" height="8" rx="1" />
                <rect x="13" y="3" width="8" height="8" rx="1" />
                <rect x="3" y="13" width="8" height="8" rx="1" />
                <rect x="13" y="13" width="8" height="8" rx="1" />
              </svg>
            </button>
            <button
              type="button"
              class="view-toggle-button"
              :class="{ active: viewMode === 'list' }"
              title="List"
              aria-label="List view"
              :aria-pressed="viewMode === 'list'"
              @click="setView('list')"
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
                <line x1="4" y1="6" x2="20" y2="6" />
                <line x1="4" y1="12" x2="20" y2="12" />
                <line x1="4" y1="18" x2="20" y2="18" />
              </svg>
            </button>
            <button
              type="button"
              class="view-toggle-button"
              :class="{ active: viewMode === 'detail' }"
              title="List + preview"
              aria-label="List and preview view"
              :aria-pressed="viewMode === 'detail'"
              @click="setView('detail')"
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
                <rect x="3" y="3" width="7" height="18" rx="1" />
                <rect x="13" y="3" width="8" height="18" rx="1" />
              </svg>
            </button>
            <button
              type="button"
              class="view-toggle-button"
              :class="{ active: viewMode === 'shelves' }"
              title="Shelves (by source)"
              aria-label="Shelves view"
              :aria-pressed="viewMode === 'shelves'"
              @click="setView('shelves')"
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
                <line x1="4" y1="6" x2="20" y2="6" />
                <line x1="4" y1="12" x2="20" y2="12" />
                <line x1="4" y1="18" x2="20" y2="18" />
                <rect x="4" y="3.5" width="5" height="5" rx="1" />
              </svg>
            </button>
          </div>

          <button
            type="button"
            class="advanced-toggle"
            :class="{ active: showAdvancedFilters }"
            :aria-expanded="showAdvancedFilters"
            @click="showAdvancedFilters = !showAdvancedFilters"
          >
            Advanced Filters
            <span v-if="advancedFilterCount" class="advanced-count">{{
              advancedFilterCount
            }}</span>
          </button>

          <div class="presets-wrap">
            <button
              type="button"
              class="advanced-toggle"
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

          <div class="select-button-wrap">
            <button
              type="button"
              class="advanced-toggle"
              :class="{ active: selectMode }"
              @click="
                toggleSelectMode();
                dismissBulkEditHint();
              "
            >
              {{ selectMode ? "Cancel Select" : "Select" }}
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
        </div>
      </div>

      <div v-if="selectMode" class="bulk-toolbar">
        <span>{{ selectedIds.size }} selected</span>
        <button
          type="button"
          class="small-button"
          :disabled="filteredGames.length === 0"
          @click="selectedIds = new Set(filteredGames.map((g) => g.id))"
        >
          Select all ({{ filteredGames.length }})
        </button>
        <button
          type="button"
          class="small-button"
          :disabled="!selectedIds.size"
          @click="clearSelection"
        >
          Clear
        </button>
        <button
          type="button"
          class="small-button"
          :disabled="!selectedIds.size || bulkAddingToCollection"
          @click="bulkAddToCollection"
        >
          {{ bulkAddingToCollection ? "Adding…" : "Add to Collection" }}
        </button>
        <button
          type="button"
          class="primary-button"
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

      <div v-if="showAdvancedFilters" class="advanced-panel">
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

      <div
        v-if="loading"
        class="skeleton-grid"
        :style="{ gridTemplateColumns: `repeat(${CARD_COLUMNS}, 1fr)` }"
      >
        <div v-for="i in 20" :key="i" class="skeleton-card">
          <SkeletonBlock height="150px" radius="8px" />
          <SkeletonBlock height="14px" width="80%" />
          <SkeletonBlock height="11px" width="50%" />
        </div>
      </div>
      <p v-else-if="error" class="error">{{ error }}</p>

      <div v-else-if="isEmpty" class="empty-state">
        <svg
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
        <h3>
          {{
            hasAnyGames
              ? "No games match your filters"
              : "Your library is empty"
          }}
        </h3>
        <p>
          {{
            hasAnyGames
              ? "Try clearing or adjusting your filters."
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
          class="secondary-button"
          @click="clearAllFilters"
        >
          Clear filters
        </button>
        <template v-else>
          <button type="button" class="primary-button" @click="openAddModal">
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
            <li>
              Set up a Bounty once you've added a few games, for a lightweight
              goal to work toward
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
            <span class="list-header-spacer"></span>
            <button
              type="button"
              class="list-title sortable"
              :class="{ active: sortBy === 'name' }"
              @click="sortBy = 'name'"
            >
              Name
            </button>
            <span class="list-status">Status</span>
            <span class="list-genre">Genre</span>
            <span class="list-platform">Platform</span>
            <button
              type="button"
              class="list-score sortable"
              :class="{ active: sortBy === 'rating' }"
              @click="sortBy = 'rating'"
            >
              Rating
            </button>
            <button
              type="button"
              class="list-playtime sortable"
              :class="{ active: sortBy === 'playtime' }"
              @click="sortBy = 'playtime'"
            >
              Playtime
            </button>
            <button
              type="button"
              class="list-last-played sortable"
              :class="{ active: sortBy === 'neglected' }"
              @click="sortBy = 'neglected'"
            >
              Last played
            </button>
            <span class="list-release">Released</span>
            <span class="list-actions-spacer"></span>
          </div>
          <div
            v-for="game in filteredGames"
            :key="game.id"
            class="list-row"
            @click="selectMode ? toggleSelect(game) : openGame(game)"
          >
            <button
              v-if="selectMode"
              type="button"
              class="list-checkbox"
              :class="{ checked: selectedIds.has(game.id) }"
              :aria-label="`Select ${game.title}`"
              :aria-pressed="selectedIds.has(game.id)"
              @click.stop="toggleSelect(game)"
            >
              <svg
                v-if="selectedIds.has(game.id)"
                viewBox="0 0 24 24"
                width="12"
                height="12"
                fill="none"
                stroke="currentColor"
                stroke-width="3"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d="M20 6L9 17l-5-5" />
              </svg>
            </button>
            <img class="list-cover" :src="game.coverImageUrl" alt="" />
            <button
              type="button"
              class="list-title list-open"
              @click.stop="selectMode ? toggleSelect(game) : openGame(game)"
            >
              {{ game.title }}
            </button>
            <span class="list-status"
              ><span class="status-pill">{{ game.status }}</span></span
            >
            <span class="list-genre" data-label="Genre">{{
              game.tags[0] ?? "N/A"
            }}</span>
            <span class="list-platform" data-label="Platform">{{
              game.platforms[0]?.platform ?? "N/A"
            }}</span>
            <span class="list-score" data-label="Rating">
              <template v-if="computeScore(game)"
                >★ {{ computeScore(game)!.sum.toFixed(1) }}</template
              >
              <template v-else>N/A</template>
            </span>
            <span class="list-playtime" data-label="Playtime">{{
              totalPlaytime(game)
            }}</span>
            <span class="list-last-played" data-label="Last played">
              {{
                gameLastPlayed(game)
                  ? new Date(gameLastPlayed(game)!).toLocaleDateString()
                  : "N/A"
              }}
            </span>
            <span class="list-release" data-label="Released">
              {{
                game.releaseDate ? formatDisplayDate(game.releaseDate) : "N/A"
              }}
            </span>
            <div class="list-actions">
              <button
                type="button"
                class="small-button"
                @click.stop="openEditModal(game)"
              >
                Edit
              </button>
              <button
                type="button"
                class="icon-button"
                title="Add to collection"
                :aria-label="`Add ${game.title} to collection`"
                @click.stop="handleAddToCollection(game)"
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
                  <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
                </svg>
              </button>
              <button
                type="button"
                class="icon-button"
                :class="{ active: game.favorite }"
                :aria-label="`${game.favorite ? 'Remove' : 'Add'} ${game.title} ${game.favorite ? 'from' : 'to'} favorites`"
                :aria-pressed="game.favorite"
                :title="
                  game.favorite ? 'Remove from favorites' : 'Add to favorites'
                "
                @click.stop="toggleFavorite(game)"
              >
                <svg
                  viewBox="0 0 24 24"
                  width="16"
                  height="16"
                  :fill="game.favorite ? 'currentColor' : 'none'"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path
                    d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.6l-1-1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 21l7.8-7.8 1-1a5.5 5.5 0 0 0 0-7.6z"
                  />
                </svg>
              </button>
            </div>
          </div>
        </div>

        <div v-else-if="viewMode === 'shelves'" class="shelves-view">
          <section
            v-for="shelf in sourceShelves"
            :key="shelf.name"
            class="shelf-row"
          >
            <div class="shelf-row-header">
              <h2>{{ shelf.name }}</h2>
              <span class="shelf-row-count">{{ shelf.games.length }}</span>
            </div>
            <div class="shelf-wrap">
              <button
                type="button"
                class="shelf-arrow left"
                @click="scrollShelf($event, -1)"
                aria-label="Scroll left"
              >
                ‹
              </button>
              <div
                class="shelf"
                @scroll="updateShelfArrows($event.target as HTMLElement)"
              >
                <GameCard
                  v-for="game in shelf.games"
                  :key="game.id"
                  :game="game"
                  @edit="openEditModal"
                  @add-to-collection="handleAddToCollection"
                />
              </div>
              <button
                type="button"
                class="shelf-arrow right"
                @click="scrollShelf($event, 1)"
                aria-label="Scroll right"
              >
                ›
              </button>
            </div>
          </section>
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
              <img class="detail-list-thumb" :src="game.coverImageUrl" alt="" />
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
                  backgroundImage: `url(${selectedGame.bannerImageUrl})`,
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
                    <svg
                      viewBox="0 0 24 24"
                      width="16"
                      height="16"
                      :fill="selectedGame.favorite ? 'currentColor' : 'none'"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    >
                      <path
                        d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.6l-1-1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 21l7.8-7.8 1-1a5.5 5.5 0 0 0 0-7.6z"
                      />
                    </svg>
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

      <UiModal
        v-if="deletingGame"
        title="Delete game"
        description="Moved to trash, recoverable for 7 days from Settings, then purged for good."
        :dismissible="!deleting"
        @close="deletingGame = null"
      >
        <p>Delete {{ deletingGame.title }}?</p>
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
      </UiModal>
    </div>
  </main>
</template>

<style scoped>
.library {
  position: relative;
  font-family: var(--ui-font-family);
  background: var(--ui-bg);
  min-height: 100dvh;
  color: var(--ui-text);
  overflow-x: hidden;
}
/* List + preview mode: the page itself doesn't scroll, only the list and
   preview panes do, via their own overflow-y (see .detail-list/.detail-preview) */
.library.locked {
  height: 100dvh;
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
  padding: 84px var(--ui-edge-right) 48px var(--ui-edge-left);
  box-sizing: border-box;
}

.header-row {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
  /* keeps search/filters reachable without scrolling back up through a long
     grid, only kicks in outside "List + preview" mode, which scrolls its
     own panes instead of the page */
  position: sticky;
  top: 64px;
  z-index: 5;
  background: var(--ui-bg);
  padding: 20px 0 16px;
  margin-top: -20px;
}
.header-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}
.search-input,
.filter-select {
  min-height: var(--ui-control-height);
  box-sizing: border-box;
  background: var(--ui-bg);
  border: 1px solid var(--ui-border-strong);
  border-radius: var(--ui-radius-control);
  color: var(--ui-text);
  padding: 0 14px;
  font: inherit;
  font-size: 13px;
  transition: border-color 0.15s ease;
}
.search-wrap {
  position: relative;
}
.search-input {
  width: 200px;
}
.search-input:focus,
.filter-select:focus {
  outline: none;
  border-color: var(--ui-accent);
}
.recent-searches-dropdown {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  width: 220px;
  background: var(--ui-surface);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-control);
  padding: 6px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.45);
  z-index: 20;
}
.recent-searches-label {
  color: var(--ui-faint);
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
  color: var(--ui-text);
  font-size: 13px;
  text-align: left;
  padding: 7px 8px;
  border-radius: 6px;
  cursor: pointer;
}
.recent-search-item:hover {
  background: color-mix(in srgb, var(--ui-text) 6%, transparent);
}
.recent-search-remove {
  color: var(--ui-faint);
  font-size: 11px;
  padding: 2px 4px;
  border-radius: 4px;
}
.recent-search-remove:hover {
  color: var(--ui-error);
}
.select-button-wrap,
.presets-wrap {
  position: relative;
}
.shelves-view {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.shelf-row-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-left: 12px;
  border-left: 3px solid var(--ui-accent);
  margin-bottom: 4px;
}
.shelf-row-header h2 {
  margin: 0;
  font-size: 1.05rem;
  color: var(--ui-text);
}
.shelf-row-count {
  background: color-mix(in srgb, var(--ui-text) 6%, transparent);
  color: var(--ui-dim);
  font-size: 12px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 999px;
}
.shelf-wrap {
  position: relative;
}
.shelf {
  display: flex;
  gap: 16px;
  overflow-x: auto;
  scroll-behavior: smooth;
  padding: 16px 4px 24px;
  scrollbar-width: none;
  -ms-overflow-style: none;
}
.shelf::-webkit-scrollbar {
  display: none;
}
.shelf-arrow {
  position: absolute;
  top: 0;
  bottom: 24px;
  width: 40px;
  border: none;
  background: linear-gradient(to right, rgba(10, 10, 10, 0.85), transparent);
  color: var(--ui-text);
  font-size: 26px;
  line-height: 1;
  cursor: pointer;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.15s ease;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: center;
}
.shelf-arrow.right {
  left: auto;
  right: 0;
  background: linear-gradient(to left, rgba(10, 10, 10, 0.85), transparent);
}
.shelf-arrow.left {
  left: 0;
}
.shelf-wrap:hover .shelf-arrow.can-scroll {
  opacity: 1;
  pointer-events: auto;
}
.shelf-arrow:hover {
  color: var(--ui-accent-text);
}
.presets-dropdown {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  width: 220px;
  background: var(--ui-surface);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-control);
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
  color: var(--ui-text);
  font-size: 13px;
  text-align: left;
  padding: 8px;
  border-radius: 6px;
  cursor: pointer;
}
.preset-item:hover {
  background: color-mix(in srgb, var(--ui-text) 6%, transparent);
}
.preset-remove {
  color: var(--ui-faint);
  font-size: 11px;
  padding: 2px 4px;
  border-radius: 4px;
}
.preset-remove:hover {
  color: var(--ui-error);
}
.preset-empty {
  color: var(--ui-faint);
  font-size: 12px;
  padding: 8px;
  margin: 0;
}
.preset-save {
  display: block;
  width: 100%;
  background: color-mix(in srgb, var(--ui-accent) 12%, transparent);
  border: none;
  color: var(--ui-accent-text);
  font-size: 12.5px;
  font-weight: 600;
  text-align: left;
  padding: 8px;
  border-radius: 6px;
  cursor: pointer;
  margin-top: 4px;
}
.preset-save:hover {
  background: color-mix(in srgb, var(--ui-accent) 20%, transparent);
}
.first-use-hint {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 240px;
  background: var(--ui-surface);
  border: 1px solid var(--ui-accent);
  border-radius: var(--ui-radius-control);
  padding: 12px 14px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.45);
  z-index: 20;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.first-use-hint span {
  color: var(--ui-text);
  font-size: 12.5px;
  line-height: 1.5;
}
.first-use-hint-dismiss {
  min-height: var(--ui-control-height);
  align-self: flex-end;
  background: color-mix(in srgb, var(--ui-accent) 14%, transparent);
  border: none;
  color: var(--ui-accent-text);
  border-radius: 6px;
  padding: 5px 10px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}
.first-use-hint-dismiss:hover {
  background: color-mix(in srgb, var(--ui-accent) 24%, transparent);
}
/* Keep the first-use tip clear of the phone navigation and tablet rail. */
@media (max-width: 1100px) {
  .first-use-hint {
    position: fixed;
    top: auto;
    left: 16px;
    right: 16px;
    bottom: calc(104px + env(safe-area-inset-bottom));
    width: auto;
    max-width: 400px;
    margin-left: auto;
  }
}
.density-toggle {
  display: flex;
  gap: 2px;
  background: var(--ui-surface);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-control);
  padding: 3px;
  min-height: var(--ui-control-height);
  box-sizing: border-box;
}
.density-button {
  background: none;
  border: none;
  color: var(--ui-dim);
  width: var(--ui-control-height);
  height: var(--ui-control-height);
  border-radius: 6px;
  cursor: pointer;
  font-size: 11px;
  font-weight: 700;
}
.density-button:hover {
  color: var(--ui-text);
  background: color-mix(in srgb, var(--ui-text) 6%, transparent);
}
.density-button.active {
  color: var(--ui-on-accent);
  background: var(--ui-accent);
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
  background: color-mix(in srgb, var(--ui-accent) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--ui-accent) 35%, transparent);
  color: var(--ui-accent-text);
  border-radius: 999px;
  padding: 5px 10px 5px 12px;
  font-size: 12px;
  cursor: pointer;
}
.filter-pill:hover {
  background: color-mix(in srgb, var(--ui-accent) 20%, transparent);
}
.filter-pill-x {
  color: var(--ui-accent-text);
  font-size: 10px;
}
.filter-pill-clear-all {
  background: none;
  border: none;
  color: var(--ui-faint);
  font-size: 12px;
  text-decoration: underline;
  cursor: pointer;
  padding: 5px 4px;
}
.filter-pill-clear-all:hover {
  color: var(--ui-text);
}
.search-suggestions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  color: var(--ui-dim);
  font-size: 13px;
  margin-top: -8px;
}
.search-suggestion-item {
  background: color-mix(in srgb, var(--ui-text) 6%, transparent);
  border: 1px solid var(--ui-border-strong);
  color: var(--ui-text);
  border-radius: 999px;
  padding: 5px 12px;
  font-size: 12.5px;
  cursor: pointer;
}
.search-suggestion-item:hover {
  border-color: var(--ui-accent);
  color: var(--ui-accent-text);
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
  color: var(--ui-dim);
  font-size: 12.5px;
  line-height: 1.5;
  background: color-mix(in srgb, var(--ui-text) 4%, transparent);
  border-radius: 6px;
  padding: 8px 12px;
}
.filter-select:hover {
  border-color: var(--ui-border-strong);
}
.filter-select {
  appearance: none;
  -webkit-appearance: none;
  padding-right: 34px;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'><path d='M1 1l4 4 4-4' stroke='%23999' stroke-width='1.5' fill='none' stroke-linecap='round' stroke-linejoin='round'/></svg>");
  background-repeat: no-repeat;
  background-position: right 16px center;
}
.view-toggle {
  display: flex;
  gap: 2px;
  background: var(--ui-surface);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-control);
  padding: 3px;
  min-height: var(--ui-control-height);
  box-sizing: border-box;
}
.view-toggle-button {
  background: none;
  border: none;
  color: var(--ui-dim);
  width: var(--ui-control-height);
  height: var(--ui-control-height);
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition:
    background 0.15s ease,
    color 0.15s ease;
}
.view-toggle-button:hover {
  color: var(--ui-text);
  background: color-mix(in srgb, var(--ui-text) 6%, transparent);
}
.view-toggle-button.active {
  color: var(--ui-on-accent);
  background: var(--ui-accent);
  box-shadow: 0 2px 8px rgba(214, 138, 52, 0.4);
}
.add-button {
  min-height: var(--ui-control-height);
  box-sizing: border-box;
  background: var(--ui-accent);
  color: var(--ui-on-accent);
  border: none;
  border-radius: var(--ui-radius-control);
  padding: 0 18px;
  font-weight: 600;
  cursor: pointer;
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
.advanced-toggle {
  min-height: var(--ui-control-height);
  box-sizing: border-box;
  background: color-mix(in srgb, var(--ui-text) 6%, transparent);
  border: 1px solid var(--ui-border-strong);
  border-radius: var(--ui-radius-control);
  color: var(--ui-text);
  padding: 0 16px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition:
    background 0.15s ease,
    border-color 0.15s ease,
    color 0.15s ease;
}
.advanced-toggle:hover {
  color: var(--ui-text);
  border-color: var(--ui-border-strong);
}
.advanced-toggle.active {
  color: var(--ui-accent-text);
  border-color: color-mix(in srgb, var(--ui-accent) 50%, transparent);
  background: color-mix(in srgb, var(--ui-accent) 10%, transparent);
}
.bulk-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  background: color-mix(in srgb, var(--ui-accent) 8%, transparent);
  border: 1px solid color-mix(in srgb, var(--ui-accent) 30%, transparent);
  border-radius: var(--ui-radius-control);
  padding: 12px 16px;
  margin-bottom: 20px;
  color: var(--ui-accent-text);
  font-size: 13px;
  font-weight: 600;
}
.bulk-toolbar .primary-button {
  margin-left: auto;
}
.form-success.bulk-success {
  color: var(--ui-good);
  font-size: 13px;
  background: rgba(34, 197, 94, 0.1);
  border: 1px solid rgba(34, 197, 94, 0.3);
  border-radius: var(--ui-radius-control);
  padding: 8px 12px;
  margin-bottom: 20px;
}
.list-checkbox {
  width: 22px;
  height: 22px;
  border-radius: 6px;
  border: 2px solid var(--ui-border-strong);
  background: var(--ui-surface);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ui-text);
  flex-shrink: 0;
  cursor: pointer;
  transition:
    background 0.15s ease,
    border-color 0.15s ease;
}
.list-checkbox.checked {
  background: var(--ui-accent);
  border-color: var(--ui-accent);
}
.advanced-count {
  background: var(--ui-accent);
  color: var(--ui-on-accent);
  font-size: 11px;
  font-weight: 700;
  border-radius: 999px;
  min-width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 5px;
}
.advanced-panel {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 14px;
  background: color-mix(in srgb, var(--ui-text) 3%, transparent);
  border: 1px solid var(--ui-border-soft);
  border-radius: var(--ui-radius-control);
  padding: 18px 20px;
  margin-bottom: 24px;
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
  background: color-mix(in srgb, var(--ui-text) 6%, transparent);
  border: 1px solid var(--ui-border-strong);
  color: var(--ui-text);
  border-radius: 999px;
  padding: 5px 12px;
  font-size: 12px;
  cursor: pointer;
}
.tag-chip:hover {
  border-color: var(--ui-border-strong);
}
.tag-chip.active {
  background: var(--ui-accent);
  border-color: var(--ui-accent);
  color: var(--ui-on-accent);
  font-weight: 600;
}
.advanced-field label {
  color: var(--ui-faint);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 600;
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
  border-top: 1px solid var(--ui-border-soft);
  margin-top: 4px;
}
.toggle-chip {
  background: color-mix(in srgb, var(--ui-text) 6%, transparent);
  border: 1px solid var(--ui-border-strong);
  color: var(--ui-text);
  border-radius: 999px;
  padding: 7px 14px;
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
  transition:
    background 0.15s ease,
    border-color 0.15s ease,
    color 0.15s ease;
}
.toggle-chip:hover {
  border-color: var(--ui-border-strong);
}
.toggle-chip.active {
  color: var(--ui-accent-text);
  border-color: color-mix(in srgb, var(--ui-accent) 50%, transparent);
  background: color-mix(in srgb, var(--ui-accent) 14%, transparent);
}
.clear-advanced {
  margin-left: auto;
  background: none;
  border: none;
  color: var(--ui-dim);
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
  text-decoration: underline;
}
.clear-advanced:hover:not(:disabled) {
  color: var(--ui-text);
}
.clear-advanced:disabled {
  color: var(--ui-faint);
  cursor: not-allowed;
  text-decoration: none;
}

.error {
  color: var(--ui-error);
}

.skeleton-grid {
  display: grid;
  grid-template-columns: repeat(10, 1fr);
  gap: 16px;
}
.skeleton-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 8px;
  padding: 80px 20px;
  color: var(--ui-faint);
}
.empty-state svg {
  color: #444;
  margin-bottom: 10px;
}
.empty-state h3 {
  margin: 0;
  color: var(--ui-text);
  font-size: 1.05rem;
}
.empty-state p {
  margin: 0 0 10px;
  font-size: 13.5px;
}

/* List view */
.list-view {
  display: flex;
  flex-direction: column;
  gap: 6px;
  overflow-x: auto;
}
.list-header {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 0 28px 8px;
  min-width: 1100px;
  box-sizing: border-box;
}
.list-header span,
.list-header .sortable {
  color: var(--ui-faint);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 600;
}
.list-header .sortable {
  background: none;
  border: none;
  padding: 0;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
}
.list-header .sortable:hover,
.list-header .sortable.active {
  color: var(--ui-accent-text);
}
.list-header-spacer {
  width: 44px;
  flex-shrink: 0;
}
.list-actions-spacer {
  width: 130px;
  flex-shrink: 0;
}
.list-row {
  display: flex;
  align-items: center;
  gap: 24px;
  min-width: 1100px;
  box-sizing: border-box;
  padding: 12px 28px;
  background: color-mix(in srgb, var(--ui-text) 3%, transparent);
  border: 1px solid var(--ui-border-soft);
  border-radius: var(--ui-radius-control);
  cursor: pointer;
  transition:
    background 0.15s ease,
    transform 0.15s ease,
    box-shadow 0.15s ease,
    border-color 0.15s ease;
}
.list-row:hover {
  background: color-mix(in srgb, var(--ui-text) 6%, transparent);
  border-color: var(--ui-border);
  transform: translateX(2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
}
.list-cover {
  width: 44px;
  height: 58px;
  object-fit: cover;
  border-radius: 6px;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
}
.list-title {
  flex: 1;
  font-weight: 600;
  font-size: 14.5px;
  color: var(--ui-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.list-open {
  border: 0;
  background: transparent;
  padding: 0;
  text-align: left;
  font-family: inherit;
  cursor: pointer;
  min-height: var(--ui-control-height);
}
.list-status {
  width: 100px;
  flex-shrink: 0;
  display: flex;
  justify-content: center;
  text-transform: capitalize;
  color: var(--ui-text);
  font-size: 12px;
}
.status-pill {
  width: 82px;
  text-align: center;
  background: color-mix(in srgb, var(--ui-text) 6%, transparent);
  padding: 4px 0;
  border-radius: 999px;
}
.list-header .list-status {
  text-align: center;
}
.list-genre,
.list-platform,
.list-last-played,
.list-release {
  color: var(--ui-dim);
  font-size: 12px;
  min-width: 100px;
}
.list-score {
  min-width: 60px;
  color: var(--ui-accent-text);
  font-size: 12px;
  font-weight: 700;
}
.list-header .list-score {
  color: var(--ui-faint);
  font-weight: 600;
}
.list-playtime {
  width: 60px;
  color: var(--ui-dim);
  font-size: 12px;
}
.list-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 130px;
  flex-shrink: 0;
}
.icon-button {
  background: color-mix(in srgb, var(--ui-text) 8%, transparent);
  color: var(--ui-dim);
  border: none;
  border-radius: var(--ui-radius-control);
  width: var(--ui-control-height);
  height: var(--ui-control-height);
  flex-shrink: 0;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition:
    background 0.15s ease,
    color 0.15s ease;
}
.icon-button:hover {
  background: color-mix(in srgb, var(--ui-text) 14%, transparent);
  color: var(--ui-text);
}
.icon-button.active {
  color: var(--ui-accent-text);
  background: color-mix(in srgb, var(--ui-accent) 16%, transparent);
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
  min-height: 280px;
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
  background: none;
  border: 1px solid transparent;
  border-radius: var(--ui-radius-control);
  padding: 8px;
  cursor: pointer;
  color: var(--ui-text);
  text-align: left;
  transition:
    background 0.15s ease,
    border-color 0.15s ease,
    transform 0.15s ease;
}
.detail-list-item:hover {
  background: color-mix(in srgb, var(--ui-text) 5%, transparent);
  transform: translateX(2px);
}
.detail-list-item.active {
  background: color-mix(in srgb, var(--ui-accent) 16%, transparent);
  border-color: color-mix(in srgb, var(--ui-accent) 50%, transparent);
  color: var(--ui-text);
  box-shadow: 0 4px 16px rgba(214, 138, 52, 0.15);
}
.detail-list-thumb {
  width: 40px;
  height: 54px;
  object-fit: cover;
  border-radius: 6px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.4);
  flex-shrink: 0;
}
.detail-preview {
  border: 1px solid var(--ui-border);
  border-radius: 16px;
  background: var(--ui-surface);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.45);
  height: 100%;
  overflow-y: auto;
}
.preview-banner {
  position: relative;
  height: 260px;
  background-size: cover;
  background-position: center;
}
.preview-banner-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, transparent 40%, var(--ui-surface) 100%);
}
.preview-info {
  padding: 20px;
}
.preview-info h2 {
  margin: 0 0 10px;
}
.preview-meta {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
}
.preview-badge {
  background: color-mix(in srgb, var(--ui-text) 8%, transparent);
  border: 1px solid color-mix(in srgb, var(--ui-text) 10%, transparent);
  padding: 5px 14px;
  border-radius: 999px;
  font-size: 12px;
  text-transform: capitalize;
  color: var(--ui-text);
}
.preview-details {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 18px;
  padding-top: 14px;
  border-top: 1px solid var(--ui-border);
}
.preview-platforms {
  display: flex;
  flex-direction: column;
  gap: 2px;
  color: var(--ui-text);
  font-size: 13px;
}
.preview-links {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.preview-links a {
  color: var(--ui-accent-text);
  font-size: 13px;
  text-decoration: none;
}
.preview-links a:hover {
  text-decoration: underline;
}
.preview-detail-row {
  display: flex;
  gap: 10px;
  font-size: 13px;
  color: var(--ui-text);
  align-items: baseline;
}
.preview-detail-label {
  color: var(--ui-faint);
  min-width: 80px;
  flex-shrink: 0;
}
.preview-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.preview-pill {
  background: var(--ui-border);
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 11px;
  color: var(--ui-text);
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
  color: var(--ui-accent-text);
}
.preview-description-html {
  color: var(--ui-text);
  line-height: 1.6;
  margin: 0 0 18px;
  max-width: 100%;
  overflow-wrap: break-word;
}
.preview-description-html :deep(img),
.preview-description-html :deep(video) {
  max-width: 100%;
  height: auto;
  border-radius: var(--ui-radius-control);
  margin: 10px 0;
  display: block;
}
.preview-description-html :deep(h1),
.preview-description-html :deep(h2),
.preview-description-html :deep(h3) {
  margin: 18px 0 6px;
  font-size: 15px;
  font-weight: 700;
  color: var(--ui-text);
}
.preview-description-html :deep(p) {
  margin: 0 0 12px;
}
.preview-description-html :deep(a) {
  color: var(--ui-accent-text);
}
.preview-description-html :deep(ul) {
  padding-left: 20px;
  margin: 0 0 12px;
}
.preview-actions {
  display: flex;
  gap: 10px;
}
.empty-row {
  color: var(--ui-faint);
  font-size: 14px;
}

/* Shared buttons */
.primary-button,
.secondary-button,
.small-button,
.danger-button {
  border: none;
  border-radius: var(--ui-radius-control);
  padding: 9px 16px;
  font-weight: 600;
  cursor: pointer;
  font-size: 13px;
}
.primary-button {
  background: var(--ui-accent);
  color: var(--ui-on-accent);
}
.secondary-button,
.small-button {
  background: color-mix(in srgb, var(--ui-text) 8%, transparent);
  color: var(--ui-text);
}
.danger-button {
  background: rgba(220, 38, 38, 0.18);
  color: var(--ui-error);
}
.danger-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Confirm dialog */
.confirm-dialog p {
  margin: 0 0 16px;
  color: var(--ui-dim);
  font-size: 14px;
}
.confirm-error {
  color: var(--ui-error);
  font-size: 13px;
  margin-bottom: 12px;
}
.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

/* Phone lists retain all fields and actions as labelled cards. The preview
   switches to a horizontal picker above its content. */
@media (max-width: 1100px) {
  .library.locked {
    height: auto;
    overflow-y: visible;
  }
  .library.locked .content {
    height: auto;
    display: block;
  }
  .library.locked .detail-view {
    min-height: 420px;
  }
}
@media (max-width: 760px) {
  .header-row {
    position: static;
    margin-top: 0;
    padding: 0;
  }
  .header-actions {
    width: 100%;
    gap: 8px;
  }
  .search-wrap,
  .search-input {
    width: 100%;
  }
  .header-actions > .combobox,
  .header-actions > .filter-select {
    flex: 1 1 130px;
    min-width: 0;
    max-width: 100%;
  }
  .header-actions > .combobox :deep(input) {
    width: 100%;
  }
  .advanced-panel {
    grid-template-columns: minmax(0, 1fr);
  }
  .bulk-toolbar,
  .preview-actions,
  .preview-meta {
    flex-wrap: wrap;
  }
  .list-view {
    overflow-x: visible;
  }
  .list-header {
    display: none;
  }
  .list-row {
    position: relative;
    min-width: 0;
    display: grid;
    grid-template-columns: 44px minmax(0, 1fr) minmax(0, 1fr);
    gap: 8px 12px;
    padding: 16px;
    border-radius: var(--ui-radius-row);
  }
  .list-open {
    grid-column: 2 / -1;
    min-width: 0;
    white-space: normal;
    overflow-wrap: anywhere;
  }
  .list-cover {
    grid-column: 1;
    grid-row: 1 / 4;
    align-self: start;
  }
  .list-status {
    grid-column: 2 / -1;
    width: auto;
    justify-content: flex-start;
  }
  .status-pill {
    width: auto;
    padding: 4px 10px;
  }
  .list-row > [data-label] {
    min-width: 0;
    width: auto;
    overflow-wrap: anywhere;
  }
  .list-row > [data-label]::before {
    content: attr(data-label);
    display: block;
    font-size: 10px;
    color: var(--ui-dim);
    font-weight: 400;
  }
  .list-genre,
  .list-score,
  .list-last-played {
    grid-column: 2;
  }
  .list-platform,
  .list-playtime,
  .list-release {
    grid-column: 3;
  }
  .list-actions {
    grid-column: 1 / -1;
    width: auto;
    justify-content: flex-end;
    border-top: 1px solid var(--ui-border-soft);
    padding-top: 8px;
  }
  .list-actions .small-button {
    margin-right: auto;
  }
  .list-checkbox {
    position: absolute;
    right: 12px;
    top: 12px;
    width: 44px;
    height: 44px;
  }
  .list-row:has(.list-checkbox) .list-open {
    padding-right: 48px;
  }
  .list-row:hover {
    transform: none;
  }
  .library.locked .detail-view {
    grid-template-columns: minmax(0, 1fr);
    height: auto;
    min-height: 0;
  }
  .detail-list {
    flex-direction: row;
    overflow-x: auto;
    overflow-y: hidden;
    height: auto;
    min-height: 0;
    padding-bottom: 8px;
  }
  .detail-list-item {
    flex-direction: column;
    text-align: center;
    width: 100px;
    flex-shrink: 0;
  }
  .detail-list-item span {
    font-size: 12px;
    overflow-wrap: anywhere;
    width: 100%;
  }
  .detail-preview {
    height: auto;
    min-width: 0;
    overflow: visible;
  }
  .preview-detail-row {
    flex-wrap: wrap;
  }
  .preview-detail-label {
    min-width: 0;
  }
  .preview-banner {
    height: 180px;
  }
  .preview-info {
    padding: 16px;
  }
  .preview-actions > button {
    flex: 1 1 auto;
  }
  .preview-info h2,
  .preview-links a {
    overflow-wrap: anywhere;
  }
  .skeleton-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .density-toggle,
  .view-toggle {
    height: auto;
  }
}

.primary-button,
.secondary-button,
.small-button,
.danger-button,
.tag-chip,
.toggle-chip,
.filter-pill,
.clear-advanced,
.preset-item,
.preset-save,
.recent-search-item {
  min-height: var(--ui-control-height);
  box-sizing: border-box;
}

@media (max-width: 760px) {
  .library .content {
    padding-top: 84px;
  }
}
</style>
