<script setup lang="ts">
// One statistics page with a tab per lens: Overview, Games, Movies, TV
// Shows, Anime. Same layout as the library pages' Stats tab: headline
// cards, a big row of top-rated posters, then panels of charts.
//
// Every number is exact or absent. Watch time adds up real runtimes of
// episodes actually watched (flagged, or within the season's progress
// counter), plus one more pass through those for each logged rewatch; a season counts as completed only when every one of
// its episodes is watched. Anything with no runtime on record is reported
// in a note, never given a guessed length.
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import AppTopBar from "../components/AppTopBar.vue";
import SegmentedTabs from "../components/SegmentedTabs.vue";
import BarList from "../components/stats/BarList.vue";
import ColumnChart from "../components/stats/ColumnChart.vue";
import ActivityHeatmap from "../components/stats/ActivityHeatmap.vue";
import DonutChart from "../components/stats/DonutChart.vue";
import StatCard from "../components/stats/StatCard.vue";
import TopRatedRow from "../components/stats/TopRatedRow.vue";
import { fetchMediaStats, peekMediaStats } from "../services/mediaStats";
import type {
  EpisodicStats,
  MediaStats,
  StatusCounts,
  TopTitle,
} from "../services/mediaStats";
import { useKeptAlive } from "../utils/useKeptAlive";

type Tab = "overview" | "games" | "movie" | "tv" | "anime";
const TABS: { value: Tab; label: string }[] = [
  { value: "overview", label: "Overview" },
  { value: "games", label: "Games" },
  { value: "movie", label: "Movies" },
  { value: "tv", label: "TV Shows" },
  { value: "anime", label: "Anime" },
];

const router = useRouter();
const stats = ref<MediaStats | null>(peekMediaStats());
const loading = ref(!stats.value);
const error = ref<string | null>(null);
const tab = ref<Tab>((localStorage.getItem("statsTab") as Tab) || "overview");

async function load() {
  error.value = null;
  try {
    stats.value = await fetchMediaStats();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to load statistics.";
  } finally {
    loading.value = false;
  }
}
onMounted(load);
useKeptAlive(load);

function setTab(t: Tab) {
  tab.value = t;
  try {
    localStorage.setItem("statsTab", t);
  } catch {
    /* remembering the tab is optional */
  }
}

// ---- formatting ----
function fmtMinutes(m: number): string {
  const d = Math.floor(m / 1440);
  const h = Math.floor((m % 1440) / 60);
  const mm = m % 60;
  if (d) return `${d}d ${h}h`;
  if (h) return `${h}h ${mm}m`;
  return `${mm}m`;
}
function fmtHours(minutes: number): string {
  return `${(minutes / 60).toLocaleString(undefined, { maximumFractionDigits: 1 })} hours`;
}
function fmtSeconds(seconds: number): string {
  return fmtMinutes(Math.floor(seconds / 60));
}
function pct(a: number, b: number): string {
  return b ? `${Math.round((a / b) * 100)}%` : "0%";
}
function shortMonth(key: string): string {
  const [y, m] = key.split("-").map(Number);
  return new Date(y, m - 1, 1).toLocaleDateString(undefined, {
    month: "short",
  });
}

// ---- chart inputs ----
const STATUS_META: { key: keyof StatusCounts; label: string; color: string }[] =
  [
    { key: "watching", label: "Watching", color: "#d68a34" },
    { key: "completed", label: "Completed", color: "#6fbf73" },
    { key: "hold", label: "On Hold", color: "#7ba7d9" },
    { key: "dropped", label: "Dropped", color: "#d96f6f" },
    { key: "plan", label: "Plan to Watch", color: "#9d8cd9" },
  ];
function statusSlices(s: StatusCounts, games = false) {
  return STATUS_META.map((m) => ({
    name:
      games && m.key === "watching"
        ? "Playing"
        : games && m.key === "plan"
          ? "Wishlist"
          : m.label,
    value: s[m.key],
    color: m.color,
  }));
}
function scoreColumns(d: Record<string, number>) {
  return Array.from({ length: 10 }, (_, i) => ({
    label: String(i + 1),
    value: d[String(i + 1)] ?? 0,
  }));
}
// "151 episodes", "3 achievements", or both, from the exact split for the day
const busiestDayText = computed(() => {
  const day = stats.value?.overview.activity.busiest_day;
  if (!day) return "";
  const parts: string[] = [];
  if (day.episodes)
    parts.push(`${day.episodes} episode${day.episodes === 1 ? "" : "s"}`);
  if (day.achievements)
    parts.push(
      `${day.achievements} achievement${day.achievements === 1 ? "" : "s"}`,
    );
  return parts.join(" and ") || `${day.count} entries`;
});

