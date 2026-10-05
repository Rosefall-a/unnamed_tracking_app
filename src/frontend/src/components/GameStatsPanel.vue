<script setup lang="ts">
// Stats on top, the game's story underneath. The numbers are the ones the
// page already knows (playtime, achievements, score, dates). The timeline
// lists what happened to the game as one kind of entry each: added to the
// library, purchased, achievements unlocked, metadata updated, price or status
// changed, media added. An entry shows the date and a one line summary; open
// it for the details. Entries that happened together are grouped.
import { ref, computed } from "vue";
import { parseDisplayDate } from "../utils/dates";
import { isUnlocked } from "../utils/achievements";
import { computeScore } from "../utils/scoring";
import type { Game } from "../types/game";
import type { FieldChange } from "../services/games";
import type { MediaItem } from "../services/media";

const props = defineProps<{
  game: Game;
  changes: FieldChange[];
  media: MediaItem[];
  loading: boolean;
  error: string | null;
}>();

// ---------------------------------------------------------------- stats ----
const minutes = computed(() =>
  props.game.platforms.reduce((sum, p) => sum + p.playtimeMinutes, 0),
);
const playtime = computed(() => {
  const h = Math.floor(minutes.value / 60);
  const m = minutes.value % 60;
  if (!minutes.value) return "None yet";
  return h ? `${h}h ${m}m` : `${m}m`;
});
const unlocked = computed(() =>
  props.game.achievements.filter(isUnlocked).map((a) => ({
    a,
    at: a.unlockedAt ? Date.parse(a.unlockedAt) : NaN,
  })),
);
const dated = computed(() => unlocked.value.filter((u) => !Number.isNaN(u.at)));
const tally = computed(() => computeScore(props.game));

function when(iso: string | null | undefined): number | null {
  if (!iso) return null;
  const t = parseDisplayDate(iso).getTime();
  return Number.isNaN(t) ? null : t;
}
const dayFmt = new Intl.DateTimeFormat(undefined, {
  month: "short",
  day: "numeric",
  year: "numeric",
});
const timeFmt = new Intl.DateTimeFormat(undefined, {
  hour: "numeric",
  minute: "2-digit",
});
const monthFmt = new Intl.DateTimeFormat(undefined, {
  month: "long",
  year: "numeric",
});
function day(ms: number | null): string {
  return ms === null ? "N/A" : dayFmt.format(ms);
}

const firstUnlock = computed(() =>
  dated.value.length ? Math.min(...dated.value.map((u) => u.at)) : null,
);
const lastUnlock = computed(() =>
  dated.value.length ? Math.max(...dated.value.map((u) => u.at)) : null,
);
const rarest = computed(() => {
  const withRate = unlocked.value.filter(
    (u) => typeof u.a.rarityPercent === "number",
  );
  if (!withRate.length) return null;
  return withRate.reduce((best, u) =>
    (u.a.rarityPercent as number) < (best.a.rarityPercent as number) ? u : best,
  ).a;
});
const busiest = computed(() => {
  const perDay = new Map<string, number>();
  for (const u of dated.value) {
    const k = new Date(u.at).toDateString();
    perDay.set(k, (perDay.get(k) ?? 0) + 1);
  }
  let top: { key: string; n: number } | null = null;
  for (const [key, n] of perDay) if (!top || n > top.n) top = { key, n };
  return top && top.n > 1 ? top : null;
});

function money(value: number | null, currency: string | null): string {
  if (value === null) return "";
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: currency || "USD",
    }).format(value);
  } catch {
    return String(value);
  }
}
const purchase = computed(() => {
  const o = props.game.ownership;
  const bits = [
    day(when(o.purchaseDate)),
    money(o.price, o.priceCurrency),
  ].filter((b) => b && b !== "N/A");
  return bits.length ? bits.join(" · ") : "N/A";
});

