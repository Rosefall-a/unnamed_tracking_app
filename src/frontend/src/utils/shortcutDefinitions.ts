import { isGameDetailPath } from "../state/libraryScroll";

export interface ShortcutDefinition {
  id: string;
  label: string;
  group: string;
  keys: string[];
  paths?: string[];
  context?: string;
  destination?: string;
  pluginId?: string;
  control?: "search" | "create";
}
export const NAVIGATION_SHORTCUTS = [
  { key: "h", label: "Home", path: "/" },
  { key: "g", label: "Games", path: "/games" },
  { key: "c", label: "Game collections", path: "/games/collections" },
  { key: "m", label: "Movies", path: "/movies" },
  { key: "t", label: "TV shows", path: "/tv" },
  { key: "a", label: "Anime", path: "/anime" },
  { key: "l", label: "Media collections", path: "/media/collections" },
  { key: "v", label: "Calendar", path: "/calendar" },
  { key: "r", label: "Statistics", path: "/statistics" },
  { key: "p", label: "Settings", path: "/settings" },
  { key: "u", label: "Upload", path: "/upload" },
  { key: "o", label: "Notifications", path: "/notifications" },
] as const;

export const CORE_SHORTCUTS: ShortcutDefinition[] = [
  {
    id: "app.search",
    group: "Anywhere",
    label: "Search library",
    keys: ["CtrlOrMeta+K"],
  },
  {
    id: "app.help",
    group: "Anywhere",
    label: "Show keyboard shortcuts",
    keys: ["?"],
  },
  {
    id: "app.focus-search",
    group: "Anywhere",
    label: "Focus this page's search, or open Search library",
    keys: ["/"],
  },
  ...NAVIGATION_SHORTCUTS.map((item) => ({
    id: `nav.${item.key}`,
    group: "Anywhere",
    label: `Go to ${item.label}`,
    destination: item.path,
    keys: [`Alt+${item.key.toUpperCase()}`],
  })),
  {
    id: "app.create",
    group: "Page actions",
    label: "Add a title or create a collection",
    keys: ["N"],
    paths: [
      "/games",
      "/movies",
      "/tv",
      "/anime",
      "/games/collections",
      "/media/collections",
      "/collections",
      "/lists",
    ],
  },
  {
    id: "games.next",
    group: "Game page",
    label: "Next game from the previous library",
    keys: ["J"],
    paths: ["/games/*"],
  },
  {
    id: "games.previous",
    group: "Game page",
    label: "Previous game from the previous library",
    keys: ["K"],
    paths: ["/games/*"],
  },
  {
    id: "games.preview.next",
    group: "Games library",
    label: "Next selection (List + preview)",
    keys: ["J", "ArrowDown"],
    paths: ["/games"],
    context: "games.preview",
  },
  {
    id: "games.preview.previous",
    group: "Games library",
    label: "Previous selection (List + preview)",
    keys: ["K", "ArrowUp"],
    paths: ["/games"],
    context: "games.preview",
  },
  ...["Left", "Right", "Up", "Down"].map((direction) => ({
    id: `games.cards.${direction.toLowerCase()}`,
    group: "Games library",
    label: `Move card focus ${direction.toLowerCase()}`,
    keys: [`Arrow${direction}`],
    paths: ["/games"],
    context: "games.cards",
  })),
  {
    id: "games.cards.open",
    group: "Games library",
    label: "Open focused card",
    keys: ["Enter"],
    paths: ["/games"],
    context: "games.cards",
  },
  {
    id: "calendar.previous",
    group: "Calendar",
    label: "Previous month or week",
    keys: ["ArrowLeft"],
    paths: ["/calendar"],
  },
  {
    id: "calendar.next",
    group: "Calendar",
    label: "Next month or week",
    keys: ["ArrowRight"],
    paths: ["/calendar"],
  },
  {
    id: "calendar.today",
    group: "Calendar",
    label: "Jump to today",
    keys: ["T"],
    paths: ["/calendar"],
  },
];
export function shortcutPathMatches(
  paths: string[] | undefined,
  path: string,
): boolean {
  return (
    !paths?.length ||
    paths.some((pattern) =>
      pattern === "/games/*"
        ? isGameDetailPath(path)
        : pattern.endsWith("*")
          ? path.startsWith(pattern.slice(0, -1))
          : pattern === path,
    )
  );
}
export function shortcutScopesOverlap(
  first: ShortcutDefinition,
  second: ShortcutDefinition,
): boolean {
  if (first.context && second.context && first.context !== second.context)
    return false;
  if (!first.paths?.length || !second.paths?.length) return true;
  return first.paths.some((a) =>
    second.paths!.some(
      (b) =>
        a === b ||
        (a.endsWith("*") && b.startsWith(a.slice(0, -1))) ||
        (b.endsWith("*") && a.startsWith(b.slice(0, -1))),
    ),
  );
}