function named(rows: { name: string; count: number }[]) {
  return rows.map((r) => ({ name: r.name, value: r.count }));
}
function years(rows: { year: number; count: number }[]) {
  return rows.map((y) => ({ label: String(y.year), value: y.count }));
}
function months(rows: { month: string; count: number }[]) {
  return rows.map((m) => ({ label: shortMonth(m.month), value: m.count }));
}

const KIND_LABEL: Record<string, string> = {
  movie: "Movies",
  tv: "TV Shows",
  anime: "Anime",
  game: "Games",
};
function openKind(kind: string, id: string) {
  const base =
    kind === "movie"
      ? "/movies"
      : kind === "tv"
        ? "/tv"
        : kind === "anime"
          ? "/anime"
          : "/games";
  router.push(`${base}/${id}`);
}
// genres you rate highest: only ones with a score, best first
function bestGenres(
  rows: { name: string; count: number; average?: number | null }[],
) {
  return rows
    .filter((g) => g.average != null)
    .sort((a, b) => (b.average ?? 0) - (a.average ?? 0))
    .map((g) => ({
      name: g.name,
      value: g.average ?? 0,
      label: String(g.average),
      hint: `${g.count} titles`,
    }));
}
function progressPct(p: { watched: number; total: number }): number {
  return p.total ? Math.min(100, Math.round((p.watched / p.total) * 100)) : 0;
}
function openTitle(t: TopTitle) {
  const base =
    t.kind === "movie"
      ? "/movies"
      : t.kind === "tv"
        ? "/tv"
        : t.kind === "anime"
          ? "/anime"
          : "/games";
  router.push(`${base}/${t.id}`);
}