const summary = computed(() => [
  { label: "Playtime", value: playtime.value, sub: platformsLabel() },
  {
    label: "Achievements",
    value: props.game.achievementTotal
      ? `${unlocked.value.length} / ${props.game.achievementTotal}`
      : "N/A",
    sub: props.game.achievementTotal
      ? `${props.game.achievementPercent}% complete`
      : "",
    progress: props.game.achievementTotal
      ? Math.min(100, props.game.achievementPercent)
      : null,
  },
  {
    label: "Rating",
    value: tally.value ? `${tally.value.sum.toFixed(1)}` : "Not rated",
    sub: tally.value ? `out of ${tally.value.max}` : "",
  },
  {
    label: "Status",
    value: STATUS_LABEL[props.game.status] ?? props.game.status,
    sub: props.game.source ? `from ${props.game.source}` : "",
  },
]);
function platformsLabel(): string {
  const p = props.game.platforms.filter((x) => x.playtimeMinutes > 0);
  return p.length > 1 ? p.map((x) => x.platform).join(", ") : "";
}

const facts = computed(() => {
  const list: { label: string; value: string; note?: string }[] = [
    { label: "Added", value: day(when(props.game.dateAdded)) },
    { label: "Purchased", value: purchase.value },
    { label: "Last played", value: day(when(props.game.lastPlayedAt)) },
    { label: "First achievement", value: day(firstUnlock.value) },
    { label: "Latest achievement", value: day(lastUnlock.value) },
  ];
  if (props.game.completionDate)
    list.push({
      label: "Completed",
      value: day(when(props.game.completionDate)),
    });
  if (rarest.value)
    list.push({
      label: "Rarest unlocked",
      value: rarest.value.name,
      note: `${rarest.value.rarityPercent}% of players`,
    });
  if (busiest.value)
    list.push({
      label: "Busiest day",
      value: dayFmt.format(new Date(busiest.value.key)),
      note: `${busiest.value.n} achievements`,
    });
  if (props.game.timeToBeatHours)
    list.push({
      label: "Time to beat",
      value: `${props.game.timeToBeatHours}h`,
    });
  // a fact with nothing to say is left out rather than shown as N/A
  return list.filter((f) => f.value !== "N/A");
});

// achievements by month, only the months that have any, newest 12
const monthly = computed(() => {
  const counts = new Map<string, number>();
  for (const u of dated.value) {
    const d = new Date(u.at);
    const k = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
    counts.set(k, (counts.get(k) ?? 0) + 1);
  }
  const rows = [...counts.entries()].sort().slice(-12);
  const max = Math.max(1, ...rows.map((r) => r[1]));
  return rows.map(([k, n]) => {
    const [y, m] = k.split("-").map(Number);
    return {
      key: k,
      n,
      pct: Math.max(8, Math.round((n / max) * 100)),
      label: new Date(y, m - 1, 1).toLocaleDateString(undefined, {
        month: "short",
      }),
      year: y,
    };
  });
});

// ------------------------------------------------------------- timeline ----
type Filter = "all" | "achievements" | "library" | "metadata" | "media";
type Detail =
  | { type: "change"; label: string; from: string; to: string }
  | { type: "achievement"; name: string; icon?: string; note: string }
  | { type: "media"; url: string; kind: string; name: string }
  | { type: "fact"; label: string; value: string };
interface Entry {
  id: string;
  at: number;
  group: Exclude<Filter, "all">;
  icon: string;
  title: string;
  summary: string;
  details: Detail[];
  more?: number;
}

const STATUS_LABEL: Record<string, string> = {
  playing: "Playing",
  beaten: "Beaten",
  mastered: "Mastered",
  played: "Played",
  "on hold": "On hold",
  dropped: "Dropped",
  backlog: "Backlog",
  wishlist: "Wishlist",
  PLAYING: "Playing",
  BEATEN: "Beaten",
  MASTERED: "Mastered",
  PLAYED: "Played",
  ON_HOLD: "On hold",
  DROPPED: "Dropped",
  BACKLOG: "Backlog",
  WISHLIST: "Wishlist",
};
const FIELD_LABEL: Record<string, string> = {
  developer: "Developer",
  publisher: "Publisher",
  series: "Series",
  tags: "Tags",
  features: "Features",
  description: "Description",
  age_rating: "Age rating",
  release_date: "Release date",
  time_to_beat_hours: "Time to beat",
  status: "Status",
  purchase_price: "Price",
  purchase_price_currency_code: "Currency",
  purchase_date: "Purchase date",
};
function readable(field: string, value: string | null): string {
  if (value === null || value === "") return "Empty";
  if (field === "status") return STATUS_LABEL[value] ?? value;
  if (field === "purchase_price")
    return money(Number(value), props.game.ownership.priceCurrency);
  if (field.endsWith("_date")) {
    const n = Number(value);
    const ms = /^\d{9,}$/.test(value) ? n * 1000 : when(value);
    return ms === null ? value : dayFmt.format(ms);
  }
  return value.length > 160 ? `${value.slice(0, 160)}…` : value;
}

