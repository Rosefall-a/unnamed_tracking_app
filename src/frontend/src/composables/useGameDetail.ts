import {
  displayFileName,
  sortedAchievements,
  deriveTier,
  formatUnlockedAt,
  formatPlaytime,
} from "../utils/gameDetailDisplay";
import { useGameNotes } from "./useGameNotes";

import { documentReaderUrl } from "../state/pluginExtensions";
import { usePageTitle } from "../state/pageTitle";
import { formatDisplayDate } from "../utils/dates";
import { activePriority, priorityLabel } from "../utils/priority";
import { computed, ref, watch, onMounted, onUnmounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  deleteGame,
  fetchGame,
  fetchGameVariants,
  fetchGameAchievements,
  fetchGameFieldChanges,
  fetchGames,
  setFavorite,
  setResumeNote,
  setPlaytimeSeconds,
} from "../services/games";
import type { FieldChange } from "../services/games";
import { peekAdjacentGameId } from "../state/libraryNav";
import {
  uploadGameScreenshots,
  listGameScreenshots,
  deleteGameScreenshot,
  updateMediaItem,
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
  GameFile,
  GameFileKind,
  TrashedMediaItem,
  TrashedGameFile,
} from "../services/media";
import {
  listGameProfiles,
  createGameProfile,
  renameGameProfile,
  updateGameProfile,
  deleteGameProfile,
  syncProfileWiseOldMan,
  fetchProfileStatHistory,
  listChecklist,
  createChecklistItem,
  updateChecklistItem,
  deleteChecklistItem,
  reorderChecklist,
} from "../services/gameProfiles";
import type {
  GameProfile,
  ChecklistItem,
  StatSnapshot,
} from "../services/gameProfiles";
import {
  fetchArchives,
  createArchive,
  addArchiveVersion,
  renameArchive,
  deleteArchive,
  deleteArchiveVersion,
  worldMapViewUrl,
  worldMapThumbnailUrl,
  fetchArchiveTrash,
  restoreArchive,
} from "../services/gameArchives";
import type {
  GameArchiveData,
  ArchiveVersion,
  TrashedArchive,
} from "../services/gameArchives";

import {
  startTask,
  updateTask,
  completeTask,
  errorTask,
  addFeedItem,
  setTaskRetry,
} from "../state/taskProgress";
import type { Game } from "../types/game";

