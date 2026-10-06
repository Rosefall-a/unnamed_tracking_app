// What a game's page shows. There is one set of defaults for every game (a
// setting in Settings > Game page) and each game can override any part of it
// (the Page tab of its Edit dialog). A tab is set to Show, Hide, or Auto, which
// means "only once the game has something in it". Hiding a tab also hides the
// parts of the page that only make sense with it: with no Achievements tab
// there is no achievement badge, no achievement stats, and no tying files to
// achievements.

export const OPTIONAL_TABS = [
  "Achievements",
  "Screenshots",
  "Clips",
  "Soundtrack",
  "Saves",
  "Docs",
  "Notes",
  "Stats",
] as const;
export type OptionalTab = (typeof OPTIONAL_TABS)[number];
export type TabMode = "show" | "hide" | "auto";

export const HIDE_FLAGS = [
  "hide_rating",
  "hide_collections",
  "hide_favorite",
  "hide_credits",
  "hide_date_badge",
  "hide_platform_badge",
  "hide_history",
] as const;
export type HideFlag = (typeof HIDE_FLAGS)[number];

export interface PageSettings {
  tabs: Record<OptionalTab, TabMode>;
  // the tab a game opens on
  default_tab: "Overview" | OptionalTab;
  hide_rating: boolean;
  hide_collections: boolean;
  hide_favorite: boolean;
  hide_credits: boolean;
  hide_date_badge: boolean;
  hide_platform_badge: boolean;
  hide_history: boolean;
}

// a game's overrides: only what differs from the defaults is present
export type PageOverrides = Partial<Omit<PageSettings, "tabs">> & {
  tabs?: Partial<Record<OptionalTab, TabMode>>;
};

export const DEFAULT_PAGE_SETTINGS: PageSettings = {
  tabs: Object.fromEntries(OPTIONAL_TABS.map((t) => [t, "show"])) as Record<
    OptionalTab,
    TabMode
  >,
  default_tab: "Overview",
  hide_rating: false,
  hide_collections: false,
  hide_favorite: false,
  hide_credits: false,
  hide_date_badge: false,
  hide_platform_badge: false,
  hide_history: false,
};

export const TAB_HINTS: Record<OptionalTab, string> = {
  Achievements: "The achievement list, and everything that depends on it",
  Screenshots: "Screenshot gallery",
  Clips: "Video clips",
  Soundtrack: "Music and audio files",
  Saves: "Named save files with versions",
  Docs: "Manuals, guides and other files",
  Notes: "Your markdown notes",
  Stats: "Playtime, dates and the history timeline",
};

export const FLAG_LABELS: Record<HideFlag, { label: string; hint: string }> = {
  hide_rating: {
    label: "Hide the score button",
    hint: "The star rating in the header and the score in the stats.",
  },
  hide_collections: {
    label: "Hide the collections button",
    hint: "The list button next to Edit.",
  },
  hide_favorite: {
    label: "Hide the favorite heart",
    hint: "The heart next to Edit.",
  },
  hide_credits: {
    label: "Hide developer and publisher",
    hint: "The line above the title.",
  },
  hide_date_badge: {
    label: "Hide the date badge",
    hint: "The date added, under the title.",
  },
  hide_platform_badge: {
    label: "Hide the platform badge",
    hint: "The platform, under the title.",
  },
  hide_history: {
    label: "Hide the history timeline",
    hint: "Keeps the numbers in Stats but drops the timeline below them.",
  },
};

export function resolvePage(
  defaults: Partial<PageSettings> | null | undefined,
  overrides: PageOverrides | null | undefined,
): PageSettings {
  return {
    ...DEFAULT_PAGE_SETTINGS,
    ...(defaults ?? {}),
    ...(overrides ?? {}),
    tabs: {
      ...DEFAULT_PAGE_SETTINGS.tabs,
      ...(defaults?.tabs ?? {}),
      ...(overrides?.tabs ?? {}),
    },
  };
}

export interface ContentCounts {
  achievements: number;
  screenshots: number;
  clips: number;
  soundtrack: number;
  saves: number;
  worlds: number;
  docs: number;
  notes: number;
}

// whether a game has anything in a tab, which is what Auto looks at
export function hasContent(
  tab: OptionalTab,
  counts: ContentCounts | null,
  game: { achievementTotal: number; platforms: { playtimeMinutes: number }[] },
): boolean {
  switch (tab) {
    case "Achievements":
      return game.achievementTotal > 0 || (counts?.achievements ?? 0) > 0;
    case "Screenshots":
      return (counts?.screenshots ?? 0) > 0;
    case "Clips":
      return (counts?.clips ?? 0) > 0;
    case "Soundtrack":
      return (counts?.soundtrack ?? 0) > 0;
    case "Saves":
      return (counts?.saves ?? 0) > 0;
    case "Docs":
      return (counts?.docs ?? 0) > 0;
    case "Notes":
      return (counts?.notes ?? 0) > 0;
    case "Stats":
      return (
        game.achievementTotal > 0 ||
        game.platforms.some((p) => p.playtimeMinutes > 0)
      );
  }
}

export interface TabPlan {
  // the tabs shown in the bar, in order
  visible: string[];
  // tabs set to Auto that are empty: reachable from the "+" menu
  more: string[];
}

// Works out the tab bar. The tab you are on always stays, so a tab that
// empties (or is hidden) under you does not make the page jump.
export function planTabs(
  all: readonly string[],
  settings: PageSettings,
  counts: ContentCounts | null,
  game: Parameters<typeof hasContent>[2],
  active: string,
): TabPlan {
  const visible: string[] = [];
  const more: string[] = [];
  for (const tab of all) {
    if (!(OPTIONAL_TABS as readonly string[]).includes(tab)) {
      visible.push(tab);
      continue;
    }
    const mode = settings.tabs[tab as OptionalTab];
    if (mode === "show" || tab === active) visible.push(tab);
    else if (mode === "auto") {
      // until the counts arrive, an Auto tab is shown rather than flicker in
      if (counts === null || hasContent(tab as OptionalTab, counts, game))
        visible.push(tab);
      else more.push(tab);
    }
  }
  return { visible, more };
}