function plural(n: number, one: string, many = `${one}s`): string {
  return `${n} ${n === 1 ? one : many}`;
}
function list(names: string[], max = 2): string {
  const shown = names.slice(0, max).join(", ");
  return names.length > max ? `${shown} and ${names.length - max} more` : shown;
}

const entries = computed<Entry[]>(() => {
  const out: Entry[] = [];

  const added = when(props.game.dateAdded);
  if (added !== null)
    out.push({
      id: "added",
      at: added,
      group: "library",
      icon: "plus",
      title: "Added to your library",
      summary: props.game.source ? `From ${props.game.source}` : "",
      details: [
        ...(props.game.source
          ? [
              {
                type: "fact",
                label: "Source",
                value: props.game.source,
              } as Detail,
            ]
          : []),
        ...props.game.platforms.map(
          (p) =>
            ({ type: "fact", label: "Platform", value: p.platform }) as Detail,
        ),
      ],
    });

  const bought = when(props.game.ownership.purchaseDate);
  if (bought !== null)
    out.push({
      id: "purchased",
      at: bought,
      group: "library",
      icon: "tag",
      title: "Purchased",
      summary: money(
        props.game.ownership.price,
        props.game.ownership.priceCurrency,
      ),
      details: [
        { type: "fact", label: "Date", value: day(bought) },
        ...(props.game.ownership.price !== null
          ? [
              {
                type: "fact",
                label: "Price",
                value: money(
                  props.game.ownership.price,
                  props.game.ownership.priceCurrency,
                ),
              } as Detail,
            ]
          : []),
        ...(props.game.ownership.format
          ? [
              {
                type: "fact",
                label: "Format",
                value: props.game.ownership.format,
              } as Detail,
            ]
          : []),
        ...(props.game.ownership.condition
          ? [
              {
                type: "fact",
                label: "Condition",
                value: props.game.ownership.condition,
              } as Detail,
            ]
          : []),
      ],
    });

  // achievements, one entry per day
  const perDay = new Map<string, typeof dated.value>();
  for (const u of dated.value) {
    const k = new Date(u.at).toDateString();
    perDay.set(k, [...(perDay.get(k) ?? []), u]);
  }
  for (const [k, group] of perDay) {
    const sorted = [...group].sort((a, b) => a.at - b.at);
    const at = sorted[sorted.length - 1].at;
    out.push({
      id: `ach-${k}`,
      at,
      group: "achievements",
      icon: "trophy",
      title:
        sorted.length === 1
          ? `Unlocked ${sorted[0].a.name}`
          : `Unlocked ${plural(sorted.length, "achievement")}`,
      summary:
        sorted.length === 1
          ? (sorted[0].a.description ?? "")
          : list(sorted.map((u) => u.a.name)),
      details: sorted.map((u) => ({
        type: "achievement",
        name: u.a.name,
        icon: u.a.iconUrl ?? undefined,
        note: [
          timeFmt.format(u.at),
          typeof u.a.rarityPercent === "number"
            ? `${u.a.rarityPercent}% of players`
            : "",
        ]
          .filter(Boolean)
          .join(" · "),
      })),
    });
  }

  const done = when(props.game.completionDate);
  if (done !== null)
    out.push({
      id: "completed",
      at: done,
      group: "achievements",
      icon: "flag",
      title: "Completed",
      summary: "Every achievement unlocked",
      details: [{ type: "fact", label: "Date", value: day(done) }],
    });

  // metadata: one entry per moment and kind of change
  const byMoment = new Map<string, FieldChange[]>();
  for (const c of props.changes) {
    const category =
      c.fieldName === "status"
        ? "status"
        : c.fieldName === "purchase_price" ||
            c.fieldName === "purchase_price_currency_code"
          ? "price"
          : c.fieldName === "purchase_date"
            ? "purchase"
            : "metadata";
    const k = `${c.changedAt}|${category}`;
    byMoment.set(k, [...(byMoment.get(k) ?? []), c]);
  }
  for (const [k, group] of byMoment) {
    const category = k.split("|")[1];
    const at = Date.parse(group[0].changedAt);
    const details: Detail[] = group.map((c) => ({
      type: "change",
      label: FIELD_LABEL[c.fieldName] ?? c.fieldName,
      from: readable(c.fieldName, c.oldValue),
      to: readable(c.fieldName, c.newValue),
    }));
    const first = details[0] as Extract<Detail, { type: "change" }>;
    if (category === "status")
      out.push({
        id: `chg-${k}`,
        at,
        group: "library",
        icon: "status",
        title: "Changed status",
        summary: `${first.from} to ${first.to}`,
        details,
      });
    else if (category === "price")
      out.push({
        id: `chg-${k}`,
        at,
        group: "library",
        icon: "price",
        title: "Changed price",
        summary: `${first.from} to ${first.to}`,
        details,
      });
    else if (category === "purchase")
      out.push({
        id: `chg-${k}`,
        at,
        group: "library",
        icon: "tag",
        title: "Changed purchase date",
        summary: `${first.from} to ${first.to}`,
        details,
      });
    else
      out.push({
        id: `chg-${k}`,
        at,
        group: "metadata",
        icon: "edit",
        title: "Updated metadata",
        summary: list(
          details.map((d) => (d as { label: string }).label),
          3,
        ),
        details,
      });
  }

  // media, one entry per day and kind
  const mediaGroups = new Map<string, MediaItem[]>();
  for (const m of props.media) {
    const k = `${new Date(m.created_at * 1000).toDateString()}|${m.kind}`;
    mediaGroups.set(k, [...(mediaGroups.get(k) ?? []), m]);
  }
  const NOUN: Record<string, [string, string]> = {
    screenshot: ["screenshot", "screenshots"],
    clip: ["clip", "clips"],
    soundtrack: ["track", "tracks"],
  };
  for (const [k, group] of mediaGroups) {
    const kind = k.split("|")[1];
    const [one, many] = NOUN[kind] ?? ["file", "files"];
    const at = Math.max(...group.map((m) => m.created_at)) * 1000;
    const shown = group.slice(0, 12);
    out.push({
      id: `media-${k}`,
      at,
      group: "media",
      icon:
        kind === "clip" ? "film" : kind === "soundtrack" ? "music" : "image",
      title: `Added ${plural(group.length, one, many)}`,
      summary: list(
        group.map((m) => m.title || m.filename.split("_").slice(1).join("_")),
      ),
      details: shown.map((m) => ({
        type: "media",
        url: m.url,
        kind: m.kind,
        name: m.title || m.filename.split("_").slice(1).join("_"),
      })),
      more: group.length - shown.length,
    });
  }

  const played = when(props.game.lastPlayedAt);
  if (played !== null)
    out.push({
      id: "played",
      at: played,
      group: "library",
      icon: "play",
      title: "Last played",
      summary:
        playtime.value === "None yet"
          ? ""
          : `${playtime.value} played in total`,
      details: [],
    });

  return out.sort((a, b) => b.at - a.at);
});

