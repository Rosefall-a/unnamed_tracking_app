import { computed, ref, watch } from "vue";
import {
  listGameProfiles,
  createGameProfile,
  renameGameProfile,
  updateGameProfile,
  deleteGameProfile,
  syncProfileWiseOldMan,
  fetchProfileStatHistory,
} from "../services/gameProfiles";
import type { GameProfile, StatSnapshot } from "../services/gameProfiles";
import type { Game } from "../types/game";
import { usePrompt } from "../state/dialog";
import type { Ref } from "vue";
export function useGameProfiles(
  game: Ref<Game | null>,
  prompt: ReturnType<typeof usePrompt>,
) {
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

  return {
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
  };
}
