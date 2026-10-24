// Every widget the Home page can hold. A widget is one entry here: what it is
// called, how big it may be, what settings it has (the settings form is drawn
// from `fields`, so a widget writes no form of its own), what data it needs, and
// its component. Anything that wants to add a widget later, a plugin included,
// adds an entry here and nothing else changes.
import { defineAsyncComponent } from "vue";
import type { Component } from "vue";
import { CHROME_DEFAULTS } from "./chrome";
import { allTitles, homeData, titlesByKind } from "./data";
import type { DataKey } from "./data";

interface FieldBase {
  key: string;
  label: string;
  help?: string;
  // shown only when this says so, given the widget's current settings
  when?: (settings: Record<string, unknown>) => boolean;
}

export type FieldOption = { value: string; label: string };

export type SettingField =
  | (FieldBase & {
      type: "select";
      // a function for choices that come from the library (your collections)
      options: FieldOption[] | (() => FieldOption[]);
    })
  | (FieldBase & { type: "toggle" })
  | (FieldBase & { type: "number"; min: number; max: number })
  | (FieldBase & { type: "text"; placeholder?: string })
  | (FieldBase & { type: "date" })
  | (FieldBase & { type: "textarea" })
  | (FieldBase & {
      type: "multi";
      options: { value: string; label: string }[];
    });

export type WidgetCategory =
  | "Library"
  | "Progress"
  | "Achievements"
  | "Calendar"
  | "Stats"
  | "Tools"
  | "Layout";

export interface WidgetVariant {
  id: string;
  label: string;
}

export interface WidgetDefinition {
  type: string;
  name: string;
  description: string;
  // a longer explanation for the gallery's detail view
  details: string;
  category: WidgetCategory;
  size: { w: number; h: number; minW: number; minH: number };
  defaults: Record<string, unknown>;
  fields: SettingField[];
  variants: WidgetVariant[];
  // draws rows of artwork, so the card size and card text options apply
  cards: boolean;
  // has a cogwheel on the widget itself for the options you change while using it
  cog?: boolean;
  needs: DataKey[];
  // loaded too, but the widget works without it if it is missing
  soft?: DataKey[];
  // false when this person has nothing for it yet, so a preview shows examples
  hasData: () => boolean;
  component: Component;
}

// Props every widget component receives.
export interface WidgetProps {
  settings: Record<string, unknown>;
  variant: string | null;
  // draw example entries instead of this person's own
  sample: boolean;
  loading: boolean;
  w: number;
  h: number;
}

export const KIND_OPTIONS = [
  { value: "game", label: "Games" },
  { value: "movie", label: "Movies" },
  { value: "tv", label: "TV" },
  { value: "anime", label: "Anime" },
];

export const RAIL_SOURCES = [
  { value: "recently-added", label: "Recently added" },
  { value: "recently-updated", label: "Recently updated" },
  { value: "backlog", label: "Backlog and plan to watch" },
  { value: "wishlist", label: "Wishlist" },
  { value: "favorites", label: "Favorites" },
  { value: "highest-rated", label: "Highest rated" },
  { value: "finished", label: "Finished" },
  { value: "dropped", label: "Dropped" },
  { value: "unfinished", label: "Started but not finished" },
  { value: "collection", label: "One collection or list" },
  { value: "everything", label: "Everything" },
];

/** The game collections and media lists a shelf can show, as "game:<name>" and
 * "list:<id>". */
export function collectionOptions(): FieldOption[] {
  const names = new Set<string>();
  for (const t of titlesByKind.value.game)
    for (const name of t.collections) names.add(name);
  const games = [...names]
    .sort((a, b) => a.localeCompare(b))
    .map((name) => ({ value: `game:${name}`, label: `Games: ${name}` }));
  const lists = (homeData.lists.value ?? []).map((l) => ({
    value: `list:${l.id}`,
    label: `List: ${l.name}`,
  }));
  const all = [...games, ...lists];
  return all.length
    ? [{ value: "", label: "Pick one" }, ...all]
    : [{ value: "", label: "You have no collections or lists yet" }];
}

const unfinishedFields: SettingField[] = [
  {
    key: "staleDays",
    label: "Untouched for at least (days)",
    type: "number",
    min: 0,
    max: 365,
    help: "0 shows everything started and not finished.",
  },
  {
    key: "minHours",
    label: "Games played at least (hours)",
    type: "number",
    min: 0,
    max: 500,
  },
];

export const SORTS = [
  { value: "default", label: "Best fit for this shelf" },
  { value: "added", label: "Newest added" },
  { value: "updated", label: "Recently updated" },
  { value: "title", label: "Title, A to Z" },
  { value: "rating", label: "Highest rated" },
  { value: "random", label: "Shuffled" },
];

const POSTER_WIDE: WidgetVariant[] = [
  { id: "poster", label: "Posters" },
  { id: "wide", label: "Wide banners" },
];

const lazy = (loader: () => Promise<{ default: Component }>) =>
  defineAsyncComponent(loader);

const hasTitles = () => allTitles.value.length > 0;

const countField = (max = 40): SettingField => ({
  key: "count",
  label: "How many to show",
  type: "number",
  min: 1,
  max,
});
const kindsField: SettingField = {
  key: "kinds",
  label: "Include",
  type: "multi",
  options: KIND_OPTIONS,
  help: "Leave all off to include everything.",
};
const sortField: SettingField = {
  key: "sort",
  label: "Order",
  type: "select",
  options: SORTS,
};
const countdownField: SettingField = {
  key: "showCountdown",
  label: "Countdown on airing shows",
  type: "toggle",
  help: "Shows the time until the next episode on shows that have a confirmed air date.",
};
const genreField: SettingField = {
  key: "genre",
  label: "Only this genre or tag",
  type: "text",
  placeholder: "For example Horror",
};
const minRatingField: SettingField = {
  key: "minRating",
  label: "Lowest rating to include",
  type: "number",
  min: 0,
  max: 10,
};

