<script setup lang="ts">
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
  updateArchive,
  deleteArchive,
  deleteArchiveVersion,
  fetchWorldMaps,
  renderWorldMap,
  worldMapViewUrl,
  worldMapThumbnailUrl,
  fetchArchiveTrash,
  restoreArchive,
} from "../services/gameArchives";
import type {
  GameArchiveData,
  ArchiveVersion,
  WorldMapEntry,
  TrashedArchive,
} from "../services/gameArchives";
import DuplicateNotice from "../components/DuplicateNotice.vue";
import UploadDropzone from "../components/UploadDropzone.vue";
import SkeletonBlock from "../components/SkeletonBlock.vue";
import MediaTile from "../components/MediaTile.vue";
import GameMediaPanel from "../components/GameMediaPanel.vue";
import { isGuess, unlockSeconds } from "../utils/mediaDate";
import { normalizePlatformFamily } from "../utils/platforms";
import { frameFromSource } from "../utils/videoThumbnail";
import GameArchivesPanel from "../components/GameArchivesPanel.vue";
import ArchiveCard from "../components/ArchiveCard.vue";
import ArchiveEditDialog from "../components/ArchiveEditDialog.vue";
import GameNotesPanel from "../components/GameNotesPanel.vue";
import { preferences, preferencesLoaded } from "../state/preferences";
import { OPTIONAL_TABS, resolvePage, planTabs } from "../utils/gamePage";
import type { OptionalTab } from "../utils/gamePage";
import type { ContentCounts } from "../utils/gamePage";
import GameStatsPanel from "../components/GameStatsPanel.vue";
import {
  startTask,
  updateTask,
  completeTask,
  errorTask,
  addFeedItem,
  setTaskRetry,
} from "../state/taskProgress";
import type { Achievement, Game, GameStatus } from "../types/game";
import GameFormModal from "../components/GameFormModal.vue";
import GameRatingPicker from "../components/GameRatingPicker.vue";
import GameCollectionsButton from "../components/GameCollectionsButton.vue";
import BackButton from "../components/BackButton.vue";
import GameTopBar from "../components/GameTopBar.vue";
import HeartIcon from "../components/HeartIcon.vue";
import SegmentedTabs from "../components/SegmentedTabs.vue";
import type { SegmentOption } from "../components/SegmentedTabs.vue";
import {
  isUnlocked,
  formatPercent,
  unlockedOn,
  KIND_LABEL,
} from "../utils/achievements";
import {
  loadAchievementLocal,
  saveAchievementLocal,
} from "../state/achievementLocal";
import type { AchievementLocal } from "../state/achievementLocal";
import { computeScore } from "../utils/scoring";
import DOMPurify from "dompurify";
import { useConfirm, usePrompt } from "../state/dialog";

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
    const updated = await renameGameProfile(game.value.id, profile.id, trimmed);
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
    collapsedSections.value = new Set(raw ? (JSON.parse(raw) as string[]) : []);
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
    checklistItems.value = checklistItems.value.filter((i) => i.id !== item.id);
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
          (achievements.filter(isUnlocked).length / achievements.length) * 100,
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
  if (isTypingTarget(e.target)) return;
  if (showEditModal.value || showDeleteConfirm.value) return;
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
      [filter]: filter === "platform" ? normalizePlatformFamily(value) : value,
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
const moreTabs = computed(() => tabPlan.value.more as (typeof tabs)[number][]);
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
    (activeTab.value === "Accounts" && accountMediaKind.value === "screenshot")
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
const clips = computed(() => mediaItems.value.filter((m) => m.kind === "clip"));
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
    if (!game.value || mediaLoadedFor.value !== game.value.id) void loadMedia();
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
          updateTask(taskId, Math.round(fraction * 100), undefined, speedLabel),
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
    applyClip(await saveClipThumbnail(game.value.id, item.id, blob, duration));
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
    mediaError.value = err instanceof Error ? err.message : "Failed to delete";
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
    mediaError.value = err instanceof Error ? err.message : "Failed to restore";
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
    if (game.value && mediaLoadedFor.value !== game.value.id) void loadMedia();
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
          updateTask(taskId, Math.round(fraction * 100), undefined, speedLabel),
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
    const updated = await updateGameFile(game.value.id, kind, file.id, changes);
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
    filesError.value = err instanceof Error ? err.message : "Failed to delete";
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
    fileTrashRefFor(kind).value = await fetchGameFileTrash(game.value.id, kind);
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
    filesError.value = err instanceof Error ? err.message : "Failed to restore";
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
      await createArchive(gameId, "save", trimmedName, file, (f, speedLabel) =>
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

async function bulkDeleteArchives(items: GameArchiveData[], isWorld: boolean) {
  if (!game.value || !items.length) return;
  const ok = await confirm({
    title: "Move to trash",
    message: `Move ${items.length} ${isWorld ? "world" : "save"}${items.length === 1 ? "" : "s"} to trash? ${items.length === 1 ? "It stays" : "They stay"} recoverable for 7 days, then ${items.length === 1 ? "is" : "are"} purged for good.`,
    confirmLabel: "Move to trash",
    danger: true,
  });
  if (!ok) return;
  try {
    for (const archive of items) await deleteArchive(game.value.id, archive.id);
    if (isWorld) {
      await refreshWorldMaps();
      await refreshWorldTrash();
    } else {
      await refreshSaveArchives();
      await refreshSaveTrash();
    }
  } catch (err) {
    filesError.value = err instanceof Error ? err.message : "Failed to delete";
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
    filesError.value = err instanceof Error ? err.message : "Failed to delete";
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
    filesError.value = err instanceof Error ? err.message : "Failed to restore";
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

// --- World Map (BlueMap render of a world_save archive) --------------------
// a game (e.g. a modpack) can have several worlds, one card, many worlds,
// each named, versioned, rendered, and viewed independently
const worldMaps = ref<WorldMapEntry[]>([]);
const worldMapsLoaded = ref(false);
const worldMapStarting = ref<Set<string>>(new Set());
const activeMapArchiveId = ref<string | null>(null);
let worldMapPollTimer: ReturnType<typeof setInterval> | null = null;

function stopWorldMapPolling() {
  if (worldMapPollTimer) {
    clearInterval(worldMapPollTimer);
    worldMapPollTimer = null;
  }
}

async function refreshWorldMaps() {
  if (!game.value) return;
  try {
    worldMaps.value = await fetchWorldMaps(game.value.id);
    worldMapsLoaded.value = true;
    const anyRendering = worldMaps.value.some((w) => w.status === "rendering");
    if (anyRendering && !worldMapPollTimer) {
      // no push mechanism for a background render, poll every few
      // seconds only while at least one world is actually in flight
      worldMapPollTimer = setInterval(refreshWorldMaps, 4000);
    } else if (!anyRendering) {
      stopWorldMapPolling();
    }
  } catch {
    // list just doesn't update this tick, not worth surfacing an error
    // for a polling request
  }
}

async function onNewWorldSelected(files: File[]) {
  const file = files[0];
  if (!file || !game.value) return;
  const gameId = game.value.id;
  const name = await prompt({
    title: "Name this world",
    message: "World name",
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
        "world_save",
        trimmedName,
        file,
        (f, speedLabel) =>
          updateTask(taskId, Math.round(f * 100), undefined, speedLabel),
      );
      completeTask(taskId, "Saved");
      await refreshWorldMaps();
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

async function onAddWorldVersion(archive: GameArchiveData, files: File[]) {
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
      completeTask(taskId, "Saved: render again to update the map");
      await refreshWorldMaps();
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

async function startWorldMapRender(archiveId: string) {
  if (!game.value) return;
  worldMapStarting.value = new Set(worldMapStarting.value).add(archiveId);
  filesError.value = null;
  try {
    await renderWorldMap(game.value.id, archiveId);
    await refreshWorldMaps();
  } catch (err) {
    filesError.value =
      err instanceof Error ? err.message : "Failed to start render";
  } finally {
    const next = new Set(worldMapStarting.value);
    next.delete(archiveId);
    worldMapStarting.value = next;
  }
}

function viewWorldMap(archiveId: string) {
  activeMapArchiveId.value = archiveId;
}

onUnmounted(stopWorldMapPolling);

// ---- achievements tab ----
// A hidden achievement's description isn't something the services publish
// until it's unlocked, so say that instead of leaving a blank.
function descriptionOf(a: Achievement): string {
  if (a.description) return a.description;
  if (a.hidden) {
    return isUnlocked(a)
      ? "No description is available for this hidden achievement."
      : "This one is hidden, so its description isn't available until you unlock it.";
  }
  return "";
}
type AchFilter = "all" | "unlocked" | "locked" | "hidden" | "pinned";
type AchSortKey = "unlocked" | "rarity" | "name";
const achFilter = ref<AchFilter>("all");
const achSortKey = ref<AchSortKey>("unlocked");
const achSortDir = ref<"asc" | "desc">("desc");
const achProvider = ref("all");
const achSearch = ref("");
const achLocal = ref<AchievementLocal>({ pins: [], notes: {}, overall: "" });
const revealedIds = ref<Set<string>>(new Set());
const noteOpen = ref<string | null>(null);
const noteDraft = ref("");
const overallOpen = ref(false);
const overallDraft = ref("");

watch(
  () => game.value?.id,
  (id) => {
    achLocal.value = id
      ? loadAchievementLocal(id)
      : { pins: [], notes: {}, overall: "" };
    revealedIds.value = new Set();
    achProvider.value = "all";
    noteOpen.value = null;
    overallOpen.value = false;
  },
  { immediate: true },
);

function persistAch() {
  if (game.value) saveAchievementLocal(game.value.id, achLocal.value);
}
const isPinned = (a: Achievement) => achLocal.value.pins.includes(a.id);
function togglePin(a: Achievement) {
  const pins = achLocal.value.pins;
  achLocal.value = {
    ...achLocal.value,
    pins: isPinned(a) ? pins.filter((id) => id !== a.id) : [...pins, a.id],
  };
  persistAch();
}
// a hidden achievement stays hidden until it's unlocked or you reveal it
const isHiddenLocked = (a: Achievement) =>
  !!a.hidden && !isUnlocked(a) && !revealedIds.value.has(a.id);
function revealAchievement(a: Achievement) {
  revealedIds.value = new Set(revealedIds.value).add(a.id);
}
function hideAchievement(a: Achievement) {
  const next = new Set(revealedIds.value);
  next.delete(a.id);
  revealedIds.value = next;
}
function toggleNote(a: Achievement) {
  if (noteOpen.value === a.id) {
    noteOpen.value = null;
    return;
  }
  noteOpen.value = a.id;
  noteDraft.value = achLocal.value.notes[a.id] ?? "";
}
function saveNote(a: Achievement) {
  const text = noteDraft.value.trim();
  const notes = { ...achLocal.value.notes };
  if (text) notes[a.id] = text;
  else delete notes[a.id];
  achLocal.value = { ...achLocal.value, notes };
  persistAch();
  noteOpen.value = null;
}
function clearNote(a: Achievement) {
  noteDraft.value = "";
  saveNote(a);
}
function toggleOverall() {
  overallOpen.value = !overallOpen.value;
  if (overallOpen.value) overallDraft.value = achLocal.value.overall;
}
function saveOverall() {
  achLocal.value = { ...achLocal.value, overall: overallDraft.value.trim() };
  persistAch();
  overallOpen.value = false;
}

const unlockedCount = computed(
  () => game.value?.achievements.filter(isUnlocked).length ?? 0,
);
const achFilterOptions = computed<SegmentOption[]>(() => {
  const list = game.value?.achievements ?? [];
  return [
    { value: "all", label: "All", count: list.length },
    { value: "unlocked", label: "Unlocked", count: unlockedCount.value },
    {
      value: "locked",
      label: "Locked",
      count: list.length - unlockedCount.value,
    },
    {
      value: "hidden",
      label: "Hidden",
      count: list.filter((a) => a.hidden && !isUnlocked(a)).length,
    },
    { value: "pinned", label: "Pinned", count: list.filter(isPinned).length },
  ];
});

// Clicking a column header sorts by it; clicking it again flips the order.
// A new column starts the way people usually want it: newest unlocks first,
// rarest first, A to Z.
function sortBy(key: AchSortKey) {
  if (achSortKey.value === key) {
    achSortDir.value = achSortDir.value === "asc" ? "desc" : "asc";
  } else {
    achSortKey.value = key;
    achSortDir.value = key === "unlocked" ? "desc" : "asc";
  }
}
const sortMark = (key: AchSortKey) =>
  achSortKey.value === key ? (achSortDir.value === "asc" ? "▲" : "▼") : "";
const ariaSort = (key: AchSortKey) =>
  achSortKey.value === key
    ? achSortDir.value === "asc"
      ? "ascending"
      : "descending"
    : "none";
// the same four orders as one dropdown, for screens too narrow for headers
const MOBILE_SORTS: Record<string, [AchSortKey, "asc" | "desc"]> = {
  recent: ["unlocked", "desc"],
  rarest: ["rarity", "asc"],
  easiest: ["rarity", "desc"],
  name: ["name", "asc"],
};
const mobileSort = computed({
  get: () =>
    Object.entries(MOBILE_SORTS).find(
      ([, [k, d]]) => k === achSortKey.value && d === achSortDir.value,
    )?.[0] ?? "",
  set: (v: string) => {
    const pick = MOBILE_SORTS[v];
    if (pick) [achSortKey.value, achSortDir.value] = pick;
  },
});

// unlocked ones come before locked ones, then by when (newest or oldest first)
function byUnlocked(a: Achievement, b: Achievement, dir: number): number {
  const ua = isUnlocked(a);
  const ub = isUnlocked(b);
  if (ua !== ub) return ua ? -1 : 1;
  if (!ua) return 0;
  if (a.unlockedAt && b.unlockedAt)
    return dir * a.unlockedAt.localeCompare(b.unlockedAt);
  if (a.unlockedAt) return -1;
  if (b.unlockedAt) return 1;
  return 0;
}
// no percent known sorts last either way round
function byRarity(a: Achievement, b: Achievement, dir: number): number {
  const pa = a.rarityPercent ?? null;
  const pb = b.rarityPercent ?? null;
  if (pa === null && pb === null) return 0;
  if (pa === null) return 1;
  if (pb === null) return -1;
  return dir * (pa - pb);
}

// the platforms its achievements come from, for the filter that only shows
// when a game has achievements from more than one
const achProviders = computed(() => [
  ...new Set(
    (game.value?.achievements ?? [])
      .map((a) => a.provider)
      .filter((x): x is string => !!x),
  ),
]);

const shownAchievements = computed(() => {
  const q = achSearch.value.trim().toLowerCase();
  const list = (game.value?.achievements ?? []).filter((a) => {
    const unlocked = isUnlocked(a);
    if (achProvider.value !== "all" && a.provider !== achProvider.value)
      return false;
    if (achFilter.value === "unlocked" && !unlocked) return false;
    if (achFilter.value === "locked" && unlocked) return false;
    if (achFilter.value === "hidden" && !(a.hidden && !unlocked)) return false;
    if (achFilter.value === "pinned" && !isPinned(a)) return false;
    if (q) {
      // a hidden achievement's text isn't searchable, so a search can't spoil it
      if (isHiddenLocked(a)) return false;
      return (
        a.name.toLowerCase().includes(q) ||
        (a.description ?? "").toLowerCase().includes(q)
      );
    }
    return true;
  });
  const dir = achSortDir.value === "asc" ? 1 : -1;
  const compare = (a: Achievement, b: Achievement) => {
    if (achSortKey.value === "rarity") return byRarity(a, b, dir);
    if (achSortKey.value === "name") {
      // a hidden one sorts under its placeholder, so its place can't give it away
      const label = (x: Achievement) =>
        isHiddenLocked(x) ? "Hidden achievement" : x.name;
      return dir * label(a).localeCompare(label(b));
    }
    return byUnlocked(a, b, dir);
  };
  // pinned always float to the top, whatever the sort
  return [...list].sort(
    (a, b) => Number(isPinned(b)) - Number(isPinned(a)) || compare(a, b),
  );
});

// A few figures about your own progress, each only when there is real data
// behind it: nothing here is estimated.
const achStats = computed(() => {
  const list = game.value?.achievements ?? [];
  const done = list.filter(isUnlocked);
  const stats: { label: string; value: string }[] = [];
  if (list.length)
    stats.push({
      label: "complete",
      value: `${Math.round((done.length / list.length) * 100)}%`,
    });
  const percents = done
    .map((a) => a.rarityPercent)
    .filter((p): p is number => typeof p === "number");
  if (percents.length)
    stats.push({
      label: "rarest unlock",
      value: formatPercent(Math.min(...percents)),
    });
  const times = done.map((a) => a.unlockedAt).filter((t): t is string => !!t);
  if (times.length) {
    const last = times.reduce((m, t) => (t > m ? t : m));
    stats.push({
      label: "last unlock",
      value: new Date(last).toLocaleDateString(),
    });
    const weekAgo = Date.now() - 7 * 86_400_000;
    const week = times.filter((t) => new Date(t).getTime() >= weekAgo).length;
    if (week) stats.push({ label: "in the past 7 days", value: String(week) });
  }
  return stats;
});

function formatPlaytime(minutes: number) {
  if (minutes === 0) return "Not played yet";
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
}

// Last, so everything the first load touches has been set up by now.
void loadGame(route.params.id as string);
</script>

<template>
  <main v-if="loading" class="detail loading-state" aria-busy="true">
    <GameTopBar active="games" />
    <!-- the shape of the real page: hero with poster, title, badges and
         buttons, then the tabs, then the first block of content -->
    <section class="hero">
      <div class="hero-overlay"></div>
      <div class="hero-content">
        <SkeletonBlock width="212px" height="307px" radius="8px" />
        <div class="hero-text detail-skeleton-text">
          <SkeletonBlock width="30%" height="12px" />
          <SkeletonBlock width="60%" height="40px" />
          <div class="detail-skeleton-row">
            <SkeletonBlock
              v-for="w in [64, 96, 80, 72]"
              :key="w"
              :width="`${w}px`"
              height="24px"
              radius="999px"
            />
          </div>
          <div class="detail-skeleton-row">
            <SkeletonBlock width="88px" height="36px" radius="8px" />
            <SkeletonBlock width="36px" height="36px" radius="8px" />
            <SkeletonBlock width="36px" height="36px" radius="8px" />
          </div>
        </div>
      </div>
    </section>
    <div class="tabbar-wrap">
      <SkeletonBlock width="470px" height="44px" radius="10px" />
    </div>
    <div class="detail-skeleton-body">
      <div class="detail-skeleton-row">
        <SkeletonBlock
          v-for="i in 4"
          :key="i"
          width="120px"
          height="44px"
          radius="8px"
        />
      </div>
      <SkeletonBlock height="14px" />
      <SkeletonBlock height="14px" width="92%" />
      <SkeletonBlock height="14px" width="70%" />
    </div>
  </main>

  <main v-else-if="error" class="detail error-state">
    <GameTopBar active="games" />
    <p>{{ error }}</p>
  </main>

  <main v-else-if="game" class="detail">
    <GameTopBar active="games" />

    <BackButton class="back-spot" @click="goBackToLibrary" />

    <GameFormModal
      v-if="showEditModal"
      :game="game"
      @close="showEditModal = false"
      @saved="onGameSaved"
      @delete="onDeleteFromModal"
    />

    <ArchiveEditDialog
      v-if="editingArchive && editingArchiveLive"
      :archive="editingArchiveLive"
      :noun="editingArchive.isWorld ? 'world' : 'save'"
      :uploading="saveUploading.has(editingArchive.id)"
      @close="editingArchive = null"
      @save="
        (a, patch) => saveArchiveDetails(a, editingArchive!.isWorld, patch)
      "
      @delete="onDeleteArchive($event, editingArchive!.isWorld)"
      @add-version="
        (a, files) =>
          editingArchive!.isWorld
            ? onAddWorldVersion(a, files)
            : onAddSaveVersion(a, files)
      "
      @delete-version="(a, v) => onDeleteVersion(a, v, editingArchive!.isWorld)"
    />

    <div
      v-if="showDeleteConfirm"
      class="confirm-backdrop"
      @click.self="showDeleteConfirm = false"
    >
      <div class="confirm-dialog">
        <h3>Delete {{ game.title }}?</h3>
        <p>This can't be undone.</p>
        <div v-if="deleteError" class="confirm-error">{{ deleteError }}</div>
        <div class="confirm-actions">
          <button
            type="button"
            class="secondary-button"
            @click="showDeleteConfirm = false"
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

    <section class="hero">
      <DuplicateNotice v-if="game" class="hero-notice" :game-id="game.id" />
      <div
        class="hero-backdrop"
        :style="{
          backgroundImage: `url(${sizedAssetUrl(game.bannerImageUrl, HERO_WIDTH)})`,
        }"
      ></div>
      <div class="hero-overlay"></div>
      <div class="hero-content">
        <div
          class="poster-card"
          :style="
            game.coverImageUrl
              ? {
                  backgroundImage: `url(${sizedAssetUrl(game.coverImageUrl, POSTER_WIDTH)})`,
                }
              : {}
          "
        >
          <span v-if="!game.coverImageUrl">{{ game.title }}</span>
        </div>
        <div class="hero-text">
          <router-link
            v-if="game.parentGameId"
            :to="`/games/${game.parentGameId}`"
            class="parent-breadcrumb"
          >
            {{ parentGameTitle ?? "…" }}
            <span v-if="game.relationshipType" class="relationship-tag">{{
              RELATIONSHIP_LABELS[game.relationshipType] ??
              game.relationshipType
            }}</span>
            →
          </router-link>
          <div
            v-if="heroCredits.length && !pageSettings.hide_credits"
            class="native-title"
          >
            <template v-for="(name, i) in heroCredits" :key="name">
              <span v-if="i" class="credit-dot"> · </span>
              <router-link
                class="filter-link"
                :to="libraryLink('company', name)"
                :title="`All games by ${name}`"
                >{{ name }}</router-link
              >
            </template>
          </div>
          <h1 class="title">{{ game.title }}</h1>
          <div class="badge-row">
            <select
              :value="game.status"
              class="badge status status-select"
              title="Change status"
              @change="
                changeStatus(
                  ($event.target as HTMLSelectElement).value as GameStatus,
                )
              "
            >
              <option v-for="s in STATUS_OPTIONS" :key="s" :value="s">
                {{ s }}
              </option>
            </select>
            <GameRatingPicker
              v-if="!pageSettings.hide_rating"
              :model-value="{
                ratingOverall: game.ratingOverall,
                ratingStory: game.ratingStory,
                ratingGameplay: game.ratingGameplay,
                ratingSound: game.ratingSound,
              }"
              @change="onRatingsChange"
            />
            <span
              v-if="game.dateAdded && !pageSettings.hide_date_badge"
              class="badge"
            >
              {{ new Date(game.dateAdded).toLocaleDateString() }}
            </span>
            <router-link
              v-if="game.platforms.length && !pageSettings.hide_platform_badge"
              class="badge filter-badge"
              :to="libraryLink('platform', game.platforms[0].platform)"
              :title="`All ${normalizePlatformFamily(game.platforms[0].platform)} games`"
              >{{ game.platforms[0].platform }}</router-link
            >
            <button
              v-if="game.achievementTotal > 0 && achievementsOn"
              type="button"
              class="badge achievement-progress-badge"
              title="Jump to Achievements"
              @click="activeTab = 'Achievements'"
            >
              <svg
                viewBox="0 0 24 24"
                width="13"
                height="13"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d="M8 4h8v5a4 4 0 0 1-8 0z" />
                <path d="M8 4H5a2 2 0 0 0 0 4h1.5M16 4h3a2 2 0 0 1 0 4h-1.5" />
                <path d="M12 13v3" />
                <path d="M9 20h6" />
                <path d="M10 16.5h4l.8 3.5H9.2z" />
              </svg>
              {{ game.achievementPercent }}%
            </button>
            <span
              v-if="game.staleSince"
              class="badge stale-badge"
              :title="`Last sync (${new Date(game.staleSince).toLocaleDateString()}) no longer saw this in your ${game.source} library.`"
            >
              Not currently in your {{ game.source }} library
            </span>
          </div>
          <div class="action-row">
            <button
              class="edit-btn"
              type="button"
              @click="showEditModal = true"
            >
              ✎ Edit
            </button>
            <button
              v-if="!pageSettings.hide_favorite"
              class="icon-btn"
              :class="{ active: game.favorite }"
              type="button"
              :title="
                game.favorite ? 'Remove from favorites' : 'Add to favorites'
              "
              @click="toggleFavorite"
            >
              <HeartIcon :filled="game.favorite" />
            </button>
            <GameCollectionsButton
              v-if="!pageSettings.hide_collections"
              :game="game"
              @changed="onCollectionsChanged"
            />
          </div>
        </div>
      </div>
    </section>

    <div class="tabbar-wrap">
      <nav class="tabbar">
        <button
          v-for="tab in visibleTabs"
          :key="tab"
          type="button"
          class="tab-btn"
          :class="{ active: activeTab === tab }"
          @click="activeTab = tab"
        >
          {{ tab }}
        </button>
        <div v-if="moreTabs.length" class="tab-more">
          <button
            type="button"
            class="tab-btn tab-more-btn"
            title="Tabs with nothing in them yet"
            aria-haspopup="menu"
            :aria-expanded="showMoreTabs"
            @click.stop="showMoreTabs = !showMoreTabs"
          >
            +
          </button>
          <ul v-if="showMoreTabs" class="tab-more-menu" role="menu">
            <li v-for="tab in moreTabs" :key="tab">
              <button type="button" role="menuitem" @click="openMoreTab(tab)">
                {{ tab }}
              </button>
            </li>
          </ul>
        </div>
      </nav>
    </div>

    <section v-if="activeTab === 'Overview'" class="overview">
      <div v-if="overviewFacts.length" class="meta-block">
        <div v-if="overviewFacts.length" class="meta-grid">
          <div
            v-for="fact in overviewFacts"
            :key="fact.label"
            class="meta-item"
          >
            <span class="meta-label">{{ fact.label }}</span>
            <button
              v-if="fact.tab"
              type="button"
              class="meta-value meta-link"
              :class="{ accent: fact.accent, muted: fact.muted }"
              :title="`Open ${fact.tab}`"
              @click="activeTab = fact.tab"
            >
              {{ fact.value }}
            </button>
            <span
              v-else
              class="meta-value"
              :class="{ accent: fact.accent, muted: fact.muted }"
              >{{ fact.value }}</span
            >
          </div>
        </div>
      </div>

      <div v-if="mainTags.length" class="chip-row">
        <router-link
          v-for="tag in mainTags"
          :key="tag"
          class="chip primary chip-link"
          :to="libraryLink('tag', tag)"
          :title="`All ${tag} games`"
          >{{ tag }}</router-link
        >
      </div>

      <div v-if="descriptionHtml" class="description-block">
        <div
          class="description description-html"
          :class="{ clamped: descriptionOverflows && !descriptionExpanded }"
          v-html="descriptionHtml"
        ></div>
        <button
          v-if="descriptionOverflows"
          type="button"
          class="read-more-btn"
          @click="descriptionExpanded = !descriptionExpanded"
        >
          {{ descriptionExpanded ? "Show less" : "Read more" }}
        </button>
      </div>

      <section
        class="my-note"
        :class="{ empty: !game.resumeNote && !resumeNoteEditing }"
      >
        <template v-if="resumeNoteEditing">
          <header class="note-head">
            <h3>Where I left off</h3>
          </header>
          <textarea
            v-model="resumeNoteDraft"
            class="note-input"
            rows="3"
            placeholder="e.g. Just beat the third boss, about to start the desert region…"
            aria-label="Where I left off"
          ></textarea>
          <p v-if="resumeNoteError" class="note-error">
            {{ resumeNoteError }}
          </p>
          <div class="note-actions">
            <button
              type="button"
              class="btn-solid"
              :disabled="resumeNoteSaving"
              @click="saveResumeNote"
            >
              {{ resumeNoteSaving ? "Saving…" : "Save" }}
            </button>
            <button
              type="button"
              class="btn-text muted"
              @click="resumeNoteEditing = false"
            >
              Cancel
            </button>
          </div>
        </template>
        <template v-else-if="game.resumeNote">
          <header class="note-head">
            <h3>Where I left off</h3>
            <span class="note-private">Only you can see this</span>
            <button type="button" class="btn-text" @click="startEditResumeNote">
              Edit
            </button>
          </header>
          <p class="note-text">{{ game.resumeNote }}</p>
        </template>
        <template v-else>
          <button type="button" class="btn-text" @click="startEditResumeNote">
            + Add a note on where you left off
          </button>
          <span class="note-private">Only you can see this</span>
        </template>
      </section>

      <div v-if="variants.length" class="related-section">
        <div class="section-heading">
          <h2>Variants</h2>
        </div>
        <div class="poster-grid">
          <router-link
            v-for="variant in variants"
            :key="variant.id"
            :to="`/games/${variant.id}`"
            class="poster-card-sm"
          >
            <div
              class="poster-card-sm-art"
              :style="
                variant.coverImageUrl
                  ? {
                      backgroundImage: `url(${sizedAssetUrl(variant.coverImageUrl, POSTER_WIDTH)})`,
                    }
                  : {}
              "
            ></div>
            <div class="poster-card-sm-title">{{ variant.title }}</div>
            <div v-if="variant.relationshipType" class="poster-card-sm-meta">
              {{
                RELATIONSHIP_LABELS[variant.relationshipType] ??
                variant.relationshipType
              }}
            </div>
          </router-link>
        </div>
      </div>

      <div v-if="similarGames.length" class="related-section">
        <div class="section-heading">
          <h2>Similar games in your library</h2>
        </div>
        <div class="poster-grid">
          <router-link
            v-for="g in similarGames"
            :key="g.id"
            :to="`/games/${g.id}`"
            class="poster-card-sm"
          >
            <div
              class="poster-card-sm-art"
              :style="
                g.coverImageUrl
                  ? {
                      backgroundImage: `url(${sizedAssetUrl(g.coverImageUrl, POSTER_WIDTH)})`,
                    }
                  : {}
              "
            ></div>
            <div class="poster-card-sm-title">{{ g.title }}</div>
          </router-link>
        </div>
      </div>

      <details class="more-details">
        <summary>More details</summary>

        <div v-if="game.platforms.length" class="more-block">
          <h3 class="more-title">Platforms</h3>
          <ul class="platform-list">
            <li
              v-for="p in game.platforms"
              :key="p.platform"
              class="platform-item"
            >
              <div class="platform-top">
                <span class="platform-name">{{ p.platform }}</span>
                <span class="platform-hours">{{
                  formatPlaytime(p.playtimeMinutes)
                }}</span>
              </div>
              <div
                v-if="p.completionPercent !== null || p.lastPlayedAt"
                class="platform-sub"
              >
                <span v-if="p.completionPercent !== null"
                  >{{ p.completionPercent }}% complete</span
                >
                <span v-if="p.lastPlayedAt"
                  >last played
                  {{ new Date(p.lastPlayedAt).toLocaleDateString() }}</span
                >
              </div>
            </li>
          </ul>
          <button
            type="button"
            class="read-more-btn"
            :disabled="loggingPlaytime"
            title="Log a session just played, without editing the total by hand"
            @click="logPlaytime(30)"
          >
            + Log 30 min just played
          </button>
        </div>

        <div v-if="ratingParts.length" class="more-block">
          <h3 class="more-title">Your ratings</h3>
          <div class="kv-grid">
            <div v-for="part in ratingParts" :key="part.name" class="kv-row">
              <span class="kv-label">{{ part.name }}</span>
              <span class="kv-value accent">{{ part.value }}</span>
            </div>
          </div>
        </div>

        <div v-if="moreTags.length || game.features.length" class="more-block">
          <h3 class="more-title">Tags and features</h3>
          <div class="chip-row">
            <router-link
              v-for="tag in moreTags"
              :key="tag"
              class="chip chip-link"
              :to="libraryLink('tag', tag)"
              :title="`All ${tag} games`"
              >{{ tag }}</router-link
            >
            <span v-for="f in game.features" :key="f" class="chip">{{
              f
            }}</span>
          </div>
        </div>

        <div class="more-block">
          <h3 class="more-title">Library</h3>
          <div class="kv-grid">
            <div v-if="game.series" class="kv-row">
              <span class="kv-label">Series</span>
              <router-link
                class="kv-value filter-link"
                :to="libraryLink('series', game.series)"
                :title="`All games in ${game.series}`"
                >{{ game.series }}</router-link
              >
            </div>
            <div v-if="game.dateAdded" class="kv-row">
              <span class="kv-label">Added</span>
              <span class="kv-value">{{
                new Date(game.dateAdded).toLocaleDateString()
              }}</span>
            </div>
            <div v-if="recentActivity" class="kv-row">
              <span class="kv-label">Last played</span>
              <span class="kv-value">{{
                new Date(recentActivity).toLocaleDateString()
              }}</span>
            </div>
            <div v-if="game.source" class="kv-row">
              <span class="kv-label">Source</span>
              <span class="kv-value">{{ game.source }}</span>
            </div>
            <div v-if="activePriority(game) !== null" class="kv-row">
              <span class="kv-label">Priority</span>
              <span class="kv-value">{{
                priorityLabel(activePriority(game)!)
              }}</span>
            </div>
            <div v-if="game.ageRating" class="kv-row">
              <span class="kv-label">Age rating</span>
              <span class="kv-value">{{ game.ageRating }}</span>
            </div>
            <div v-if="game.region" class="kv-row">
              <span class="kv-label">Region</span>
              <span class="kv-value">{{ game.region }}</span>
            </div>
            <div v-if="game.language" class="kv-row">
              <span class="kv-label">Language</span>
              <span class="kv-value">{{ game.language }}</span>
            </div>
            <div v-if="game.achievementsProvider" class="kv-row">
              <span class="kv-label">Achievements via</span>
              <span class="kv-value">{{
                game.achievementsProvider === "retroachievements"
                  ? "RetroAchievements"
                  : "Native"
              }}</span>
            </div>
            <div
              v-if="
                game.ownership.format ||
                game.ownership.purchaseDate ||
                game.ownership.price !== null
              "
              class="kv-row stack"
            >
              <span class="kv-label">Ownership</span>
              <span class="kv-value ownership-info">
                <span v-if="game.ownership.format" class="ownership-format">{{
                  game.ownership.format
                }}</span>
                <span v-if="game.ownership.purchaseDate">
                  Purchased
                  {{ formatDisplayDate(game.ownership.purchaseDate) }}
                </span>
                <span v-if="game.ownership.price !== null">
                  {{ game.ownership.priceCurrency ?? "USD" }}
                  {{ game.ownership.price.toFixed(2) }}
                </span>
                <span v-if="game.ownership.condition">{{
                  game.ownership.condition
                }}</span>
              </span>
            </div>
            <div v-if="game.links.length" class="kv-row stack">
              <span class="kv-label">Links</span>
              <ul class="links-list">
                <li v-for="link in game.links" :key="link.url">
                  <a
                    :href="link.url"
                    target="_blank"
                    rel="noopener noreferrer"
                    >{{ link.label }}</a
                  >
                </li>
              </ul>
            </div>
            <div v-if="game.folderLocation" class="kv-row stack">
              <span class="kv-label">Folder</span>
              <span class="kv-value folder-value">{{
                game.folderLocation
              }}</span>
            </div>
          </div>
        </div>
      </details>
    </section>

    <section v-else-if="activeTab === 'Achievements'" class="achievements">
      <div class="ach-head">
        <h2 class="ach-title">Achievements</h2>
        <span class="ach-count"
          >{{ unlockedCount }} / {{ game.achievements.length }}</span
        >
        <div class="ach-tools">
          <input
            v-model="achSearch"
            type="text"
            class="ui-field ach-search"
            placeholder="Search achievements…"
            aria-label="Search achievements"
          />
          <select
            v-if="achProviders.length > 1"
            v-model="achProvider"
            class="ui-field ach-sort"
            aria-label="Filter by platform"
          >
            <option value="all">All platforms</option>
            <option v-for="pr in achProviders" :key="pr" :value="pr">
              {{ pr }}
            </option>
          </select>
          <select
            v-model="mobileSort"
            class="ui-field ach-sort ach-mobile-sort"
            aria-label="Sort achievements"
          >
            <option value="recent">Recently unlocked</option>
            <option value="rarest">Rarest first</option>
            <option value="easiest">Easiest first</option>
            <option value="name">A to Z</option>
          </select>
          <button
            type="button"
            class="ui-btn ui-btn-secondary ui-btn-sm"
            :class="{ on: overallOpen || !!achLocal.overall }"
            @click="toggleOverall"
          >
            Overall notes
          </button>
        </div>
      </div>

      <div v-if="overallOpen" class="ach-overall">
        <textarea
          v-model="overallDraft"
          class="ach-textarea"
          rows="3"
          placeholder="Plans, routes and reminders for hunting this game"
          aria-label="Overall achievement notes"
        ></textarea>
        <div class="ach-note-actions">
          <button
            type="button"
            class="ui-btn ui-btn-primary ui-btn-sm"
            @click="saveOverall"
          >
            Save
          </button>
          <button
            type="button"
            class="ui-btn ui-btn-ghost ui-btn-sm"
            @click="overallOpen = false"
          >
            Cancel
          </button>
          <span class="ach-hint">Only you can see this</span>
        </div>
      </div>

      <div v-if="achStats.length" class="ach-stats">
        <span v-for="st in achStats" :key="st.label"
          ><b>{{ st.value }}</b> {{ st.label }}</span
        >
      </div>

      <SegmentedTabs
        v-if="game.achievements.length"
        :options="achFilterOptions"
        :model-value="achFilter"
        aria-label="Filter achievements"
        @update:model-value="achFilter = $event as AchFilter"
      />

      <p v-if="!game.achievements.length" class="ach-empty">
        No achievements yet. They appear here after a library sync for Steam,
        PlayStation or RetroAchievements.
      </p>
      <p v-else-if="!shownAchievements.length" class="ach-empty">
        Nothing matches that search or filter.
      </p>

      <div
        v-if="game.achievements.length && shownAchievements.length"
        class="ach-cols"
        role="row"
      >
        <span></span>
        <button
          type="button"
          class="ach-colbtn left"
          :aria-sort="ariaSort('name')"
          @click="sortBy('name')"
        >
          Achievement <i>{{ sortMark("name") }}</i>
        </button>
        <button
          type="button"
          class="ach-colbtn"
          :aria-sort="ariaSort('rarity')"
          @click="sortBy('rarity')"
        >
          <i>{{ sortMark("rarity") }}</i> Players
        </button>
        <button
          type="button"
          class="ach-colbtn"
          :aria-sort="ariaSort('unlocked')"
          @click="sortBy('unlocked')"
        >
          <i>{{ sortMark("unlocked") }}</i> Unlocked
        </button>
        <span></span>
      </div>
      <ul v-if="shownAchievements.length" class="ach-list">
        <li v-for="a in shownAchievements" :key="a.id" class="ach-item">
          <div
            class="ach-row"
            :class="{
              done: isUnlocked(a),
              lock: !isUnlocked(a),
              pin: isPinned(a),
            }"
          >
            <div
              class="ach-icon"
              :style="
                a.iconUrl && !isHiddenLocked(a)
                  ? { backgroundImage: `url(${a.iconUrl})` }
                  : {}
              "
            ></div>

            <div class="ach-main">
              <div class="ach-name">
                <span v-if="isHiddenLocked(a)" class="ach-hidden-name"
                  >Hidden achievement</span
                >
                <router-link
                  v-else
                  :to="{
                    name: 'achievement-detail',
                    params: { gameId: game.id, achievementId: a.id },
                  }"
                  class="ach-link"
                  >{{ a.name }}</router-link
                >
                <span
                  v-if="a.kind && !isHiddenLocked(a)"
                  class="ach-tag"
                  :class="a.kind"
                  >{{ KIND_LABEL[a.kind] }}</span
                >
              </div>
              <div class="ach-desc">
                <template v-if="isHiddenLocked(a)">
                  Details for this achievement will be revealed once unlocked.
                  <button
                    type="button"
                    class="ach-reveal"
                    @click="revealAchievement(a)"
                  >
                    Show
                  </button>
                </template>
                <template v-else>
                  {{ descriptionOf(a) }}
                  <button
                    v-if="a.hidden && !isUnlocked(a)"
                    type="button"
                    class="ach-reveal"
                    @click="hideAchievement(a)"
                  >
                    Hide
                  </button>
                </template>
              </div>
            </div>

            <div class="ach-col">
              <template v-if="a.rarityPercent != null">
                <div class="ach-big">{{ formatPercent(a.rarityPercent) }}</div>
                <div class="ach-lab">of players</div>
              </template>
              <div v-else class="ach-big ach-dim">–</div>
            </div>

            <div class="ach-col">
              <template v-if="isUnlocked(a)">
                <template v-if="a.unlockedAt">
                  <div class="ach-big ach-small">
                    {{ unlockedOn(a.unlockedAt).date }}
                  </div>
                  <div class="ach-lab">{{ unlockedOn(a.unlockedAt).time }}</div>
                </template>
                <div v-else class="ach-big ach-small">Unlocked</div>
              </template>
              <template
                v-else-if="a.progressCurrent != null && a.progressTarget"
              >
                <div class="ach-big ach-small">
                  {{ a.progressCurrent }} / {{ a.progressTarget }}
                </div>
                <div class="ach-bar">
                  <i
                    :style="{
                      width: `${Math.min(100, (a.progressCurrent / a.progressTarget) * 100)}%`,
                    }"
                  ></i>
                </div>
              </template>
              <div v-else class="ach-big ach-small ach-dim">Locked</div>
            </div>

            <div class="ach-acts">
              <button
                type="button"
                class="ach-btn"
                :class="{ on: isPinned(a) }"
                :aria-pressed="isPinned(a)"
                @click="togglePin(a)"
              >
                {{ isPinned(a) ? "Pinned" : "Pin" }}
              </button>
              <button
                type="button"
                class="ach-btn"
                :class="{ on: !!achLocal.notes[a.id] || noteOpen === a.id }"
                @click="toggleNote(a)"
              >
                {{ achLocal.notes[a.id] ? "Note · 1" : "Note" }}
              </button>
              <button
                v-if="mediaByAchievement.get(a.id)?.length"
                type="button"
                class="ach-btn ach-btn-media"
                :class="{ on: achMediaOpen === a.id }"
                :title="`${mediaByAchievement.get(a.id)!.length} tied to this achievement`"
                @click="toggleAchMedia(a)"
              >
                <svg
                  viewBox="0 0 24 24"
                  width="14"
                  height="14"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <rect x="3" y="4" width="18" height="16" rx="2" />
                  <circle cx="9" cy="10" r="1.6" />
                  <path d="M21 16l-5-5-8 9" />
                </svg>
                {{ mediaByAchievement.get(a.id)!.length }}
              </button>
            </div>
          </div>

          <div v-if="achMediaOpen === a.id" class="ach-media-strip">
            <template v-for="m in mediaByAchievement.get(a.id)" :key="m.id">
              <button
                v-if="m.kind === 'screenshot'"
                type="button"
                class="ach-media-thumb"
                :title="m.note ?? 'View screenshot'"
                @click="lightboxUrl = m.url"
              >
                <img :src="m.url" alt="" loading="lazy" />
              </button>
              <video
                v-else-if="m.kind === 'clip'"
                class="ach-media-thumb"
                :src="m.url"
                controls
                preload="metadata"
              ></video>
              <audio
                v-else
                class="ach-media-audio"
                :src="m.url"
                controls
                preload="metadata"
              ></audio>
            </template>
          </div>

          <div v-if="noteOpen === a.id" class="ach-note-box">
            <textarea
              v-model="noteDraft"
              class="ach-textarea"
              rows="2"
              placeholder="How you got it, or how you plan to"
              :aria-label="`Note on ${a.name}`"
            ></textarea>
            <div class="ach-note-actions">
              <button
                type="button"
                class="ui-btn ui-btn-primary ui-btn-sm"
                @click="saveNote(a)"
              >
                Save
              </button>
              <button
                type="button"
                class="ui-btn ui-btn-ghost ui-btn-sm"
                @click="noteOpen = null"
              >
                Cancel
              </button>
              <button
                v-if="achLocal.notes[a.id]"
                type="button"
                class="ui-btn ui-btn-ghost ui-btn-sm"
                @click="clearNote(a)"
              >
                Delete note
              </button>
            </div>
          </div>
        </li>
      </ul>
      <div
        v-if="lightboxUrl"
        class="lightbox-backdrop"
        @click="lightboxUrl = null"
      >
        <img :src="lightboxUrl" alt="" class="lightbox-image" />
      </div>
    </section>

    <section v-else-if="activeTab === 'Notes'" class="notes-panel">
      <GameNotesPanel
        :game-id="game.id"
        :achievements="tieAchievements"
        :open-note="(route.query.note as string | undefined) ?? null"
        @open-achievement="openAchievement"
      />
    </section>

    <section v-else-if="activeTab === 'Accounts'" class="accounts-panel">
      <div class="accounts-layout">
        <aside class="accounts-sidebar">
          <button
            type="button"
            class="account-list-item"
            :class="{ active: activeProfileId === null }"
            @click="activeProfileId = null"
          >
            <span class="account-list-name">General</span>
          </button>
          <button
            v-for="profile in profiles"
            :key="profile.id"
            type="button"
            class="account-list-item"
            :class="{ active: activeProfileId === profile.id }"
            @click="activeProfileId = profile.id"
          >
            <span class="account-list-name">{{ profile.name }}</span>
            <span v-if="profile.stats.Overall" class="account-list-meta"
              >Lvl {{ profile.stats.Overall }}</span
            >
          </button>
          <form class="account-add" @submit.prevent="void addProfile()">
            <input
              v-model="newProfileName"
              type="text"
              placeholder="Add account…"
            />
            <button
              type="submit"
              title="Add account"
              :disabled="!newProfileName.trim()"
            >
              +
            </button>
          </form>
          <div v-if="profileError" class="note-error">{{ profileError }}</div>
        </aside>

        <div class="accounts-detail">
          <div class="accounts-detail-header">
            <h2>{{ selectedProfile ? selectedProfile.name : "General" }}</h2>
            <div v-if="selectedProfile" class="accounts-detail-actions">
              <button
                type="button"
                class="small-button"
                @click="promptRenameProfile(selectedProfile)"
              >
                Rename
              </button>
              <button
                type="button"
                class="danger-button"
                @click="void removeProfile(selectedProfile)"
              >
                Delete
              </button>
            </div>
          </div>

          <template v-if="selectedProfile">
            <div class="account-note-card">
              <h3>Note</h3>
              <textarea
                v-model="profileNoteDraft"
                rows="3"
                placeholder="What are you working toward on this account?"
              ></textarea>
              <button
                type="button"
                class="small-button"
                :disabled="profileNoteSaving"
                @click="void saveProfileNote()"
              >
                {{ profileNoteSaving ? "Saving…" : "Save note" }}
              </button>
            </div>
          </template>

          <div class="checklist-card">
            <div class="checklist-card-header">
              <h3>Checklist</h3>
              <span
                v-if="checklistProgress.total"
                class="checklist-progress-label"
              >
                {{ checklistProgress.done }}/{{ checklistProgress.total }}
              </span>
            </div>
            <div v-if="checklistProgress.total" class="checklist-progress-bar">
              <div
                class="checklist-progress-fill"
                :style="{
                  width: `${Math.round((checklistProgress.done / checklistProgress.total) * 100)}%`,
                }"
              ></div>
            </div>
            <div v-if="checklistError" class="note-error">
              {{ checklistError }}
            </div>
            <p v-if="checklistLoading" class="empty-state">Loading…</p>
            <p v-else-if="!checklistItems.length" class="empty-state">
              Nothing on the checklist yet.
            </p>
            <template v-else>
              <div
                v-for="section in checklistSections"
                :key="section.header?.id ?? 'default'"
                class="checklist-section"
              >
                <div
                  v-if="section.header"
                  class="checklist-section-header"
                  @click="toggleSectionCollapsed(section.header.id)"
                >
                  <span class="checklist-section-caret">{{
                    collapsedSections.has(section.header.id) ? "▸" : "▾"
                  }}</span>
                  <template v-if="editingItemId === section.header.id">
                    <input
                      v-model="editingText"
                      type="text"
                      class="checklist-edit-input"
                      autofocus
                      @click.stop
                      @keydown.enter="commitEditItem(section.header)"
                      @keydown.escape="cancelEditItem"
                      @blur="commitEditItem(section.header)"
                    />
                  </template>
                  <span
                    v-else
                    class="checklist-section-title"
                    @click.stop="startEditItem(section.header)"
                  >
                    {{ section.header.text }}
                  </span>
                  <span class="checklist-section-count"
                    >{{ sectionProgress(section).done }}/{{
                      sectionProgress(section).total
                    }}</span
                  >
                  <button
                    type="button"
                    class="checklist-remove"
                    title="Delete section"
                    @click.stop="void removeChecklistItem(section.header)"
                  >
                    ×
                  </button>
                </div>
                <ul
                  v-if="
                    !section.header || !collapsedSections.has(section.header.id)
                  "
                  class="checklist-items"
                >
                  <li
                    v-for="item in section.items"
                    :key="item.id"
                    class="checklist-row"
                  >
                    <div class="checklist-move-buttons">
                      <button
                        type="button"
                        class="checklist-move"
                        title="Move up"
                        @click="void moveChecklistItem(item, -1)"
                      >
                        ▲
                      </button>
                      <button
                        type="button"
                        class="checklist-move"
                        title="Move down"
                        @click="void moveChecklistItem(item, 1)"
                      >
                        ▼
                      </button>
                    </div>
                    <label class="checklist-label">
                      <input
                        type="checkbox"
                        :checked="item.done"
                        @change="void toggleChecklistItem(item)"
                      />
                      <input
                        v-if="editingItemId === item.id"
                        v-model="editingText"
                        type="text"
                        class="checklist-edit-input"
                        autofocus
                        @keydown.enter="commitEditItem(item)"
                        @keydown.escape="cancelEditItem"
                        @blur="commitEditItem(item)"
                      />
                      <span
                        v-else
                        :class="{ done: item.done }"
                        @click="startEditItem(item)"
                        >{{ item.text }}</span
                      >
                    </label>
                    <button
                      type="button"
                      class="checklist-remove"
                      title="Delete"
                      @click="void removeChecklistItem(item)"
                    >
                      ×
                    </button>
                  </li>
                </ul>
              </div>
            </template>
            <div class="checklist-add-row">
              <form
                class="checklist-add"
                @submit.prevent="void addChecklistItem()"
              >
                <input
                  v-model="newChecklistText"
                  type="text"
                  placeholder="Add a checklist item…"
                />
                <button
                  type="submit"
                  class="small-button"
                  :disabled="!newChecklistText.trim()"
                >
                  Add
                </button>
              </form>
              <button
                type="button"
                class="small-button"
                @click="addChecklistSection"
              >
                + Section
              </button>
            </div>
          </div>

          <div class="account-gallery-card">
            <div class="account-gallery-header">
              <h3>Media</h3>
              <div class="account-gallery-kinds">
                <button
                  v-for="kind in ACCOUNT_MEDIA_KINDS"
                  :key="kind"
                  type="button"
                  class="account-chip"
                  :class="{ active: accountMediaKind === kind }"
                  @click="accountMediaKind = kind"
                >
                  {{ kind }}
                </button>
              </div>
            </div>

            <UploadDropzone
              :accept="
                accountMediaKind === 'screenshot'
                  ? 'image/*'
                  : accountMediaKind === 'clip'
                    ? 'video/*'
                    : 'audio/*'
              "
              :uploading="uploadingMedia"
              :title="`Drop ${accountMediaKind}s here`"
              :hint="`Drag and drop, or click to browse, tagged to ${selectedProfile ? selectedProfile.name : 'General'}`"
              @files-selected="onMediaFilesSelected"
              @drop-error="onDropError"
            />
            <div v-if="mediaError" class="form-error">{{ mediaError }}</div>

            <div v-if="accountMediaCategories.length" class="account-bar">
              <button
                type="button"
                class="account-chip"
                :class="{ active: accountMediaCategory === null }"
                @click="accountMediaCategory = null"
              >
                All
              </button>
              <button
                v-for="category in accountMediaCategories"
                :key="category"
                type="button"
                class="account-chip"
                :class="{ active: accountMediaCategory === category }"
                @click="accountMediaCategory = category"
              >
                {{ category }}
              </button>
            </div>

            <p v-if="mediaLoading" class="empty-row">Loading…</p>
            <p v-else-if="!accountMediaFiltered.length" class="empty-row">
              No {{ accountMediaKind }}s yet.
            </p>
            <div v-else class="media-grid">
              <MediaTile
                v-for="item in accountMediaFiltered"
                :key="item.id"
                :item="item"
                :achievements="tieAchievements"
                :profiles="profiles"
                @preview="onPreviewMedia($event.url)"
                @delete="removeMedia"
                @save="saveMediaItem"
              />
            </div>
          </div>

          <div v-if="selectedProfile" class="account-stats-card">
            <div class="account-stats-header">
              <h3>Stats</h3>
              <button
                v-if="!editingStats"
                type="button"
                class="small-button"
                @click="startEditStats"
              >
                Edit
              </button>
            </div>
            <div v-if="game.osrsStatsEnabled" class="wom-sync-row">
              <input
                v-model="womUsername"
                type="text"
                placeholder="RuneScape username (WiseOldMan)"
              />
              <button
                type="button"
                class="small-button"
                :disabled="womSyncing"
                @click="void syncWiseOldMan()"
              >
                {{ womSyncing ? "Syncing…" : "Sync from WiseOldMan" }}
              </button>
            </div>
            <div v-if="womError" class="note-error">{{ womError }}</div>

            <p
              v-if="!editingStats && !Object.keys(selectedProfile.stats).length"
              class="empty-state small"
            >
              No stats yet, add one manually{{
                game.osrsStatsEnabled ? ", or sync from WiseOldMan above" : ""
              }}.
            </p>
            <template v-else-if="!editingStats && game.osrsStatsEnabled">
              <div v-if="headlineStats.length" class="stat-grid headline">
                <div
                  v-for="entry in headlineStats"
                  :key="entry.key"
                  class="account-stat-tile headline"
                >
                  <img
                    :src="skillIconUrl(entry.key)"
                    alt=""
                    class="stat-tile-icon"
                    @error="
                      ($event.target as HTMLElement).style.visibility = 'hidden'
                    "
                  />
                  <span class="stat-tile-label">{{ entry.key }}</span>
                  <span class="stat-tile-value">{{ entry.value }}</span>
                </div>
              </div>
              <template v-if="skillStats.length">
                <h4 class="stat-group-heading">Skills</h4>
                <div class="stat-grid">
                  <div
                    v-for="[key, value] in skillStats"
                    :key="key"
                    class="account-stat-tile"
                  >
                    <img
                      :src="skillIconUrl(key)"
                      alt=""
                      class="stat-tile-icon"
                      @error="
                        ($event.target as HTMLElement).style.visibility =
                          'hidden'
                      "
                    />
                    <span class="stat-tile-label">{{ key }}</span>
                    <span class="stat-tile-value">{{ value }}</span>
                  </div>
                </div>
              </template>
              <template v-if="bossStats.length">
                <h4 class="stat-group-heading">Bosses &amp; Activities</h4>
                <div class="stat-grid">
                  <div
                    v-for="[key, value] in bossStats"
                    :key="key"
                    class="account-stat-tile"
                  >
                    <svg
                      viewBox="0 0 24 24"
                      width="20"
                      height="20"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="1.6"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      class="stat-tile-boss-icon"
                    >
                      <path d="M6.5 2 3 6l3.5 2M17.5 2 21 6l-3.5 2" />
                      <path
                        d="M12 2c-3 0-5 2-5 5 0 2.5 1.5 4 2 5.5L8 21h8l-1-8.5c.5-1.5 2-3 2-5.5 0-3-2-5-5-5z"
                      />
                      <circle
                        cx="9.5"
                        cy="8"
                        r="1"
                        fill="currentColor"
                        stroke="none"
                      />
                      <circle
                        cx="14.5"
                        cy="8"
                        r="1"
                        fill="currentColor"
                        stroke="none"
                      />
                    </svg>
                    <span class="stat-tile-label">{{ key }}</span>
                    <span class="stat-tile-value">{{ value }}</span>
                  </div>
                </div>
              </template>
            </template>
            <div v-else-if="!editingStats" class="stat-grid">
              <div
                v-for="(value, key) in selectedProfile.stats"
                :key="key"
                class="account-stat-tile"
              >
                <span class="stat-tile-label">{{ key }}</span>
                <span class="stat-tile-value">{{ value }}</span>
              </div>
            </div>

            <template v-else>
              <div v-if="statRows.length" class="stat-rows">
                <div
                  v-for="(row, index) in statRows"
                  :key="index"
                  class="stat-row"
                >
                  <input
                    v-model="row.key"
                    type="text"
                    placeholder="Label (e.g. Overall)"
                  />
                  <input v-model="row.value" type="text" placeholder="Value" />
                  <button
                    type="button"
                    class="checklist-remove"
                    title="Remove"
                    @click="removeStatRow(index)"
                  >
                    ×
                  </button>
                </div>
              </div>
              <div class="stat-actions">
                <button type="button" class="small-button" @click="addStatRow">
                  + Add stat
                </button>
                <button
                  type="button"
                  class="small-button"
                  @click="cancelEditStats"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  class="primary-button"
                  @click="void saveProfileStats()"
                >
                  Save stats
                </button>
              </div>
            </template>
          </div>

          <div v-if="selectedProfile" class="account-history-card">
            <button
              type="button"
              class="account-history-toggle"
              @click="void toggleStatHistory()"
            >
              <span>History</span>
              <span class="account-history-caret">{{
                showStatHistory ? "▾" : "▸"
              }}</span>
            </button>
            <div v-if="showStatHistory">
              <p v-if="statHistoryLoading" class="empty-state small">
                Loading…
              </p>
              <p v-else-if="!statHistory.length" class="empty-state small">
                No history yet, it builds up automatically every time you sync
                or save stats.
              </p>
              <template v-else>
                <ul class="stat-history-list">
                  <li
                    v-for="snapshot in visibleHistory"
                    :key="snapshot.id"
                    class="stat-history-row"
                  >
                    <span class="stat-history-date">{{
                      formatSnapshotDate(snapshot.recorded_at)
                    }}</span>
                    <span
                      v-if="statGains[snapshot.id]?.length"
                      class="stat-history-values"
                    >
                      <span
                        v-for="line in statGains[snapshot.id]"
                        :key="line"
                        class="stat-history-chip gain"
                        >{{ line }}</span
                      >
                    </span>
                    <span v-else class="stat-history-values">
                      <span
                        v-for="(value, key) in snapshot.stats"
                        :key="key"
                        class="stat-history-chip"
                        >{{ key }}: {{ value }}</span
                      >
                    </span>
                  </li>
                </ul>
                <button
                  v-if="
                    !historyShowAll && statHistory.length > HISTORY_PAGE_SIZE
                  "
                  type="button"
                  class="small-button"
                  @click="historyShowAll = true"
                >
                  Show all {{ statHistory.length }}
                </button>
              </template>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section
      v-else-if="
        activeTab === 'Screenshots' ||
        activeTab === 'Clips' ||
        activeTab === 'Soundtrack'
      "
      class="media-panel"
    >
      <GameMediaPanel
        :kind="
          activeTab === 'Screenshots'
            ? 'screenshot'
            : activeTab === 'Clips'
              ? 'clip'
              : 'soundtrack'
        "
        :items="
          activeTab === 'Screenshots'
            ? screenshots
            : activeTab === 'Clips'
              ? clips
              : soundtrackItems
        "
        :trash="activeTabTrash"
        :achievements="tieAchievements"
        :profiles="game.profilesEnabled ? profiles : undefined"
        :loading="mediaLoadedFor !== game.id && !mediaError"
        :uploading="uploadingMedia"
        :error="mediaError"
        @files="onMediaFilesSelected"
        @delete="removeMedia"
        :detect="detectOne"
        @save="saveMediaItem"
        @bulk-save="bulkSaveMedia"
        @bulk-delete="bulkDeleteMedia"
        @bulk-detect="detectMany"
        @restore="restoreMediaItem"
        @open-achievement="openAchievement"
        @thumbnail="keepThumbnail"
        @problem="mediaError = $event"
      />
    </section>

    <section v-else-if="activeTab === 'Saves'" class="files-panel">
      <GameArchivesPanel
        title="Saves"
        plural="saves"
        singular="save"
        hint="Drop a save here or click to browse. You'll be asked to name it: one game can hold as many named saves as you want."
        :archives="saveArchives"
        :trash="saveTrash"
        :loaded="saveArchivesLoaded"
        :uploading="saveUploading.has('')"
        :error="filesError"
        @files="onNewSaveSelected"
        @bulk-delete="bulkDeleteArchives($event, false)"
        @restore="onRestoreArchive($event, false)"
        @problem="filesError = $event"
      >
        <template #card="{ archive, selecting, selected, toggle }">
          <ArchiveCard
            :archive="archive"
            kind="save"
            :selecting="selecting"
            :selected="selected"
            :uploading="saveUploading.has(archive.id)"
            @toggle="toggle"
            @edit="openArchiveEdit($event, false)"
            @delete="onDeleteArchive($event, false)"
            @add-version="onAddSaveVersion"
          />
        </template>
      </GameArchivesPanel>
    </section>

    <section v-else-if="activeTab === 'Docs'" class="files-panel">
      <GameMediaPanel
        kind="doc"
        :items="docsFiles"
        :trash="docsTrash"
        :loading="filesLoaded.doc === null"
        :uploading="uploadingFiles"
        :error="filesError"
        @files="onGameFilesSelected($event, 'doc')"
        @delete="removeGameFile('doc', $event)"
        @save="(item, patch) => saveGameFile('doc', item, patch)"
        @bulk-save="bulkSaveFiles('doc', $event)"
        @bulk-delete="(items) => items.forEach((f) => removeGameFile('doc', f))"
        @restore="restoreFileItem('doc', $event as TrashedGameFile)"
        @problem="filesError = $event"
      />
    </section>

    <section v-else-if="activeTab === 'World Map'" class="world-map-panel">
      <GameArchivesPanel
        scoped
        title="Worlds"
        plural="worlds"
        singular="world"
        hint="Zip the world folder (the one containing level.dat), then drop it here. You'll be asked to name it."
        :archives="worldMaps"
        :trash="worldTrash"
        :loaded="worldMapsLoaded"
        :uploading="saveUploading.has('')"
        :error="filesError"
        @files="onNewWorldSelected"
        @bulk-delete="bulkDeleteArchives($event, true)"
        @restore="onRestoreArchive($event, true)"
        @problem="filesError = $event"
      >
        <template #card="{ archive: world, selecting, selected, toggle }">
          <ArchiveCard
            :archive="world"
            kind="world"
            :selecting="selecting"
            :selected="selected"
            :uploading="saveUploading.has(world.id)"
            :thumbnail-url="
              world.has_thumbnail
                ? worldMapThumbnailUrl(game.id, world.id)
                : null
            "
            :rendering="world.status === 'rendering'"
            @toggle="toggle"
            @open="viewWorldMap($event.id)"
            @edit="openArchiveEdit($event, true)"
            @delete="onDeleteArchive($event, true)"
            @add-version="onAddWorldVersion"
          >
            <span class="world-map-status" :class="world.status">{{
              world.detail || world.status
            }}</span>
            <div class="world-map-card-actions">
              <button
                type="button"
                class="secondary-button small"
                :disabled="
                  worldMapStarting.has(world.id) || world.status === 'rendering'
                "
                @click="startWorldMapRender(world.id)"
              >
                {{
                  world.status === "rendering"
                    ? "Rendering…"
                    : world.has_thumbnail
                      ? "Re-render"
                      : "Render Map"
                }}
              </button>
              <button
                v-if="world.has_thumbnail"
                type="button"
                class="primary-button small"
                @click="viewWorldMap(world.id)"
              >
                View Map
              </button>
            </div>
          </ArchiveCard>
        </template>
        <template #after>
          <iframe
            v-if="activeMapArchiveId"
            :src="worldMapViewUrl(game.id, activeMapArchiveId)"
            class="world-map-frame"
            title="World map"
          ></iframe>
        </template>
      </GameArchivesPanel>

      <div class="modpack-block">
        <GameMediaPanel
          scoped
          kind="modpack"
          :items="modpackFiles"
          :trash="modpackTrash"
          :loading="filesLoaded.modpack === null"
          :uploading="uploadingFiles"
          :error="null"
          @files="onGameFilesSelected($event, 'modpack')"
          @delete="removeGameFile('modpack', $event)"
          @save="(item, patch) => saveGameFile('modpack', item, patch)"
          @bulk-save="bulkSaveFiles('modpack', $event)"
          @bulk-delete="
            (items) => items.forEach((f) => removeGameFile('modpack', f))
          "
          @restore="restoreFileItem('modpack', $event as TrashedGameFile)"
          @problem="filesError = $event"
        />
      </div>
    </section>

    <section v-else-if="activeTab === 'Stats'" class="stats-panel">
      <GameStatsPanel
        :show-achievements="achievementsOn"
        :show-rating="!pageSettings.hide_rating"
        :hide-history="pageSettings.hide_history"
        :game="game"
        :changes="fieldChanges"
        :media="mediaItems"
        :loading="fieldChangesLoading"
        :error="fieldChangesError"
      />
    </section>
  </main>

  <main v-else class="not-found">
    <p>Game not found.</p>
  </main>