import { computeScore } from "../utils/scoring";
import DOMPurify from "dompurify";
import { useConfirm, usePrompt } from "../state/dialog";
import { useGameWorldMaps } from "./useGameWorldMaps";
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

  const {
    noteNames,
    noteMode,
    viewingNoteName,
    editingNoteName,
    draftName,
    draftContent,
    noteLoading,
    noteSaving,
    noteError,
    hasDraft,
    renderedNoteHtml,
    startNewNote,
    viewNote,
    editFromView,
    backToList,
    saveDraft,
    deleteNote,
    loadNotes,
  } = useGameNotes(game);

  // Steam's "About This Game" section is rich HTML (headers, screenshots,
  // gifs), sanitize it instead of stripping it down to plain text so that
  // content survives
  const descriptionHtml = computed(() => {
    if (!game.value?.description) return "";
    return DOMPurify.sanitize(game.value.description);
  });

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

  // --- Profiles (e.g. separate OSRS accounts) --------------------------------
  // shared across the Notes checklist and the Screenshots/Clips/Soundtrack
  // gallery, one "which account am I looking at" selector, not two, so a
  // game with several accounts doesn't need everything dug through together.
  const profiles = ref<GameProfile[]>([]);
  const profilesLoadedFor = ref<string | null>(null);
  // null = "General" (unscoped), the default, matching how most games (no
  // multi-account concept) never need to touch this at all
  const activeProfileId = ref<string | null>(null);
  const newProfileName = ref("");
  const profileError = ref<string | null>(null);

  async function loadProfiles() {
    if (!game.value || profilesLoadedFor.value === game.value.id) return;
    try {
      profiles.value = await listGameProfiles(game.value.id);
      profilesLoadedFor.value = game.value.id;
    } catch (err) {
      profileError.value =
        err instanceof Error ? err.message : "Failed to load profiles";
    }
  }

  async function addProfile() {
    if (!game.value) return;
    const name = newProfileName.value.trim();
    if (!name) return;
    profileError.value = null;
    try {
      const created = await createGameProfile(game.value.id, name);
      profiles.value = [...profiles.value, created];
      newProfileName.value = "";
      activeProfileId.value = created.id;
    } catch (err) {
      profileError.value =
        err instanceof Error ? err.message : "Failed to create profile";
    }
  }

  async function promptRenameProfile(profile: GameProfile) {
    const name = await prompt({
      title: "Rename account",
      message: "Account name",
      defaultValue: profile.name,
      confirmLabel: "Rename",
    });
    if (name) void renameProfile(profile, name);
  }

  async function renameProfile(profile: GameProfile, name: string) {
    if (!game.value) return;
    const trimmed = name.trim();
    if (!trimmed || trimmed === profile.name) return;
    try {
      const updated = await renameGameProfile(
        game.value.id,
        profile.id,
        trimmed,
      );
      const idx = profiles.value.findIndex((p) => p.id === profile.id);
      if (idx !== -1) profiles.value[idx] = updated;
    } catch (err) {
      profileError.value =
        err instanceof Error ? err.message : "Failed to rename profile";
    }
  }

  async function removeProfile(profile: GameProfile) {
    if (!game.value) return;
    try {
      await deleteGameProfile(game.value.id, profile.id);
      profiles.value = profiles.value.filter((p) => p.id !== profile.id);
      if (activeProfileId.value === profile.id) activeProfileId.value = null;
    } catch (err) {
      profileError.value =
        err instanceof Error ? err.message : "Failed to delete profile";
    }
  }

  // --- Accounts tab: selected account's note/stats/WiseOldMan sync -----------
  // null activeProfileId means the sidebar's "General" entry, there's no
  // GameProfile row for that, so note/stats/WiseOldMan simply don't apply
  const selectedProfile = computed(
    () => profiles.value.find((p) => p.id === activeProfileId.value) ?? null,
  );

  const profileNoteDraft = ref("");
  const profileNoteSaving = ref(false);
  watch(selectedProfile, (profile) => {
    profileNoteDraft.value = profile?.note ?? "";
  });

  async function saveProfileNote() {
    if (!game.value || !selectedProfile.value) return;
    profileNoteSaving.value = true;
    try {
      const updated = await updateGameProfile(
        game.value.id,
        selectedProfile.value.id,
        {
          note: profileNoteDraft.value.trim() || null,
        },
      );
      const idx = profiles.value.findIndex((p) => p.id === updated.id);
      if (idx !== -1) profiles.value[idx] = updated;
    } catch (err) {
      profileError.value =
        err instanceof Error ? err.message : "Failed to save note";
    } finally {
      profileNoteSaving.value = false;
    }
  }

  interface StatRow {
    key: string;
    value: string;
  }
  const statRows = ref<StatRow[]>([]);
  // display mode by default (a clean read-only grid), editing mode swaps in
  // the raw label/value rows, entered explicitly rather than always showing
  // 30+ input pairs for an account with a full WiseOldMan sync
  const editingStats = ref(false);
  watch(selectedProfile, (profile) => {
    statRows.value = profile
      ? Object.entries(profile.stats).map(([key, value]) => ({ key, value }))
      : [];
    editingStats.value = false;
  });
  function startEditStats() {
    if (selectedProfile.value) {
      statRows.value = Object.entries(selectedProfile.value.stats).map(
        ([key, value]) => ({ key, value }),
      );
    }
    editingStats.value = true;
  }
  function cancelEditStats() {
    if (selectedProfile.value) {
      statRows.value = Object.entries(selectedProfile.value.stats).map(
        ([key, value]) => ({ key, value }),
      );
    }
    editingStats.value = false;
  }
  function addStatRow() {
    statRows.value = [...statRows.value, { key: "", value: "" }];
  }
  function removeStatRow(index: number) {
    statRows.value = statRows.value.filter((_, i) => i !== index);
  }
  async function saveProfileStats() {
    if (!game.value || !selectedProfile.value) return;
    const stats: Record<string, string> = {};
    for (const row of statRows.value) {
      const key = row.key.trim();
      if (key) stats[key] = row.value.trim();
    }
    try {
      const updated = await updateGameProfile(
        game.value.id,
        selectedProfile.value.id,
        { stats },
      );
      const idx = profiles.value.findIndex((p) => p.id === updated.id);
      if (idx !== -1) profiles.value[idx] = updated;
      statRows.value = Object.entries(updated.stats).map(([key, value]) => ({
        key,
        value,
      }));
      editingStats.value = false;
      if (showStatHistory.value) await loadStatHistory();
    } catch (err) {
      profileError.value =
        err instanceof Error ? err.message : "Failed to save stats";
    }
  }

  const womUsername = ref("");
  watch(selectedProfile, (profile) => {
    womUsername.value = profile?.wiseoldman_username ?? "";
  });
  const womSyncing = ref(false);
  const womError = ref<string | null>(null);
  async function syncWiseOldMan() {
    if (!game.value || !selectedProfile.value) return;
    const username = womUsername.value.trim();
    if (!username) {
      womError.value = "Enter a RuneScape username first.";
      return;
    }
    womSyncing.value = true;
    womError.value = null;
    try {
      const updated = await syncProfileWiseOldMan(
        game.value.id,
        selectedProfile.value.id,
        username,
      );
      const idx = profiles.value.findIndex((p) => p.id === updated.id);
      if (idx !== -1) profiles.value[idx] = updated;
      statRows.value = Object.entries(updated.stats).map(([key, value]) => ({
        key,
        value,
      }));
      await loadStatHistory();
    } catch (err) {
      womError.value =
        err instanceof Error ? err.message : "Failed to sync WiseOldMan";
    } finally {
      womSyncing.value = false;
    }
  }

  // --- Stat history: dated snapshots, so progression is visible over time ----
  const statHistory = ref<StatSnapshot[]>([]);
  const statHistoryLoading = ref(false);
  const showStatHistory = ref(false);
  const historyShowAll = ref(false);
  const HISTORY_PAGE_SIZE = 12;
  watch(selectedProfile, () => {
    statHistory.value = [];
    showStatHistory.value = false;
    historyShowAll.value = false;
  });
  async function loadStatHistory() {
    if (!game.value || !selectedProfile.value) return;
    statHistoryLoading.value = true;
    try {
      statHistory.value = await fetchProfileStatHistory(
        game.value.id,
        selectedProfile.value.id,
      );
    } catch {
      // history is a nice-to-have alongside the live stats, not worth
      // failing the whole Stats card over
    } finally {
      statHistoryLoading.value = false;
    }
  }
  async function toggleStatHistory() {
    showStatHistory.value = !showStatHistory.value;
    if (showStatHistory.value && !statHistory.value.length)
      await loadStatHistory();
  }
  function formatSnapshotDate(epochSeconds: number): string {
    return new Date(epochSeconds * 1000).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  }

  // "on this day" gains, each snapshot compared against the next-older one
  // in the list (statHistory is newest-first) using the raw xp/kc integers,
  // not the display-string levels (a single level can span tens of
  // thousands of XP, so diffing levels would be meaningless). A manually-
  // edited snapshot has empty xp/kc, so it simply contributes no gain lines
  //, nothing to divide by zero on, just nothing to show.
  const statGains = computed<Record<string, string[]>>(() => {
    const gains: Record<string, string[]> = {};
    const list = statHistory.value;
    for (let i = 0; i < list.length; i++) {
      const current = list[i];
      const older = list[i + 1];
      if (!older) {
        gains[current.id] = [];
        continue;
      }
      const lines: string[] = [];
      for (const [skill, xp] of Object.entries(current.xp)) {
        const oldXp = older.xp[skill];
        if (oldXp !== undefined && xp > oldXp) {
          lines.push(`+${(xp - oldXp).toLocaleString()} ${skill} XP`);
        }
      }
      for (const [boss, kc] of Object.entries(current.kc)) {
        const oldKc = older.kc[boss];
        if (oldKc !== undefined && kc > oldKc) {
          lines.push(`+${kc - oldKc} ${boss} KC`);
        }
      }
      gains[current.id] = lines;
    }
    return gains;
  });
  const visibleHistory = computed(() =>
    historyShowAll.value
      ? statHistory.value
      : statHistory.value.slice(0, HISTORY_PAGE_SIZE),
  );

  // grouped for display: Overall/Combat as headline tiles, boss kill counts
  // (WOM always formats these as "N KC") in their own section instead of
  // mixed in alphabetically with skill levels
  const HEADLINE_STAT_KEYS = ["Overall", "Combat"];
  const headlineStats = computed(() =>
    HEADLINE_STAT_KEYS.filter((key) => selectedProfile.value?.stats[key]).map(
      (key) => ({
        key,
        value: selectedProfile.value!.stats[key],
      }),
    ),
  );
  const skillStats = computed(() =>
    Object.entries(selectedProfile.value?.stats ?? {}).filter(
      ([key, value]) =>
        !HEADLINE_STAT_KEYS.includes(key) && !value.endsWith(" KC"),
    ),
  );
  const bossStats = computed(() =>
    Object.entries(selectedProfile.value?.stats ?? {}).filter(([, value]) =>
      value.endsWith(" KC"),
    ),
  );

  // real OSRS Wiki icons for skills/Overall/Combat, the wiki's own
  // "<Name>_icon.png" naming is reliable for these (verified: 22/23 skills
  // match directly, "Runecrafting" is the one renamed in-game to
  // "Runecraft"). Boss/activity icons on the same wiki follow no reliable
  // pattern (spot-checked well under half of ~60 names resolve), so those
  // get one shared generic icon instead of a wall of broken images.
  const SKILL_ICON_OVERRIDES: Record<string, string> = {
    Runecrafting: "Runecraft",
    Overall: "Stats",
  };
  function skillIconUrl(label: string): string {
    const name = SKILL_ICON_OVERRIDES[label] ?? label;
    return `https://oldschool.runescape.wiki/images/${encodeURIComponent(name.replace(/ /g, "_"))}_icon.png`;
  }

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

  // --- Checklist (per-game, or per-profile when one account is selected) -----
  const checklistItems = ref<ChecklistItem[]>([]);
  const checklistLoading = ref(false);
  const checklistError = ref<string | null>(null);
  const newChecklistText = ref("");
  const editingItemId = ref<string | null>(null);
  const editingText = ref("");

  const checklistProgress = computed(() => {
    const real = checklistItems.value.filter((i) => !i.is_header);
    return { done: real.filter((i) => i.done).length, total: real.length };
  });

  // groups the flat, already-ordered list into sections at each header row,
  // a header just being another row in the same sort order, not a separate
  // table, keeps "move an item above/below a header" a plain reorder
  interface ChecklistSection {
    header: ChecklistItem | null;
    items: ChecklistItem[];
  }
  const checklistSections = computed<ChecklistSection[]>(() => {
    const sections: ChecklistSection[] = [{ header: null, items: [] }];
    for (const item of checklistItems.value) {
      if (item.is_header) {
        sections.push({ header: item, items: [] });
      } else {
        sections[sections.length - 1].items.push(item);
      }
    }
    return sections.filter((s) => s.header !== null || s.items.length > 0);
  });

  // collapsed section state, per game, remembered across visits
  const collapsedSections = ref<Set<string>>(new Set());
  function collapsedStorageKey(gameId: string) {
    return `checklist-collapsed-${gameId}`;
  }
  function loadCollapsedSections() {
    if (!game.value) return;
    try {
      const raw = localStorage.getItem(collapsedStorageKey(game.value.id));
      collapsedSections.value = new Set(
        raw ? (JSON.parse(raw) as string[]) : [],
      );
    } catch {
      collapsedSections.value = new Set();
    }
  }
  function saveCollapsedSections() {
    if (!game.value) return;
    try {
      localStorage.setItem(
        collapsedStorageKey(game.value.id),
        JSON.stringify([...collapsedSections.value]),
      );
    } catch {
      // best-effort, a checklist with no persisted collapse state just
      // starts fully expanded next time, not worth failing over
    }
  }
  function toggleSectionCollapsed(headerId: string) {
    if (collapsedSections.value.has(headerId))
      collapsedSections.value.delete(headerId);
    else collapsedSections.value.add(headerId);
    collapsedSections.value = new Set(collapsedSections.value);
    saveCollapsedSections();
  }
  function sectionProgress(section: ChecklistSection) {
    return {
      done: section.items.filter((i) => i.done).length,
      total: section.items.length,
    };
  }

  async function loadChecklist() {
    if (!game.value) return;
    checklistLoading.value = true;
    checklistError.value = null;
    loadCollapsedSections();
    try {
      checklistItems.value = await listChecklist(
        game.value.id,
        activeProfileId.value,
      );
    } catch (err) {
      checklistError.value =
        err instanceof Error ? err.message : "Failed to load checklist";
    } finally {
      checklistLoading.value = false;
    }
  }

  async function addChecklistItem() {
    if (!game.value) return;
    const text = newChecklistText.value.trim();
    if (!text) return;
    try {
      const created = await createChecklistItem(
        game.value.id,
        text,
        activeProfileId.value,
      );
      checklistItems.value = [...checklistItems.value, created];
      newChecklistText.value = "";
    } catch (err) {
      checklistError.value =
        err instanceof Error ? err.message : "Failed to add item";
    }
  }

  async function addChecklistSection() {
    if (!game.value) return;
    const name = await prompt({
      title: "New section",
      message: 'Section name (e.g. "Quest cape reqs")',
      confirmLabel: "Add",
    });
    const text = name?.trim();
    if (!text) return;
    createChecklistItem(game.value.id, text, activeProfileId.value, true)
      .then((created) => {
        checklistItems.value = [...checklistItems.value, created];
      })
      .catch((err) => {
        checklistError.value =
          err instanceof Error ? err.message : "Failed to add section";
      });
  }

  async function toggleChecklistItem(item: ChecklistItem) {
    if (!game.value) return;
    const next = !item.done;
    item.done = next;
    try {
      await updateChecklistItem(game.value.id, item.id, { done: next });
    } catch (err) {
      item.done = !next;
      checklistError.value =
        err instanceof Error ? err.message : "Failed to update item";
    }
  }

  function startEditItem(item: ChecklistItem) {
    editingItemId.value = item.id;
    editingText.value = item.text;
  }

  async function commitEditItem(item: ChecklistItem) {
    if (!game.value) return;
    const text = editingText.value.trim();
    editingItemId.value = null;
    if (!text || text === item.text) return;
    item.text = text;
    try {
      await updateChecklistItem(game.value.id, item.id, { text });
    } catch (err) {
      checklistError.value =
        err instanceof Error ? err.message : "Failed to rename item";
    }
  }

  function cancelEditItem() {
    editingItemId.value = null;
  }

  async function moveChecklistItem(item: ChecklistItem, direction: -1 | 1) {
    if (!game.value) return;
    const list = checklistItems.value;
    const index = list.indexOf(item);
    const targetIndex = index + direction;
    if (index === -1 || targetIndex < 0 || targetIndex >= list.length) return;
    const reordered = [...list];
    [reordered[index], reordered[targetIndex]] = [
      reordered[targetIndex],
      reordered[index],
    ];
    checklistItems.value = reordered;
    try {
      await reorderChecklist(
        game.value.id,
        activeProfileId.value,
        reordered.map((i) => i.id),
      );
    } catch (err) {
      checklistError.value =
        err instanceof Error ? err.message : "Failed to reorder checklist";
      await loadChecklist();
    }
  }

  async function removeChecklistItem(item: ChecklistItem) {
    if (!game.value) return;
    try {
      await deleteChecklistItem(game.value.id, item.id);
      checklistItems.value = checklistItems.value.filter(
        (i) => i.id !== item.id,
      );
    } catch (err) {
      checklistError.value =
        err instanceof Error ? err.message : "Failed to delete item";
    }
  }

  // the Accounts tab's sidebar selection, reload that account's checklist
  // and media whenever it changes
  watch(activeProfileId, () => {
    if (activeTab.value !== "Accounts") return;
    void loadChecklist();
    void reloadMediaForCurrentTab();
  });

  async function loadGame(id: string) {
    loading.value = true;
    error.value = null;
    try {
      const fetched = await fetchGame(id);
      // the route can change again while this was in flight (fast
      // click-through on the parent breadcrumb or a variant card), a
      // slower response for the game we've already navigated away from
      // must not overwrite the newer one that may have already loaded
      if (route.params.id !== id) return;
      game.value = fetched;
      if (game.value) {
        try {
          const achievements = await fetchGameAchievements(id);
          if (route.params.id !== id) return;
          game.value.achievements = achievements;
          game.value.achievementTotal = achievements.length;
          game.value.achievementPercent = achievements.length
            ? Math.round(
                (achievements.filter((a) => a.unlockedAt !== null).length /
                  achievements.length) *
                  100,
              )
            : 0;
        } catch {
          // achievements are a nice-to-have overlay, a failure here
          // shouldn't block the rest of the game page from rendering
        }
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

        parentGameTitle.value = null;
        if (game.value.parentGameId) {
          try {
            const parent = await fetchGame(game.value.parentGameId);
            parentGameTitle.value = parent?.title ?? null;
          } catch {
            // breadcrumb just doesn't show a name, not worth failing the page
          }
        }

        variants.value = [];
        try {
          variants.value = await fetchGameVariants(id);
        } catch {
          // variants section just doesn't show, not worth failing the page
        }
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : "Failed to load game";
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
      e.ctrlKey ||
      e.metaKey ||
      e.altKey ||
      document.querySelector("dialog[open]")
    )
      return;
    if (isTypingTarget(e.target)) return;
    if (
      showEditModal.value ||
      showDeleteConfirm.value ||
      showCollectionPicker.value
    )
      return;
    if (!game.value) return;
    if (e.key === "j" || e.key === "k") {
      const nextId = peekAdjacentGameId(game.value.id, e.key === "j" ? 1 : -1);
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

  const showCollectionPicker = ref(false);

  async function onCollectionAdded() {
    await loadGame(route.params.id as string);
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
  watch(() => route.params.id as string, loadGame, { immediate: true });
  watch(
    () => game.value?.id,
    () => {
      if (game.value) {
        void loadNotes();
      }
    },
  );

  const recentActivity = computed(() => game.value?.lastPlayedAt ?? null);

  const tally = computed(() => (game.value ? computeScore(game.value) : null));

  const statsPlaytimeMinutes = computed(() =>
    game.value
      ? game.value.platforms.reduce((sum, p) => sum + p.playtimeMinutes, 0)
      : 0,
  );
  const statsPlaytimeLabel = computed(() => {
    const minutes = statsPlaytimeMinutes.value;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (hours === 0) return `${mins}m`;
    return `${hours}h ${mins}m`;
  });
  const unlockedAchievements = computed(
    () => game.value?.achievements.filter((a) => a.unlockedAt !== null) ?? [],
  );
  const firstUnlockedAt = computed(() => {
    const dates = unlockedAchievements.value
      .map((a) => a.unlockedAt)
      .filter((d): d is string => d !== null);
    return dates.length
      ? dates.reduce((earliest, d) => (d < earliest ? d : earliest))
      : null;
  });
  const lastUnlockedAt = computed(() => {
    const dates = unlockedAchievements.value
      .map((a) => a.unlockedAt)
      .filter((d): d is string => d !== null);
    return dates.length
      ? dates.reduce((latest, d) => (d > latest ? d : latest))
      : null;
  });
  function formatStatsDate(iso: string | null): string {
    if (!iso) return "N/A";
    return formatDisplayDate(iso, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  }

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
    "History",
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
  const visibleTabs = computed(() =>
    tabs.filter(
      (tab) =>
        (tab !== "World Map" || isMinecraftGame.value) &&
        (tab !== "Accounts" || game.value?.profilesEnabled),
    ),
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

  watch(activeTab, (tab) => {
    if (tab === "Screenshots" || tab === "Clips" || tab === "Soundtrack") {
      void loadProfiles();
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

  async function saveMediaItem(
    item: MediaItem,
    tags: string[],
    note: string | null,
    linkedAchievementId: string | null,
    profileId: string | null,
  ) {
    if (!game.value) return;
    try {
      const updated = await updateMediaItem(game.value.id, item.id, {
        tags,
        note,
        linked_achievement_id: linkedAchievementId,
        profile_id: profileId,
      });
      const index = mediaItems.value.findIndex((m) => m.id === item.id);
      if (index !== -1) mediaItems.value[index] = updated;
      // the item may have just moved out of the Accounts tab's currently
      // selected scope (or into it), refetch so the gallery reflects that
      if (
        activeTab.value === "Accounts" &&
        (activeProfileId.value !== null || profileId !== null)
      ) {
        await reloadMediaForCurrentTab();
      }
    } catch (err) {
      mediaError.value = err instanceof Error ? err.message : "Failed to save";
    }
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
    if (tab === "History") {
      void loadFieldChanges();
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
  const FIELD_CHANGE_LABELS: Record<string, string> = {
    developer: "Developer",
    publisher: "Publisher",
    series: "Series",
    tags: "Tags",
    features: "Features",
    description: "Description",
    age_rating: "Age rating",
    release_date: "Release date",
    time_to_beat_hours: "Time to beat",
  };
  function formatFieldChangeDate(iso: string): string {
    return new Date(iso).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
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

  async function removeGameFile(kind: FlatFileKind, file: GameFile) {
    if (!game.value) return;
    try {
      await deleteGameFile(game.value.id, kind, file.filename);
      filesRefFor(kind).value = filesRefFor(kind).value.filter(
        (f) => f !== file,
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
  const expandedSaveId = ref<string | null>(null);
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

  async function onRenameArchive(archive: GameArchiveData, isWorld: boolean) {
    if (!game.value) return;
    const name = await prompt({
      title: "Rename",
      message: "Name",
      defaultValue: archive.name,
      confirmLabel: "Rename",
    });
    if (!name || !name.trim() || name.trim() === archive.name) return;
    try {
      await renameArchive(game.value.id, archive.id, name.trim());
      if (isWorld) await refreshWorldMaps();
      else await refreshSaveArchives();
    } catch (err) {
      filesError.value =
        err instanceof Error ? err.message : "Failed to rename";
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

  function daysUntil(unixSeconds: number): number {
    return Math.max(0, Math.ceil((unixSeconds - Date.now() / 1000) / 86400));
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

  const isPlatinumEarned = computed(
    () =>
      !!game.value &&
      game.value.achievements.length > 0 &&
      game.value.achievements.every((a) => a.unlockedAt !== null),
  );

  const trophyCounts = computed(() => {
    const counts = { bronze: 0, silver: 0, gold: 0 };
    if (!game.value) return counts;
    for (const a of game.value.achievements) {
      if (a.unlockedAt !== null) counts[deriveTier(a)]++;
    }
    return counts;
  });

  return {
    documentReaderUrl,
    formatDisplayDate,
    activePriority,
    priorityLabel,
    worldMapViewUrl,
    worldMapThumbnailUrl,
    confirm,
    router,
    goBackToLibrary,
    game,
    loading,
    error,
    showEditModal,
    deleting,
    deleteError,
    showDeleteConfirm,
    noteNames,
    noteMode,
    viewingNoteName,
    editingNoteName,
    draftName,
    draftContent,
    noteLoading,
    noteSaving,
    noteError,
    hasDraft,
    renderedNoteHtml,
    startNewNote,
    viewNote,
    editFromView,
    backToList,
    saveDraft,
    deleteNote,
    descriptionHtml,
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
    showCollectionPicker,
    onCollectionAdded,
    onDeleteFromModal,
    confirmDelete,
    recentActivity,
    tally,
    statsPlaytimeLabel,
    unlockedAchievements,
    firstUnlockedAt,
    lastUnlockedAt,
    formatStatsDate,
    tabs,
    activeTab,
    visibleTabs,
    panelMode,
    onDropError,
    onPreviewMedia,
    mediaLoading,
    mediaError,
    screenshots,
    clips,
    soundtrackItems,
    lightboxUrl,
    uploadingMedia,
    onMediaFilesSelected,
    removeMedia,
    showMediaTrash,
    activeTabTrash,
    restoreMediaItem,
    saveMediaItem,
    docsFiles,
    modpackFiles,
    filesError,
    uploadingFiles,
    fieldChanges,
    fieldChangesLoading,
    fieldChangesError,
    FIELD_CHANGE_LABELS,
    formatFieldChangeDate,
    onGameFilesSelected,
    removeGameFile,
    docsTrash,
    modpackTrash,
    showDocsTrash,
    showModpackTrash,
    restoreFileItem,
    formatFileSize,
    formatArchiveDate,
    saveArchives,
    saveArchivesLoaded,
    expandedSaveId,
    saveUploading,
    onNewSaveSelected,
    onAddSaveVersion,
    onRenameArchive,
    onDeleteArchive,
    saveTrash,
    worldTrash,
    showSaveTrash,
    showWorldTrash,
    daysUntil,
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
    displayFileName,
    sortedAchievements,
    deriveTier,
    isPlatinumEarned,
    trophyCounts,
    formatUnlockedAt,
    formatPlaytime,
  };
}
