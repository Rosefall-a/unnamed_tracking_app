import { useGameChecklist } from "./useGameChecklist";
import { usePageTitle } from "../state/pageTitle";
import { computed, ref, watch, onMounted, onUnmounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  deleteGame,
  fetchGame,
  fetchGameVariants,
  fetchGameAchievements,
  fetchContentCounts,
  peekGame,
  fetchGameFieldChanges,
  fetchGames,
  setFavorite,
  setRatings,
  setStatus,
  setResumeNote,
  setPlaytimeSeconds,
} from "../services/games";
import type { FieldChange, GameRatings } from "../services/games";
import { peekAdjacentGameId } from "../state/libraryNav";
import {
  HERO_WIDTH,
  POSTER_WIDTH,
  preloadImage,
  sizedAssetUrl,
} from "../utils/gameImages";
import {
  uploadGameScreenshots,
  listGameScreenshots,
  deleteGameScreenshot,
  updateMediaItem,
  updateGameFile,
  detectMediaDates,
  saveClipThumbnail,
  uploadGameFiles,
  listGameFiles,
  deleteGameFile,
  fetchGameMediaTrash,
  restoreGameMedia,
  fetchGameFileTrash,
  restoreGameFile,
} from "../services/media";
import type {
  MediaItem,
  FileDetails,
  MediaItemUpdate,
  GameFile,
  GameFileUpdate,
  GameFileKind,
  TrashedMediaItem,
  TrashedGameFile,
} from "../services/media";
import {} from "../services/gameProfiles";
import {
  fetchArchives,
  createArchive,
  addArchiveVersion,
  updateArchive,
  deleteArchive,
  deleteArchiveVersion,
  fetchArchiveTrash,
  restoreArchive,
} from "../services/gameArchives";
import type {
  GameArchiveData,
  ArchiveVersion,
  TrashedArchive,
} from "../services/gameArchives";
import { isGuess, unlockSeconds } from "../utils/mediaDate";
import { normalizePlatformFamily } from "../utils/platforms";
import { frameFromSource } from "../utils/videoThumbnail";
import { preferences, preferencesLoaded } from "../state/preferences";
import { OPTIONAL_TABS, resolvePage, planTabs } from "../utils/gamePage";
import type { OptionalTab } from "../utils/gamePage";
import type { ContentCounts } from "../utils/gamePage";
import {
  startTask,
  updateTask,
  completeTask,
  errorTask,
  addFeedItem,
  setTaskRetry,
} from "../state/taskProgress";
import type { Achievement, Game, GameStatus } from "../types/game";
import { isUnlocked } from "../utils/achievements";
import { computeScore } from "../utils/scoring";
import DOMPurify from "dompurify";
import { useConfirm, usePrompt } from "../state/dialog";
import { matchesShortcut } from "../state/shortcuts";
import { useGameProfiles } from "./useGameProfiles";
import { useGameWorldMaps } from "./useGameWorldMaps";
import { useGameAchievements } from "./useGameAchievements";
export function useGameDetail() {
  const confirm = useConfirm();
  const prompt = usePrompt();

  const route = useRoute();
  const router = useRouter();

  function goBackToLibrary() {
    if (window.history.length > 1) {
      router.back();
    } else {
      router.push("/games");
    }
  }

  const game = ref<Game | null>(null);
  usePageTitle(() => game.value?.title);
  const loading = ref(true);
  const error = ref<string | null>(null);
  const showEditModal = ref(false);

  const deleting = ref(false);
  const deleteError = ref<string | null>(null);
  const showDeleteConfirm = ref(false);

  // Steam's "About This Game" section is rich HTML (headers, screenshots,
  // gifs), sanitize it instead of stripping it down to plain text so that
  // content survives
  const descriptionHtml = computed(() => {
    if (!game.value?.description) return "";
    return DOMPurify.sanitize(game.value.description);
  });

  const descriptionExpanded = ref(false);
  const descriptionOverflows = computed(
    () => descriptionHtml.value.replace(/<[^>]*>/g, "").length > 320,
  );

  // resolved separately from game.value.parentGameId (which is only an id),
  // see loadGame()
  const parentGameTitle = ref<string | null>(null);
  const RELATIONSHIP_LABELS: Record<string, string> = {
    mod: "Mod",
    modpack: "Modpack",
    expansion: "Expansion",
    dlc: "DLC",
    standalone_expansion: "Standalone Expansion",
    total_conversion: "Total Conversion",
  };

  // games whose parentGameId points at this one, e.g. Minecraft's page
  // listing GTNH, Vanilla, Create Pack as variants of itself. The reverse of
  // the parent-breadcrumb link above.
  const variants = ref<Game[]>([]);

  const {
    profiles,
    profilesLoadedFor,
    activeProfileId,
    newProfileName,
    profileError,
    loadProfiles,
    addProfile,
    promptRenameProfile,
    removeProfile,
    selectedProfile,
    profileNoteDraft,
    profileNoteSaving,
    saveProfileNote,
    statRows,
    editingStats,
    startEditStats,
    cancelEditStats,
    addStatRow,
    removeStatRow,
    saveProfileStats,
    womUsername,
    womSyncing,
    womError,
    syncWiseOldMan,
    statHistory,
    statHistoryLoading,
    showStatHistory,
    historyShowAll,
    HISTORY_PAGE_SIZE,
    toggleStatHistory,
    formatSnapshotDate,
    statGains,
    visibleHistory,
    headlineStats,
    skillStats,
    bossStats,
    skillIconUrl,
  } = useGameProfiles(game, prompt);

  // --- Accounts tab: gallery, split by kind + free-form category (tag) -------
  const ACCOUNT_MEDIA_KINDS = ["screenshot", "clip", "soundtrack"] as const;
  const accountMediaKind =
    ref<(typeof ACCOUNT_MEDIA_KINDS)[number]>("screenshot");
  const accountMediaCategory = ref<string | null>(null);
  watch(activeProfileId, () => {
    accountMediaCategory.value = null;
  });
  const accountMediaByKind = computed(() =>
    mediaItems.value.filter((m) => m.kind === accountMediaKind.value),
  );
  // distinct tags present among this account's items of the current kind,
  // e.g. "Levelups"/"Quests"/"Achievement diary" for OSRS screenshots, built
  // from whatever tags you've actually used rather than a fixed list
  const accountMediaCategories = computed(() => {
    const set = new Set<string>();
    for (const item of accountMediaByKind.value) {
      for (const tag of item.tags) set.add(tag);
    }
    return [...set].sort();
  });
  const accountMediaFiltered = computed(() =>
    accountMediaCategory.value
      ? accountMediaByKind.value.filter((m) =>
          m.tags.includes(accountMediaCategory.value as string),
        )
      : accountMediaByKind.value,
  );

  const {
    checklistItems,
    checklistLoading,
    checklistError,
    newChecklistText,
    editingItemId,
    editingText,
    checklistProgress,
    checklistSections,
    collapsedSections,
    toggleSectionCollapsed,
    sectionProgress,
    loadChecklist,
    addChecklistItem,
    addChecklistSection,
    toggleChecklistItem,
    startEditItem,
    commitEditItem,
    cancelEditItem,
    moveChecklistItem,
    removeChecklistItem,
  } = useGameChecklist(game, activeProfileId, prompt);

  // the Accounts tab's sidebar selection, reload that account's checklist
  // and media whenever it changes
  watch(activeProfileId, () => {
    if (activeTab.value !== "Accounts") return;
    void loadChecklist();
    void reloadMediaForCurrentTab();
  });

  // Opening a game: forget what belonged to the one before, and have whichever
  // tab is showing start loading its own things.
  function resetForGame() {
    mediaItems.value = [];
    mediaLoadedFor.value = null;
    mediaTrash.value = [];
    showMediaTrash.value = false;
    fieldChanges.value = [];
    fieldChangesError.value = null;
    docsFiles.value = [];
    modpackFiles.value = [];
    filesLoaded.value = { doc: null, modpack: null };
    docsTrash.value = [];
    modpackTrash.value = [];
    showDocsTrash.value = false;
    showModpackTrash.value = false;
    saveArchives.value = [];
    saveArchivesLoaded.value = false;
    saveTrash.value = [];
    showSaveTrash.value = false;
    stopWorldMapPolling();
    worldMaps.value = [];
    worldMapsLoaded.value = false;
    worldTrash.value = [];
    showWorldTrash.value = false;
    activeMapArchiveId.value = null;
    profiles.value = [];
    profilesLoadedFor.value = null;
    activeProfileId.value = null;
    checklistItems.value = [];
    if (
      activeTab.value === "Screenshots" ||
      activeTab.value === "Clips" ||
      activeTab.value === "Soundtrack"
    ) {
      void loadProfiles();
      void loadMedia();
      void refreshMediaTrash();
    }
    if (activeTab.value === "Accounts") {
      void loadProfiles();
      void loadChecklist();
      void reloadMediaForCurrentTab();
    }
    if (activeTab.value === "Saves") {
      void refreshSaveArchives();
      void refreshSaveTrash();
    }
    if (activeTab.value === "Docs") {
      void loadGameFiles("doc");
      void refreshFileTrash("doc");
    }
    if (activeTab.value === "World Map") {
      void loadGameFiles("modpack");
      void refreshFileTrash("modpack");
      void refreshWorldMaps();
      void refreshWorldTrash();
    }
  }

  async function loadGame(id: string) {
    error.value = null;
    // the hero picture is big, so it starts downloading now rather than once the
    // game's details have come back
    preloadImage(sizedAssetUrl(`/api/game/${id}/assets/banner`, HERO_WIDTH));
    preloadImage(sizedAssetUrl(`/api/game/${id}/assets/key_art`, POSTER_WIDTH));
    // true when this only refreshes the game already on screen (after an edit)
    const refresh = game.value?.id === id;
    // everything the page fills in on its own is asked for at once, so none of
    // it waits for the game or for each other
    let achievements: Achievement[] | null = null;
    const applyAchievements = () => {
      if (route.params.id !== id || !game.value || !achievements) return;
      game.value.achievements = achievements;
      game.value.achievementTotal = achievements.length;
      game.value.achievementPercent = achievements.length
        ? Math.round(
            (achievements.filter(isUnlocked).length / achievements.length) *
              100,
          )
        : 0;
    };
    void fetchGameAchievements(id)
      .then((list) => {
        achievements = list;
        applyAchievements();
      })
      .catch(() => {
        // achievements are a nice-to-have overlay, a failure here
        // shouldn't block the rest of the game page from rendering
      });
    if (!refresh) variants.value = [];
    void fetchGameVariants(id)
      .then((list) => {
        if (route.params.id === id) variants.value = list;
      })
      .catch(() => {
        // variants section just doesn't show, not worth failing the page
      });

    // a game seen before is on screen straight away, and refreshed behind it
    const seen = refresh ? undefined : peekGame(id);
    if (seen) {
      game.value = seen;
      resetForGame();
      parentGameTitle.value = null;
      loading.value = false;
    } else if (!refresh) {
      loading.value = true;
    }
    try {
      const fetched = await fetchGame(id);
      // the route can change again while this was in flight (fast
      // click-through on the parent breadcrumb or a variant card), a
      // slower response for the game we've already navigated away from
      // must not overwrite the newer one that may have already loaded
      if (route.params.id !== id) return;
      game.value = fetched;
      if (fetched && !seen && !refresh) {
        resetForGame();
        parentGameTitle.value = null;
      }
      applyAchievements();
      if (fetched?.parentGameId) {
        const parentId = fetched.parentGameId;
        void fetchGame(parentId)
          .then((parent) => {
            if (route.params.id === id)
              parentGameTitle.value = parent?.title ?? null;
          })
          .catch(() => {
            // breadcrumb just doesn't show a name, not worth failing the page
          });
      }
    } catch (err) {
      // with the game already showing, a failed refresh is not worth an error page
      if (!seen && !refresh)
        error.value =
          err instanceof Error ? err.message : "Failed to load game";
    } finally {
      loading.value = false;
    }
  }

  async function onGameSaved() {
    showEditModal.value = false;
    await loadGame(route.params.id as string);
  }

  // --- resume note ("where I left off") ---------------------------------
  const resumeNoteDraft = ref("");
  const resumeNoteEditing = ref(false);
  const resumeNoteSaving = ref(false);
  const resumeNoteError = ref<string | null>(null);
  watch(
    () => game.value?.id,
    () => {
      resumeNoteDraft.value = game.value?.resumeNote ?? "";
      resumeNoteEditing.value = false;
      resumeNoteError.value = null;
    },
  );
  function startEditResumeNote() {
    resumeNoteDraft.value = game.value?.resumeNote ?? "";
    resumeNoteEditing.value = true;
  }
  async function saveResumeNote() {
    if (!game.value) return;
    resumeNoteSaving.value = true;
    resumeNoteError.value = null;
    try {
      const trimmed = resumeNoteDraft.value.trim() || null;
      const updated = await setResumeNote(game.value.id, trimmed);
      game.value.resumeNote = updated.resumeNote;
      resumeNoteEditing.value = false;
    } catch (err) {
      resumeNoteError.value =
        err instanceof Error ? err.message : "Failed to save note";
    } finally {
      resumeNoteSaving.value = false;
    }
  }

  // --- quick playtime logging --------------------------------------------
  const loggingPlaytime = ref(false);
  async function logPlaytime(minutes: number) {
    if (!game.value || loggingPlaytime.value) return;
    loggingPlaytime.value = true;
    try {
      const currentSeconds = game.value.platforms.reduce(
        (sum, p) => sum + p.playtimeMinutes * 60,
        0,
      );
      const updated = await setPlaytimeSeconds(
        game.value.id,
        currentSeconds + minutes * 60,
      );
      game.value.platforms = updated.platforms;
      game.value.lastPlayedAt = updated.lastPlayedAt;
    } catch {
      // the button just doesn't reflect the change, not worth a whole error banner for this
    } finally {
      loggingPlaytime.value = false;
    }
  }

  // --- similar games in the library, by shared tags -----------------------
  // fetched once per page visit (not per-game), cheap enough at this
  // library's scale and avoids a second heavier endpoint just for this
  const libraryGames = ref<Game[]>([]);
  async function loadLibraryForSimilar() {
    try {
      libraryGames.value = await fetchGames();
    } catch {
      // similar-games section just doesn't show, not worth failing the page
    }
  }
  onMounted(() => void loadLibraryForSimilar());

  const similarGames = computed(() => {
    if (!game.value || !libraryGames.value.length) return [];
    const tagSet = new Set(game.value.tags);
    if (!tagSet.size) return [];
    return libraryGames.value
      .filter((g) => g.id !== game.value!.id)
      .map((g) => ({
        game: g,
        shared: g.tags.filter((t) => tagSet.has(t)).length,
      }))
      .filter((e) => e.shared > 0)
      .sort((a, b) => b.shared - a.shared)
      .slice(0, 8)
      .map((e) => e.game);
  });

  // --- J/K next/prev game, mirroring the library grid's own shortcut -------
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
  function onDetailKeydown(e: KeyboardEvent) {
    if (
      e.defaultPrevented ||
      e.isComposing ||
      e.repeat ||
      e.getModifierState("AltGraph") ||
      document.querySelector("dialog[open]")
    )
      return;
    if (isTypingTarget(e.target)) return;
    if (showEditModal.value || showDeleteConfirm.value) return;
    if (!game.value) return;
    const next = matchesShortcut("games.next", e);
    if (next || matchesShortcut("games.previous", e)) {
      const nextId = peekAdjacentGameId(game.value.id, next ? 1 : -1);
      if (nextId) {
        e.preventDefault();
        router.push(`/games/${nextId}`);
      }
    }
  }
  window.addEventListener("keydown", onDetailKeydown);
  onUnmounted(() => window.removeEventListener("keydown", onDetailKeydown));

  async function toggleFavorite() {
    if (!game.value) return;
    const next = !game.value.favorite;
    game.value.favorite = next;
    try {
      await setFavorite(game.value.id, next);
    } catch {
      game.value.favorite = !next;
    }
  }

  const STATUS_OPTIONS: GameStatus[] = [
    "playing",
    "beaten",
    "mastered",
    "played",
    "on hold",
    "dropped",
    "backlog",
    "wishlist",
  ];
  async function changeStatus(next: GameStatus) {
    if (!game.value || next === game.value.status) return;
    const previous = game.value.status;
    game.value.status = next;
    try {
      await setStatus(game.value.id, next);
    } catch {
      game.value.status = previous;
    }
  }

  function onCollectionsChanged(collections: string[]) {
    if (game.value) game.value.collections = collections;
  }

  async function onRatingsChange(ratings: GameRatings) {
    if (!game.value) return;
    const previous = {
      ratingOverall: game.value.ratingOverall,
      ratingStory: game.value.ratingStory,
      ratingGameplay: game.value.ratingGameplay,
      ratingSound: game.value.ratingSound,
    };
    Object.assign(game.value, ratings);
    try {
      await setRatings(game.value.id, ratings);
    } catch {
      Object.assign(game.value, previous);
    }
  }

  function onDeleteFromModal() {
    showEditModal.value = false;
    deleteError.value = null;
    showDeleteConfirm.value = true;
  }

  async function confirmDelete() {
    if (!game.value) return;
    deleting.value = true;
    deleteError.value = null;
    try {
      await deleteGame(game.value.id);
      router.push("/games");
    } catch (err) {
      deleteError.value =
        err instanceof Error ? err.message : "Failed to delete game";
    } finally {
      deleting.value = false;
    }
  }

  // re-fetches automatically if you ever navigate from one game's page
  // straight to another, not just on the first load
  watch(() => route.params.id as string, loadGame);
  const recentActivity = computed(() => game.value?.lastPlayedAt ?? null);

  const tally = computed(() => (game.value ? computeScore(game.value) : null));

  // the developer and publisher sit by the title, the way Media shows an
  // alternate name, instead of in the details
  const heroCredits = computed(() => [
    ...new Set(
      [game.value?.developer, game.value?.publisher].filter(
        (x): x is string => !!x,
      ),
    ),
  ]);

  // A genre, developer, publisher, platform or series is a link to the library
  // with that filter on: click FromSoftware and see all their games.
  type LibraryFilter = "tag" | "company" | "platform" | "series";
  function libraryLink(filter: LibraryFilter, value: string) {
    return {
      path: "/games",
      query: {
        [filter]:
          filter === "platform" ? normalizePlatformFamily(value) : value,
      },
    };
  }

  // The parts of the score you have rated, named, in the order they're listed
  // elsewhere. Whole numbers show without a ".0".
  const ratingParts = computed(() => {
    const g = game.value;
    if (!g || pageSettings.value.hide_rating) return [];
    const shown = (n: number) => String(Number(n.toFixed(1)));
    return [
      { name: "Atmosphere", value: g.ratingOverall },
      { name: "Story", value: g.ratingStory },
      { name: "Gameplay", value: g.ratingGameplay },
      { name: "Sound", value: g.ratingSound },
    ]
      .filter((r): r is { name: string; value: number } => r.value !== null)
      .map((r) => ({ name: r.name, value: shown(r.value) }));
  });

  // Where this game sits among everything you have rated, highest score first,
  // the same ranking the library shows. Only for a game that has a score.
  const libraryRank = computed(() => {
    const g = game.value;
    if (!g || !tally.value || !libraryGames.value.length) return null;
    const others = libraryGames.value
      .filter((x) => x.id !== g.id)
      .map((x) => computeScore(x)?.sum)
      .filter((sum): sum is number => typeof sum === "number");
    return 1 + others.filter((sum) => sum > tally.value!.sum).length;
  });

  // The few figures worth seeing first, like the row at the top of a Media
  // title: the first five of these that apply, in this order. Score, rank and
  // playtime always show, with a dash when empty. Everything else is under "More details".
  type TabName = (typeof tabs)[number];
  const overviewFacts = computed(() => {
    const g = game.value;
    if (!g) return [];
    const facts: {
      label: string;
      value: string;
      accent?: boolean;
      muted?: boolean;
      tab?: TabName;
    }[] = [];
    // your verdict first (score and where it ranks), then how you played it;
    // the individual ratings get their own row under these
    if (!pageSettings.value.hide_rating) {
      facts.push(
        tally.value
          ? {
              label: "Your score",
              value: tally.value.sum.toFixed(1),
              accent: true,
            }
          : { label: "Your score", value: "–", muted: true },
      );
      facts.push(
        libraryRank.value !== null
          ? { label: "Rank", value: `#${libraryRank.value}` }
          : { label: "Rank", value: "–", muted: true },
      );
    }
    const minutes = g.platforms.reduce((sum, p) => sum + p.playtimeMinutes, 0);
    facts.push(
      minutes > 0
        ? { label: "Playtime", value: formatPlaytime(minutes) }
        : { label: "Playtime", value: "–", muted: true },
    );
    if (g.achievementTotal > 0 && achievementsOn.value)
      facts.push({
        label: "Achievements",
        value: `${g.achievementPercent}%`,
        tab: "Achievements",
      });
    // the furthest you are through it on any platform
    const completions = g.platforms
      .map((p) => p.completionPercent)
      .filter((c): c is number => c !== null);
    if (completions.length)
      facts.push({
        label: "Completion",
        value: `${Math.max(...completions)}%`,
      });
    if (g.platforms.length)
      facts.push({
        label: g.platforms.length === 1 ? "Platform" : "Platforms",
        value: g.platforms.map((p) => p.platform).join(", "),
      });
    return facts.slice(0, 5);
  });

  // only the main genres up top; the rest of the tags are under "More details"
  const MAIN_TAG_COUNT = 6;
  const mainTags = computed(
    () => game.value?.tags.slice(0, MAIN_TAG_COUNT) ?? [],
  );
  const moreTags = computed(() => game.value?.tags.slice(MAIN_TAG_COUNT) ?? []);

  const tabs = [
    "Overview",
    "Achievements",
    "Screenshots",
    "Clips",
    "Soundtrack",
    "Saves",
    "Docs",
    "World Map",
    "Notes",
    "Accounts",
    "Stats",
  ] as const;
  const activeTab = ref<(typeof tabs)[number]>("Overview");

  // World Map only makes sense for Minecraft (BlueMap is Minecraft-specific)
  //, checks this game's own title, and its parent's if it's a mod/modpack
  // variant (e.g. "GregTech: New Horizons" has no "Minecraft" in its own
  // title, but its parent breadcrumb does).
  const isMinecraftGame = computed(() => {
    const title = game.value?.title ?? "";
    const parentTitle = parentGameTitle.value ?? "";
    return /minecraft/i.test(title) || /minecraft/i.test(parentTitle);
  });
  // ---- what this page shows: the defaults from Settings, then this game's own
  // overrides. A tab can be shown, hidden, or shown once it has something in it.
  const contentCounts = ref<ContentCounts | null>(null);
  async function refreshCounts() {
    if (!game.value) return;
    const id = game.value.id;
    try {
      const counts = await fetchContentCounts(id);
      if (game.value?.id === id) contentCounts.value = counts;
    } catch {
      // the tabs just stay as they are until the next try
    }
  }
  const pageSettings = computed(() =>
    resolvePage(preferences.value.game_page, game.value?.pageSettings),
  );
  const baseTabs = computed(() =>
    tabs.filter(
      (tab) =>
        (tab !== "World Map" || isMinecraftGame.value) &&
        (tab !== "Accounts" || game.value?.profilesEnabled),
    ),
  );
  const tabPlan = computed(() =>
    game.value
      ? planTabs(
          baseTabs.value,
          pageSettings.value,
          contentCounts.value,
          game.value,
          activeTab.value,
        )
      : { visible: [...baseTabs.value] as string[], more: [] as string[] },
  );
  const visibleTabs = computed(
    () => tabPlan.value.visible as (typeof tabs)[number][],
  );
  const moreTabs = computed(
    () => tabPlan.value.more as (typeof tabs)[number][],
  );
  const showMoreTabs = ref(false);
  function closeMoreTabs() {
    showMoreTabs.value = false;
  }
  onMounted(() => document.addEventListener("click", closeMoreTabs));
  onUnmounted(() => document.removeEventListener("click", closeMoreTabs));
  function openMoreTab(tab: (typeof tabs)[number]) {
    showMoreTabs.value = false;
    activeTab.value = tab;
  }
  // With no Achievements tab there is nothing to tie things to or count, so
  // everything that depends on achievements steps aside too.
  const achievementsOn = computed(() => {
    const mode = pageSettings.value.tabs.Achievements;
    if (mode === "hide") return false;
    if (mode === "show") return true;
    return !!game.value && game.value.achievementTotal > 0;
  });
  const tieAchievements = computed(() =>
    achievementsOn.value ? (game.value?.achievements ?? []) : [],
  );

  // Opens on the tab the page settings name (or the one a link asked for), once
  // for each game, when both the game and the settings have arrived.
  let openedFor: string | null = null;
  watch(
    () => [game.value?.id, preferencesLoaded.value] as const,
    ([id, ready]) => {
      if (!id || !ready || openedFor === id) return;
      openedFor = id;
      void refreshCounts();
      const asked = route.query.tab as string | undefined;
      const wanted = asked ?? pageSettings.value.default_tab;
      const hidden =
        (OPTIONAL_TABS as readonly string[]).includes(wanted) &&
        pageSettings.value.tabs[wanted as OptionalTab] === "hide";
      if (
        (tabs as readonly string[]).includes(wanted) &&
        !(hidden && !asked) &&
        baseTabs.value.includes(wanted as (typeof tabs)[number])
      )
        activeTab.value = wanted as (typeof tabs)[number];
    },
    { immediate: true },
  );

  // Screenshots/Clips/Soundtrack/Saves/Docs/World Map all share the same
  // RomM-style layout: a small View/Upload sidebar instead of the dropzone
  // always sitting at the top. One shared ref is enough since only one of
  // these panels is ever visible at a time, reset to 'view' on every tab
  // switch so leaving a panel mid-upload-mode doesn't leak into the next one.
  const panelMode = ref<"view" | "upload">("view");
  watch(activeTab, () => {
    panelMode.value = "view";
  });
  function onDropError(message: string) {
    filesError.value = message;
    mediaError.value = message;
  }
  function onPreviewMedia(url: string) {
    if (
      activeTab.value === "Screenshots" ||
      (activeTab.value === "Accounts" &&
        accountMediaKind.value === "screenshot")
    ) {
      lightboxUrl.value = url;
    }
  }

  watch(isMinecraftGame, (isMinecraft) => {
    if (!isMinecraft && activeTab.value === "World Map")
      activeTab.value = "Overview";
  });

  watch(
    () => game.value?.profilesEnabled,
    (enabled) => {
      if (!enabled && activeTab.value === "Accounts")
        activeTab.value = "Overview";
    },
  );

  // --- Screenshots / Clips / Soundtrack --------------------------------------
  // same backend media store (kind is auto-classified by content-type on
  // upload), split into three tabs client-side by filtering on `kind`
  const mediaItems = ref<MediaItem[]>([]);
  const mediaLoading = ref(false);
  const mediaError = ref<string | null>(null);
  const mediaLoadedFor = ref<string | null>(null);
  const screenshots = computed(() =>
    mediaItems.value.filter((m) => m.kind === "screenshot"),
  );
  const clips = computed(() =>
    mediaItems.value.filter((m) => m.kind === "clip"),
  );
  const soundtrackItems = computed(() =>
    mediaItems.value.filter((m) => m.kind === "soundtrack"),
  );
  const lightboxUrl = ref<string | null>(null);

  // no args: every item regardless of account (the plain Screenshots/Clips/
  // Soundtrack tabs, which have no account concept of their own). Passed
  // explicitly by the Accounts tab to scope to one account or "General".
  async function loadMedia(profileId?: string | null, unscopedOnly = false) {
    if (!game.value) return;
    mediaLoading.value = true;
    mediaError.value = null;
    try {
      mediaItems.value = await listGameScreenshots(
        game.value.id,
        profileId,
        unscopedOnly,
      );
      mediaLoadedFor.value = game.value.id;
    } catch (err) {
      mediaError.value =
        err instanceof Error ? err.message : "Failed to load media";
    } finally {
      mediaLoading.value = false;
    }
  }

  // media tied to an achievement shows on that achievement's row, so the
  // Achievements tab needs the media list too
  const mediaByAchievement = computed(() => {
    const map = new Map<string, MediaItem[]>();
    for (const m of mediaItems.value) {
      if (!m.linked_achievement_id) continue;
      const list = map.get(m.linked_achievement_id) ?? [];
      list.push(m);
      map.set(m.linked_achievement_id, list);
    }
    return map;
  });
  const achMediaOpen = ref<string | null>(null);
  function toggleAchMedia(a: Achievement) {
    achMediaOpen.value = achMediaOpen.value === a.id ? null : a.id;
  }

  watch(activeTab, (tab) => {
    if (
      tab === "Achievements" &&
      game.value &&
      mediaLoadedFor.value !== game.value.id
    ) {
      void loadMedia();
    }
    if (tab === "Screenshots" || tab === "Clips" || tab === "Soundtrack") {
      void loadProfiles();
      // Screenshots, Clips and Soundtrack are one list, so it is loaded once for
      // the game and switching between them does not reload (and flash) it
      if (!game.value || mediaLoadedFor.value !== game.value.id)
        void loadMedia();
      void refreshMediaTrash();
    }
    if (tab === "Accounts") {
      void loadProfiles();
      void loadChecklist();
      void reloadMediaForCurrentTab();
    }
  });

  // media is scoped to an account only from within the Accounts tab, the
  // plain Screenshots/Clips/Soundtrack tabs upload unscoped, same as any
  // game without accounts enabled
  function reloadMediaForCurrentTab() {
    mediaLoadedFor.value = null;
    if (activeTab.value === "Accounts") {
      return loadMedia(activeProfileId.value, activeProfileId.value === null);
    }
    return loadMedia();
  }

  const uploadingMedia = ref(false);
  async function onMediaFilesSelected(files: File[]) {
    if (!files.length || !game.value) return;
    const gameId = game.value.id;
    mediaError.value = null;
    uploadingMedia.value = true;
    const taskId = startTask(
      `Uploading ${files.length} file${files.length === 1 ? "" : "s"}`,
      100,
    );
    const uploadProfileId =
      activeTab.value === "Accounts" ? activeProfileId.value : null;

    const attempt = async () => {
      try {
        const results = await uploadGameScreenshots(
          gameId,
          files,
          (fraction, speedLabel) =>
            updateTask(
              taskId,
              Math.round(fraction * 100),
              undefined,
              speedLabel,
            ),
          uploadProfileId,
        );
        for (const r of results) {
          addFeedItem(
            taskId,
            r.status === "saved"
              ? `${r.filename} uploaded`
              : `${r.filename}: ${r.reason ?? "rejected"}`,
          );
        }
        const saved = results.filter((r) => r.status === "saved").length;
        const summary = `${saved} uploaded${results.length > saved ? `, ${results.length - saved} rejected` : ""}`;
        if (saved === 0) {
          errorTask(taskId, summary);
        } else {
          completeTask(taskId, summary);
        }
        await reloadMediaForCurrentTab();
        // clips get their preview picture now, from the file in hand, so it is
        // saved before anyone has to load the video to see it
        void makeClipThumbnails(files, results);
      } catch (err) {
        // a network blip shouldn't force re-picking files from scratch
        errorTask(taskId, err instanceof Error ? err.message : "Upload failed");
        setTaskRetry(taskId, () => void attempt());
      } finally {
        uploadingMedia.value = false;
      }
    };
    await attempt();
  }

  function openAchievement(achievementId: string) {
    if (game.value)
      router.push(`/games/${game.value.id}/achievements/${achievementId}`);
  }

  const thumbnailing = new Set<string>();
  function applyClip(updated: MediaItem) {
    const i = mediaItems.value.findIndex((m) => m.id === updated.id);
    if (i !== -1) mediaItems.value[i] = updated;
  }
  async function keepThumbnail(item: MediaItem, blob: Blob, duration: number) {
    if (!game.value || thumbnailing.has(item.id)) return;
    thumbnailing.add(item.id);
    try {
      applyClip(
        await saveClipThumbnail(game.value.id, item.id, blob, duration),
      );
    } catch {
      // the picture is a nicety; the clip still plays and will be tried again
      thumbnailing.delete(item.id);
    }
  }
  async function makeClipThumbnails(
    files: File[],
    results: { filename: string; status: string; kind?: string }[],
  ) {
    for (let i = 0; i < results.length; i++) {
      const r = results[i];
      if (r.status !== "saved" || r.kind !== "clip") continue;
      const item = mediaItems.value.find((m) => m.filename === r.filename);
      if (!item || item.thumbnail_url) continue;
      const frame = await frameFromSource(files[i]);
      if (frame) await keepThumbnail(item, frame.blob, frame.duration);
    }
  }

  async function removeMedia(item: MediaItem) {
    if (!game.value) return;
    try {
      await deleteGameScreenshot(game.value.id, item.kind, item.filename);
      mediaItems.value = mediaItems.value.filter((m) => m !== item);
      await refreshMediaTrash();
    } catch (err) {
      mediaError.value =
        err instanceof Error ? err.message : "Failed to delete";
    }
  }

  // --- Trash: soft-deleted media stays recoverable for 7 days before the
  // background sweep purges it for good (features/trash/sweep.py) ----------
  const mediaTrash = ref<TrashedMediaItem[]>([]);
  const showMediaTrash = ref(false);
  const trashedScreenshots = computed(() =>
    mediaTrash.value.filter((m) => m.kind === "screenshot"),
  );
  const trashedClips = computed(() =>
    mediaTrash.value.filter((m) => m.kind === "clip"),
  );
  const trashedSoundtrack = computed(() =>
    mediaTrash.value.filter((m) => m.kind === "soundtrack"),
  );
  const activeTabTrash = computed(() => {
    if (activeTab.value === "Screenshots") return trashedScreenshots.value;
    if (activeTab.value === "Clips") return trashedClips.value;
    if (activeTab.value === "Soundtrack") return trashedSoundtrack.value;
    return [];
  });

  async function refreshMediaTrash() {
    if (!game.value) return;
    try {
      mediaTrash.value = await fetchGameMediaTrash(game.value.id);
    } catch {
      // trash listing failing silently isn't worth blocking the main view
    }
  }

  async function restoreMediaItem(item: TrashedMediaItem) {
    if (!game.value) return;
    try {
      await restoreGameMedia(game.value.id, item.kind, item.filename);
      mediaLoadedFor.value = null;
      await loadMedia();
      await refreshMediaTrash();
    } catch (err) {
      mediaError.value =
        err instanceof Error ? err.message : "Failed to restore";
    }
  }

  async function saveMediaItem(item: MediaItem, patch: MediaItemUpdate) {
    if (!game.value) return;
    try {
      const updated = await updateMediaItem(game.value.id, item.id, patch);
      const index = mediaItems.value.findIndex((m) => m.id === item.id);
      if (index !== -1) mediaItems.value[index] = updated;
      // the item may have just moved out of the Accounts tab's currently
      // selected scope (or into it), refetch so the gallery reflects that
      if (
        activeTab.value === "Accounts" &&
        "profile_id" in patch &&
        (activeProfileId.value !== null || patch.profile_id !== null)
      ) {
        await reloadMediaForCurrentTab();
      }
    } catch (err) {
      mediaError.value = err instanceof Error ? err.message : "Failed to save";
    }
  }

  async function bulkSaveMedia(
    updates: { id: string; patch: MediaItemUpdate }[],
  ) {
    if (!game.value) return;
    const gameId = game.value.id;
    try {
      const updated = await Promise.all(
        updates.map((u) => updateMediaItem(gameId, u.id, u.patch)),
      );
      for (const u of updated) {
        const index = mediaItems.value.findIndex((m) => m.id === u.id);
        if (index !== -1) mediaItems.value[index] = u;
      }
    } catch (err) {
      mediaError.value = err instanceof Error ? err.message : "Failed to save";
    }
  }

  async function bulkDeleteMedia(items: MediaItem[]) {
    for (const item of items) await removeMedia(item);
  }

  // Finds the real date for the given files. The file's own data and name come
  // first; a file that has neither takes the unlock time of the achievement it is
  // tied to, as long as its current date is only a guess. Resolves with where
  // the date came from, per file.
  async function detectDates(
    ids: string[],
  ): Promise<Map<string, "file" | "achievement" | "none">> {
    const outcome = new Map<string, "file" | "achievement" | "none">();
    for (const id of ids) outcome.set(id, "none");
    if (!game.value) return outcome;
    try {
      const found = await detectMediaDates(game.value.id, ids);
      for (const u of found) {
        const index = mediaItems.value.findIndex((m) => m.id === u.id);
        if (index !== -1) mediaItems.value[index] = u;
        outcome.set(u.id, "file");
      }
      for (const id of ids) {
        if (outcome.get(id) === "file") continue;
        const item = mediaItems.value.find((m) => m.id === id);
        if (!item?.linked_achievement_id || !isGuess(item)) continue;
        const when = unlockSeconds(
          game.value.achievements.find(
            (a) => a.id === item.linked_achievement_id,
          ),
        );
        if (when === null) continue;
        await saveMediaItem(item, {
          taken_at: when,
          taken_source: "achievement",
        });
        outcome.set(id, "achievement");
      }
    } catch (err) {
      mediaError.value =
        err instanceof Error ? err.message : "Failed to detect dates";
    }
    return outcome;
  }
  async function detectOne(item: FileDetails) {
    return (await detectDates([item.id])).get(item.id) ?? "none";
  }
  async function detectMany(ids: string[]) {
    const outcome = await detectDates(ids);
    const values = [...outcome.values()];
    const file = values.filter((v) => v === "file").length;
    const achievement = values.filter((v) => v === "achievement").length;
    const none = values.length - file - achievement;
    if (!none) return;
    mediaError.value = `${none} file${none === 1 ? " has" : "s have"} no date in ${none === 1 ? "it" : "them"} and no unlocked achievement to take one from. Set those by hand.`;
  }

  // --- Docs / Modpack ---------------------------------------------------------
  // generic flat-file attachments (any format), Saves/World Save moved to
  // named, versioned archives below; docs/modpacks stay simple since
  // naming/history doesn't add much for a single manual or modpack zip
  type FlatFileKind = Extract<GameFileKind, "doc" | "modpack">;
  const docsFiles = ref<GameFile[]>([]);
  const modpackFiles = ref<GameFile[]>([]);
  const filesLoaded = ref<Record<FlatFileKind, string | null>>({
    doc: null,
    modpack: null,
  });
  const filesError = ref<string | null>(null);
  const uploadingFiles = ref(false);

  const FILE_REFS: Record<FlatFileKind, typeof docsFiles> = {
    doc: docsFiles,
    modpack: modpackFiles,
  };
  function filesRefFor(kind: FlatFileKind) {
    return FILE_REFS[kind];
  }

  async function loadGameFiles(kind: FlatFileKind) {
    if (!game.value || filesLoaded.value[kind] === game.value.id) return;
    filesError.value = null;
    try {
      filesRefFor(kind).value = await listGameFiles(game.value.id, kind);
      filesLoaded.value[kind] = game.value.id;
    } catch (err) {
      filesError.value =
        err instanceof Error ? err.message : "Failed to load files";
    }
  }

  watch(activeTab, (tab) => {
    void refreshCounts();
    if (tab === "Docs") {
      void loadGameFiles("doc");
      void refreshFileTrash("doc");
    }
    if (tab === "Saves") {
      void refreshSaveArchives();
      void refreshSaveTrash();
    }
    if (tab === "World Map") {
      void loadGameFiles("modpack");
      void refreshFileTrash("modpack");
      void refreshWorldMaps();
      void refreshWorldTrash();
    }
    if (tab === "Stats") {
      void loadFieldChanges();
      if (game.value && mediaLoadedFor.value !== game.value.id)
        void loadMedia();
    }
  });

  const fieldChanges = ref<FieldChange[]>([]);
  const fieldChangesLoading = ref(false);
  const fieldChangesError = ref<string | null>(null);
  async function loadFieldChanges() {
    if (!game.value) return;
    fieldChangesLoading.value = true;
    fieldChangesError.value = null;
    try {
      fieldChanges.value = await fetchGameFieldChanges(game.value.id);
    } catch (err) {
      fieldChangesError.value =
        err instanceof Error ? err.message : "Failed to load history";
    } finally {
      fieldChangesLoading.value = false;
    }
  }
  async function onGameFilesSelected(files: File[], kind: FlatFileKind) {
    if (!files.length || !game.value) return;
    const gameId = game.value.id;
    uploadingFiles.value = true;
    const taskId = startTask(
      `Uploading ${files.length} file${files.length === 1 ? "" : "s"}`,
      100,
    );

    const attempt = async () => {
      try {
        const results = await uploadGameFiles(
          gameId,
          kind,
          files,
          (fraction, speedLabel) =>
            updateTask(
              taskId,
              Math.round(fraction * 100),
              undefined,
              speedLabel,
            ),
        );
        for (const r of results) {
          addFeedItem(
            taskId,
            r.status === "saved"
              ? `${r.filename} uploaded`
              : `${r.filename}: ${r.reason ?? "rejected"}`,
          );
        }
        const saved = results.filter((r) => r.status === "saved").length;
        const summary = `${saved} uploaded${results.length > saved ? `, ${results.length - saved} rejected` : ""}`;
        if (saved === 0) {
          errorTask(taskId, summary);
        } else {
          completeTask(taskId, summary);
        }
        filesLoaded.value[kind] = null;
        await loadGameFiles(kind);
      } catch (err) {
        errorTask(taskId, err instanceof Error ? err.message : "Upload failed");
        setTaskRetry(taskId, () => void attempt());
      } finally {
        uploadingFiles.value = false;
      }
    };
    await attempt();
  }

  async function saveGameFile(
    kind: FlatFileKind,
    file: FileDetails,
    patch: MediaItemUpdate,
  ) {
    if (!game.value) return;
    try {
      // only the fields that changed: a missing key means "leave it alone"
      const changes: GameFileUpdate = {};
      if ("title" in patch) changes.title = patch.title;
      if ("note" in patch) changes.note = patch.note;
      if ("tags" in patch) changes.tags = patch.tags;
      if ("taken_at" in patch) {
        changes.taken_at = patch.taken_at;
        changes.taken_source = patch.taken_source;
      }
      const updated = await updateGameFile(
        game.value.id,
        kind,
        file.id,
        changes,
      );
      const list = filesRefFor(kind);
      const index = list.value.findIndex((f) => f.id === updated.id);
      if (index !== -1) list.value[index] = updated;
    } catch (err) {
      filesError.value = err instanceof Error ? err.message : "Failed to save";
    }
  }

  async function bulkSaveFiles(
    kind: FlatFileKind,
    updates: { id: string; patch: MediaItemUpdate }[],
  ) {
    for (const u of updates) {
      const file = filesRefFor(kind).value.find((f) => f.id === u.id);
      if (file) await saveGameFile(kind, file, u.patch);
    }
  }

  async function removeGameFile(kind: FlatFileKind, file: FileDetails) {
    if (!game.value) return;
    try {
      await deleteGameFile(game.value.id, kind, file.filename);
      filesRefFor(kind).value = filesRefFor(kind).value.filter(
        (f) => f.filename !== file.filename,
      );
      await refreshFileTrash(kind);
    } catch (err) {
      filesError.value =
        err instanceof Error ? err.message : "Failed to delete";
    }
  }

  // --- Trash: soft-deleted docs/modpacks stay recoverable for 7 days before
  // the background sweep purges them for good (features/trash/sweep.py) ----
  const docsTrash = ref<TrashedGameFile[]>([]);
  const modpackTrash = ref<TrashedGameFile[]>([]);
  const showDocsTrash = ref(false);
  const showModpackTrash = ref(false);
  const FILE_TRASH_REFS: Record<FlatFileKind, typeof docsTrash> = {
    doc: docsTrash,
    modpack: modpackTrash,
  };
  function fileTrashRefFor(kind: FlatFileKind) {
    return FILE_TRASH_REFS[kind];
  }

  async function refreshFileTrash(kind: FlatFileKind) {
    if (!game.value) return;
    try {
      fileTrashRefFor(kind).value = await fetchGameFileTrash(
        game.value.id,
        kind,
      );
    } catch {
      // trash listing failing silently isn't worth blocking the main view
    }
  }

  async function restoreFileItem(kind: FlatFileKind, item: TrashedGameFile) {
    if (!game.value) return;
    try {
      await restoreGameFile(game.value.id, kind, item.filename);
      filesLoaded.value[kind] = null;
      await loadGameFiles(kind);
      await refreshFileTrash(kind);
    } catch (err) {
      filesError.value =
        err instanceof Error ? err.message : "Failed to restore";
    }
  }

  function formatFileSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  function formatArchiveDate(unixSeconds: number): string {
    return new Date(unixSeconds * 1000).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  // --- Saves (named, versioned archives) --------------------------------------
  const saveArchives = ref<GameArchiveData[]>([]);
  const saveArchivesLoaded = ref(false);
  const saveUploading = ref<Set<string>>(new Set()); // archive id, or '' for "new save"

  async function refreshSaveArchives() {
    if (!game.value) return;
    try {
      saveArchives.value = await fetchArchives(game.value.id, "save");
      saveArchivesLoaded.value = true;
    } catch (err) {
      filesError.value =
        err instanceof Error ? err.message : "Failed to load saves";
    }
  }

  async function onNewSaveSelected(files: File[]) {
    const file = files[0];
    if (!file || !game.value) return;
    const gameId = game.value.id;
    const name = await prompt({
      title: "Name this save",
      message: "Save name",
      defaultValue: file.name.replace(/\.[^.]+$/, ""),
      confirmLabel: "Upload",
    });
    if (!name || !name.trim()) return;
    const trimmedName = name.trim();
    const taskId = startTask(`Uploading "${trimmedName}"`, 100);

    const attempt = async () => {
      saveUploading.value = new Set(saveUploading.value).add("");
      try {
        await createArchive(
          gameId,
          "save",
          trimmedName,
          file,
          (f, speedLabel) =>
            updateTask(taskId, Math.round(f * 100), undefined, speedLabel),
        );
        completeTask(taskId, "Saved");
        await refreshSaveArchives();
      } catch (err) {
        errorTask(taskId, err instanceof Error ? err.message : "Upload failed");
        setTaskRetry(taskId, () => void attempt());
      } finally {
        const next = new Set(saveUploading.value);
        next.delete("");
        saveUploading.value = next;
      }
    };
    await attempt();
  }

  async function onAddSaveVersion(archive: GameArchiveData, files: File[]) {
    const file = files[0];
    if (!file || !game.value) return;
    const gameId = game.value.id;
    const taskId = startTask(`Uploading new version of "${archive.name}"`, 100);

    const attempt = async () => {
      saveUploading.value = new Set(saveUploading.value).add(archive.id);
      try {
        await addArchiveVersion(gameId, archive.id, file, (f, speedLabel) =>
          updateTask(taskId, Math.round(f * 100), undefined, speedLabel),
        );
        completeTask(taskId, "Saved");
        await refreshSaveArchives();
      } catch (err) {
        errorTask(taskId, err instanceof Error ? err.message : "Upload failed");
        setTaskRetry(taskId, () => void attempt());
      } finally {
        const next = new Set(saveUploading.value);
        next.delete(archive.id);
        saveUploading.value = next;
      }
    };
    await attempt();
  }

  // The save or world being edited. Held by id, so the dialog reads the current
  // copy from the list and shows a version as soon as it is added or removed.
  const editingArchive = ref<{ id: string; isWorld: boolean } | null>(null);
  const editingArchiveLive = computed(() => {
    const e = editingArchive.value;
    if (!e) return null;
    const list: GameArchiveData[] = e.isWorld
      ? worldMaps.value
      : saveArchives.value;
    return list.find((a) => a.id === e.id) ?? null;
  });
  function openArchiveEdit(archive: GameArchiveData, isWorld: boolean) {
    editingArchive.value = { id: archive.id, isWorld };
  }

  async function saveArchiveDetails(
    archive: GameArchiveData,
    isWorld: boolean,
    patch: { name?: string; note?: string | null; tags?: string[] },
  ) {
    if (!game.value) return;
    try {
      await updateArchive(game.value.id, archive.id, patch);
      if (isWorld) await refreshWorldMaps();
      else await refreshSaveArchives();
    } catch (err) {
      filesError.value = err instanceof Error ? err.message : "Failed to save";
    }
  }

  async function bulkDeleteArchives(
    items: GameArchiveData[],
    isWorld: boolean,
  ) {
    if (!game.value || !items.length) return;
    const ok = await confirm({
      title: "Move to trash",
      message: `Move ${items.length} ${isWorld ? "world" : "save"}${items.length === 1 ? "" : "s"} to trash? ${items.length === 1 ? "It stays" : "They stay"} recoverable for 7 days, then ${items.length === 1 ? "is" : "are"} purged for good.`,
      confirmLabel: "Move to trash",
      danger: true,
    });
    if (!ok) return;
    try {
      for (const archive of items)
        await deleteArchive(game.value.id, archive.id);
      if (isWorld) {
        await refreshWorldMaps();
        await refreshWorldTrash();
      } else {
        await refreshSaveArchives();
        await refreshSaveTrash();
      }
    } catch (err) {
      filesError.value =
        err instanceof Error ? err.message : "Failed to delete";
    }
  }

  async function onDeleteArchive(archive: GameArchiveData, isWorld: boolean) {
    if (!game.value) return;
    const ok = await confirm({
      title: "Move to trash",
      message: `Move "${archive.name}" (${archive.versions.length} version(s)) to trash? It stays recoverable for 7 days, then is purged for good.`,
      confirmLabel: "Move to trash",
      danger: true,
    });
    if (!ok) return;
    try {
      await deleteArchive(game.value.id, archive.id);
      if (isWorld) {
        worldMaps.value = worldMaps.value.filter((w) => w.id !== archive.id);
        if (activeMapArchiveId.value === archive.id)
          activeMapArchiveId.value = null;
        await refreshWorldTrash();
      } else {
        saveArchives.value = saveArchives.value.filter(
          (a) => a.id !== archive.id,
        );
        await refreshSaveTrash();
      }
    } catch (err) {
      filesError.value =
        err instanceof Error ? err.message : "Failed to delete";
    }
  }

  // --- Trash: soft-deleted archives stay recoverable for 7 days before the
  // background sweep purges them for good (features/trash/sweep.py) ---------
  const saveTrash = ref<TrashedArchive[]>([]);
  const worldTrash = ref<TrashedArchive[]>([]);
  const showSaveTrash = ref(false);
  const showWorldTrash = ref(false);

  async function refreshSaveTrash() {
    if (!game.value) return;
    try {
      saveTrash.value = await fetchArchiveTrash(game.value.id, "save");
    } catch {
      // trash listing failing silently isn't worth blocking the main view
    }
  }

  async function refreshWorldTrash() {
    if (!game.value) return;
    try {
      worldTrash.value = await fetchArchiveTrash(game.value.id, "world_save");
    } catch {
      // same as above
    }
  }

  async function onRestoreArchive(archive: TrashedArchive, isWorld: boolean) {
    if (!game.value) return;
    try {
      await restoreArchive(game.value.id, archive.id);
      if (isWorld) {
        await refreshWorldMaps();
        await refreshWorldTrash();
      } else {
        await refreshSaveArchives();
        await refreshSaveTrash();
      }
    } catch (err) {
      filesError.value =
        err instanceof Error ? err.message : "Failed to restore";
    }
  }

  async function onDeleteVersion(
    archive: GameArchiveData,
    version: ArchiveVersion,
    isWorld: boolean,
  ) {
    if (!game.value) return;
    if (archive.versions.length <= 1) {
      filesError.value =
        "Delete the whole save to remove its last remaining version.";
      return;
    }
    const ok = await confirm({
      title: "Move to trash",
      message: `Move this version (${formatFileSize(version.size)}, ${formatArchiveDate(version.uploaded_at)}) to trash? Recoverable for 7 days.`,
      confirmLabel: "Move to trash",
      danger: true,
    });
    if (!ok) return;
    try {
      await deleteArchiveVersion(game.value.id, archive.id, version.id);
      if (isWorld) await refreshWorldMaps();
      else await refreshSaveArchives();
    } catch (err) {
      filesError.value =
        err instanceof Error ? err.message : "Failed to delete version";
    }
  }

  const {
    worldMaps,
    worldMapsLoaded,
    worldMapStarting,
    activeMapArchiveId,
    stopWorldMapPolling,
    refreshWorldMaps,
    onNewWorldSelected,
    onAddWorldVersion,
    startWorldMapRender,
    viewWorldMap,
  } = useGameWorldMaps(game, saveUploading, filesError, prompt);

  const {
    descriptionOf,
    achFilter,
    achProvider,
    achSearch,
    achLocal,
    noteOpen,
    noteDraft,
    overallOpen,
    overallDraft,
    isPinned,
    togglePin,
    isHiddenLocked,
    revealAchievement,
    hideAchievement,
    toggleNote,
    saveNote,
    clearNote,
    toggleOverall,
    saveOverall,
    unlockedCount,
    achFilterOptions,
    sortBy,
    sortMark,
    ariaSort,
    mobileSort,
    achProviders,
    shownAchievements,
    achStats,
    formatPlaytime,
  } = useGameAchievements(game, () => loadGame(route.params.id as string));

  return {
    confirm,
    route,
    router,
    goBackToLibrary,
    game,
    loading,
    error,
    showEditModal,
    deleting,
    deleteError,
    showDeleteConfirm,
    descriptionHtml,
    descriptionExpanded,
    descriptionOverflows,
    parentGameTitle,
    RELATIONSHIP_LABELS,
    variants,
    profiles,
    activeProfileId,
    newProfileName,
    profileError,
    addProfile,
    promptRenameProfile,
    removeProfile,
    selectedProfile,
    profileNoteDraft,
    profileNoteSaving,
    saveProfileNote,
    statRows,
    editingStats,
    startEditStats,
    cancelEditStats,
    addStatRow,
    removeStatRow,
    saveProfileStats,
    womUsername,
    womSyncing,
    womError,
    syncWiseOldMan,
    statHistory,
    statHistoryLoading,
    showStatHistory,
    historyShowAll,
    HISTORY_PAGE_SIZE,
    toggleStatHistory,
    formatSnapshotDate,
    statGains,
    visibleHistory,
    headlineStats,
    skillStats,
    bossStats,
    skillIconUrl,
    ACCOUNT_MEDIA_KINDS,
    accountMediaKind,
    accountMediaCategory,
    accountMediaCategories,
    accountMediaFiltered,
    checklistItems,
    checklistLoading,
    checklistError,
    newChecklistText,
    editingItemId,
    editingText,
    checklistProgress,
    checklistSections,
    collapsedSections,
    toggleSectionCollapsed,
    sectionProgress,
    addChecklistItem,
    addChecklistSection,
    toggleChecklistItem,
    startEditItem,
    commitEditItem,
    cancelEditItem,
    moveChecklistItem,
    removeChecklistItem,
    onGameSaved,
    resumeNoteDraft,
    resumeNoteEditing,
    resumeNoteSaving,
    resumeNoteError,
    startEditResumeNote,
    saveResumeNote,
    loggingPlaytime,
    logPlaytime,
    similarGames,
    toggleFavorite,
    STATUS_OPTIONS,
    changeStatus,
    onCollectionsChanged,
    onRatingsChange,
    onDeleteFromModal,
    confirmDelete,
    recentActivity,
    heroCredits,
    libraryLink,
    ratingParts,
    overviewFacts,
    mainTags,
    moreTags,
    activeTab,
    pageSettings,
    visibleTabs,
    moreTabs,
    showMoreTabs,
    openMoreTab,
    achievementsOn,
    tieAchievements,
    onDropError,
    onPreviewMedia,
    mediaItems,
    mediaLoading,
    mediaError,
    mediaLoadedFor,
    screenshots,
    clips,
    soundtrackItems,
    lightboxUrl,
    mediaByAchievement,
    achMediaOpen,
    toggleAchMedia,
    uploadingMedia,
    onMediaFilesSelected,
    openAchievement,
    keepThumbnail,
    removeMedia,
    activeTabTrash,
    restoreMediaItem,
    saveMediaItem,
    bulkSaveMedia,
    bulkDeleteMedia,
    detectOne,
    detectMany,
    docsFiles,
    modpackFiles,
    filesLoaded,
    filesError,
    uploadingFiles,
    fieldChanges,
    fieldChangesLoading,
    fieldChangesError,
    onGameFilesSelected,
    saveGameFile,
    bulkSaveFiles,
    removeGameFile,
    docsTrash,
    modpackTrash,
    restoreFileItem,
    saveArchives,
    saveArchivesLoaded,
    saveUploading,
    onNewSaveSelected,
    onAddSaveVersion,
    editingArchive,
    editingArchiveLive,
    openArchiveEdit,
    saveArchiveDetails,
    bulkDeleteArchives,
    onDeleteArchive,
    saveTrash,
    worldTrash,
    onRestoreArchive,
    onDeleteVersion,
    worldMaps,
    worldMapsLoaded,
    worldMapStarting,
    activeMapArchiveId,
    onNewWorldSelected,
    onAddWorldVersion,
    startWorldMapRender,
    viewWorldMap,
    descriptionOf,
    achFilter,
    achProvider,
    achSearch,
    achLocal,
    noteOpen,
    noteDraft,
    overallOpen,
    overallDraft,
    isPinned,
    togglePin,
    isHiddenLocked,
    revealAchievement,
    hideAchievement,
    toggleNote,
    saveNote,
    clearNote,
    toggleOverall,
    saveOverall,
    unlockedCount,
    achFilterOptions,
    sortBy,
    sortMark,
    ariaSort,
    mobileSort,
    achProviders,
    shownAchievements,
    achStats,
    formatPlaytime,
  };
}