</template>

<style scoped>
.detail {
  position: relative;
  font-family: system-ui, sans-serif;
  color: #f2f2f2;
  min-height: 100vh;
  background: #0d0d0d;
  /* clip, not hidden: hidden would turn this into a scroll container and stop
     the top bar sticking */
  overflow-x: clip;
}
.detail-skeleton-body {
  max-width: 1180px;
  margin: 22px auto 0;
  padding: 0 24px 40px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.detail-skeleton-text {
  flex: 1;
  max-width: 560px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.detail-skeleton-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.loading-state .tabbar-wrap {
  max-width: 1180px;
}
.hero {
  position: relative;
  background-color: #1a1a1a;
  min-height: 440px;
  display: flex;
  align-items: flex-end;
  overflow: hidden;
}
/* the possible-duplicate pill floats at the hero's top right, clear of the back
   button on the left, and takes the full width less the gutters on a narrow screen */
.hero-notice {
  position: absolute;
  top: 16px;
  right: 24px;
  z-index: 3;
  max-width: calc(100% - 48px);
}
@media (max-width: 640px) {
  .hero-notice {
    right: 16px;
    max-width: calc(100% - 32px);
  }
}
.hero-backdrop {
  position: absolute;
  inset: 0;
  background-size: cover;
  background-repeat: no-repeat;
  background-position: center 20%;
  filter: brightness(0.55) saturate(1.15);
  z-index: 0;
}
.hero-overlay {
  position: absolute;
  inset: 0;
  z-index: 1;
  background:
    linear-gradient(
      180deg,
      rgba(13, 13, 13, 0.25) 0%,
      rgba(13, 13, 13, 0.55) 45%,
      #0d0d0d 96%
    ),
    linear-gradient(
      90deg,
      rgba(13, 13, 13, 0.75) 0%,
      rgba(13, 13, 13, 0.15) 40%
    );
}
.hero-content {
  position: relative;
  z-index: 2;
  width: 100%;
  max-width: 1180px;
  margin: 0 auto;
  padding: 0 24px 28px;
  box-sizing: border-box;
  display: flex;
  align-items: flex-end;
  gap: 26px;
}
.poster-card {
  width: 190px;
  aspect-ratio: 2 / 3;
  flex-shrink: 0;
  border-radius: 8px;
  background-size: cover;
  background-repeat: no-repeat;
  background-origin: border-box;
  background-clip: border-box;
  background-position: center;
  background-color: #222222;
  border: 1px solid transparent;
  box-shadow: 0 24px 48px -14px rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.78rem;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.3);
  text-align: center;
  padding: 10px;
}
.hero-text {
  min-width: 0;
  padding-bottom: 4px;
}
.native-title {
  font-size: 0.82rem;
  color: #666;
  margin-bottom: 4px;
  font-weight: 500;
}
.title {
  font-weight: 800;
  font-size: 2.5rem;
  line-height: 1.05;
  margin: 0 0 14px;
  letter-spacing: -0.01em;
  text-shadow: 0 4px 24px rgba(0, 0, 0, 0.5);
}
.overview,
.achievements,
.notes-panel,
.accounts-panel,
.files-panel,
.media-panel,
.stats-panel,
.world-map-panel {
  position: relative;
  z-index: 1;
}
@media (max-width: 640px) {
  .hero-content {
    flex-direction: column;
    align-items: flex-start;
  }
}
/* Sits under the top bar and stays there while the page scrolls. It is sticky
   rather than absolute so it never slides over the bar, and the negative
   bottom margin gives back the room it takes so the hero does not move. */
.detail > .back-spot {
  display: flex;
  width: 38px;
  position: sticky;
  top: 76px;
  z-index: 79;
  margin: 16px 0 -54px var(--ui-edge-left);
}
.parent-breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #ccc;
  font-size: 0.9rem;
  text-decoration: none;
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.6);
  margin-bottom: -8px;
}
.parent-breadcrumb:hover {
  color: #fff;
}
.relationship-tag {
  background: rgba(214, 138, 52, 0.22);
  color: #d68a34;
  border-radius: 999px;
  padding: 2px 10px;
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.badge-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.badge {
  line-height: 1.25;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 7px;
  padding: 4px 11px;
  font-size: 0.78rem;
  font-weight: 600;
  color: #9c9c9c;
  text-transform: capitalize;
}
.status-select option {
  background: #171717;
  color: #f2f2f2;
}
.status-select {
  color-scheme: dark;
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
  border-color: rgba(214, 138, 52, 0.4);
  color: #d68a34;
  font-family: inherit;
  cursor: pointer;
  padding-right: 26px;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23d68a34' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 8px center;
  background-size: 10px;
}
.action-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.edit-btn {
  background: #d68a34;
  border: none;
  color: #14100a;
  border-radius: 8px;
  padding: 0 20px;
  height: 38px;
  font-family: inherit;
  font-size: 0.86rem;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
}
.icon-btn {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: #f2f2f2;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
}
.icon-btn svg {
  width: 16px;
  height: 16px;
}
.icon-btn:hover {
  border-color: rgba(214, 138, 52, 0.4);
}
.icon-btn.active {
  color: #d68a34;
  border-color: rgba(214, 138, 52, 0.4);
  background: rgba(214, 138, 52, 0.16);
}
.stale-badge {
  background: rgba(220, 38, 38, 0.18);
  color: #fca5a5;
  text-transform: none;
}
.achievement-progress-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  cursor: pointer;
  font-family: inherit;
  text-transform: none;
}
.achievement-progress-badge svg {
  flex-shrink: 0;
  opacity: 0.85;
}
.achievement-progress-badge:hover {
  background: rgba(214, 138, 52, 0.22);
  color: #d68a34;
}
.meta {
  text-transform: capitalize;
  color: #ddd;
}
.tab-more {
  position: relative;
  flex-shrink: 0;
}
.tab-more-btn {
  min-width: 36px;
  font-size: 1.05rem;
  line-height: 1;
}
.tab-more-menu {
  position: absolute;
  right: 0;
  top: calc(100% + 6px);
  z-index: 60;
  min-width: 150px;
  list-style: none;
  margin: 0;
  padding: 6px;
  background: #171717;
  border: 1px solid #2b2b2b;
  border-radius: 12px;
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.5);
}
.tab-more-menu button {
  width: 100%;
  padding: 8px 10px;
  border: none;
  border-radius: 8px;
  background: none;
  color: #ddd;
  font-family: inherit;
  font-size: 0.84rem;
  text-align: left;
  cursor: pointer;
}
.tab-more-menu button:hover {
  background: rgba(255, 255, 255, 0.07);
}
.tabbar-wrap {
  position: relative;
  z-index: 1;
  max-width: 1180px;
  margin: 22px auto 0;
  padding: 0 24px;
  box-sizing: border-box;
}
.tabbar {
  display: flex;
  gap: 4px;
  background: #1a1a1a;
  border-radius: 10px;
  width: fit-content;
  max-width: 100%;
  overflow-x: auto;
  padding: 5px;
  scrollbar-width: none;
}
.tabbar::-webkit-scrollbar {
  display: none;
}
.tab-btn {
  flex-shrink: 0;
  white-space: nowrap;
  background: transparent;
  border: none;
  color: #9c9c9c;
  font-family: inherit;
  font-size: 0.84rem;
  font-weight: 600;
  padding: 8px 18px;
  border-radius: 7px;
  cursor: pointer;
}
.tab-btn.active {
  background: #d68a34;
  color: #14100a;
}
.overview {
  width: 100%;
  max-width: 1180px;
  margin: 0 auto;
  padding: 22px 24px 60px;
  box-sizing: border-box;
}
.text-button {
  background: none;
  border: none;
  color: #d68a34;
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
  /* larger tap target without moving the text */
  padding: 6px 4px;
  margin: -6px -4px;
}
.text-button:hover {
  text-decoration: underline;
}
.text-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.form-error-inline {
  color: #fca5a5;
  font-size: 12.5px;
  margin: 6px 0;
}
.log-playtime-button {
  display: block;
  margin-top: 4px;
}
.my-note {
  margin-top: 26px;
  padding-top: 22px;
  border-top: 1px solid #1f1f1f;
}
.my-note.empty {
  display: flex;
  align-items: baseline;
  gap: 12px;
}
.note-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin: 0 0 10px;
}
.note-head h3 {
  margin: 0;
  font-size: 0.9rem;
  font-weight: 800;
  color: #f2f2f2;
}
.note-private {
  flex: 1;
  font-size: 0.72rem;
  color: #666;
}
.note-text {
  margin: 0;
  font-size: 0.96rem;
  line-height: 1.7;
  color: #d0d0d0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.note-input {
  display: block;
  width: 100%;
  box-sizing: border-box;
  min-height: 84px;
  resize: vertical;
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid #2a2a2a;
  background: #1a1a1a;
  color: #f2f2f2;
  font: inherit;
  font-size: 0.96rem;
  line-height: 1.7;
}
.note-input::placeholder {
  color: #666;
}
.note-input:focus {
  outline: none;
  border-color: rgba(214, 138, 52, 0.7);
}
.note-error {
  color: #e57373;
  font-size: 0.8rem;
  margin: 8px 0 0;
}
.note-actions {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 12px;
}
.btn-text {
  background: none;
  border: none;
  /* larger tap target without moving the text */
  padding: 6px 4px;
  margin: -6px -4px;
  color: #d68a34;
  font-family: inherit;
  font-size: 0.82rem;
  font-weight: 700;
  cursor: pointer;
}
.btn-text:hover {
  color: #e8a552;
}
.btn-text.muted {
  color: #9c9c9c;
}
.btn-text.muted:hover {
  color: #f2f2f2;
}
.btn-solid {
  background: #d68a34;
  border: none;
  border-radius: 8px;
  padding: 8px 18px;
  color: #14100a;
  font-family: inherit;
  font-size: 0.82rem;
  font-weight: 800;
  cursor: pointer;
}
.btn-solid:hover {
  background: #e29a48;
}
.btn-solid:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.description-block {
  margin-top: 22px;
}
.description {
  font-size: 0.96rem;
  line-height: 1.7;
  color: #9c9c9c;
  margin: 0;
}
.description.clamped {
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.read-more-btn {
  background: none;
  border: none;
  color: #d68a34;
  font-family: inherit;
  font-size: 0.82rem;
  font-weight: 700;
  cursor: pointer;
  padding: 6px 0 0;
}
.read-more-btn:hover {
  text-decoration: underline;
}
.read-more-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.description-html :deep(img),
.description-html :deep(video) {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  margin: 10px 0;
  display: block;
}
.description-html :deep(h1),
.description-html :deep(h2),
.description-html :deep(h3) {
  margin: 18px 0 6px;
  font-size: 15px;
  font-weight: 700;
  color: #f2f2f2;
}
.description-html :deep(p) {
  margin: 0 0 12px;
}
.description-html :deep(a) {
  color: #d68a34;
}
.description-html :deep(ul) {
  padding-left: 20px;
  margin: 0 0 12px;
}
/* Media's row of small label/value pairs: fixed-width columns that start at
   the left, so a long value never stretches a cell and leaves a gap. */
.meta-block {
  margin-bottom: 24px;
  padding-bottom: 24px;
  border-bottom: 1px solid #202020;
}
.meta-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, 132px);
  gap: 18px 40px;
}
@media (max-width: 640px) {
  .meta-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 16px 20px;
  }
}
.meta-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
.meta-label {
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: #666;
  font-weight: 700;
}
.meta-value {
  font-size: 0.9rem;
  color: #f2f2f2;
  font-variant-numeric: tabular-nums;
}
.meta-value.accent {
  color: #d68a34;
  font-weight: 700;
}
.meta-value.muted {
  color: #666;
}
.meta-link {
  background: none;
  border: none;
  padding: 0;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
}
.meta-link:hover {
  text-decoration: underline;
}
.more-details {
  margin-top: 28px;
  padding-top: 16px;
  border-top: 1px solid #202020;
}
.more-details > summary {
  cursor: pointer;
  list-style: none;
  color: #d68a34;
  font-size: 0.82rem;
  font-weight: 700;
}
.more-details > summary::-webkit-details-marker {
  display: none;
}
.more-details > summary::before {
  content: "▸ ";
}
.more-details[open] > summary::before {
  content: "▾ ";
}
.more-block {
  margin-top: 20px;
}
.more-title {
  margin: 0 0 8px;
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: #666;
  font-weight: 700;
}
.more-details .read-more-btn {
  display: block;
  padding-top: 10px;
}
.kv-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 16px;
  padding: 9px 0;
  border-bottom: 1px solid #202020;
  font-size: 0.88rem;
}
.kv-row:last-child {
  border-bottom: none;
}
.kv-row.stack {
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}
.kv-label {
  color: #9c9c9c;
  flex-shrink: 0;
}
.kv-value {
  color: #f2f2f2;
  text-align: right;
  min-width: 0;
  overflow-wrap: anywhere;
  font-variant-numeric: tabular-nums;
}
.kv-row.stack .kv-value {
  text-align: left;
}
.kv-value.accent {
  color: #d68a34;
  font-weight: 700;
}
.kv-row.total {
  font-weight: 700;
}
.folder-value {
  font-size: 0.8rem;
}
.ownership-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.ownership-format {
  text-transform: capitalize;
  font-weight: 700;
}
.links-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.links-list a {
  color: #d68a34;
  font-size: 0.88rem;
  text-decoration: none;
}
.links-list a:hover {
  text-decoration: underline;
}
.platform-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.platform-item {
  padding: 9px 0;
  border-bottom: 1px solid #202020;
}
.platform-top {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
}
.platform-name {
  color: #f2f2f2;
  font-weight: 700;
  font-size: 0.9rem;
}
.platform-hours {
  color: #f2f2f2;
  font-size: 0.88rem;
  font-variant-numeric: tabular-nums;
}
.platform-sub {
  display: flex;
  flex-wrap: wrap;
  gap: 2px 12px;
  margin-top: 2px;
  font-size: 0.74rem;
  color: #666;
}
.kv-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  column-gap: 32px;
}
.chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}
.chip {
  background: #222222;
  color: #9c9c9c;
  border: 1px solid #2b2b2b;
  border-radius: 999px;
  padding: 5px 13px;
  font-size: 0.78rem;
  font-weight: 600;
}
.filter-link {
  color: inherit;
  text-decoration: none;
  border-bottom: 1px solid transparent;
  transition:
    color 0.15s ease,
    border-color 0.15s ease;
}
.filter-link:hover,
.filter-link:focus-visible {
  color: #d68a34;
  border-bottom-color: rgba(214, 138, 52, 0.5);
  outline: none;
}
.credit-dot {
  opacity: 0.6;
}
.badge.filter-badge {
  text-decoration: none;
  transition:
    border-color 0.15s ease,
    color 0.15s ease;
}
.badge.filter-badge:hover,
.badge.filter-badge:focus-visible {
  color: #d68a34;
  border-color: rgba(214, 138, 52, 0.5);
  outline: none;
}
.chip.chip-link {
  text-decoration: none;
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    color 0.15s ease;
}
.chip.chip-link:hover,
.chip.chip-link:focus-visible {
  border-color: rgba(214, 138, 52, 0.6);
  color: #fff;
  outline: none;
}
.chip.primary {
  background: rgba(214, 138, 52, 0.16);
  color: #d68a34;
  border-color: rgba(214, 138, 52, 0.4);
}
.related-section {
  margin-top: 28px;
}
.section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.section-heading h2 {
  font-weight: 800;
  font-size: 1.05rem;
  margin: 0;
}
.poster-grid {
  margin-top: 20px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 16px;
}
.poster-card-sm {
  cursor: pointer;
  text-decoration: none;
  color: inherit;
}
.poster-card-sm-art {
  aspect-ratio: 2 / 3;
  border-radius: 8px;
  background-size: cover;
  background-repeat: no-repeat;
  background-origin: border-box;
  background-clip: border-box;
  background-position: center;
  background-color: #222222;
  border: 1px solid transparent;
  transition: border-color 0.15s ease;
}
.poster-card-sm:hover .poster-card-sm-art {
  border-color: rgba(214, 138, 52, 0.5);
}
.poster-card-sm-title {
  margin-top: 6px;
  font-size: 0.8rem;
  font-weight: 700;
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.poster-card-sm-meta {
  margin-top: 2px;
  font-size: 0.7rem;
  color: #666;
}
.achievements {
  max-width: 1180px;
  margin: 0 auto;
  padding: 22px 24px 60px;
  box-sizing: border-box;
}
.ach-head {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
.ach-title {
  font-weight: 800;
  font-size: 1.25rem;
  margin: 0;
}
.ach-count {
  margin-right: auto;
  font-size: 1rem;
  color: #9c9c9c;
  font-variant-numeric: tabular-nums;
}
.ach-tools {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.ach-search {
  width: 220px;
  height: 34px;
}
.ach-sort {
  height: 34px;
}
.ach-overall,
.ach-note-box {
  margin: 0 0 12px;
  padding: 12px;
  background: #1a1a1a;
  border: 1px solid #202020;
  border-radius: 10px;
}
.ach-note-box {
  margin: 4px 0 0;
}
.ach-textarea {
  display: block;
  width: 100%;
  box-sizing: border-box;
  resize: vertical;
  padding: 8px 10px;
  background: #0d0d0d;
  border: 1px solid #2b2b2b;
  border-radius: 8px;
  color: #f2f2f2;
  font: inherit;
  font-size: 0.82rem;
  line-height: 1.5;
}
.ach-textarea::placeholder {
  color: #666;
}
.ach-textarea:focus {
  outline: none;
  border-color: rgba(214, 138, 52, 0.7);
}
.ach-note-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}
.ach-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 22px;
  margin: 0 0 12px;
  font-size: 0.85rem;
  color: #666;
}
.ach-stats b {
  color: #f2f2f2;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.ach-cols {
  display: grid;
  grid-template-columns: 64px minmax(0, 1fr) 96px 120px 200px;
  column-gap: 20px;
  align-items: center;
  margin: 14px 0 0;
  padding: 0 19px 0 13px;
}
.ach-colbtn {
  padding: 4px 0;
  background: none;
  border: none;
  color: #666;
  font: inherit;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  text-align: right;
  cursor: pointer;
}
.ach-colbtn.left {
  text-align: left;
}
.ach-colbtn:hover,
.ach-colbtn[aria-sort="ascending"],
.ach-colbtn[aria-sort="descending"] {
  color: #d68a34;
}
.ach-colbtn i {
  font-style: normal;
  font-size: 0.6rem;
}
.ach-mobile-sort {
  display: none;
}
.ach-hint {
  margin-left: auto;
  font-size: 0.72rem;
  color: #666;
}
.ach-empty {
  margin: 0;
  padding: 24px 0;
  color: #666;
  font-size: 0.85rem;
}
.ach-list {
  list-style: none;
  margin: 6px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 9px;
}
.ach-row {
  display: grid;
  grid-template-columns: 64px minmax(0, 1fr) 96px 120px 200px;
  column-gap: 20px;
  align-items: center;
  min-height: 88px;
  padding: 12px 18px 12px 12px;
  background: #1a1a1a;
  border: 1px solid #202020;
  border-radius: 12px;
  transition: border-color 0.15s ease;
}
.ach-row:hover {
  border-color: rgba(214, 138, 52, 0.4);
}
.ach-row.done {
  background: #16201a;
  border-color: #22352a;
}
.ach-row.pin {
  border-color: rgba(214, 138, 52, 0.5);
}
.ach-icon {
  width: 64px;
  height: 64px;
  border-radius: 10px;
  background-color: #2a2a2a;
  background-size: cover;
  background-repeat: no-repeat;
  background-position: center;
}
.ach-row.lock .ach-icon {
  background-color: #1f1f1f;
  filter: grayscale(1) brightness(0.6);
}
.ach-main {
  min-width: 0;
}
.ach-name {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  font-weight: 700;
  font-size: 1.05rem;
  line-height: 1.3;
}
.ach-link {
  color: #f2f2f2;
  text-decoration: none;
}
.ach-link:hover {
  color: #d68a34;
}
.ach-row.lock .ach-link,
.ach-hidden-name {
  color: #9c9c9c;
}
.ach-tag {
  padding: 2px 9px;
  border-radius: 5px;
  background: #262626;
  color: #9c9c9c;
  font-size: 0.7rem;
  font-weight: 700;
  line-height: 1.5;
}
.ach-tag.missable {
  background: rgba(217, 111, 111, 0.14);
  color: #d96f6f;
}
.ach-tag.win_condition {
  background: rgba(214, 138, 52, 0.14);
  color: #d68a34;
}
.ach-desc {
  margin-top: 3px;
  font-size: 0.88rem;
  line-height: 1.5;
  color: #9c9c9c;
}
.ach-reveal {
  padding: 0;
  background: none;
  border: none;
  color: #d68a34;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}
.ach-col {
  text-align: right;
}
.ach-big {
  font-size: 1.05rem;
  font-weight: 700;
  line-height: 1.25;
  font-variant-numeric: tabular-nums;
}
.ach-big.ach-small {
  font-size: 0.9rem;
}
.ach-dim {
  color: #666;
}
.ach-lab {
  margin-top: 3px;
  font-size: 0.72rem;
  color: #666;
}
.ach-bar {
  width: 72px;
  height: 5px;
  margin: 6px 0 0 auto;
  border-radius: 999px;
  background: #2a2a2a;
  overflow: hidden;
}
.ach-bar i {
  display: block;
  height: 100%;
  background: #d68a34;
}
.ach-acts {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.ach-btn {
  padding: 6px 13px;
  background: transparent;
  border: 1px solid #2b2b2b;
  border-radius: 7px;
  color: #9c9c9c;
  font: inherit;
  font-size: 0.78rem;
  white-space: nowrap;
  cursor: pointer;
}
.ach-btn:hover {
  color: #f2f2f2;
}
.ach-btn-media {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 10px;
  font-variant-numeric: tabular-nums;
}
.ach-btn.on {
  color: #d68a34;
  border-color: rgba(214, 138, 52, 0.5);
}
.ach-media-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 10px 14px 12px;
  border-top: 1px solid #232323;
}
.ach-media-thumb {
  width: 160px;
  aspect-ratio: 16 / 9;
  padding: 0;
  border: 1px solid #2b2b2b;
  border-radius: 8px;
  background: #000;
  overflow: hidden;
  cursor: pointer;
  object-fit: cover;
}
.ach-media-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.ach-media-audio {
  height: 36px;
  max-width: 100%;
}
@media (max-width: 720px) {
  .ach-cols {
    display: none;
  }
  .ach-mobile-sort {
    display: block;
  }
  .ach-row {
    grid-template-columns: 52px minmax(0, 1fr);
    row-gap: 8px;
    min-height: 0;
  }
  .ach-icon {
    width: 52px;
    height: 52px;
  }
  .ach-col,
  .ach-acts {
    grid-column: 2;
    justify-content: flex-start;
    text-align: left;
  }
  .ach-col {
    display: flex;
    align-items: baseline;
    gap: 8px;
  }
  .ach-bar {
    margin-left: 0;
  }
}
.notes-panel {
  width: 100%;
  max-width: 1180px;
  margin: 0 auto;
  padding: 22px 24px 60px;
  box-sizing: border-box;
}
.account-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.account-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid #3a3a3a;
  border-radius: 999px;
  color: #ccc;
  padding: 6px 12px;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  transition:
    background 0.15s ease,
    border-color 0.15s ease,
    color 0.15s ease;
}
.account-chip:hover {
  border-color: #d68a34;
}
.account-chip.active {
  background: rgba(214, 138, 52, 0.18);
  border-color: #d68a34;
  color: #d68a34;
}
.account-add {
  display: flex;
  gap: 6px;
}
.account-add input {
  background: #111;
  border: 1px solid #3a3a3a;
  border-radius: 999px;
  color: #fff;
  padding: 6px 12px;
  font-size: 0.8rem;
  min-width: 200px;
}
.checklist-card {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid #2a2a2a;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.checklist-card h3 {
  margin: 0;
  font-size: 0.95rem;
  color: #fff;
}
.checklist-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.checklist-progress-label {
  font-size: 0.8rem;
  color: #999;
  font-weight: 600;
}
.checklist-progress-bar {
  height: 5px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
}
.checklist-progress-fill {
  height: 100%;
  background: #d68a34;
  transition: width 0.2s ease;
}
.checklist-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.checklist-section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 0;
  border-bottom: 1px solid #2a2a2a;
}
.checklist-section-caret {
  color: #777;
  font-size: 0.7rem;
  width: 10px;
}
.checklist-section-title {
  flex: 1;
  color: #fff;
  font-weight: 700;
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.checklist-section-count {
  color: #777;
  font-size: 0.75rem;
  font-weight: 600;
}
.checklist-items {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.checklist-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.checklist-move-buttons {
  display: flex;
  flex-direction: column;
  gap: 0;
}
.checklist-move {
  background: none;
  border: none;
  color: #555;
  cursor: pointer;
  font-size: 0.55rem;
  line-height: 1;
  padding: 1px 2px;
}
.checklist-move:hover {
  color: #d68a34;
}
.checklist-label {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  color: #ddd;
  cursor: pointer;
}
.checklist-label span.done {
  color: #777;
  text-decoration: line-through;
}
.checklist-edit-input {
  flex: 1;
  background: #111;
  border: 1px solid #d68a34;
  border-radius: 6px;
  color: #fff;
  padding: 4px 8px;
  font-size: 0.9rem;
}
.checklist-remove {
  background: none;
  border: none;
  color: #777;
  cursor: pointer;
  font-weight: 700;
  padding: 0 4px;
}
.checklist-remove:hover {
  color: #fca5a5;
}
.checklist-add-row {
  display: flex;
  gap: 8px;
}
.checklist-add {
  display: flex;
  gap: 8px;
  flex: 1;
}
.checklist-add input {
  flex: 1;
  background: #111;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  color: #fff;
  padding: 8px 10px;
}
.accounts-panel {
  max-width: 1180px;
  margin: 0 auto;
  padding: 22px 24px 60px;
  box-sizing: border-box;
}
.accounts-layout {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 20px;
  align-items: start;
}
.accounts-sidebar {
  display: flex;
  flex-direction: column;
  gap: 4px;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid #2a2a2a;
  border-radius: 8px;
  padding: 10px;
  position: sticky;
  top: 24px;
}
.account-list-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  background: none;
  border: none;
  border-radius: 6px;
  color: #ccc;
  padding: 9px 10px;
  font-size: 0.85rem;
  text-align: left;
  cursor: pointer;
}
.account-list-item:hover {
  background: rgba(255, 255, 255, 0.05);
}
.account-list-item.active {
  background: rgba(214, 138, 52, 0.16);
  color: #d68a34;
  font-weight: 600;
}
.account-list-meta {
  color: #888;
  font-size: 0.72rem;
}
.accounts-sidebar .account-add {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 6px;
  padding-top: 10px;
  border-top: 1px solid #2a2a2a;
}
.accounts-sidebar .account-add input {
  flex: 1;
  min-width: 0;
  background: none;
  border: none;
  border-radius: 6px;
  color: #fff;
  padding: 7px 8px;
  font-size: 0.85rem;
}
.accounts-sidebar .account-add input:focus {
  outline: none;
  background: rgba(255, 255, 255, 0.05);
}
.accounts-sidebar .account-add button {
  flex-shrink: 0;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: 1px solid #3a3a3a;
  background: none;
  color: #ccc;
  font-size: 1rem;
  line-height: 1;
  cursor: pointer;
}
.accounts-sidebar .account-add button:hover:not(:disabled) {
  border-color: #d68a34;
  color: #d68a34;
}
.accounts-sidebar .account-add button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.accounts-detail {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}
.accounts-detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.accounts-detail-header h2 {
  margin: 0;
  font-size: 1.2rem;
}
.accounts-detail-actions {
  display: flex;
  gap: 8px;
}
.account-note-card,
.account-stats-card,
.account-gallery-card {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid #2a2a2a;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.account-note-card h3,
.account-stats-card h3,
.account-gallery-card h3 {
  margin: 0;
  font-size: 0.95rem;
  color: #fff;
}
.account-note-card textarea {
  background: #111;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  color: #fff;
  padding: 10px;
  font: inherit;
  resize: vertical;
}
.account-stats-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(88px, 1fr));
  gap: 8px;
  margin-bottom: 4px;
}
.stat-grid.headline {
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  margin-bottom: 14px;
}
.stat-group-heading {
  margin: 4px 0 8px;
  color: #999;
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.account-stat-tile {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid #2a2a2a;
  border-radius: 8px;
  padding: 8px 6px;
  text-align: center;
}
.account-stat-tile.headline {
  padding: 14px 6px;
  background: rgba(214, 138, 52, 0.1);
  border-color: rgba(214, 138, 52, 0.35);
}
.account-stat-tile.headline .stat-tile-value {
  color: #d68a34;
  font-size: 1.3rem;
}
.stat-tile-label {
  color: #999;
  font-size: 0.65rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}
.stat-tile-value {
  color: #fff;
  font-weight: 700;
  font-size: 0.95rem;
}
.stat-tile-icon {
  width: 20px;
  height: 20px;
  object-fit: contain;
  image-rendering: pixelated;
}
.account-stat-tile.headline .stat-tile-icon {
  width: 26px;
  height: 26px;
}
.stat-tile-boss-icon {
  color: #999;
}
.account-history-card {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid #2a2a2a;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.account-history-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: none;
  border: none;
  color: #fff;
  font-size: 0.95rem;
  font-weight: 700;
  cursor: pointer;
  padding: 0;
}
.account-history-caret {
  color: #777;
  font-size: 0.75rem;
}
.wom-sync-row {
  display: flex;
  gap: 8px;
}
.wom-sync-row input {
  flex: 1;
  background: #111;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  color: #fff;
  padding: 8px 10px;
}
.stat-rows {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.stat-row {
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  gap: 6px;
  align-items: center;
}
.stat-row input {
  background: #111;
  border: 1px solid #3a3a3a;
  border-radius: 6px;
  color: #fff;
  padding: 6px 8px;
  font-size: 0.85rem;
}
.stat-actions {
  display: flex;
  gap: 8px;
}
.empty-state.small {
  font-size: 0.78rem;
  margin: 0;
}
.stat-history-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 260px;
  overflow-y: auto;
}
.stat-history-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.stat-history-date {
  color: #999;
  font-size: 0.75rem;
  font-weight: 600;
}
.stat-history-values {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.stat-history-chip {
  background: rgba(255, 255, 255, 0.06);
  color: #ccc;
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 0.68rem;
}
.stat-history-chip.gain {
  background: rgba(74, 222, 128, 0.14);
  color: #86efac;
  font-weight: 600;
}
.account-gallery-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}
.account-gallery-kinds {
  display: flex;
  gap: 6px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: #ddd;
  font-size: 0.85rem;
}
.field input {
  background: #111;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  color: #fff;
  padding: 10px 12px;
}
.field input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.primary-button,
.small-button,
.danger-button {
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: opacity 0.15s ease;
}
.primary-button {
  background: #d68a34;
  color: #111;
  padding: 10px 12px;
}
.small-button {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
  padding: 7px 10px;
  font-size: 0.8rem;
}
.danger-button {
  background: rgba(220, 38, 38, 0.18);
  color: #fca5a5;
  padding: 8px 10px;
}
.primary-button:disabled,
.danger-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.note-error {
  color: #fca5a5;
}
.field input:focus {
  outline: none;
  border-color: #d68a34;
}
.empty-state {
  color: #777;
  margin: 0;
}
.empty-state.error {
  color: #fca5a5;
}

/* Screenshots / Clips / Saves / Docs / Stats / History */
.media-panel,
.files-panel,
.world-map-panel,
.stats-panel,
.history-panel {
  width: 100%;
  max-width: 1180px;
  margin: 0 auto;
  padding: 22px 24px 60px;
  box-sizing: border-box;
  position: relative;
  z-index: 1;
}
.panel-body {
  display: flex;
  gap: 24px;
  align-items: flex-start;
}
.panel-content {
  flex: 1;
  min-width: 0;
}
.stats-panel h2,
.history-panel h2 {
  margin: 0;
  font-size: 1.1rem;
}
.stats-panel h2,
.history-panel h2 {
  margin-bottom: 16px;
}
.upload-label {
  display: inline-flex;
  align-items: center;
  cursor: pointer;
}
.hidden-input {
  display: none;
}
.section-hint {
  color: #999;
  font-size: 0.85rem;
  margin: 0 0 16px;
}
.empty-row {
  color: #777;
  font-size: 14px;
}
.form-error {
  color: #fca5a5;
  font-size: 13px;
  background: rgba(220, 38, 38, 0.1);
  border: 1px solid rgba(220, 38, 38, 0.3);
  border-radius: 8px;
  padding: 8px 10px;
  margin-bottom: 14px;
}
.media-panel h2,
.files-panel h2 {
  margin: 0 0 16px;
  font-size: 1.1rem;
}
.media-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 14px;
  margin-top: 16px;
}
.lightbox-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: 40px;
  box-sizing: border-box;
}
.lightbox-image {
  max-width: 100%;
  max-height: 100%;
  border-radius: 8px;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.6);
}
.file-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.file-row {
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid #2a2a2a;
  border-radius: 8px;
  padding: 12px 16px;
  color: #999;
}
.file-name {
  color: #fff;
  font-size: 0.9rem;
  text-decoration: none;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.file-name:hover {
  text-decoration: underline;
}
.world-map-panel h2 {
  margin: 0 0 4px;
  color: #fff;
}
.world-map-uploads {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin: 16px 0;
}
.world-map-upload-col h3 {
  margin: 0 0 8px;
  font-size: 0.85rem;
  color: #ccc;
}
/* Saves: named, versioned archives ---------------------------------------- */
.archive-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
}
.archive-card {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid #2a2a2a;
  border-radius: 10px;
  padding: 14px;
}
.archive-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.archive-name {
  color: #fff;
  font-weight: 600;
  font-size: 0.92rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.archive-card-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}