const filter = ref<Filter>("all");
const FILTERS: { key: Filter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "achievements", label: "Achievements" },
  { key: "library", label: "Library" },
  { key: "metadata", label: "Metadata" },
  { key: "media", label: "Media" },
];
const counts = computed(() => {
  const c: Record<Filter, number> = {
    all: entries.value.length,
    achievements: 0,
    library: 0,
    metadata: 0,
    media: 0,
  };
  for (const e of entries.value) c[e.group]++;
  return c;
});
const shown = computed(() =>
  filter.value === "all"
    ? entries.value
    : entries.value.filter((e) => e.group === filter.value),
);
const months = computed(() => {
  const groups: { key: string; label: string; items: Entry[] }[] = [];
  for (const e of shown.value) {
    const d = new Date(e.at);
    const key = `${d.getFullYear()}-${d.getMonth()}`;
    let g = groups[groups.length - 1];
    if (!g || g.key !== key) {
      g = { key, label: monthFmt.format(d), items: [] };
      groups.push(g);
    }
    g.items.push(e);
  }
  return groups;
});

const open = ref<Set<string>>(new Set());
function toggle(id: string) {
  const next = new Set(open.value);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  open.value = next;
}
function hasDetails(e: Entry): boolean {
  return e.details.length > 0;
}