// The look options every widget gets. Card options only appear on widgets that
// draw artwork rows.
export function commonFields(def: WidgetDefinition): SettingField[] {
  const fields: SettingField[] = [
    {
      key: "_heading",
      label: "Heading",
      type: "text",
      placeholder: "Leave blank for the default",
    },
    { key: "_showHeading", label: "Show the heading", type: "toggle" },
  ];
  // Pick something draws its own picture, so it has no panel to choose
  if (def.type !== "random")
    fields.push({
      key: "_panel",
      label: "Background",
      type: "select",
      options: [
        { value: "auto", label: "Default for this widget" },
        { value: "panel", label: "In a panel" },
        { value: "plain", label: "Plain" },
      ],
    });
  if (def.cards)
    fields.push(
      {
        key: "_cardSize",
        label: "Artwork size",
        type: "select",
        options: [
          { value: "small", label: "Small" },
          { value: "medium", label: "Medium" },
          { value: "large", label: "Large" },
        ],
      },
      {
        key: "_cardTag",
        label: "Kind label on artwork",
        type: "select",
        options: [
          { value: "auto", label: "When a row mixes kinds" },
          { value: "always", label: "Always" },
          { value: "never", label: "Never" },
        ],
      },
      {
        key: "_cardText",
        label: "Titles on artwork",
        type: "select",
        options: [
          { value: "always", label: "Always" },
          { value: "hover", label: "On hover" },
          { value: "never", label: "Never" },
        ],
      },
    );
  return fields;
}

const achievementEntry = (
  type: string,
  name: string,
  description: string,
  details: string,
  mode: string,
  size: { w: number; h: number },
  variants: WidgetVariant[],
  fields: SettingField[],
  extra: Record<string, unknown>,
): WidgetDefinition => ({
  type,
  name,
  description,
  details,
  category: "Achievements",
  size: { ...size, minW: 3, minH: 3 },
  defaults: { mode, count: 15, ...extra },
  fields: [countField(30), ...fields],
  variants,
  cards: false,
  needs:
    mode === "recent" || mode === "rare"
      ? ["feed"]
      : ["games", "achievements", "feed"],
  hasData: () =>
    homeData.achFeed.value.recent.length > 0 ||
    Object.keys(homeData.achSummary.value).length > 0,
  component: lazy(
    () => import("../components/home/widgets/AchievementsWidget.vue"),
  ),
});

const releaseEntry = (
  type: string,
  name: string,
  description: string,
  details: string,
  kinds: string[],
): WidgetDefinition => ({
  type,
  name,
  description,
  details,
  category: "Calendar",
  size: { w: 12, h: 4, minW: 3, minH: 3 },
  defaults: { kinds, when: "upcoming", within: 90, scope: "all", count: 14 },
  fields: [
    kindsField,
    {
      key: "when",
      label: "Show",
      type: "select",
      options: [
        { value: "upcoming", label: "Coming up" },
        { value: "recent", label: "Just out" },
        { value: "both", label: "Both" },
      ],
    },
    {
      key: "within",
      label: "Within",
      type: "select",
      options: [
        { value: "30", label: "30 days" },
        { value: "90", label: "3 months" },
        { value: "180", label: "6 months" },
        { value: "365", label: "A year" },
        { value: "3650", label: "Any time" },
      ],
    },
    {
      key: "scope",
      label: "From my library",
      type: "select",
      options: [
        { value: "all", label: "Everything" },
        { value: "waiting", label: "Backlog and wishlist" },
        { value: "wishlist", label: "Wishlist only" },
      ],
    },
    countField(30),
  ],
  variants: POSTER_WIDE,
  cards: true,
  cog: true,
  needs: ["games", "movies", "tv", "anime"],
  hasData: () => allTitles.value.some((t) => t.release > 0),
  component: lazy(
    () => import("../components/home/widgets/ReleasesWidget.vue"),
  ),
});

const activityEntry = (
  type: string,
  name: string,
  description: string,
  details: string,
  defaults: Record<string, unknown>,
  extraFields: SettingField[],
  size: { w: number; h: number },
): WidgetDefinition => ({
  type,
  name,
  description,
  details,
  category: "Stats",
  size: { ...size, minW: 3, minH: 2 },
  defaults: { kinds: [], ...defaults },
  fields: [...extraFields, kindsField],
  variants: [],
  cards: false,
  needs: ["games", "movies", "tv", "anime"],
  hasData: hasTitles,
  component: lazy(
    () => import("../components/home/widgets/ActivityWidget.vue"),
  ),
});

const ICONS_LIST: WidgetVariant[] = [
  { id: "icons", label: "Icons" },
  { id: "list", label: "List" },
];

const iconFields: SettingField[] = [
  {
    key: "iconSize",
    label: "Icon size",
    type: "select",
    options: [
      { value: "small", label: "Small" },
      { value: "medium", label: "Medium" },
      { value: "large", label: "Large" },
    ],
  },
  { key: "showMore", label: "Show +N for the rest", type: "toggle" },
];

export const METRICS = [
  { value: "game", label: "Games" },
  { value: "movie", label: "Movies" },
  { value: "tv", label: "TV shows" },
  { value: "anime", label: "Anime" },
  { value: "all", label: "Everything" },
  { value: "favorites", label: "Favorites" },
  { value: "in-progress", label: "In progress" },
  { value: "queue", label: "Waiting" },
  { value: "wishlist", label: "Wishlist" },
  { value: "finished", label: "Finished" },
  { value: "dropped", label: "Dropped" },
  { value: "unrated", label: "Not rated yet" },
  { value: "average", label: "Average rating" },
  { value: "added-week", label: "Added this week" },
  { value: "added-month", label: "Added this month" },
  { value: "added-year", label: "Added this year" },
  { value: "ach-unlocked", label: "Achievements unlocked" },
  { value: "ach-complete", label: "Games at 100%" },
];