const totalMinutes = computed(() =>
  stats.value
    ? stats.value.overview.media_minutes +
      Math.floor(stats.value.overview.game_seconds / 60)
    : 0,
);
const totalTitles = computed(() =>
  stats.value
    ? stats.value.overview.kinds.reduce((n, k) => n + k.titles, 0)
    : 0,
);
const totalCompleted = computed(() =>
  stats.value
    ? stats.value.overview.kinds.reduce((n, k) => n + k.completed, 0)
    : 0,
);
const totalFavorites = computed(() =>
  stats.value
    ? stats.value.overview.media_favorites + stats.value.games.favorites
    : 0,
);
const unplayedSub = computed(() => {
  const u = stats.value?.games.insights.unplayed;
  if (!u) return "";
  const spent = u.spent
    .map((s) => `${s.amount.toLocaleString()} ${s.currency}`)
    .join(", ");
  return spent ? `owned games, ${spent} spent on them` : "owned games";
});
const backlogHours = computed(() => {
  const b = stats.value?.games.insights.backlog;
  if (!b || b.count === b.without_estimate) return "–";
  return `${b.hours} hours`;
});
// backlog hours only add games that have a time-to-beat; the rest are named
const backlogSub = computed(() => {
  const b = stats.value?.games.insights.backlog;
  if (!b) return "";
  const missing = b.without_estimate
    ? `, ${b.without_estimate} without a time-to-beat`
    : "";
  return `${b.count} backlog game${b.count === 1 ? "" : "s"}${missing}`;
});
function progressText(p: {
  label?: string;
  watched: number;
  total: number;
}): string {
  if (p.label) return p.label;
  return p.total ? `${p.watched} / ${p.total}` : String(p.watched);
}
function secondsRows(rows: { name: string; seconds: number }[]) {
  return rows.map((r) => ({
    name: r.name,
    value: r.seconds,
    label: fmtSeconds(r.seconds),
  }));
}
function fmtDate(epoch: number): string {
  return new Date(epoch * 1000).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

// the TV and Anime tabs share one layout
const episodic = computed<EpisodicStats | null>(() => {
  if (!stats.value) return null;
  return tab.value === "tv"
    ? stats.value.tv
    : tab.value === "anime"
      ? stats.value.anime
      : null;
});
</script>

<template>
  <main class="ui-page">
    <AppTopBar>
      <SegmentedTabs
        :options="TABS"
        :model-value="tab"
        aria-label="Statistics sections"
        @update:model-value="setTab($event as Tab)"
      />
    </AppTopBar>

    <div class="ui-content">
      <div class="ui-head">
        <h1>Statistics</h1>
      </div>
      <p v-if="loading" class="ui-state">Loading…</p>
      <p v-else-if="error && !stats" class="ui-state error">{{ error }}</p>

      <template v-else-if="stats">
        <!-- ================= OVERVIEW ================= -->
        <template v-if="tab === 'overview'">
          <div class="stats-summary">
            <StatCard
              icon="clock"
              label="Total time"
              :value="fmtMinutes(totalMinutes)"
              :sub="`${fmtMinutes(stats.overview.media_minutes)} watched, ${fmtSeconds(stats.overview.game_seconds)} played`"
            />
            <StatCard
              icon="grid"
              label="Titles tracked"
              :value="totalTitles"
              :sub="`${totalCompleted} completed across movies, TV, anime and games`"
            />
            <StatCard
              icon="heart"
              label="Favorites"
              :value="totalFavorites"
              sub="across every type"
            />
            <StatCard
              icon="trophy"
              label="Games finished this year"
              :value="stats.overview.games_finished_this_year"
              :sub="`${stats.games.achievements_unlocked} achievements unlocked overall`"
            />
            <StatCard
              icon="flame"
              label="Current streak"
              :value="`${stats.overview.activity.current_streak} days`"
              :sub="`longest ${stats.overview.activity.longest_streak} days`"
            />
            <StatCard
              icon="calendar"
              label="Active days"
              :value="stats.overview.activity.active_days_total"
              sub="days with an episode or achievement logged"
            />
          </div>

          <section
            v-if="stats.overview.top_rated.length"
            class="stats-panel toprated-panel"
          >
            <h2>Top rated</h2>
            <TopRatedRow
              :items="stats.overview.top_rated"
              :limit="10"
              @open="openTitle"
            />
          </section>

          <div class="stats-panels">
            <section class="stats-panel">
              <h2>Titles by type</h2>
              <DonutChart
                :slices="
                  stats.overview.kinds.map((k) => ({
                    name: KIND_LABEL[k.kind],
                    value: k.titles,
                  }))
                "
                center-label="titles"
              />
            </section>
            <section class="stats-panel">
              <h2>Time by type</h2>
              <DonutChart
                :slices="
                  stats.overview.kinds.map((k) => ({
                    name: `${KIND_LABEL[k.kind]} (${fmtMinutes(k.minutes)})`,
                    value: k.minutes,
                  }))
                "
                center-label="minutes"
                empty="Nothing watched or played yet."
              />
            </section>
            <section
              v-if="stats.overview.in_progress.length"
              class="stats-panel wide"
            >
              <h2>In progress</h2>
              <div class="progress-list">
                <button
                  v-for="p in stats.overview.in_progress"
                  :key="`${p.kind}-${p.id}`"
                  type="button"
                  class="progress-row"
                  @click="openKind(p.kind, p.id)"
                >
                  <span
                    class="progress-art"
                    :style="
                      p.posterUrl
                        ? { backgroundImage: `url(${p.posterUrl})` }
                        : {}
                    "
                  ></span>
                  <span class="progress-main">
                    <span class="progress-title">{{ p.title }}</span>
                    <span v-if="p.kind !== 'game'" class="progress-track"
                      ><span
                        class="progress-fill"
                        :style="{ width: progressPct(p) + '%' }"
                      ></span
                    ></span>
                    <span v-else class="dim">Game</span>
                  </span>
                  <span class="progress-count">{{ progressText(p) }}</span>
                </button>
              </div>
            </section>
            <section class="stats-panel">
              <h2>Backlog by type</h2>
              <ul class="plain-list">
                <li v-for="b in stats.overview.backlog" :key="b.kind">
                  <span>{{ KIND_LABEL[b.kind] }}</span>
                  <span class="dim"
                    >{{ b.waiting }}
                    {{ b.kind === "game" ? "on the wishlist" : "planned" }},
                    {{ b.on_hold }} in the backlog</span
                  >
                </li>
              </ul>
              <p v-if="stats.overview.game_backlog.count" class="note">
                {{ backlogSub }}
              </p>
            </section>
            <section class="stats-panel">
              <h2>Average score by type</h2>
              <BarList
                :rows="
                  stats.overview.score_by_type
                    .filter((s) => s.average !== null)
                    .map((s) => ({
                      name: KIND_LABEL[s.kind],
                      value: s.average ?? 0,
                      label: String(s.average),
                      hint: `${s.rated} rated`,
                    }))
                "
                empty="Nothing rated yet."
              />
            </section>
            <section
              v-if="stats.overview.needs_score.count"
              class="stats-panel"
            >
              <h2>Completed, not scored yet</h2>
              <p class="note lead">
                {{ stats.overview.needs_score.count }} completed title{{
                  stats.overview.needs_score.count === 1 ? "" : "s"
                }}
                still have no score.
              </p>
              <ul class="plain-list">
                <li
                  v-for="t in stats.overview.needs_score.items"
                  :key="`${t.kind}-${t.id}`"
                >
                  <button type="button" @click="openKind(t.kind, t.id)">
                    {{ t.title }}
                  </button>
                  <span class="dim">{{ KIND_LABEL[t.kind] }}</span>
                </li>
              </ul>
            </section>
            <section class="stats-panel wide">
              <h2>Activity, last 52 weeks</h2>
              <ActivityHeatmap :days="stats.overview.activity.per_day" />
              <p v-if="stats.overview.activity.busiest_day" class="note">
                Busiest day: {{ stats.overview.activity.busiest_day.date }} with
                {{ busiestDayText }}.
              </p>
            </section>
          </div>
        </template>

        <!-- ================= GAMES ================= -->
        <template v-else-if="tab === 'games'">
          <div class="stats-summary">
            <StatCard
              icon="grid"
              label="Games"
              :value="stats.games.titles"
              :sub="`${stats.games.by_status.completed} completed`"
            />
            <StatCard
              icon="heart"
              label="Favorites"
              :value="stats.games.favorites"
            />
            <StatCard
              icon="clock"
              label="Playtime"
              :value="fmtSeconds(stats.games.playtime_seconds)"
              :sub="`${(stats.games.playtime_seconds / 3600).toLocaleString(undefined, { maximumFractionDigits: 1 })} hours across ${stats.games.games_with_playtime} games`"
            />
            <StatCard
              icon="trophy"
              label="Achievements"
              :value="`${stats.games.achievements_unlocked} / ${stats.games.achievements_total}`"
              :sub="`${pct(stats.games.achievements_unlocked, stats.games.achievements_total)} unlocked`"
            />
            <StatCard
              icon="star"
              label="Mean score"
              :value="stats.games.score.average ?? '–'"
              :sub="`${stats.games.score.rated} rated`"
            />
            <StatCard
              icon="clock"
              label="Average playtime"
              :value="
                stats.games.insights.average_seconds === null
                  ? '–'
                  : fmtSeconds(stats.games.insights.average_seconds)
              "
              :sub="
                stats.games.insights.median_seconds === null
                  ? 'no playtime recorded'
                  : `median ${fmtSeconds(stats.games.insights.median_seconds)}`
              "
            />
            <StatCard
              icon="grid"
              label="No playtime recorded"
              :value="stats.games.insights.unplayed.count"
              :sub="unplayedSub"
            />
            <StatCard
              icon="play"
              label="Played last 30 days"
              :value="stats.games.insights.played_last_30_days"
              :sub="`${stats.games.insights.finished_this_year} finished this year`"
            />
            <StatCard
              icon="check"
              label="Backlog"
              :value="backlogHours"
              :sub="backlogSub"
            />
            <StatCard
              v-for="s in stats.games.spent"
              :key="s.currency"
              icon="check"
              :label="`Spent (${s.currency})`"
              :value="s.amount.toLocaleString()"
              sub="from recorded purchase prices"
            />
          </div>
          <section
            v-if="stats.games.top_rated.length"
            class="stats-panel toprated-panel"
          >
            <h2>Top rated</h2>
            <TopRatedRow :items="stats.games.top_rated" @open="openTitle" />
          </section>
          <div class="stats-panels">
            <section class="stats-panel">
              <h2>Status breakdown</h2>
              <DonutChart
                :slices="statusSlices(stats.games.by_status, true)"
                center-label="games"
              />
            </section>
            <section class="stats-panel">
              <h2>Score distribution</h2>
              <ColumnChart
                :columns="scoreColumns(stats.games.score.distribution)"
                empty="Nothing rated yet."
              />
            </section>
            <section class="stats-panel">
              <h2>Most played</h2>
              <BarList
                :rows="
                  stats.games.most_played.map((g) => ({
                    name: g.title,
                    value: g.seconds,
                    label: fmtSeconds(g.seconds),
                  }))
                "
                empty="No playtime recorded yet."
              />
            </section>
            <section v-if="stats.games.sources.length" class="stats-panel">
              <h2>Sources</h2>
              <DonutChart
                :slices="named(stats.games.sources)"
                center-label="games"
              />
            </section>
            <section
              v-if="stats.games.finished_per_year.length"
              class="stats-panel"
            >
              <h2>Finished per year</h2>
              <ColumnChart :columns="years(stats.games.finished_per_year)" />
            </section>
            <section class="stats-panel">
              <h2>Release years</h2>
              <ColumnChart :columns="years(stats.games.by_release_year)" />
            </section>
            <section v-if="stats.games.tags.length" class="stats-panel">
              <h2>Top tags</h2>
              <BarList :rows="named(stats.games.tags)" />
            </section>
            <section v-if="stats.games.developers.length" class="stats-panel">
              <h2>Top developers</h2>
              <BarList :rows="named(stats.games.developers)" />
            </section>
            <section class="stats-panel">
              <h2>Added, last 12 months</h2>
              <ColumnChart :columns="months(stats.games.added_per_month)" />
            </section>
            <section class="stats-panel">
              <h2>Playtime distribution</h2>
              <ColumnChart
                :columns="
                  stats.games.insights.playtime_buckets.map((b) => ({
                    label: b.label,
                    value: b.count,
                  }))
                "
              />
              <p class="note">
                "No playtime recorded" means the platform reported none for that
                game.
              </p>
            </section>
            <section
              v-if="stats.games.insights.recently_played.length"
              class="stats-panel"
            >
              <h2>Recently played</h2>
              <ul class="plain-list">
                <li
                  v-for="g in stats.games.insights.recently_played"
                  :key="g.id"
                >
                  <button type="button" @click="openKind('game', g.id)">
                    {{ g.title }}
                  </button>
                  <span class="dim">{{ fmtDate(g.last_played_at) }}</span>
                </li>
              </ul>
            </section>
            <section
              v-if="stats.games.insights.closest_to_full.length"
              class="stats-panel"
            >
              <h2>Closest to 100%</h2>
              <BarList
                :rows="
                  stats.games.insights.closest_to_full.map((g) => ({
                    name: g.title,
                    value: g.unlocked / g.total,
                    label: `${g.unlocked} / ${g.total}`,
                  }))
                "
              />
              <p class="note">
                {{ stats.games.insights.fully_unlocked }} game{{
                  stats.games.insights.fully_unlocked === 1 ? "" : "s"
                }}
                fully unlocked.
              </p>
            </section>
            <section
              v-if="stats.games.insights.cost_per_hour.length"
              class="stats-panel"
            >
              <h2>Cost per hour</h2>
              <ul class="plain-list">
                <li
                  v-for="c in stats.games.insights.cost_per_hour"
                  :key="c.currency"
                >
                  <span
                    >{{ c.per_hour.toLocaleString() }} {{ c.currency }} per
                    hour</span
                  >
                  <span class="dim"
                    >{{ c.hours.toLocaleString() }} hours over
                    {{ c.games }} priced game{{
                      c.games === 1 ? "" : "s"
                    }}</span
                  >
                </li>
              </ul>
              <p class="note">
                Only games with both a purchase price and recorded playtime.
              </p>
            </section>
            <section
              v-if="stats.games.insights.seconds_by_source.length"
              class="stats-panel"
            >
              <h2>Playtime by source</h2>
              <BarList
                :rows="secondsRows(stats.games.insights.seconds_by_source)"
              />
            </section>
            <section
              v-if="stats.games.insights.seconds_by_developer.length"
              class="stats-panel"
            >
              <h2>Playtime by developer</h2>
              <BarList
                :rows="secondsRows(stats.games.insights.seconds_by_developer)"
              />
            </section>
            <section
              v-if="stats.games.insights.seconds_by_series.length"
              class="stats-panel"
            >
              <h2>Playtime by series</h2>
              <BarList
                :rows="secondsRows(stats.games.insights.seconds_by_series)"
              />
            </section>
            <section
              v-if="stats.games.insights.decades.length"
              class="stats-panel"
            >
              <h2>Release decades</h2>
              <ColumnChart
                :columns="
                  stats.games.insights.decades.map((d) => ({
                    label: `${d.decade}s`,
                    value: d.count,
                  }))
                "
              />
            </section>
            <section
              v-if="stats.games.insights.age_ratings.length"
              class="stats-panel"
            >
              <h2>Age ratings</h2>
              <BarList :rows="named(stats.games.insights.age_ratings)" />
            </section>
            <section
              v-if="stats.games.insights.features.length"
              class="stats-panel"
            >
              <h2>Features</h2>
              <BarList :rows="named(stats.games.insights.features)" />
            </section>
          </div>
        </template>

        <!-- ================= MOVIES ================= -->
        <template v-else-if="tab === 'movie'">
          <div class="stats-summary">
            <StatCard
              icon="grid"
              label="Total titles"
              :value="stats.movie.titles"
              :sub="`${stats.movie.movies_watched} watched`"
            />
            <StatCard
              icon="check"
              label="Completed"
              :value="stats.movie.by_status.completed"
            />
            <StatCard
              icon="heart"
              label="Favorites"
              :value="stats.movie.favorites"
            />
            <StatCard
              icon="clock"
              label="Time watched"
              :value="fmtMinutes(stats.movie.minutes_watched)"
              :sub="`${fmtHours(stats.movie.minutes_watched)}; ${fmtMinutes(stats.movie.minutes_rewatch)} of it rewatches`"
            />
            <StatCard
              icon="play"
              label="Rewatches"
              :value="stats.movie.rewatches"
              :sub="`${stats.movie.rewatch_logs} logged with a date`"
            />
            <StatCard
              icon="star"
              label="Mean score"
              :value="stats.movie.score.average ?? '–'"
              :sub="`${stats.movie.score.rated} rated`"
            />
          </div>
          <p v-if="stats.movie.movies_without_runtime" class="note warn">
            {{ stats.movie.movies_without_runtime }} watched movie{{
              stats.movie.movies_without_runtime === 1 ? " has" : "s have"
            }}
            no runtime on record and
            {{ stats.movie.movies_without_runtime === 1 ? "is" : "are" }} left
            out of the watch time rather than guessed.
          </p>
          <section
            v-if="stats.movie.top_rated.length"
            class="stats-panel toprated-panel"
          >
            <h2>Top rated</h2>
            <TopRatedRow :items="stats.movie.top_rated" @open="openTitle" />
          </section>
          <div class="stats-panels">
            <section class="stats-panel">
              <h2>Status breakdown</h2>
              <DonutChart
                :slices="statusSlices(stats.movie.by_status)"
                center-label="movies"
              />
            </section>
            <section class="stats-panel">
              <h2>Score distribution</h2>
              <ColumnChart
                :columns="scoreColumns(stats.movie.score.distribution)"
                empty="Nothing rated yet."
              />
            </section>
            <section v-if="stats.movie.minutes_rewatch" class="stats-panel">
              <h2>Watch time</h2>
              <DonutChart
                :slices="[
                  {
                    name: 'First watch',
                    value: stats.movie.minutes_first,
                    color: '#d68a34',
                  },
                  {
                    name: 'Rewatches',
                    value: stats.movie.minutes_rewatch,
                    color: '#7ba7d9',
                  },
                ]"
                center-label="minutes"
              />
            </section>
            <section
              v-if="stats.movie.most_rewatched.length"
              class="stats-panel"
            >
              <h2>Most rewatched</h2>
              <BarList
                :rows="
                  stats.movie.most_rewatched.map((r) => ({
                    name: r.title,
                    value: r.count,
                    label: `${r.count}x`,
                  }))
                "
              />
            </section>
            <section v-if="stats.movie.genres.length" class="stats-panel">
              <h2>Top genres</h2>
              <DonutChart
                :slices="named(stats.movie.genres)"
                center-label="genre tags"
              />
            </section>
            <section
              v-if="bestGenres(stats.movie.genres).length"
              class="stats-panel"
            >
              <h2>Genres you rate highest</h2>
              <BarList :rows="bestGenres(stats.movie.genres)" />
            </section>
            <section class="stats-panel">
              <h2>Release years</h2>
              <ColumnChart :columns="years(stats.movie.by_release_year)" />
            </section>
            <section v-if="stats.movie.directors.length" class="stats-panel">
              <h2>Directors</h2>
              <BarList :rows="named(stats.movie.directors)" />
            </section>
            <section v-if="stats.movie.studios.length" class="stats-panel">
              <h2>Studios</h2>
              <BarList :rows="named(stats.movie.studios)" />
            </section>
            <section class="stats-panel">
              <h2>Added, last 12 months</h2>
              <ColumnChart :columns="months(stats.movie.added_per_month)" />
            </section>
          </div>
        </template>

        <!-- ================= TV + ANIME ================= -->
        <template v-else-if="episodic">
          <div class="stats-summary">
            <StatCard
              icon="grid"
              label="Total titles"
              :value="episodic.titles"
              :sub="`${episodic.by_status.completed} completed`"
            />
            <StatCard
              icon="heart"
              label="Favorites"
              :value="episodic.favorites"
            />
            <StatCard
              icon="play"
              label="Episodes watched"
              :value="episodic.episodes_watched + episodic.episodes_rewatched"
              :sub="
                episodic.episodes_rewatched
                  ? `${episodic.episodes_watched} first watch + ${episodic.episodes_rewatched} rewatched`
                  : `of ${episodic.episodes_known} known episodes`
              "
            />
            <StatCard
              icon="clock"
              label="Time watched"
              :value="fmtMinutes(episodic.minutes_watched)"
              :sub="`${fmtHours(episodic.minutes_watched)}; ${fmtMinutes(episodic.minutes_rewatch)} of it rewatches`"
            />
            <StatCard
              icon="check"
              label="Seasons completed"
              :value="episodic.seasons_completed"
              :sub="`${episodic.seasons_in_progress} more in progress, not counted`"
            />
            <StatCard
              icon="star"
              label="Mean score"
              :value="episodic.score.average ?? '–'"
              :sub="`${episodic.score.rated} rated`"
            />
          </div>
          <p v-if="episodic.episodes_without_runtime" class="note warn">
            {{ episodic.episodes_without_runtime }} watched episode{{
              episodic.episodes_without_runtime === 1 ? " has" : "s have"
            }}
            no runtime on record and
            {{ episodic.episodes_without_runtime === 1 ? "is" : "are" }} left
            out of the watch time rather than guessed.
          </p>
          <section
            v-if="episodic.top_rated.length"
            class="stats-panel toprated-panel"
          >
            <h2>Top rated</h2>
            <TopRatedRow :items="episodic.top_rated" @open="openTitle" />
          </section>
          <div class="stats-panels">
            <section class="stats-panel">
              <h2>Status breakdown</h2>
              <DonutChart
                :slices="statusSlices(episodic.by_status)"
                :center-label="tab === 'tv' ? 'shows' : 'anime'"
              />
            </section>
            <section class="stats-panel">
              <h2>Score distribution</h2>
              <ColumnChart
                :columns="scoreColumns(episodic.score.distribution)"
                empty="Nothing rated yet."
              />
            </section>
            <section v-if="episodic.minutes_rewatch" class="stats-panel">
              <h2>Watch time</h2>
              <DonutChart
                :slices="[
                  {
                    name: 'First watch',
                    value: episodic.minutes_first,
                    color: '#d68a34',
                  },
                  {
                    name: 'Rewatches',
                    value: episodic.minutes_rewatch,
                    color: '#7ba7d9',
                  },
                ]"
                center-label="minutes"
              />
            </section>
            <section v-if="episodic.most_rewatched.length" class="stats-panel">
              <h2>Most rewatched</h2>
              <BarList
                :rows="
                  episodic.most_rewatched.map((r) => ({
                    name: r.title,
                    value: r.count,
                    label: `${r.count}x`,
                  }))
                "
              />
            </section>
            <section v-if="episodic.genres.length" class="stats-panel">
              <h2>Top genres</h2>
              <DonutChart
                :slices="named(episodic.genres)"
                center-label="genre tags"
              />
            </section>
            <section
              v-if="tab === 'anime' && episodic.formats.length"
              class="stats-panel"
            >
              <h2>By format</h2>
              <DonutChart
                :slices="named(episodic.formats)"
                center-label="titles"
              />
            </section>
            <section v-if="episodic.most_watched.length" class="stats-panel">
              <h2>Most time watched</h2>
              <BarList
                :rows="
                  episodic.most_watched.map((s) => ({
                    name: s.title,
                    value: s.minutes,
                    label: `${fmtMinutes(s.minutes)} · ${s.episodes} eps`,
                  }))
                "
              />
            </section>
            <section
              v-if="bestGenres(episodic.genres).length"
              class="stats-panel"
            >
              <h2>Genres you rate highest</h2>
              <BarList :rows="bestGenres(episodic.genres)" />
            </section>
            <section class="stats-panel">
              <h2>Release years</h2>
              <ColumnChart :columns="years(episodic.by_release_year)" />
            </section>
            <section v-if="episodic.studios.length" class="stats-panel">
              <h2>{{ tab === "tv" ? "Creators" : "Studios" }}</h2>
              <BarList :rows="named(episodic.studios)" />
            </section>
            <section class="stats-panel">
              <h2>Added, last 12 months</h2>
              <ColumnChart :columns="months(episodic.added_per_month)" />
            </section>
          </div>
        </template>
      </template>
    </div>
  </main>