const ICONS: Record<string, string> = {
  plus: "M12 5v14M5 12h14",
  tag: "M20 12l-8 8-9-9V3h8z M7.5 7.5h.01",
  trophy:
    "M8 4h8v5a4 4 0 0 1-8 0z M8 4H5a2 2 0 0 0 0 4h1.5 M16 4h3a2 2 0 0 1 0 4h-1.5 M12 13v3 M9 20h6",
  flag: "M5 21V4 M5 4h11l-2 4 2 4H5",
  edit: "M12 20h9 M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z",
  status: "M5 12l5 5L20 7",
  price:
    "M12 2v20 M17 6.5C15.5 5 13.5 4.5 12 4.5c-2.5 0-4.5 1.2-4.5 3.2 0 4.3 9 2.2 9 6.6 0 2-2 3.2-4.5 3.2-2 0-4-.8-5-2",
  image: "M3 5h18v14H3z M3 16l5-5 4 4 3-3 6 6 M9 9.5h.01",
  film: "M4 4h16v16H4z M4 9h16 M4 15h16 M9 4v16 M15 4v16",
  music: "M9 18V5l12-2v13 M6 18a3 3 0 1 0 0 .01 M18 16a3 3 0 1 0 0 .01",
  play: "M8 5v14l11-7z",
};
</script>

<template>
  <div class="gs">
    <section class="gs-summary" aria-label="Summary">
      <div v-for="s in summary" :key="s.label" class="gs-stat">
        <span class="gs-label">{{ s.label }}</span>
        <span class="gs-value">{{ s.value }}</span>
        <span v-if="s.sub" class="gs-sub">{{ s.sub }}</span>
        <span v-if="s.progress != null" class="gs-meter" aria-hidden="true">
          <span :style="{ width: `${s.progress}%` }"></span>
        </span>
      </div>
    </section>

    <section class="gs-facts" aria-label="Details">
      <div v-for="f in facts" :key="f.label" class="gs-fact">
        <span class="gs-label">{{ f.label }}</span>
        <span class="gs-fact-value" :title="f.value">{{ f.value }}</span>
        <span v-if="f.note" class="gs-sub">{{ f.note }}</span>
      </div>
    </section>

    <section
      v-if="monthly.length > 1"
      class="gs-chart"
      aria-label="Achievements by month"
    >
      <h3>Achievements by month</h3>
      <div class="gs-bars">
        <div
          v-for="m in monthly"
          :key="m.key"
          class="gs-bar"
          :title="`${m.label} ${m.year}: ${m.n}`"
        >
          <span class="gs-bar-n">{{ m.n }}</span>
          <span class="gs-bar-fill" :style="{ height: `${m.pct}%` }"></span>
          <span class="gs-bar-label">{{ m.label }}</span>
        </div>
      </div>
    </section>

    <section class="gs-timeline" aria-label="History">
      <div class="gs-tl-head">
        <h2>History</h2>
        <div class="gs-chips" role="group" aria-label="Filter history">
          <button
            v-for="f in FILTERS"
            :key="f.key"
            type="button"
            class="ui-chip"
            :class="{ on: filter === f.key }"
            @click="filter = f.key"
          >
            {{ f.label }} <span class="n">{{ counts[f.key] }}</span>
          </button>
        </div>
      </div>

      <p v-if="error" class="gs-note">{{ error }}</p>
      <p v-else-if="loading && !entries.length" class="gs-note">Loading…</p>
      <p v-else-if="!shown.length" class="gs-note">
        Nothing here yet. Unlocking achievements, editing the game, or adding
        screenshots shows up in this timeline.
      </p>

      <div v-for="g in months" :key="g.key" class="gs-month">
        <h3 class="gs-month-label">{{ g.label }}</h3>
        <ol class="gs-list">
          <li
            v-for="e in g.items"
            :key="e.id"
            class="gs-entry"
            :class="[e.group, { open: open.has(e.id) }]"
          >
            <span class="gs-dot" aria-hidden="true">
              <svg
                viewBox="0 0 24 24"
                width="14"
                height="14"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path
                  v-for="(d, i) in (ICONS[e.icon] ?? ICONS.edit).split(' M')"
                  :key="i"
                  :d="i ? 'M' + d : d"
                />
              </svg>
            </span>
            <button
              type="button"
              class="gs-row"
              :disabled="!hasDetails(e)"
              :aria-expanded="hasDetails(e) ? open.has(e.id) : undefined"
              @click="toggle(e.id)"
            >
              <span class="gs-row-main">
                <span class="gs-row-title">{{ e.title }}</span>
                <span v-if="e.summary" class="gs-row-summary">{{
                  e.summary
                }}</span>
              </span>
              <span class="gs-row-when">
                <span>{{ dayFmt.format(e.at) }}</span>
                <span
                  v-if="!['added', 'purchased', 'completed'].includes(e.id)"
                  >{{ timeFmt.format(e.at) }}</span
                >
              </span>
              <svg
                v-if="hasDetails(e)"
                class="gs-chev"
                viewBox="0 0 24 24"
                width="14"
                height="14"
                fill="none"
                stroke="currentColor"
                stroke-width="2.2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <polyline points="6 9 12 15 18 9" />
              </svg>
            </button>

            <div v-if="open.has(e.id)" class="gs-details">
              <template v-for="(d, i) in e.details" :key="i">
                <div v-if="d.type === 'change'" class="gs-change">
                  <span class="gs-change-label">{{ d.label }}</span>
                  <span class="gs-from">{{ d.from }}</span>
                  <span class="gs-arrow">→</span>
                  <span class="gs-to">{{ d.to }}</span>
                </div>
                <div v-else-if="d.type === 'achievement'" class="gs-ach">
                  <span
                    class="gs-ach-icon"
                    :style="d.icon ? { backgroundImage: `url(${d.icon})` } : {}"
                  ></span>
                  <span class="gs-ach-name">{{ d.name }}</span>
                  <span class="gs-ach-note">{{ d.note }}</span>
                </div>
                <div v-else-if="d.type === 'fact'" class="gs-factrow">
                  <span>{{ d.label }}</span>
                  <strong>{{ d.value }}</strong>
                </div>
              </template>
              <div
                v-if="e.details.some((d) => d.type === 'media')"
                class="gs-media"
              >
                <template v-for="(d, i) in e.details" :key="i">
                  <template v-if="d.type === 'media'">
                    <img
                      v-if="d.kind === 'screenshot'"
                      :src="d.url"
                      :alt="d.name"
                      :title="d.name"
                      loading="lazy"
                    />
                    <span v-else class="gs-media-file" :title="d.name">{{
                      d.name
                    }}</span>
                  </template>
                </template>
                <span v-if="e.more" class="gs-more">+{{ e.more }} more</span>
              </div>
            </div>
          </li>
        </ol>
      </div>
    </section>
  </div>
