// The Settings menu: six pages, each split into tabs. Settings.vue renders the
// sections a tab lists; this file only says what goes where, so the menu, the
// search and old links all agree.

export type SettingsPart =
  | "profile"
  | "connections"
  | "anilist"
  | "api-keys"
  | "devices"
  | "appearance"
  | "appearance-badge"
  | "display"
  | "interface"
  | "sidebar"
  | "media-prefs"
  | "game-page"
  | "shortcuts"
  | "notifications"
  | "calendar"
  | "upload"
  | "duplicates"
  | "library-folders"
  | "library-refresh"
  | "media-trash"
  | "export"
  | "metadata-sources"
  | "scan"
  | "steam-tags"
  | "steam-wishlist"
  | "media-refresh"
  | "stats"
  | "server-overview"
  | "users"
  | "tasks"
  | "backups"
  | "repair"
  | "oidc"
  | "server-integrations"
  | "limits"
  | "password-policy"
  | "dev-tools"
  | "logs";

export interface SettingsTabDef {
  id: string;
  label: string;
  parts: SettingsPart[];
  adminOnly?: boolean;
}

export interface SettingsPageDef {
  id: string;
  label: string;
  // one line under the name in the menu, saying what is inside
  sub: string;
  // one sentence under the page title
  lead: string;
  group: string;
  tabs: SettingsTabDef[];
}

export const SETTINGS_PAGES: SettingsPageDef[] = [
  {
    id: "account",
    label: "Account",
    sub: "Profile, linked accounts, devices",
    lead: "You, the accounts your library syncs from, and keys for other apps.",
    group: "You",
    tabs: [
      { id: "profile", label: "Profile", parts: ["profile"] },
      {
        id: "connections",
        label: "Linked accounts",
        parts: ["connections", "anilist"],
      },
      { id: "keys", label: "App keys", parts: ["api-keys"] },
      {
        id: "devices",
        label: "Signed-in devices",
        parts: ["devices"],
      },
    ],
  },
  {
    id: "look",
    label: "Look and feel",
    sub: "Colours, views, game page",
    lead: "How the app looks and what each page opens on. Saved to your account.",
    group: "App",
    tabs: [
      {
        id: "appearance",
        label: "Appearance",
        parts: ["appearance", "display", "appearance-badge"],
      },
      {
        id: "nav",
        label: "Sidebar and navigation",
        parts: ["sidebar"],
      },
      {
        id: "views",
        label: "Library views",
        parts: ["interface", "media-prefs"],
      },
      { id: "game-page", label: "Game page", parts: ["game-page"] },
      { id: "shortcuts", label: "Shortcuts", parts: ["shortcuts"] },
    ],
  },
  {
    id: "notify",
    label: "Notifications",
    sub: "Bell and calendar",
    lead: "What reaches the bell, and what the calendar shows.",
    group: "App",
    tabs: [
      { id: "bell", label: "Bell", parts: ["notifications"] },
      { id: "calendar", label: "Calendar", parts: ["calendar"] },
    ],
  },
  {
    id: "library",
    label: "Library",
    sub: "Upload, tidy up, trash, import",
    lead: "Add files, clean up duplicates, get things back, and move your library in or out.",
    group: "Library",
    tabs: [
      { id: "upload", label: "Upload", parts: ["upload"] },
      {
        id: "tidy",
        label: "Tidy up",
        parts: ["duplicates", "library-folders"],
      },
      { id: "trash", label: "Trash", parts: ["media-trash"] },
      { id: "io", label: "Import and export", parts: ["export"] },
    ],
  },
  {
    id: "sources",
    label: "Data sources",
    sub: "Providers, what gets saved, refresh",
    lead: "Where details and art come from, what they may change, and refreshing them.",
    group: "Library",
    tabs: [
      { id: "providers", label: "Providers", parts: ["metadata-sources"] },
      {
        id: "saved",
        label: "What gets saved",
        parts: ["scan", "steam-tags", "steam-wishlist"],
      },
      {
        id: "refresh",
        label: "Refresh",
        parts: ["library-refresh", "media-refresh"],
      },
    ],
  },
  {
    id: "server",
    label: "Server",
    sub: "Overview, users, tasks, backups",
    lead: "Everything that runs the server. Only admins see more than the overview.",
    group: "Server",
    tabs: [
      {
        id: "overview",
        label: "Overview",
        parts: ["server-overview", "stats"],
      },
      {
        id: "users",
        label: "Users",
        parts: ["users", "password-policy"],
        adminOnly: true,
      },
      {
        id: "tasks",
        label: "Tasks and backups",
        parts: ["tasks", "backups"],
        adminOnly: true,
      },
      { id: "repair", label: "Repair", parts: ["repair"], adminOnly: true },
      {
        id: "access",
        label: "Access and limits",
        parts: ["oidc", "limits", "server-integrations"],
        adminOnly: true,
      },
      { id: "dev", label: "Dev tools", parts: ["dev-tools"], adminOnly: true },
      { id: "logs", label: "Logs", parts: ["logs"], adminOnly: true },
    ],
  },
];