export const WIDGETS: WidgetDefinition[] = [
  {
    type: "greeting",
    name: "Greeting",
    description: "A welcome with your name and this week at a glance.",
    details:
      "Says hello by time of day, shows today's date and how big your library is, and lines up what you did this week.",
    category: "Tools",
    size: { w: 12, h: 2, minW: 4, minH: 2 },
    defaults: { recap: true, showDate: true, showCount: true },
    fields: [
      { key: "recap", label: "Show this week", type: "toggle" },
      { key: "showDate", label: "Show the date", type: "toggle" },
      { key: "showCount", label: "Show library size", type: "toggle" },
    ],
    variants: [],
    cards: false,
    needs: ["games", "movies", "tv", "anime", "digest"],
    hasData: () => true,
    component: lazy(
      () => import("../components/home/widgets/GreetingWidget.vue"),
    ),
  },
  {
    type: "continue",
    name: "Continue",
    description: "Games you are playing and shows you are partway through.",
    details:
      "One row of everything in progress, most recently touched first. Shows how far through each show you are.",
    category: "Progress",
    size: { w: 12, h: 4, minW: 3, minH: 3 },
    defaults: {
      kinds: [],
      count: 16,
      sort: "updated",
      showProgress: true,
      showCountdown: true,
    },
    fields: [
      kindsField,
      countdownField,
      { key: "showProgress", label: "Show progress bars", type: "toggle" },
      sortField,
      countField(),
    ],
    variants: POSTER_WIDE,
    cards: true,
    needs: ["games", "movies", "tv", "anime"],
    soft: ["calendar"],
    hasData: hasTitles,
    component: lazy(
      () => import("../components/home/widgets/ContinueWidget.vue"),
    ),
  },
  {
    type: "rail",
    name: "Shelf",
    description: "A row of artwork from any part of your library.",
    details:
      "Pick what it shows (recently added, backlog, favorites and more), narrow it by kind, genre or rating, and choose the order. Add as many shelves as you like.",
    category: "Library",
    size: { w: 12, h: 4, minW: 3, minH: 3 },
    defaults: {
      source: "recently-added",
      collection: "",
      staleDays: 30,
      minHours: 3,
      kinds: [],
      count: 16,
      sort: "default",
      genre: "",
      minRating: 0,
      showProgress: true,
      showCountdown: true,
    },
    fields: [
      {
        key: "source",
        label: "What to show",
        type: "select",
        options: RAIL_SOURCES,
      },
      {
        key: "collection",
        label: "Which collection or list",
        type: "select",
        options: collectionOptions,
        when: (s) => s.source === "collection",
      },
      ...unfinishedFields.map((f) => ({
        ...f,
        when: (s: Record<string, unknown>) => s.source === "unfinished",
      })),
      kindsField,
      sortField,
      genreField,
      minRatingField,
      countdownField,
      { key: "showProgress", label: "Show progress bars", type: "toggle" },
      countField(),
    ],
    variants: POSTER_WIDE,
    cards: true,
    cog: true,
    needs: ["games", "movies", "tv", "anime"],
    soft: ["calendar", "lists"],
    hasData: hasTitles,
    component: lazy(() => import("../components/home/widgets/RailWidget.vue")),
  },
  {
    type: "unfinished",
    name: "Unfinished",
    description: "Things you started and have not touched in a while.",
    details:
      "Games with real playtime that are not finished, and shows and films you are partway through, that you have not touched for a month (you choose how long). Uses only recorded playtime and episodes watched.",
    category: "Progress",
    size: { w: 12, h: 4, minW: 3, minH: 3 },
    defaults: {
      source: "unfinished",
      staleDays: 30,
      minHours: 3,
      kinds: [],
      count: 16,
      sort: "updated",
      showProgress: true,
      showCountdown: false,
    },
    fields: [...unfinishedFields, kindsField, sortField, countField()],
    variants: POSTER_WIDE,
    cards: true,
    needs: ["games", "movies", "tv", "anime"],
    hasData: hasTitles,
    component: lazy(() => import("../components/home/widgets/RailWidget.vue")),
  },
  {
    type: "up-next",
    name: "Airing soon",
    description: "Countdowns to the next episodes of what you are watching.",
    details:
      "Every show you are watching with a live countdown to its next episode, soonest first. Switch between a list and a row of posters.",
    category: "Calendar",
    size: { w: 6, h: 4, minW: 3, minH: 3 },
    defaults: {
      days: 14,
      count: 8,
      kinds: [],
      onlyWatching: true,
      showCountdown: true,
      showSeconds: false,
    },
    fields: [
      {
        key: "days",
        label: "Look ahead",
        type: "select",
        options: [
          { value: "3", label: "3 days" },
          { value: "7", label: "A week" },
          { value: "14", label: "Two weeks" },
        ],
      },
      {
        key: "onlyWatching",
        label: "Only what I am watching",
        type: "toggle",
        help: "Off also lists plan to watch and on hold.",
      },
      {
        key: "kinds",
        label: "Include",
        type: "multi",
        options: KIND_OPTIONS.filter((o) => o.value !== "game"),
        help: "Leave all off to include everything.",
      },
      countField(20),
      { key: "showCountdown", label: "Show a countdown", type: "toggle" },
      { key: "showSeconds", label: "Count down to the second", type: "toggle" },
    ],
    variants: [
      { id: "list", label: "List" },
      { id: "posters", label: "Posters" },
    ],
    cards: true,
    cog: true,
    needs: ["calendar", "tv", "anime", "movies"],
    hasData: () => (homeData.calendar.value ?? []).length > 0,
    component: lazy(
      () => import("../components/home/widgets/UpNextWidget.vue"),
    ),
  },
  achievementEntry(
    "achievements-recent",
    "Recent achievements",
    "The latest things you unlocked, across every game.",
    "Your newest unlocks as a grid of just their icons, the way Steam shows them. Point at one for its name, game and date, and the +N tile counts the rest.",
    "recent",
    { w: 6, h: 4 },
    ICONS_LIST,
    [
      { key: "showGame", label: "Show the game name", type: "toggle" },
      ...iconFields,
    ],
    { showGame: true, iconSize: "medium", showMore: true },
  ),
  achievementEntry(
    "achievements-games",
    "Latest games with achievements",
    "Games with achievements you have been working on, with how far along each is.",
    "Cover art for the games behind your latest unlocks, with a bar for how much of each is done.",
    "games",
    { w: 12, h: 4 },
    [],
    [
      {
        key: "hideCompleted",
        label: "Hide games at 100%",
        type: "toggle",
      },
      {
        key: "minTotal",
        label: "Ignore games with fewer achievements than",
        type: "number",
        min: 0,
        max: 100,
      },
    ],
    { hideCompleted: false, minTotal: 0 },
  ),
  achievementEntry(
    "achievements-close",
    "Closest to 100%",
    "Games where only a few achievements are left.",
    "Games you are nearly done with, fewest left first.",
    "close",
    { w: 12, h: 4 },
    [],
    [
      {
        key: "minTotal",
        label: "Ignore games with fewer achievements than",
        type: "number",
        min: 0,
        max: 100,
      },
    ],
    { minTotal: 5 },
  ),
  achievementEntry(
    "achievements-rare",
    "Rarest achievements",
    "Your hardest to find achievements, rarest first.",
    "The achievements the fewest players have, from the games you have unlocked them in, drawn as just their icons with a glow on the rarest.",
    "rare",
    { w: 6, h: 4 },
    ICONS_LIST,
    [
      { key: "showGame", label: "Show the game name", type: "toggle" },
      {
        key: "maxPercent",
        label: "Only below this share of players (%)",
        type: "number",
        min: 1,
        max: 100,
      },
      ...iconFields,
    ],
    {
      showGame: true,
      maxPercent: 100,
      iconSize: "medium",
      showMore: false,
    },
  ),
  {
    type: "stats",
    name: "Numbers",
    description: "Counts from your library, as many as you pick.",
    details:
      "Tiles with counts: titles per kind, favorites, what is in progress or waiting, average rating, how much you added this week, achievements unlocked and more.",
    category: "Stats",
    size: { w: 4, h: 4, minW: 3, minH: 2 },
    defaults: {
      metrics: ["game", "movie", "tv", "anime", "favorites", "in-progress"],
      kinds: [],
      size: "normal",
    },
    fields: [
      {
        key: "metrics",
        label: "Show",
        type: "multi",
        options: METRICS,
      },
      {
        ...kindsField,
        label: "Count only",
        help: "Limits the counts to these kinds. Leave all off for everything.",
      },
      {
        key: "size",
        label: "Tile size",
        type: "select",
        options: [
          { value: "compact", label: "Compact" },
          { value: "normal", label: "Normal" },
          { value: "large", label: "Large" },
        ],
      },
    ],
    variants: [],
    cards: false,
    needs: ["games", "movies", "tv", "anime", "achievements"],
    hasData: hasTitles,
    component: lazy(() => import("../components/home/widgets/StatsWidget.vue")),
  },
  {
    type: "random",
    name: "Pick something",
    description: "Can't decide? Get a random title from what is waiting.",
    details:
      "Rolls a title for you, over its background picture, its cover cropped wide, or as a cover card. Choose where it picks from, then narrow it by kind, genre, platform, rating or how long it takes, right on the widget, and roll again until something sounds right.",
    category: "Tools",
    size: { w: 6, h: 5, minW: 2, minH: 4 },
    defaults: {
      kinds: [],
      pool: "waiting",
      genre: "",
      platform: "",
      minRating: 0,
      maxHours: 0,
      buttonLabel: "Pick again",
    },
    fields: [
      kindsField,
      {
        key: "pool",
        label: "Pick from",
        type: "select",
        options: [
          { value: "waiting", label: "Backlog and wishlist" },
          { value: "backlog", label: "Backlog and plan to watch" },
          { value: "wishlist", label: "Wishlist" },
          { value: "favorites", label: "Favorites" },
          { value: "unfinished", label: "Anything unfinished" },
          { value: "finished", label: "Finished (for a rewatch or replay)" },
          { value: "everything", label: "Everything" },
        ],
      },
      genreField,
      {
        key: "platform",
        label: "Only this platform (games)",
        type: "text",
        placeholder: "For example PC",
      },
      minRatingField,
      {
        key: "maxHours",
        label: "Takes at most this many hours (0 for any)",
        type: "number",
        min: 0,
        max: 500,
      },
      { key: "buttonLabel", label: "Button text", type: "text" },
    ],
    variants: [
      { id: "banner", label: "Background" },
      { id: "banner-cover", label: "Cropped cover" },
      { id: "card", label: "Cover art" },
    ],
    cards: true,
    cog: true,
    needs: ["games", "movies", "tv", "anime"],
    hasData: hasTitles,
    component: lazy(
      () => import("../components/home/widgets/RandomWidget.vue"),
    ),
  },
  {
    type: "on-this-day",
    name: "Throwback",
    description: "What you added around this time in earlier years.",
    details:
      "Shows titles you added on this day, this week or this month in past years, so there is almost always something to look back on. Choose the span and how far back to look.",
    category: "Library",
    size: { w: 12, h: 4, minW: 3, minH: 3 },
    defaults: {
      span: "week",
      yearsBack: 0,
      kinds: [],
      count: 12,
    },
    fields: [
      {
        key: "span",
        label: "Around this",
        type: "select",
        options: [
          { value: "day", label: "Day" },
          { value: "week", label: "Week" },
          { value: "month", label: "Month" },
        ],
      },
      {
        key: "yearsBack",
        label: "Years back (0 for all)",
        type: "number",
        min: 0,
        max: 30,
      },
      kindsField,
      countField(30),
    ],
    variants: POSTER_WIDE,
    cards: true,
    needs: ["games", "movies", "tv", "anime"],
    hasData: () => {
      const now = new Date();
      return allTitles.value.some((t) => {
        if (!t.addedAt) return false;
        const d = new Date(t.addedAt);
        return (
          d.getMonth() === now.getMonth() && d.getFullYear() < now.getFullYear()
        );
      });
    },
    component: lazy(
      () => import("../components/home/widgets/OnThisDayWidget.vue"),
    ),
  },
  releaseEntry(
    "releases",
    "Upcoming releases",
    "Games, films and shows in your library with a release date coming up.",
    "Everything with a release date soon, soonest first, with how long until it comes out. Switch it to what came out recently, and choose how far ahead to look.",
    [],
  ),
  releaseEntry(
    "game-releases",
    "Upcoming game releases",
    "Games on your wishlist and backlog that are about to come out.",
    "Your games with a release date ahead, soonest first, with a countdown in days.",
    ["game"],
  ),
  {
    type: "schedule",
    name: "Release schedule",
    description:
      "The coming days as a board: episodes, premieres and game releases.",
    details:
      "One column for each day that has something airing or releasing, with the artwork, the episode and the time. Choose which kinds to include and how many days to look ahead.",
    category: "Calendar",
    size: { w: 12, h: 5, minW: 4, minH: 3 },
    defaults: {
      days: 7,
      include: ["episodes", "premieres", "games"],
      onlyWatching: true,
    },
    fields: [
      {
        key: "days",
        label: "Look ahead",
        type: "select",
        options: [
          { value: "3", label: "3 days" },
          { value: "7", label: "A week" },
          { value: "14", label: "Two weeks" },
        ],
      },
      {
        key: "include",
        label: "Include",
        type: "multi",
        options: [
          { value: "episodes", label: "Episodes" },
          { value: "premieres", label: "Premieres" },
          { value: "games", label: "Games" },
        ],
      },
      {
        key: "onlyWatching",
        label: "Only shows I am watching",
        type: "toggle",
      },
    ],
    variants: [],
    cards: false,
    cog: true,
    needs: ["calendar", "games", "movies", "tv", "anime"],
    hasData: () => (homeData.calendar.value ?? []).length > 0,
    component: lazy(
      () => import("../components/home/widgets/ScheduleWidget.vue"),
    ),
  },
  {
    type: "breakdown",
    name: "Breakdown",
    description:
      "Your library split by genre, platform, status, rating or decade.",
    details:
      "Bars for how your library divides up, sized against the biggest. Pick what to split by and which kinds to count.",
    category: "Stats",
    size: { w: 4, h: 4, minW: 3, minH: 3 },
    defaults: { by: "genre", kinds: [], count: 8 },
    fields: [
      {
        key: "by",
        label: "Split by",
        type: "select",
        options: [
          { value: "genre", label: "Genre or tag" },
          { value: "platform", label: "Platform" },
          { value: "status", label: "Status" },
          { value: "kind", label: "Kind" },
          { value: "rating", label: "Rating" },
          { value: "maker", label: "Developer or studio" },
          { value: "decade", label: "Decade" },
        ],
      },
      kindsField,
      countField(20),
    ],
    variants: [],
    cards: false,
    cog: true,
    needs: ["games", "movies", "tv", "anime"],
    hasData: hasTitles,
    component: lazy(
      () => import("../components/home/widgets/BreakdownWidget.vue"),
    ),
  },
  {
    type: "backlog-time",
    name: "Backlog length",
    description: "How many hours your backlog adds up to.",
    details:
      "The total time to beat of what is waiting, how many titles that covers and how many have no figure, plus the quickest ones to finish.",
    category: "Stats",
    size: { w: 4, h: 4, minW: 3, minH: 3 },
    defaults: { kinds: ["game"], pool: "backlog", count: 4 },
    fields: [
      kindsField,
      {
        key: "pool",
        label: "Count",
        type: "select",
        options: [
          { value: "backlog", label: "Backlog and plan to watch" },
          { value: "waiting", label: "Backlog and wishlist" },
          { value: "unfinished", label: "Everything unfinished" },
        ],
      },
      {
        key: "count",
        label: "Quickest to finish to list",
        type: "number",
        min: 0,
        max: 10,
      },
    ],
    variants: [],
    cards: false,
    cog: true,
    needs: ["games", "movies", "tv", "anime"],
    hasData: hasTitles,
    component: lazy(
      () => import("../components/home/widgets/BacklogTimeWidget.vue"),
    ),
  },
  {
    type: "most-played",
    name: "Time played",
    description:
      "Total hours played and the games you have spent the most time in.",
    details:
      "Your total hours and a bar for each of your most played games, from the play time a synced library reports.",
    category: "Stats",
    size: { w: 4, h: 4, minW: 3, minH: 3 },
    defaults: { count: 5, showTotal: true },
    fields: [
      countField(10),
      { key: "showTotal", label: "Show the total hours", type: "toggle" },
    ],
    variants: [],
    cards: false,
    needs: ["stats", "games"],
    hasData: () =>
      (homeData.stats.value?.most_played ?? []).some(
        (g) => g.playtime_seconds > 0,
      ),
    component: lazy(
      () => import("../components/home/widgets/MostPlayedWidget.vue"),
    ),
  },
  {
    type: "screenshots",
    name: "Screenshots",
    description: "A wall of your latest screenshots from every game.",
    details:
      "The newest screenshots across your library as a grid, or a shuffled pick. Each one opens its game.",
    category: "Library",
    size: { w: 6, h: 4, minW: 3, minH: 3 },
    defaults: { count: 8, order: "recent" },
    fields: [
      countField(24),
      {
        key: "order",
        label: "Order",
        type: "select",
        options: [
          { value: "recent", label: "Newest first" },
          { value: "random", label: "Shuffled" },
        ],
      },
    ],
    variants: [],
    cards: false,
    needs: ["screenshots"],
    hasData: () => (homeData.screenshots.value ?? []).length > 0,
    component: lazy(
      () => import("../components/home/widgets/ScreenshotsWidget.vue"),
    ),
  },
  {
    type: "spacer",
    name: "Spacer",
    description: "Empty space to keep widgets apart or hold a gap open.",
    details:
      "Nothing shows on the page. The page closes gaps up on its own, so a spacer is how you leave room between sections or beside a widget. Drag it to any size.",
    category: "Layout",
    size: { w: 12, h: 1, minW: 1, minH: 1 },
    defaults: {},
    fields: [],
    variants: [],
    cards: false,
    needs: [],
    hasData: () => true,
    component: lazy(
      () => import("../components/home/widgets/SpacerWidget.vue"),
    ),
  },
  {
    type: "divider",
    name: "Divider and heading",
    description: "A line across the page, with a heading if you want one.",
    details:
      "Starts a new section: a thin line, a dotted one or a glowing one, with an optional label on the left or in the middle, small or large.",
    category: "Layout",
    size: { w: 12, h: 1, minW: 2, minH: 1 },
    defaults: { label: "", look: "line", size: "small", align: "left" },
    fields: [
      { key: "label", label: "Label", type: "text", placeholder: "Optional" },
      {
        key: "look",
        label: "Line",
        type: "select",
        options: [
          { value: "line", label: "Solid" },
          { value: "dotted", label: "Dotted" },
          { value: "glow", label: "Glowing" },
        ],
      },
      {
        key: "size",
        label: "Label size",
        type: "select",
        options: [
          { value: "small", label: "Small caps" },
          { value: "large", label: "Large heading" },
        ],
      },
      {
        key: "align",
        label: "Label position",
        type: "select",
        options: [
          { value: "left", label: "Left" },
          { value: "center", label: "Middle" },
        ],
      },
    ],
    variants: [],
    cards: false,
    needs: [],
    hasData: () => true,
    component: lazy(
      () => import("../components/home/widgets/DividerWidget.vue"),
    ),
  },
  {
    type: "clock",
    name: "Clock",
    description: "The time and the date.",
    details:
      "A large clock for a page you leave open, 12 or 24 hour, with or without seconds and the date.",
    category: "Tools",
    size: { w: 3, h: 2, minW: 2, minH: 2 },
    defaults: { format: "24h", showSeconds: false, showDate: true },
    fields: [
      {
        key: "format",
        label: "Hours",
        type: "select",
        options: [
          { value: "24h", label: "24 hour" },
          { value: "12h", label: "12 hour" },
        ],
      },
      { key: "showSeconds", label: "Show seconds", type: "toggle" },
      { key: "showDate", label: "Show the date", type: "toggle" },
    ],
    variants: [],
    cards: false,
    needs: [],
    hasData: () => true,
    component: lazy(() => import("../components/home/widgets/ClockWidget.vue")),
  },
  {
    type: "countdown",
    name: "Countdown",
    description: "Days until a date you choose.",
    details:
      "Counts down to any date, such as a release, a convention or a trip. It switches to hours in the last two days and says how long ago once it has passed.",
    category: "Tools",
    size: { w: 3, h: 3, minW: 2, minH: 2 },
    defaults: { label: "", date: "" },
    fields: [
      {
        key: "label",
        label: "What is it for",
        type: "text",
        placeholder: "For example a game release",
      },
      { key: "date", label: "Date", type: "date" },
    ],
    variants: [],
    cards: false,
    needs: [],
    hasData: () => true,
    component: lazy(
      () => import("../components/home/widgets/CountdownWidget.vue"),
    ),
  },
  {
    type: "next-episodes",
    name: "Next episodes",
    description:
      "Where you are up to in every show and anime you are watching.",
    details:
      "A list of what you are partway through, each with the episode you are on and how far through it you are.",
    category: "Progress",
    size: { w: 6, h: 5, minW: 3, minH: 3 },
    defaults: { kinds: [], count: 8, showProgress: true },
    fields: [
      {
        ...kindsField,
        options: KIND_OPTIONS.filter(
          (o) => o.value === "tv" || o.value === "anime",
        ),
      },
      countField(20),
      { key: "showProgress", label: "Show progress bars", type: "toggle" },
    ],
    variants: [],
    cards: false,
    needs: ["tv", "anime"],
    hasData: () =>
      allTitles.value.some(
        (t) => t.group === "active" && (t.kind === "tv" || t.kind === "anime"),
      ),
    component: lazy(
      () => import("../components/home/widgets/NextEpisodesWidget.vue"),
    ),
  },
  {
    type: "ratings",
    name: "Your ratings",
    description: "How you score things, from 1 to 10.",
    details:
      "A bar for each rating and your average, across everything or just the kinds you pick.",
    category: "Stats",
    size: { w: 4, h: 4, minW: 3, minH: 3 },
    defaults: { kinds: [] },
    fields: [kindsField],
    variants: [],
    cards: false,
    needs: ["games", "movies", "tv", "anime"],
    hasData: () => allTitles.value.some((t) => t.rating !== null),
    component: lazy(
      () => import("../components/home/widgets/RatingsWidget.vue"),
    ),
  },
  activityEntry(
    "activity",
    "Activity",
    "A grid of days, darker where more happened.",
    "A column for each week and a square for each day, darker where you added more titles or played games. It fills the width it is given.",
    { mode: "activity", what: "both" },
    [
      {
        key: "what",
        label: "Count",
        type: "select",
        options: [
          { value: "both", label: "Adds and plays" },
          { value: "added", label: "Titles added" },
          { value: "played", label: "Games played" },
        ],
      },
    ],
    { w: 6, h: 3 },
  ),
  activityEntry(
    "growth",
    "Added by month",
    "How many titles you added in each of the last 12 months.",
    "A bar for each month of the past year showing how many titles you added.",
    { mode: "growth", what: "added" },
    [],
    { w: 6, h: 3 },
  ),
  {
    type: "health",
    name: "Library health",
    description:
      "How complete your library's details are, for whatever slice you pick.",
    details:
      "Checks how many titles have a rating, release date, genres, a time to beat, a developer or studio, a cover or a platform. Narrow it to one kind, one genre, one platform or one status, and choose which checks to show.",
    category: "Stats",
    size: { w: 4, h: 4, minW: 3, minH: 3 },
    defaults: {
      kinds: [],
      genre: "",
      platform: "",
      status: "any",
      checks: ["rated", "release", "genres", "time"],
    },
    fields: [
      {
        key: "checks",
        label: "Checks to show",
        type: "multi",
        options: [
          { value: "rated", label: "Rated" },
          { value: "release", label: "Release date" },
          { value: "genres", label: "Genres or tags" },
          { value: "time", label: "Time to beat" },
          { value: "maker", label: "Developer or studio" },
          { value: "art", label: "Cover" },
          { value: "platform", label: "Platform" },
        ],
      },
      kindsField,
      genreField,
      {
        key: "platform",
        label: "Only this platform (games)",
        type: "text",
        placeholder: "For example PC",
      },
      {
        key: "status",
        label: "Only titles that are",
        type: "select",
        options: [
          { value: "any", label: "Any status" },
          { value: "active", label: "In progress" },
          { value: "queue", label: "Waiting" },
          { value: "wishlist", label: "On the wishlist" },
          { value: "done", label: "Finished" },
        ],
      },
    ],
    variants: [],
    cards: false,
    cog: true,
    needs: ["games", "movies", "tv", "anime"],
    hasData: hasTitles,
    component: lazy(
      () => import("../components/home/widgets/HealthWidget.vue"),
    ),
  },
  {
    type: "cover-wall",
    name: "Cover wall",
    description: "Posters filling the space, as many as fit.",
    details:
      "A wall of covers that fills the widget exactly with no scrolling. Choose what it shows (favorites, recently added, backlog and more), the order and how big each poster is.",
    category: "Library",
    size: { w: 6, h: 5, minW: 2, minH: 3 },
    defaults: {
      source: "favorites",
      kinds: [],
      sort: "default",
      genre: "",
      minRating: 0,
      tile: "medium",
    },
    fields: [
      {
        key: "source",
        label: "What to show",
        type: "select",
        options: RAIL_SOURCES,
      },
      kindsField,
      sortField,
      genreField,
      minRatingField,
      {
        key: "tile",
        label: "Poster size",
        type: "select",
        options: [
          { value: "small", label: "Small" },
          { value: "medium", label: "Medium" },
          { value: "large", label: "Large" },
        ],
      },
    ],
    variants: [],
    cards: true,
    cog: true,
    needs: ["games", "movies", "tv", "anime"],
    hasData: hasTitles,
    component: lazy(
      () => import("../components/home/widgets/CoverWallWidget.vue"),
    ),
  },
  {
    type: "tracker",
    name: "Tracker",
    description: "Count anything you can describe, with an optional goal.",
    details:
      "Keeps a count of whatever you describe: finished horror games, anime from one studio, films from the 90s, games on one platform. Set a goal and it shows the progress as a number, a ring or a bar. Add one for each thing you want to follow.",
    category: "Stats",
    size: { w: 4, h: 3, minW: 3, minH: 2 },
    defaults: {
      label: "",
      kinds: [],
      status: "done",
      genre: "",
      platform: "",
      maker: "",
      minRating: 0,
      yearFrom: 0,
      yearTo: 0,
      goal: 0,
      style: "number",
      covers: 0,
    },
    fields: [
      {
        key: "label",
        label: "Name",
        type: "text",
        placeholder: "For example Horror finished",
      },
      kindsField,
      {
        key: "status",
        label: "Count titles that are",
        type: "select",
        options: [
          { value: "any", label: "Anything in the library" },
          { value: "done", label: "Finished" },
          { value: "active", label: "In progress" },
          { value: "queue", label: "Waiting" },
          { value: "wishlist", label: "On the wishlist" },
          { value: "dropped", label: "Dropped" },
          { value: "favorite", label: "Favorites" },
        ],
      },
      genreField,
      {
        key: "maker",
        label: "Developer or studio",
        type: "text",
        placeholder: "Part of a name is enough",
      },
      {
        key: "platform",
        label: "Platform (games)",
        type: "text",
        placeholder: "For example PC",
      },
      minRatingField,
      {
        key: "yearFrom",
        label: "Released from year (0 for any)",
        type: "number",
        min: 0,
        max: 2100,
      },
      {
        key: "yearTo",
        label: "Released up to year (0 for any)",
        type: "number",
        min: 0,
        max: 2100,
      },
      {
        key: "goal",
        label: "Goal (0 for none)",
        type: "number",
        min: 0,
        max: 100000,
      },
      {
        key: "style",
        label: "Show as",
        type: "select",
        options: [
          { value: "number", label: "A number" },
          { value: "ring", label: "A ring" },
          { value: "bar", label: "A bar" },
        ],
      },
      {
        key: "covers",
        label: "Covers to show",
        type: "number",
        min: 0,
        max: 8,
      },
    ],
    variants: [],
    cards: false,
    cog: true,
    needs: ["games", "movies", "tv", "anime"],
    hasData: hasTitles,
    component: lazy(
      () => import("../components/home/widgets/TrackerWidget.vue"),
    ),
  },
  {
    type: "notifications",
    name: "Notifications",
    description: "New episodes, seasons and releases.",
    details: "Your latest notifications, with unread ones marked.",
    category: "Calendar",
    size: { w: 4, h: 4, minW: 3, minH: 3 },
    defaults: { count: 6, unreadOnly: false },
    fields: [
      countField(12),
      { key: "unreadOnly", label: "Only unread", type: "toggle" },
    ],
    variants: [],
    cards: false,
    needs: ["notifications"],
    hasData: () => (homeData.notifications.value?.items.length ?? 0) > 0,
    component: lazy(
      () => import("../components/home/widgets/NotificationsWidget.vue"),
    ),
  },
  {
    type: "quick-links",
    name: "Quick links",
    description: "Big buttons to the places you go most.",
    details: "A row of buttons to any page of the app, in the order you pick.",
    category: "Tools",
    size: { w: 6, h: 1, minW: 2, minH: 1 },
    defaults: {
      links: ["/games", "/movies", "/tv", "/anime", "/calendar"],
      _showHeading: false,
    },
    fields: [
      {
        key: "links",
        label: "Links",
        type: "multi",
        options: [
          { value: "/games", label: "Games" },
          { value: "/movies", label: "Movies" },
          { value: "/tv", label: "TV" },
          { value: "/anime", label: "Anime" },
          { value: "/calendar", label: "Calendar" },
          { value: "/statistics", label: "Statistics" },
          { value: "/games/collections", label: "Game collections" },
          { value: "/media/collections", label: "Media lists" },
          { value: "/notifications", label: "Notifications" },
          { value: "/settings", label: "Settings" },
        ],
      },
    ],
    variants: [],
    cards: false,
    needs: [],
    hasData: () => true,
    component: lazy(
      () => import("../components/home/widgets/QuickLinksWidget.vue"),
    ),
  },
  {
    type: "note",
    name: "Note",
    description: "A note to yourself that stays on the page.",
    details: "Free text, for a reminder, a goal or a to-do you want in view.",
    category: "Tools",
    size: { w: 4, h: 3, minW: 2, minH: 2 },
    defaults: { text: "" },
    fields: [{ key: "text", label: "Text", type: "textarea" }],
    variants: [],
    cards: false,
    needs: [],
    hasData: () => true,
    component: lazy(() => import("../components/home/widgets/NoteWidget.vue")),
  },
];

