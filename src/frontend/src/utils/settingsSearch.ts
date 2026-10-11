// A small search over the Settings pages: it knows what each page is called and
// the words someone is likely to look for, and it opens the page (and the tab)
// that holds the setting. It reads no setting values and loads nothing.

export interface SettingsEntry {
  // the id Settings.vue's openSection understands: a page, or an alias that
  // also picks a tab
  id: string;
  label: string;
  // where it sits in the left menu, shown under the label
  group: string;
  // other words for what is on the page
  keywords: string;
  adminOnly?: boolean;
}

export const SETTINGS_INDEX: SettingsEntry[] = [
  {
    id: "profile",
    label: "Profile",
    group: "Account",
    keywords:
      "avatar picture photo username name email password account display",
  },
  {
    id: "connections",
    label: "Connections",
    group: "Account",
    keywords:
      "steam playstation psn epic gog xbox retroachievements link accounts sign in library sync",
  },
  {
    id: "api-keys",
    label: "API Keys",
    group: "Account",
    keywords: "token keys access developer integration",
  },
  {
    id: "interface",
    label: "User Interface",
    group: "Preferences",
    keywords: "compact mode high contrast layout default sort view density",
  },
  {
    id: "game-page",
    label: "Game Page",
    group: "Preferences",
    keywords: "tabs hide rating credits badge default tab history",
  },
  {
    id: "appearance",
    label: "Appearance",
    group: "Preferences",
    keywords:
      "theme accent colour color completion badge ribbon glow border mastered",
  },
  {
    id: "notifications",
    label: "Notifications",
    group: "Preferences",
    keywords: "alerts episodes airing released movie sequel announce bell",
  },
  {
    id: "calendar",
    label: "Calendar",
    group: "Preferences",
    keywords: "feed ical subscribe schedule release dates",
  },
  {
    id: "shortcuts",
    label: "Keyboard Shortcuts",
    group: "Preferences",
    keywords: "hotkeys keys keyboard commands palette",
  },
  {
    id: "upload",
    label: "Upload",
    group: "Library",
    keywords: "files size limit screenshots clips saves maximum",
  },
  {
    id: "library",
    label: "Library",
    group: "Library",
    keywords: "manage refresh metadata games rescan cleanup",
  },
  {
    id: "media-prefs",
    label: "Media preferences",
    group: "Library",
    keywords:
      "movies tv anime collections lists sort title language english romaji native",
  },
  {
    id: "media-trash",
    label: "Media trash",
    group: "Library",
    keywords: "deleted removed restore recover bin",
  },
  {
    id: "sources",
    label: "Sources & API keys",
    group: "Library",
    keywords: "metadata tmdb omdb igdb steamgriddb twitch keys providers",
  },
  {
    id: "scan",
    label: "Scan & providers",
    group: "Library",
    keywords: "provider order steam tags wishlist import player votes genres",
  },
  {
    id: "media-refresh",
    label: "Refresh media",
    group: "Library",
    keywords:
      "episodes airing titles images anilist update fix counts movie details runtime",
  },
  {
    id: "export",
    label: "Export / Import",
    group: "Library",
    keywords:
      "backup csv json restore yamtrack anilist myanimelist import export download",
  },
  {
    id: "stats",
    label: "Server Stats",
    group: "System",
    keywords: "storage disk usage users size games count",
  },
  {
    id: "admin",
    label: "Administration",
    group: "System",
    keywords: "admin users accounts invite roles",
    adminOnly: true,
  },
  {
    id: "oidc",
    label: "Single sign-on",
    group: "System",
    keywords: "oidc sso login provider openid auth",
    adminOnly: true,
  },
  {
    id: "server-integrations",
    label: "Server integrations",
    group: "System",
    keywords: "server keys tmdb omdb igdb shared",
    adminOnly: true,
  },
  {
    id: "tasks",
    label: "Tasks",
    group: "System",
    keywords: "jobs background schedule airing check refresh running",
    adminOnly: true,
  },
];

function words(text: string): string[] {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
    .split(" ")
    .filter(Boolean);
}

// How well one word matches an entry: a label that starts with it is best, then a
// word of the label, then one of the keywords. 0 means no match.
function wordScore(word: string, entry: SettingsEntry): number {
  const label = words(entry.label);
  if (label.some((l) => l.startsWith(word)))
    return label[0].startsWith(word) ? 4 : 3;
  if (words(entry.keywords).some((k) => k.startsWith(word))) return 2;
  if (words(entry.group).some((g) => g.startsWith(word))) return 1;
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
