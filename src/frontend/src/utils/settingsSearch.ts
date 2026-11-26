// A small search over Settings: it knows what each setting is called and the
// words someone is likely to look for, and it opens the page and tab that holds
// it. It reads no setting values and loads nothing.
import { SETTINGS_PAGES } from "./settingsPages";

export interface SettingsEntry {
  // unique, for list keys
  id: string;
  label: string;
  section: string;
  tab: string;
  // other words for the setting
  keywords: string;
  adminOnly?: boolean;
  // where it sits, shown under the label: "Look and feel, Appearance"
  where: string;
}

type Raw = [label: string, section: string, tab: string, keywords: string];

const RAW: Raw[] = [
  [
    "Profile",
    "account",
    "profile",
    "avatar picture photo username name email password display",
  ],
  ["Password", "account", "profile", "change password login security"],
  [
    "Linked accounts",
    "account",
    "connections",
    "steam playstation psn epic gog xbox retroachievements link sync sign in library",
  ],
  [
    "AniList import",
    "account",
    "connections",
    "anilist import automatic update existing titles anime list",
  ],
  [
    "Signed-in devices",
    "account",
    "devices",
    "sessions devices browsers sign out everywhere logged in security",
  ],
  [
    "App keys",
    "account",
    "keys",
    "api key keys token playnite plugin developer integration access",
  ],
  [
    "Colours",
    "look",
    "appearance",
    "theme accent colour color text background panel",
  ],
  [
    "Mastered games badge",
    "look",
    "appearance",
    "completion badge ribbon glow border corner 100% mastered perfect cover image",
  ],
  ["Compact mode", "look", "views", "density spacing tight smaller"],
  [
    "High contrast",
    "look",
    "views",
    "contrast brighter borders focus accessibility",
  ],
  ["Sidebar style", "look", "nav", "sidebar minimal clean list style menu"],
  [
    "When the sidebar shows",
    "look",
    "nav",
    "sidebar overlay pinned rail icons menu button",
  ],
  ["Jump back in", "look", "nav", "recent last played watched sidebar"],
  ["Pinned", "look", "nav", "pin pinned favourite sidebar"],
  ["Media opens on", "look", "nav", "media anime movies tv last used sidebar"],
  ["Sidebar search bar", "look", "nav", "search ctrl k sidebar"],
  ["Weekly digest", "look", "views", "home summary week played"],
  [
    "Default view and sort",
    "look",
    "views",
    "list shelves sort view default layout interface",
  ],
  [
    "Anime names",
    "look",
    "views",
    "title language english romaji native japanese",
  ],
  [
    "Count Plan to Watch in Statistics",
    "look",
    "views",
    "plan to watch statistics stats media",
  ],
  [
    "Game page tabs",
    "look",
    "game-page",
    "tabs hide show rating credits badge default tab history header",
  ],
  [
    "Keyboard shortcuts",
    "look",
    "shortcuts",
    "hotkeys keys keyboard commands palette",
  ],
  [
    "Episode aired",
    "notify",
    "bell",
    "notifications alerts episode airing new",
  ],
  [
    "Season started airing",
    "notify",
    "bell",
    "notifications alerts season premiere",
  ],
  [
    "New season listed",
    "notify",
    "bell",
    "notifications alerts sequel announce",
  ],
  [
    "New movie or special listed",
    "notify",
    "bell",
    "notifications alerts movie special announce",
  ],
  ["Movie released", "notify", "bell", "notifications alerts movie release"],
  [
    "Achievement milestone",
    "notify",
    "bell",
    "notifications alerts achievements unlock 100 perfect",
  ],
  [
    "Calendar feed",
    "notify",
    "calendar",
    "feed ical subscribe schedule release dates",
  ],
  [
    "Estimated episodes",
    "notify",
    "calendar",
    "calendar estimate episodes airing guess",
  ],
  [
    "Game releases",
    "notify",
    "calendar",
    "calendar games releases history layers",
  ],
  [
    "Upload",
    "library",
    "upload",
    "files size limit screenshots clips saves maximum inbox sort",
  ],
  ["Possible duplicates", "library", "tidy", "duplicate games merge reviewed"],
  [
    "Shared folders",
    "library",
    "tidy",
    "duplicate folders storage folder mis-import",
  ],
  [
    "Refresh game details and art",
    "sources",
    "refresh",
    "refresh metadata fill missing art overwrite text fields rescan games",
  ],
  [
    "Refresh achievements",
    "sources",
    "refresh",
    "achievements rarity icons unlock dates refresh",
  ],
  ["Deleted games", "library", "trash", "deleted removed games restore trash"],
  [
    "Media trash",
    "library",
    "trash",
    "deleted removed restore recover bin movies tv anime",
  ],
  ["Export", "library", "io", "export backup csv json download"],
  [
    "Import from another service",
    "library",
    "io",
    "import yamtrack anilist myanimelist letterboxd csv games restore",
  ],
  [
    "Providers and keys",
    "sources",
    "providers",
    "metadata tmdb omdb igdb steamgriddb twitch keys providers api",
  ],
  [
    "Time to beat",
    "sources",
    "providers",
    "howlongtobeat hltb time beat hours",
  ],
  [
    "What a scan may change",
    "sources",
    "saved",
    "scan provider order key art banner logo icon description developer publisher series tags",
  ],
  [
    "Remove achievements a game no longer has",
    "sources",
    "saved",
    "achievements remove missing scan",
  ],
  [
    "Steam tags as genres",
    "sources",
    "saved",
    "steam tags genres popular player votes",
  ],
  ["Steam wishlist", "sources", "saved", "steam wishlist import"],
  [
    "Refresh episodes",
    "sources",
    "refresh",
    "show anime episodes airing titles images anilist update fix counts",
  ],
  ["Movie details", "sources", "refresh", "movie details runtime refresh"],
  [
    "Server stats",
    "server",
    "overview",
    "storage disk usage users size games count stats",
  ],
  [
    "Users",
    "server",
    "users",
    "admin users accounts invite roles grant access",
  ],
  [
    "Tasks",
    "server",
    "tasks",
    "jobs background schedule airing check refresh running run together",
  ],
  [
    "Backups",
    "server",
    "tasks",
    "backup schedule kept leftover files covers restore",
  ],
  [
    "Repair libraries",
    "server",
    "repair",
    "fix missing cover art icon banner names details steam app play time rarity",
  ],
  ["Single sign-on", "server", "access", "oidc sso login provider openid auth"],
  [
    "Server integrations",
    "server",
    "access",
    "server keys tmdb omdb igdb shared reverse proxy client ip",
  ],
  ["Upload limits", "server", "access", "upload limits size maximum"],
  ["Password rules", "server", "users", "password rules length policy"],
  [
    "Dev tools",
    "server",
    "dev",
    "test notification regenerate api request system info developer",
  ],
];

