export interface ShortcutGroup {
  title: string;
  paths?: RegExp[];
  shortcuts: { keys: string; label: string }[];
}

export const NAVIGATION_SHORTCUTS = [
  { key: "h", label: "Home", path: "/" },
  { key: "g", label: "Games", path: "/games" },
  { key: "c", label: "Collections", path: "/collections" },
  { key: "m", label: "Movies", path: "/movies" },
  { key: "t", label: "TV shows", path: "/tv" },
  { key: "a", label: "Anime", path: "/anime" },
  { key: "l", label: "Lists", path: "/lists" },
  { key: "e", label: "Cards", path: "/cards" },
  { key: "s", label: "Sets", path: "/sets" },
  { key: "b", label: "Bounties", path: "/bounties" },
  { key: "v", label: "Calendar", path: "/calendar" },
  { key: "r", label: "Statistics", path: "/statistics" },
  { key: "p", label: "Settings", path: "/settings" },
  { key: "u", label: "Upload", path: "/upload" },
  { key: "o", label: "Notifications", path: "/notifications" },
] as const;

export function navigationShortcutForKey(key: unknown) {
  if (typeof key !== "string" || key.length !== 1) return undefined;
  return NAVIGATION_SHORTCUTS.find((item) => item.key === key.toLowerCase());
}

// One list for both the `?` overlay and Settings → Keyboard Shortcuts, so
// the two can never disagree about what a key does. Page-specific groups
// describe real controls; global navigation remains available on every page.
export const SHORTCUT_GROUPS: ShortcutGroup[] = [
  {
    title: "Games library",
    paths: [/^\/games$/],
    shortcuts: [
      { keys: "/", label: "Focus search" },
      { keys: "n", label: "Add a game" },
      { keys: "j / k or ↓ / ↑", label: "Move selection (List + preview view)" },
      {
        keys: "← ↑ → ↓",
        label: "Move focus between cards (Cards view)",
      },
      { keys: "Enter", label: "Open the focused card (Cards view)" },
      {
        keys: "a–z",
        label: "Jump to the first game starting with that letter (Cards view)",
      },
      { keys: "Esc", label: "Clear search, close panels" },
    ],
  },
  {
    title: "Game page",
    paths: [/^\/games\/.+/],
    shortcuts: [
      {
        keys: "j / k",
        label: "Next / previous game (from the library you came from)",
      },
    ],
  },
  {
    title: "Calendar",
    paths: [/^\/calendar$/],
    shortcuts: [
      { keys: "← / →", label: "Previous / next month or week" },
      { keys: "t", label: "Jump to today" },
    ],
  },
  {
    title: "Media libraries",
    paths: [/^\/(movies|tv|anime)$/],
    shortcuts: [
      { keys: "/", label: "Focus library search" },
      { keys: "n", label: "Add a title" },
    ],
  },
  {
    title: "Collections & lists",
    paths: [/^\/(collections|lists)$/],
    shortcuts: [
      { keys: "/", label: "Focus search" },
      { keys: "n", label: "Create a collection or list" },
    ],
  },
  {
    title: "Cards",
    paths: [/^\/cards$/, /^\/plugins\/official\.collectors-archive\/cards$/],
    shortcuts: [{ keys: "n", label: "Create a card" }],
  },
  {
    title: "Sets",
    paths: [/^\/sets$/, /^\/plugins\/official\.collectors-archive\/sets$/],
    shortcuts: [{ keys: "n", label: "Focus the new set name" }],
  },
  {
    title: "Bounties",
    paths: [
      /^\/bounties$/,
      /^\/plugins\/official\.collectors-archive\/bounties$/,
    ],
    shortcuts: [
      { keys: "/", label: "Focus bounty search" },
      { keys: "n", label: "Create a bounty" },
    ],
  },
  {
    title: "Anywhere",
    shortcuts: [
      {
        keys: "Ctrl/Cmd + K",
        label:
          "Search games, media, collections, goals, settings and extensions",
      },
      { keys: "/", label: "Focus this page's search, or open Search library" },
      { keys: "?", label: "Show shortcuts for the current page first" },
      ...NAVIGATION_SHORTCUTS.map((item) => ({
        keys: "Alt + " + item.key.toUpperCase(),
        label: "Go to " + item.label,
      })),
      { keys: "Tab / Shift + Tab", label: "Move between controls" },
      { keys: "Enter / Space", label: "Activate the focused control" },
      { keys: "Esc", label: "Close the notification or profile menu" },
    ],
  },
];

export function shortcutGroupsForPath(path: string): ShortcutGroup[] {
  const current = SHORTCUT_GROUPS.filter((group) =>
    group.paths?.some((pattern) => pattern.test(path)),
  );
  const anywhere = SHORTCUT_GROUPS.find((group) => group.title === "Anywhere")!;
  return [
    ...current,
    anywhere,
    ...SHORTCUT_GROUPS.filter(
      (group) => group !== anywhere && !current.includes(group),
    ),
  ];
}

export function navigationShortcutForPath(path: string): string | undefined {
  const pathname = path.split("?")[0];
  const archive =
    /^\/plugins\/official\.collectors-archive\/(cards|sets|bounties)$/.exec(
      pathname ?? "",
    );
  const destination = archive ? `/${archive[1]}` : pathname;
  const item = NAVIGATION_SHORTCUTS.find((item) => item.path === destination);
  return item ? "Alt+" + item.key.toUpperCase() : undefined;
}
export function navigationTooltip(label: string, path: string): string {
  const shortcut = navigationShortcutForPath(path);
  return shortcut ? `${label} · ${shortcut.replace("+", " + ")}` : label;
}