export interface SettingsPlace {
  section: string;
  tab: string;
}

// Every id Settings used before the pages were merged, so bookmarks, the
// command palette and links elsewhere in the app keep landing on the right tab.
const OLD_SECTIONS: Record<string, SettingsPlace> = {
  profile: { section: "account", tab: "profile" },
  connections: { section: "account", tab: "connections" },
  "api-keys": { section: "account", tab: "keys" },
  interface: { section: "look", tab: "views" },
  "game-page": { section: "look", tab: "game-page" },
  appearance: { section: "look", tab: "appearance" },
  shortcuts: { section: "look", tab: "shortcuts" },
  "media-prefs": { section: "look", tab: "views" },
  notifications: { section: "notify", tab: "bell" },
  "calendar-notifications": { section: "notify", tab: "bell" },
  calendar: { section: "notify", tab: "calendar" },
  upload: { section: "library", tab: "upload" },
  "media-trash": { section: "library", tab: "trash" },
  export: { section: "library", tab: "io" },
  metadata: { section: "sources", tab: "providers" },
  scan: { section: "sources", tab: "saved" },
  "media-refresh": { section: "sources", tab: "refresh" },
  stats: { section: "server", tab: "overview" },
  admin: { section: "server", tab: "users" },
  users: { section: "server", tab: "users" },
  tasks: { section: "server", tab: "tasks" },
  backups: { section: "server", tab: "tasks" },
  repair: { section: "server", tab: "repair" },
  oidc: { section: "server", tab: "access" },
  "server-integrations": { section: "server", tab: "access" },
  "password-policy": { section: "server", tab: "users" },
  logs: { section: "server", tab: "logs" },
};

// The old merged pages had tabs of their own; the same tab name now lives on a
// different page, or under a new name.
const OLD_TABS: Record<string, SettingsPlace> = {
  "library:manage": { section: "library", tab: "tidy" },
  "library:preferences": { section: "look", tab: "views" },
  "library:trash": { section: "library", tab: "trash" },
  "metadata:sources": { section: "sources", tab: "providers" },
  "metadata:scan": { section: "sources", tab: "saved" },
  "metadata:refresh": { section: "sources", tab: "refresh" },
  "admin:users": { section: "server", tab: "users" },
  "admin:backups": { section: "server", tab: "tasks" },
  "admin:repair": { section: "server", tab: "repair" },
  "admin:sso": { section: "server", tab: "access" },
  "admin:integrations": { section: "server", tab: "access" },
  "admin:limits": { section: "server", tab: "access" },
  "admin:dev-tools": { section: "server", tab: "dev" },
};

export function visibleTabs(
  page: SettingsPageDef,
  isAdmin: boolean,
): SettingsTabDef[] {
  return page.tabs.filter((t) => isAdmin || !t.adminOnly);
}

export function visiblePages(isAdmin: boolean): SettingsPageDef[] {
  return SETTINGS_PAGES.filter((p) => visibleTabs(p, isAdmin).length > 0);
}

// Turns whatever is in the address bar (a new page id, an old section id, or an
// old page plus its old tab) into a page and tab this user can open. Anything it
// does not know falls back to Account, Profile.
export function resolveSettingsPlace(
  section: string | undefined,
  tab: string | undefined,
  isAdmin: boolean,
): SettingsPlace {
  const fallback = { section: "account", tab: "profile" };
  let place: SettingsPlace | undefined;
  if (section && tab && OLD_TABS[`${section}:${tab}`]) {
    place = OLD_TABS[`${section}:${tab}`];
  } else if (section && SETTINGS_PAGES.some((p) => p.id === section)) {
    place = { section, tab: tab ?? "" };
  } else if (section && OLD_SECTIONS[section]) {
    place = OLD_SECTIONS[section];
  }
  if (!place) return fallback;
  const page = SETTINGS_PAGES.find((p) => p.id === place!.section);
  if (!page) return fallback;
  const tabs = visibleTabs(page, isAdmin);
  if (!tabs.length) return fallback;
  const chosen = tabs.find((t) => t.id === place!.tab) ?? tabs[0];
  return { section: page.id, tab: chosen.id };
}