// Ready-made versions of widgets that are one idea with different settings, so the
// gallery lists them by name: shelves already pointed at something, and the daily
// pick.
function preset(
  from: string,
  type: string,
  name: string,
  description: string,
  details: string,
  defaults: Record<string, unknown>,
  size?: Partial<WidgetDefinition["size"]>,
) {
  const base = WIDGETS.find((w) => w.type === from);
  if (!base) return;
  WIDGETS.push({
    ...base,
    type,
    name,
    description,
    details,
    defaults: { ...base.defaults, ...defaults },
    size: { ...base.size, ...size },
  });
}
preset(
  "rail",
  "backlog-shelf",
  "Backlog",
  "A row of what is waiting for you.",
  "Your backlog and plan to watch, as a row of artwork.",
  { source: "backlog" },
);
preset(
  "rail",
  "wishlist-shelf",
  "Wishlist",
  "A row of what you want.",
  "Everything on your wishlist as a row of artwork.",
  { source: "wishlist" },
);
preset(
  "rail",
  "favorites-shelf",
  "Favorites",
  "Your favorites as a row of artwork.",
  "Everything you have hearted, as a row of artwork.",
  { source: "favorites" },
);
preset(
  "rail",
  "finished-shelf",
  "Recently finished",
  "What you finished lately.",
  "The games and shows you finished most recently, as a row of artwork.",
  { source: "finished", sort: "updated", _heading: "Recently finished" },
);
preset(
  "random",
  "spotlight",
  "Spotlight",
  "One title picked for you every day.",
  "A large banner for a single title that stays the same all day and changes tomorrow. Choose what it picks from, the same way as Pick something.",
  { daily: true, pool: "waiting" },
  { w: 12, h: 4, minW: 4, minH: 3 },
);

export const BY_TYPE = new Map(WIDGETS.map((w) => [w.type, w]));

export function definitionOf(type: string): WidgetDefinition | undefined {
  return BY_TYPE.get(type);
}

// The settings a widget actually runs with: the shared look defaults, its own
// defaults, then what was saved.
export function effectiveSettings(
  def: WidgetDefinition,
  saved: Record<string, unknown>,
): Record<string, unknown> {
  return { ...CHROME_DEFAULTS, ...def.defaults, ...saved };
}
