// What every sidebar style shows: recent titles, pins, counts, the page Media
// opens on, and a way to open search. One place, so the eight styles always
// agree. The titles come from the same cached library data Home uses.
import { computed, ref } from "vue";
import { allTitles, ensure, titlesByKind, type HomeTitle } from "../home/data";
import { isCommandPaletteOpen } from "./commandPalette";
import {
  mediaHome,
  sidebarJumpCount,
  sidebarPins,
  sidebarShowCounts,
  sidebarShowJump,
  type SidebarStyle,
} from "./sidebarPrefs";

let loaded = false;
export function loadNavData(): void {
  if (loaded || (!sidebarShowJump.value && !sidebarShowCounts.value)) return;
  loaded = true;
  for (const key of ["games", "movies", "tv", "anime"] as const)
    void ensure(key);
}

export function dayLabel(ms: number): string {
  const days = Math.floor(
    (new Date().setHours(0, 0, 0, 0) - new Date(ms).setHours(0, 0, 0, 0)) /
      86_400_000,
  );
  if (days <= 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days} days ago`;
  return new Date(ms).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

export interface NavTitle {
  key: string;
  title: string;
  art: string | null;
  to: string;
  meta: string;
  kind: HomeTitle["kind"];
}

function toNav(t: HomeTitle): NavTitle {
  return {
    key: t.key,
    title: t.title,
    art: t.art,
    to: t.to,
    meta: dayLabel(t.touchedAt),
    kind: t.kind,
  };
}

// everything, most recently played or watched first
export const recentTitles = computed<NavTitle[]>(() =>
  allTitles.value
    .filter((t) => t.touchedAt > 0)
    .sort((a, b) => b.touchedAt - a.touchedAt)
    .slice(0, 40)
    .map(toNav),
);
export const jumpItems = computed(() =>
  recentTitles.value.slice(0, sidebarJumpCount.value),
);
export const pins = sidebarPins;

export const counts = computed(() => ({
  game: titlesByKind.value.game.length,
  anime: titlesByKind.value.anime.length,
  movie: titlesByKind.value.movie.length,
  tv: titlesByKind.value.tv.length,
}));
export const mediaCount = computed(() => {
  const home = mediaHome();
  if (home === "/movies") return counts.value.movie;
  if (home === "/tv") return counts.value.tv;
  return counts.value.anime;
});

// the game collections and how many games are in each, biggest first
export const gameCollections = computed(() => {
  const byName = new Map<string, number>();
  for (const t of titlesByKind.value.game)
    for (const c of t.collections) byName.set(c, (byName.get(c) ?? 0) + 1);
  return [...byName.entries()]
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .map(([name, count]) => ({ name, count }));
});

export function openSearch(): void {
  isCommandPaletteOpen.value = true;
}

// The pages every style links to, with the icon each one uses. Media's address
// and icon follow "Media opens on".
export const ICONS = {
  home: "M4 11l8-7 8 7 M6 10v9a1 1 0 0 0 1 1h3v-5h4v5h3a1 1 0 0 0 1-1v-9",
  games:
    "M6 6h12a3 3 0 0 1 3 3v1l1.3 7a2.2 2.2 0 0 1-4 1.7L17 16H7l-1.3 2.7a2.2 2.2 0 0 1-4-1.7L3 10v-1a3 3 0 0 1 3-3z M7.3 9.3v4M5.3 11.3h4",
  media: "M12 3a9 9 0 1 0 0 18 9 9 0 1 0 0-18z M10 8.5l6 3.5-6 3.5z",
  anime:
    "M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z M19 15l.7 2 2 .7-2 .7-.7 2-.7-2-2-.7 2-.7z",
  movies:
    "M5 3h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z M3 8h18",
  tv: "M4 5h16a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z M8 21h8M12 18v3",
  collections: "M4 7l8-4 8 4-8 4-8-4z M4 12l8 4 8-4M4 17l8 4 8-4",
  calendar:
    "M5 5h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z M3 10h18M8 3v4M16 3v4",
  stats: "M5 20v-6 M12 20V9 M19 20V4",
  upload: "M12 16V4 M8 8l4-4 4 4 M4 16v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3",
  settings:
    "M12 9a3 3 0 1 0 0 6 3 3 0 1 0 0-6z M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1 7 17M17 7l2.1-2.1",
  search: "M11 4a7 7 0 1 0 0 14 7 7 0 1 0 0-14z M20 20l-3.5-3.5",
  clock: "M12 3a9 9 0 1 0 0 18 9 9 0 1 0 0-18z M12 7v5l3 2",
  pin: "M12 17v5 M9 3h6l-1 7 4 3H6l4-3z",
  chevron: "M9 18l6-6-6-6",
  down: "M6 9l6 6 6-6",
  x: "M18 6 6 18 M6 6l12 12",
} as const;

export interface NavPage {
  id: string;
  label: string;
  to: string;
  icon: string;
}
export const navPages = computed<NavPage[]>(() => {
  const media = mediaHome();
  return [
    { id: "home", label: "Home", to: "/", icon: ICONS.home },
    { id: "games", label: "Games", to: "/games", icon: ICONS.games },
    { id: "media", label: "Media", to: media, icon: ICONS.media },
    {
      id: "calendar",
      label: "Calendar",
      to: "/calendar",
      icon: ICONS.calendar,
    },
    { id: "stats", label: "Statistics", to: "/statistics", icon: ICONS.stats },
  ];
});
export const MEDIA_PAGES = [
  { id: "anime", label: "Anime", to: "/anime", icon: ICONS.anime },
  { id: "movies", label: "Movies", to: "/movies", icon: ICONS.movies },
  { id: "tv", label: "TV", to: "/tv", icon: ICONS.tv },
  {
    id: "lists",
    label: "Collections",
    to: "/media/collections",
    icon: ICONS.collections,
  },
];

export function isActivePath(path: string, current: string): boolean {
  if (path === "/") return current === "/";
  if (["/anime", "/movies", "/tv"].includes(path))
    return ["/anime", "/movies", "/tv", "/media/collections"].some(
      (p) => current === p || current.startsWith(`${p}/`),
    );
  return current === path || current.startsWith(`${path}/`);
}

// Which styles keep a sidebar on the left; the rest put navigation elsewhere.
export function usesSideNav(style: SidebarStyle): boolean {
  return ["classic", "minimal", "library", "railpanel", "peek"].includes(style);
}
// Only the list styles can be always open, behind a button, or an icon rail.
export function usesShowMode(style: SidebarStyle): boolean {
  return ["classic", "minimal", "library"].includes(style);
}

// the Guide panel, the Top bar's menus and the Dock share one "what is open"
export const openMenu = ref<string>("");