.icon-button {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  border: none;
  background: rgba(255, 255, 255, 0.06);
  color: #999;
  cursor: pointer;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.icon-button:hover {
  background: rgba(255, 255, 255, 0.14);
  color: #fff;
}
.archive-meta {
  color: #777;
  font-size: 0.76rem;
  margin: 4px 0 12px;
}
.archive-actions-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.archive-history {
  list-style: none;
  margin: 12px 0 0;
  padding: 10px 0 0;
  border-top: 1px solid #232323;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.archive-history-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.8rem;
}
.secondary-button.small,
.primary-button.small {
  padding: 6px 10px;
  font-size: 0.76rem;
}

/* Trash: recoverable-for-7-days list, shared by Saves and World Map -------- */
.trash-section {
  margin-top: 20px;
  padding-top: 14px;
  border-top: 1px solid #2a2a2a;
}
.trash-toggle {
  background: none;
  border: none;
  color: #999;
  font-size: 0.82rem;
  cursor: pointer;
  padding: 0;
}
.trash-toggle:hover {
  color: #ccc;
}
.trash-list {
  list-style: none;
  margin: 10px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.trash-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid #2a2a2a;
  border-radius: 8px;
  font-size: 0.82rem;
}
.trash-name {
  flex: 1;
  color: #ccc;
}
.trash-meta {
  color: #777;
  font-size: 0.76rem;
}

/* World Map: card grid with thumbnails ------------------------------------- */
.modpack-block {
  margin-top: 36px;
  padding-top: 28px;
  border-top: 1px solid #262626;
}
.world-map-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 14px;
}
.world-map-card {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid #2a2a2a;
  border-radius: 10px;
  overflow: hidden;
}
.world-map-thumb {
  position: relative;
  aspect-ratio: 4 / 3;
  background: #0c0f14;
  cursor: default;
}
.world-map-card:has(.world-map-status.done) .world-map-thumb {
  cursor: pointer;
}
.world-map-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  image-rendering: pixelated;
}
.world-map-thumb-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #3a3a3a;
}
.world-map-card-body {
  padding: 12px 14px;
}
.world-map-status {
  display: block;
  font-size: 0.78rem;
  color: #999;
  margin: 4px 0 10px;
}
.world-map-status.error {
  color: #fca5a5;
}
.world-map-status.done {
  color: #86efac;
}
.world-map-status.rendering {
  color: #d68a34;
}
.world-map-card-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.world-map-progress {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 4px;
  border-radius: 0;
  background: rgba(0, 0, 0, 0.4);
  overflow: hidden;
}
.world-map-progress-fill {
  width: 30%;
  height: 100%;
  border-radius: 999px;
  background: #d68a34;
  animation: world-map-scan 1.2s ease-in-out infinite;
}
@keyframes world-map-scan {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(333%);
  }
}
.world-map-frame {
  width: 100%;
  height: 70vh;
  border: 1px solid #2a2a2a;
  border-radius: 10px;
  margin-top: 16px;
  background: #000;
}
.file-size {
  color: #777;
  font-size: 0.78rem;
  flex-shrink: 0;
}
.tile-remove-inline {
  background: none;
  border: none;
  color: #777;
  cursor: pointer;
  font-size: 13px;
  padding: 2px 4px;
  flex-shrink: 0;
}
.tile-remove-inline:hover {
  color: #fca5a5;
}
.not-found {
  padding: 24px;
  color: #fff;
}
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
.confirm-actions .secondary-button,
.confirm-actions .danger-button {
  padding: 10px 18px;
}
.secondary-button {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}
</style>