function placeName(
  section: string,
  tab: string,
): {
  where: string;
  adminOnly: boolean;
} {
  const page = SETTINGS_PAGES.find((p) => p.id === section);
  const t = page?.tabs.find((x) => x.id === tab);
  if (!page || !t) throw new Error(`Unknown settings place ${section}:${tab}`);
  return {
    where: page.tabs.length > 1 ? `${page.label}, ${t.label}` : page.label,
    adminOnly: !!t.adminOnly,
  };
}

export const SETTINGS_INDEX: SettingsEntry[] = RAW.map(
  ([label, section, tab, keywords], i) => {
    const { where, adminOnly } = placeName(section, tab);
    return {
      id: `${section}:${tab}:${i}`,
      label,
      section,
      tab,
      keywords,
      where,
      adminOnly,
    };
  },
);

function words(text: string): string[] {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9%]+/g, " ")
    .trim()
    .split(" ")
    .filter(Boolean);
}

// How well one word matches an entry: a label that starts with it is best, then a
// word of the label, then one of the keywords, then the page it is on. 0 means no
// match.
function wordScore(word: string, entry: SettingsEntry): number {
  const label = words(entry.label);
  if (label.some((l) => l.startsWith(word)))
    return label[0].startsWith(word) ? 4 : 3;
  if (words(entry.keywords).some((k) => k.startsWith(word))) return 2;
  if (words(entry.where).some((g) => g.startsWith(word))) return 1;
  return 0;
}

// Every word typed has to match, so "steam wishlist" narrows rather than widens.
// An empty search finds nothing, so the box can stay quiet until someone types.
export function searchSettings(
  query: string,
  isAdmin: boolean,
  limit = 8,
): SettingsEntry[] {
  const typed = words(query);
  if (!typed.length) return [];
  const scored: { entry: SettingsEntry; score: number; at: number }[] = [];
  SETTINGS_INDEX.forEach((entry, at) => {
    if (entry.adminOnly && !isAdmin) return;
    let total = 0;
    for (const word of typed) {
      const s = wordScore(word, entry);
      if (s === 0) return;
      total += s;
    }
    scored.push({ entry, score: total, at });
  });
  return scored
    .sort((a, b) => b.score - a.score || a.at - b.at)
    .slice(0, limit)
    .map((s) => s.entry);
}