</template>

<style scoped>
.stats-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 14px;
  margin-bottom: 20px;
}
.stats-panels {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 16px;
}
.stats-panel {
  background: #1a1a1a;
  border: 1px solid #202020;
  border-radius: 12px;
  padding: 18px 20px;
  min-width: 0;
}
.stats-panel.wide {
  grid-column: 1 / -1;
}
.toprated-panel {
  margin-bottom: 16px;
}
.stats-panel h2 {
  position: relative;
  margin: 0 0 18px;
  padding-left: 12px;
  font-size: 0.92rem;
  font-weight: 800;
}
.stats-panel h2::before {
  content: "";
  position: absolute;
  left: 0;
  top: 1px;
  bottom: 1px;
  width: 3px;
  border-radius: 999px;
  background: #d68a34;
}
.note {
  margin: 12px 0 0;
  font-size: 0.78rem;
  color: #9c9c9c;
}
.note.warn {
  margin: 0 0 16px;
  color: #c9a66b;
}
.note.lead {
  margin: 0 0 12px;
}
.dim {
  color: #666;
  font-size: 0.74rem;
}
.plain-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.plain-list li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  font-size: 0.82rem;
}
.plain-list button {
  background: none;
  border: none;
  padding: 0;
  color: #ddd;
  font: inherit;
  text-align: left;
  cursor: pointer;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.plain-list button:hover {
  color: #d68a34;
}
.progress-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 10px 18px;
}
.progress-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px;
  background: none;
  border: none;
  border-radius: 8px;
  text-align: left;
  color: inherit;
  font-family: inherit;
  cursor: pointer;
  min-width: 0;
}
.progress-row:hover {
  background: rgba(255, 255, 255, 0.04);
}
.progress-art {
  width: 34px;
  height: 50px;
  border-radius: 5px;
  flex-shrink: 0;
  background: #222 center / cover;
}
.progress-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.progress-title {
  font-size: 0.84rem;
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.progress-track {
  height: 6px;
  border-radius: 999px;
  background: #222;
  overflow: hidden;
}
.progress-fill {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #d68a34, #e8a552);
}
.progress-count {
  font-size: 0.78rem;
  color: #9c9c9c;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
@media (max-width: 720px) {
  .stats-panels {
    grid-template-columns: minmax(0, 1fr);
  }
  .stats-summary {
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  }
}
</style>
