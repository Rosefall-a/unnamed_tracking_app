// Made-up entries for previews, shown only when the person has nothing of that
// kind yet. They are always drawn marked as examples, never as their data.
import type { AchievementFeedEntry } from "../services/achievementsFeed";
import type { CalendarEntry } from "../services/mediaExtras";
import type { MediaNotification } from "../services/notifications";
import type { HomeTitle, TitleKind } from "./data";

const NAMES: Record<TitleKind, string[]> = {
  game: [
    "Starfall Run",
    "Hollow Keep",
    "Tidewater",
    "Neon Ledger",
    "Ashen Road",
    "Pale Harbor",
    "Ironwood",
    "Last Lantern",
  ],
  movie: [
    "The Quiet Hour",
    "Glass Meridian",
    "Night Ferry",
    "Paper Kings",
    "Low Orbit",
    "Cold Harvest",
  ],
  tv: [
    "Salt & Signal",
    "The Long Table",
    "Dockside",
    "Northern Lights",
    "Hard Reset",
    "Crooked Lane",
  ],
  anime: [
    "Sky Courier",
    "Moonlit Blade",
    "Clockwork Tide",
    "Ember Class",
    "Starlit Diner",
    "Iron Garden",
  ],
};

const SUBTITLE: Record<TitleKind, string[]> = {
  game: ["Played yesterday", "Played 3 days ago", "PC", "Played last week"],
  movie: ["2024", "2023", "2021", "2019"],
  tv: ["S1 E4", "S2 E1", "S1 E7", "S3 E2"],
  anime: ["S1 E9", "S2 E3", "S1 E2", "S1 E12"],
};

export function sampleTitles(n: number, kinds: TitleKind[] = []): HomeTitle[] {
  const order: TitleKind[] = kinds.length
    ? kinds
    : ["game", "tv", "anime", "movie"];
  return Array.from({ length: n }, (_, i) => {
    const kind = order[i % order.length];
    const pool = NAMES[kind];
    const subtitles = SUBTITLE[kind];
    return {
      key: `sample:${kind}:${i}`,
      kind,
      id: String(i),
      title: pool[Math.floor(i / order.length) % pool.length],
      art: null,
      wide: null,
      subtitle: subtitles[i % subtitles.length],
      progress:
        kind === "movie" || kind === "game"
          ? null
          : ((i * 17) % 80) / 100 + 0.1,
      ach: kind === "game" ? { unlocked: 5 + i * 3, total: 40 } : null,
      to: "",
      status: "",
      group: "active",
      rating: 6 + (i % 4),
      favorite: false,
      addedAt: 0,
      touchedAt: 0,
      genres: ["Action", "Indie"],
      release: Date.now() + (i + 3) * 86_400_000 * 6,
      platform: kind === "game" ? "PC" : "",
      hours: 8 + i * 3,
      makers: ["Northlight Studio"],
      collections: [],
      playedHours: kind === "game" ? 6 + i * 4 : null,
    };
  });
}

export function sampleFeed(n: number): AchievementFeedEntry[] {
  const names = [
    "First Blood",
    "Perfect Run",
    "Cartographer",
    "Untouchable",
    "Hoarder",
    "Last Stand",
    "Quiet Hands",
    "Collector",
  ];
  return Array.from({ length: n }, (_, i) => ({
    id: String(i),
    gameId: String(i),
    gameTitle: sampleTitles(8, ["game"])[i % 8].title,
    name: names[i % names.length],
    description: null,
    iconUrl: null,
    unlockedAt: Math.floor(Date.now() / 1000) - i * 86_400,
    globalPercent: [2.1, 8.4, 14.2, 31, 45, 52.6, 64, 78][i % 8],
  }));
}

export function sampleCalendar(n: number): CalendarEntry[] {
  const names = [
    "Sky Courier",
    "Salt & Signal",
    "Moonlit Blade",
    "Dockside",
    "Clockwork Tide",
  ];
  const now = Math.floor(Date.now() / 1000);
  return Array.from({ length: n }, (_, i) => ({
    mediaType: i % 2 ? "tv" : "anime",
    mediaId: String(i),
    title: names[i % names.length],
    posterUrl: null,
    nextEpisodeNumber: 3 + i,
    airAt: now + (i + 1) * 43_200,
    kind: "episode",
    isProjected: false,
  }));
}

export function sampleNotifications(n: number): MediaNotification[] {
  const rows = [
    ["Sky Courier", "Episode 9 aired"],
    ["Hollow Keep", "Sequel announced"],
    ["Salt & Signal", "New season starts Friday"],
    ["Glass Meridian", "Released today"],
  ];
  return Array.from({ length: n }, (_, i) => ({
    id: String(i),
    kind: "episode_aired",
    mediaType: "tv",
    mediaId: String(i),
    title: rows[i % rows.length][0],
    body: rows[i % rows.length][1],
    posterUrl: null,
    eventAt: Math.floor(Date.now() / 1000) - i * 3_600,
    read: i > 1,
  })) as MediaNotification[];
}
