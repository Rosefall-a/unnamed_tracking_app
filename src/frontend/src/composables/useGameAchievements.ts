import { computed, ref, watch } from "vue";
import type { Achievement, Game } from "../types/game";
import type { SegmentOption } from "../components/SegmentedTabs.vue";
import { isUnlocked, formatPercent } from "../utils/achievements";
import {
  loadAchievementLocal,
  saveAchievementLocal,
} from "../state/achievementLocal";
import type { AchievementLocal } from "../state/achievementLocal";
import type { Ref } from "vue";
export type AchFilter = "all" | "unlocked" | "locked" | "hidden" | "pinned";

export function useGameAchievements(
  game: Ref<Game | null>,
  reload: () => Promise<void>,
) {
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
      if (achFilter.value === "hidden" && !(a.hidden && !unlocked))
        return false;
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
      if (week)
        stats.push({ label: "in the past 7 days", value: String(week) });
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
  void reload();

  return {
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
