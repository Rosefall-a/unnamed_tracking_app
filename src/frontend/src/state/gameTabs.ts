// The tabs across the top of the games library: the built-in ones (All,
// Library, the statuses, Set aside...) and the ones you make yourself. A tab
// you make is a name and rules, the same rules smart collections use (status,
// tag, platform, "In collection" for games you put there by hand). It can also
// keep its games out of your other tabs, so a pile you are not playing (online
// games, test servers, books) stops crowding the backlog.
// Saved to your account (state/uiState.ts), with your collections.
import { computed } from "vue";
import { getUi, setUi } from "./uiState";
import {
  matchesSmartCollection,
  renameCollectionInRules,
  type SmartCondition,
  type SmartMatch,
} from "./smartCollections";
import type { Game, GameStatus } from "../types/game";

export interface CustomGameTab {
  id: string;
  name: string;
  // the statuses this tab shows; missing means every status
  statuses?: GameStatus[];
  rules: SmartCondition[];
  match: SmartMatch;
  // its games are shown only here, not in All, Library or the other tabs
  hideElsewhere: boolean;
}

interface TabsState {
  custom: CustomGameTab[];
  // every tab's id in the order shown; a tab missing from it goes at the end
  order: string[];
  // built-in tabs you chose not to show
  hidden: string[];
  // the statuses All shows; missing means every status
  allStatuses?: GameStatus[];
}

// the built-in tabs and what they are called
export const BUILT_IN_TABS: { id: string; label: string }[] = [
  { id: "all", label: "All" },
  { id: "library", label: "Library" },
  { id: "playing", label: "Playing" },
  { id: "beaten", label: "Beaten" },
  { id: "mastered", label: "Mastered" },
  { id: "played", label: "Played" },
  { id: "on hold", label: "On hold" },
  { id: "dropped", label: "Dropped" },
  { id: "backlog", label: "Backlog" },
  { id: "wishlist", label: "Wishlist" },
  { id: "set aside", label: "Set aside" },
];
const BUILT_IN_IDS = new Set(BUILT_IN_TABS.map((t) => t.id));

const KEY = "gameTabs";
const EMPTY: TabsState = { custom: [], order: [], hidden: [] };

const state = computed<TabsState>({
  get: () => {
    const saved = getUi<Partial<TabsState> | null>(KEY, null);
    if (!saved || typeof saved !== "object") return EMPTY;
    return {
      custom: Array.isArray(saved.custom) ? saved.custom : [],
      order: Array.isArray(saved.order) ? saved.order : [],
      hidden: Array.isArray(saved.hidden) ? saved.hidden : [],
      allStatuses: Array.isArray(saved.allStatuses)
        ? saved.allStatuses
        : undefined,
    };
  },
  set: (next) => setUi(KEY, next),
});

export const customTabs = computed(() => state.value.custom);
// the statuses All shows, or null for every one
export const allTabStatuses = computed(() => state.value.allStatuses ?? null);
export function setAllTabStatuses(statuses: GameStatus[] | null) {
  save({ allStatuses: statuses ?? undefined });
}
export const customTabId = (tab: CustomGameTab) => `custom:${tab.id}`;

export interface TabEntry {
  id: string;
  label: string;
  custom: CustomGameTab | null;
  hidden: boolean;
}

// every tab in order, hidden ones included (for the editor)
export const allTabs = computed<TabEntry[]>(() => {
  const { custom, order, hidden } = state.value;
  const entries: TabEntry[] = [
    ...BUILT_IN_TABS.map((t) => ({
      id: t.id,
      label: t.label,
      custom: null,
      hidden: hidden.includes(t.id),
    })),
    ...custom.map((c) => ({
      id: customTabId(c),
      label: c.name,
      custom: c,
      hidden: false,
    })),
  ];
  const at = (id: string) => {
    const i = order.indexOf(id);
    if (i !== -1) return i;
    // a tab not placed yet keeps its default place, after the placed ones
    return order.length + entries.findIndex((e) => e.id === id);
  };
  return entries.sort((a, b) => at(a.id) - at(b.id));
});

// the tabs the library shows; All is always there
export const shownTabs = computed(() =>
  allTabs.value.filter((t) => !t.hidden || t.id === "all"),
);

function save(next: Partial<TabsState>) {
  state.value = { ...state.value, ...next };
}

export function addCustomTab(tab: Omit<CustomGameTab, "id">): string {
  const id = Math.random().toString(36).slice(2, 10);
  const order = allTabs.value.map((t) => t.id);
  // in front of Set aside, so it sits with the others you use
  const setAsideAt = order.indexOf("set aside");
  order.splice(
    setAsideAt === -1 ? order.length : setAsideAt,
    0,
    `custom:${id}`,
  );
  save({ custom: [...state.value.custom, { ...tab, id }], order });
  return id;
}

export function updateCustomTab(id: string, tab: Omit<CustomGameTab, "id">) {
  save({
    custom: state.value.custom.map((c) => (c.id === id ? { ...tab, id } : c)),
  });
}

export function removeCustomTab(id: string) {
  save({
    custom: state.value.custom.filter((c) => c.id !== id),
    order: state.value.order.filter((o) => o !== `custom:${id}`),
  });
}

export function renameCollectionInTabs(from: string, to: string) {
  save({
    custom: state.value.custom.map((c) => ({
      ...c,
      rules: renameCollectionInRules(c.rules, from, to),
    })),
  });
}

export function moveTab(id: string, by: -1 | 1) {
  const order = allTabs.value.map((t) => t.id);
  const i = order.indexOf(id);
  const j = i + by;
  if (i === -1 || j < 0 || j >= order.length) return;
  [order[i], order[j]] = [order[j], order[i]];
  save({ order });
}

// put a tab just before or just after another one (dragging on the tab bar)
export function placeTab(id: string, targetId: string, after: boolean) {
  if (id === targetId) return;
  const order = allTabs.value.map((t) => t.id).filter((t) => t !== id);
  const at = order.indexOf(targetId);
  if (at === -1) return;
  order.splice(after ? at + 1 : at, 0, id);
  save({ order });
}

export function setTabHidden(id: string, hide: boolean) {
  if (!BUILT_IN_IDS.has(id) || id === "all") return;
  const hidden = state.value.hidden.filter((h) => h !== id);
  save({ hidden: hide ? [...hidden, id] : hidden });
}

export function matchesCustomTab(game: Game, tab: CustomGameTab): boolean {
  if (tab.statuses && !tab.statuses.includes(game.status)) return false;
  if (!tab.rules.length) return true;
  return matchesSmartCollection(game, {
    id: tab.id,
    name: tab.name,
    ...tab.rules[0],
    rules: tab.rules,
    match: tab.match,
  });
}

// a game one of your "keep these here only" tabs has claimed
export function claimedByTab(game: Game): CustomGameTab | null {
  return (
    state.value.custom.find(
      (t) =>
        t.hideElsewhere &&
        (t.rules.length > 0 || !!t.statuses) &&
        matchesCustomTab(game, t),
    ) ?? null
  );
}