</template>

<style scoped>
.gs {
  display: flex;
  flex-direction: column;
  gap: 28px;
  min-width: 0;
}
.gs-label {
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: #777;
}
.gs-sub {
  font-size: 0.76rem;
  color: #888;
}

.gs-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}
.gs-stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  padding: 16px 18px;
  background: #141414;
  border: 1px solid #262626;
  border-radius: 14px;
}
.gs-value {
  font-size: 1.7rem;
  font-weight: 800;
  line-height: 1.15;
  color: #f2f2f2;
  font-variant-numeric: tabular-nums;
  overflow-wrap: anywhere;
}
.gs-meter {
  margin-top: 6px;
  height: 4px;
  border-radius: 999px;
  background: #262626;
  overflow: hidden;
}
.gs-meter span {
  display: block;
  height: 100%;
  background: #d68a34;
  border-radius: 999px;
}

.gs-facts {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
  gap: 18px 24px;
  padding: 4px 2px;
}
.gs-fact {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}
.gs-fact-value {
  font-size: 0.95rem;
  font-weight: 600;
  color: #e8e8e8;
  overflow-wrap: anywhere;
}

.gs-chart h3,
.gs-month-label {
  margin: 0 0 12px;
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #777;
}
.gs-bars {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  height: 120px;
  padding: 0 2px;
}
.gs-bar {
  flex: 1;
  min-width: 0;
  max-width: 54px;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
}
.gs-bar-fill {
  display: block;
  width: 100%;
  background: linear-gradient(to top, rgba(214, 138, 52, 0.55), #d68a34);
  border-radius: 6px 6px 2px 2px;
}
.gs-bar-n {
  font-size: 0.7rem;
  font-weight: 700;
  color: #d68a34;
  font-variant-numeric: tabular-nums;
}
.gs-bar-label {
  font-size: 0.68rem;
  color: #777;
}

.gs-tl-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 18px;
  padding-top: 24px;
  border-top: 1px solid #262626;
}
.gs-tl-head h2 {
  margin: 0;
  font-size: 1.1rem;
}
.gs-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.gs-note {
  margin: 0;
  color: #777;
  font-size: 0.88rem;
}
.gs-month {
  margin-bottom: 22px;
}
.gs-list {
  list-style: none;
  margin: 0;
  padding: 0 0 0 18px;
  border-left: 2px solid #232323;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.gs-entry {
  position: relative;
  min-width: 0;
}
.gs-dot {
  position: absolute;
  left: -34px;
  top: 10px;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #1a1a1a;
  border: 2px solid #232323;
  color: #9c9c9c;
  box-sizing: border-box;
}
.gs-entry.achievements .gs-dot {
  color: #d68a34;
}
.gs-entry.metadata .gs-dot {
  color: #7aa7d9;
}
.gs-entry.media .gs-dot {
  color: #7fc08a;
}
.gs-row {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 11px 14px;
  background: #141414;
  border: 1px solid #262626;
  border-radius: 12px;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.15s ease;
}
.gs-row:disabled {
  cursor: default;
}
.gs-row:not(:disabled):hover {
  border-color: #3a3a3a;
}
.gs-entry.open .gs-row {
  border-color: rgba(214, 138, 52, 0.45);
  border-bottom-left-radius: 0;
  border-bottom-right-radius: 0;
}
.gs-row-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.gs-row-title {
  font-size: 0.92rem;
  font-weight: 700;
  color: #f2f2f2;
  overflow-wrap: anywhere;
}
.gs-row-summary {
  font-size: 0.8rem;
  color: #8c8c8c;
  overflow-wrap: anywhere;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.gs-row-when {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 1px;
  font-size: 0.76rem;
  color: #888;
  font-variant-numeric: tabular-nums;
}
.gs-chev {
  flex-shrink: 0;
  color: #666;
  transition: transform 0.15s ease;
}
.gs-entry.open .gs-chev {
  transform: rotate(180deg);
}
.gs-details {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 14px 14px;
  background: #101010;
  border: 1px solid rgba(214, 138, 52, 0.45);
  border-top: none;
  border-radius: 0 0 12px 12px;
}
.gs-change {
  display: grid;
  grid-template-columns: 120px minmax(0, 1fr) auto minmax(0, 1fr);
  gap: 10px;
  align-items: baseline;
  font-size: 0.84rem;
}
.gs-change-label {
  color: #888;
  font-weight: 600;
}
.gs-from {
  color: #8c8c8c;
  text-decoration: line-through;
  text-decoration-color: #444;
  overflow-wrap: anywhere;
}
.gs-arrow {
  color: #666;
}
.gs-to {
  color: #d68a34;
  overflow-wrap: anywhere;
}
.gs-ach {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.gs-ach-icon {
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  border-radius: 7px;
  background: #222 center / cover no-repeat;
}
.gs-ach-name {
  flex: 1;
  min-width: 0;
  font-size: 0.86rem;
  font-weight: 600;
  overflow-wrap: anywhere;
}
.gs-ach-note {
  flex-shrink: 0;
  font-size: 0.74rem;
  color: #888;
  text-align: right;
}
.gs-factrow {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  font-size: 0.84rem;
  color: #888;
}
.gs-factrow strong {
  color: #ddd;
  text-transform: capitalize;
}
.gs-media {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.gs-media img {
  width: 110px;
  aspect-ratio: 16 / 9;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid #262626;
}
.gs-media-file {
  max-width: 220px;
  padding: 6px 10px;
  border-radius: 8px;
  background: #1a1a1a;
  font-size: 0.78rem;
  color: #bbb;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.gs-more {
  align-self: center;
  font-size: 0.78rem;
  color: #888;
}

@media (max-width: 760px) {
  .gs-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .gs-change {
    grid-template-columns: 1fr;
    gap: 2px;
  }
  .gs-arrow {
    display: none;
  }
  .gs-row {
    flex-wrap: wrap;
  }
  .gs-row-when {
    flex-direction: row;
    gap: 8px;
  }
}
</style>
