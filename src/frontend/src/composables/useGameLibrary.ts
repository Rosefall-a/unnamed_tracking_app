import type { SegmentOption } from "../components/SegmentedTabs.vue";
import { matchesShortcut } from "../state/shortcuts";
import { preferences } from "../state/preferences";
export type ViewMode = "cards" | "list" | "detail";
import { PHONE_CARD_COLUMNS } from "../utils/libraryLayout";
export type CardDensity = "compact" | "cozy" | "large";

import {
  ref,
  computed,
  onMounted,
  onUnmounted,
  onActivated,
  onDeactivated,
  nextTick,
  watch,
  useTemplateRef,
} from "vue";
import { useKeptAlive } from "../utils/useKeptAlive";
import { takeLibraryScroll } from "../state/libraryScroll";
import { useRoute, useRouter } from "vue-router";
import { useWindowVirtualizer } from "@tanstack/vue-virtual";

import { activePriority, priorityLabel } from "../utils/priority";
import { formatDisplayDate } from "../utils/dates";

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

import { computeScore } from "../utils/scoring";
import DOMPurify from "dompurify";
import {
  normalizePlatformFamily,
  PLATFORM_OPTIONS,
  RETRO_PLATFORM_OPTIONS,
} from "../utils/platforms";
import { genreOptionsFor, hasGenre } from "../utils/genres";
import type { Game, GameStatus } from "../types/game";
import { usePrompt } from "../state/dialog";
export function useGameLibrary() {
  const prompt = usePrompt();

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
      ...recentSearches.value.filter(
        (s) => s.toLowerCase() !== q.toLowerCase(),
      ),
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
  // arriving from Server Stats' tag chart (?tag=Name)
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

  const genreOptions = computed(() =>
    genreOptionsFor(games.value.map((g) => g.tags)),
  );

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
    if (
      viewMode.value === "detail" &&
      !selectedGame.value &&
      games.value.length
    )
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
      error.value = null;
      if (selectedGame.value)
        selectedGame.value =
          fetched.find((game) => game.id === selectedGame.value?.id) ?? null;
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

  async function restoreLibraryScroll() {
    await nextTick();
    if (route.path !== "/games") return;
    const y = takeLibraryScroll();
    if (y > 0) window.scrollTo(0, y);
  }
  onMounted(async () => {
    await loadGames();
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
  const searchInputRef = useTemplateRef<HTMLInputElement>("librarySearch");
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
    if (e.defaultPrevented || anyModalOpen() || e.isComposing || e.repeat)
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
    if (
      preferences.value.keyboard_shortcuts_enabled === false ||
      e.getModifierState("AltGraph")
    )
      return;
    const cardDirection = ["left", "right", "up", "down"].find((direction) =>
      matchesShortcut(`games.cards.${direction}`, e),
    );
    if (matchesShortcut("app.focus-search", e)) {
      e.preventDefault();
      searchInputRef.value?.focus();
    } else if (matchesShortcut("app.create", e)) {
      e.preventDefault();
      openAddModal();
    } else if (
      matchesShortcut("games.preview.next", e) &&
      viewMode.value === "detail"
    ) {
      e.preventDefault();
      const idx = selectedGame.value
        ? filteredGames.value.findIndex((g) => g.id === selectedGame.value?.id)
        : -1;
      if (idx < filteredGames.value.length - 1)
        selectedGame.value = filteredGames.value[idx + 1];
    } else if (
      matchesShortcut("games.preview.previous", e) &&
      viewMode.value === "detail"
    ) {
      e.preventDefault();
      const idx = selectedGame.value
        ? filteredGames.value.findIndex((g) => g.id === selectedGame.value?.id)
        : -1;
      if (idx > 0) selectedGame.value = filteredGames.value[idx - 1];
    } else if (
      /^[a-z]$/i.test(e.key) &&
      !e.ctrlKey &&
      !e.metaKey &&
      !e.altKey &&
      viewMode.value === "cards" &&
      !cardDirection &&
      !matchesShortcut("games.cards.open", e)
    ) {
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
      cardDirection
    ) {
      const count = filteredGames.value.length;
      if (!count) return;
      e.preventDefault();
      let idx = gridFocusIndex.value ?? 0;
      if (cardDirection === "right") idx = Math.min(idx + 1, count - 1);
      else if (cardDirection === "left") idx = Math.max(idx - 1, 0);
      else if (cardDirection === "down")
        idx = Math.min(idx + CARD_COLUMNS.value, count - 1);
      else if (cardDirection === "up")
        idx = Math.max(idx - CARD_COLUMNS.value, 0);
      gridFocusIndex.value = idx;
      rowVirtualizer.value.scrollToIndex(Math.floor(idx / CARD_COLUMNS.value), {
        align: "auto",
      });
    } else if (
      matchesShortcut("games.cards.open", e) &&
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
      result = result.filter((g) => hasGenre(g.tags, genreFilter.value));
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
        tagsFilter.value.some((tag) => hasGenre(g.tags, tag)),
      );
    }

    const q = searchQuery.value.trim().toLowerCase();
    if (q) {
      result = result.filter((g) => fuzzyTitleMatch(g.title, q));
    }

    // missing values always sort last, whichever way the sort runs
    const lastIfNull = <T>(
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
        return lastIfNull(
          a.timeToBeatHours,
          b.timeToBeatHours,
          (x, y) => x - y,
        );
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
    cancelAnimationFrame(gridMeasureFrame);
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
  const contentEl = useTemplateRef<HTMLElement>("libraryContent");
  const gridWidth = ref(document.documentElement.clientWidth - 72);
  let contentObserver: ResizeObserver | null = null;
  let gridMeasureFrame = 0;
  onMounted(() => {
    if (!contentEl.value) return;
    contentObserver = new ResizeObserver((entries) => {
      const width = entries[0].contentRect.width;
      if (width === gridWidth.value) return;
      cancelAnimationFrame(gridMeasureFrame);
      gridMeasureFrame = requestAnimationFrame(() => {
        gridWidth.value = width;
      });
    });
    contentObserver.observe(contentEl.value);
  });
  onUnmounted(() => {
    contentObserver?.disconnect();
    cancelAnimationFrame(gridMeasureFrame);
  });

  const CARD_COLUMNS = computed(() => {
    if (viewportWidth.value <= 760)
      return PHONE_CARD_COLUMNS[cardDensity.value];
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
      enabled: isLibraryActive.value,
      useAnimationFrameWithResizeObserver: true,
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

  return {
    viewportWidth,
    activePriority,
    priorityLabel,
    formatDisplayDate,
    computeScore,
    games,
    loading,
    error,
    showFormModal,
    editingGame,
    deletingGame,
    deleting,
    deleteError,
    viewMode,
    selectedGame,
    gridFocusIndex,
    selectMode,
    selectedIds,
    showBulkEditModal,
    showRandomPicker,
    showBulkEditHint,
    dismissBulkEditHint,
    toggleSelectMode,
    toggleSelect,
    clearSelection,
    onBulkEditSaved,
    bulkEditResultCount,
    bulkAddingToCollection,
    bulkAddToCollection,
    selectedGameDescriptionHtml,
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
    toggleTagFilter,
    recentSearches,
    showRecentSearches,
    commitSearchToRecent,
    pickRecentSearch,
    removeRecentSearch,
    advancedFilterCount,
    filterCount,
    clearAdvancedFilters,
    clearAllFilters,
    filterPresets,
    showPresetsMenu,
    saveCurrentAsPreset,
    applyPreset,
    deletePreset,
    statusOptions,
    VIEW_OPTIONS,
    statusCounts,
    platformOptions,
    platformExtraOptions,
    genreOptions,
    franchiseOptions,
    collectionOptions,
    companyOptions,
    ageRatingOptions,
    regionOptions,
    languageOptions,
    metadataProviderOptions,
    setView,
    openAddModal,
    openEditModal,
    onGameSaved,
    onDeleteFromModal,
    toggleFavorite,
    collectionPickerGame,
    handleAddToCollection,
    onCollectionAdded,
    confirmDelete,
    totalPlaytime,
    gameLastPlayed,
    openGame,
    filteredGames,
    hasAnyGames,
    isEmpty,
    searchSuggestions,
    activeFilterPills,
    cardDensity,
    CARD_COLUMNS,
    rankByGameId,
    rowVirtualizer,
    cardsInRow,
  };
}
