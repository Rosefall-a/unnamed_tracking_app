<script setup lang="ts">
import { computed } from "vue";
import WidgetFrame from "../WidgetFrame.vue";
import { homeData, titlesOf } from "../../../home/data";
import { METRICS } from "../../../home/registry";
import type { WidgetProps } from "../../../home/registry";

const props = defineProps<WidgetProps>();

const SAMPLE: Record<string, string> = {
  game: "128",
  movie: "64",
  tv: "22",
  anime: "31",
  all: "245",
  favorites: "18",
  "in-progress": "7",
  average: "7.6",
};

const DAY = 86_400_000;

function value(metric: string): string {
  if (props.sample) return SAMPLE[metric] ?? "12";
  const titles = titlesOf(props.settings.kinds);
  const now = Date.now();
  const since = (days: number) =>
    String(
      titles.filter((t) => t.addedAt && now - t.addedAt <= days * DAY).length,
    );
  switch (metric) {
    case "game":
    case "movie":
    case "tv":
    case "anime":
      return String(titles.filter((t) => t.kind === metric).length);
    case "all":
      return String(titles.length);
    case "favorites":
      return String(titles.filter((t) => t.favorite).length);
    case "in-progress":
      return String(titles.filter((t) => t.group === "active").length);
    case "queue":
      return String(titles.filter((t) => t.group === "queue").length);
    case "wishlist":
      return String(titles.filter((t) => t.group === "wishlist").length);
    case "finished":
      return String(titles.filter((t) => t.group === "done").length);
    case "dropped":
      return String(titles.filter((t) => t.group === "dropped").length);
    case "unrated":
      return String(titles.filter((t) => t.rating === null).length);
    case "added-week":
      return since(7);
    case "added-month":
      return since(30);
    case "added-year":
      return since(365);
    case "average": {
      const rated = titles.filter((t) => t.rating !== null);
      if (!rated.length) return "–";
      return (
        rated.reduce((sum, t) => sum + (t.rating ?? 0), 0) / rated.length
      ).toFixed(1);
    }
    case "ach-unlocked":
      return String(
        Object.values(homeData.achSummary.value).reduce(
          (n, a) => n + a.unlocked,
          0,
        ),
      );
    case "ach-complete":
      return String(
        Object.values(homeData.achSummary.value).filter(
          (a) => a.total > 0 && a.unlocked >= a.total,
        ).length,
      );
    default:
      return "–";
  }
}

const LABEL = new Map(METRICS.map((m) => [m.value, m.label]));
// the kinds go to their library and carry their colour; the rest are plain
const LINK: Record<string, string> = {
  game: "/games",
  movie: "/movies",
  tv: "/tv",
  anime: "/anime",
  "ach-unlocked": "/games",
  "ach-complete": "/games",
};
const tiles = computed(() => {
  const chosen = Array.isArray(props.settings.metrics)
    ? (props.settings.metrics as string[])
    : [];
  return chosen
    .filter((m) => LABEL.has(m))
    .map((m) => ({
      key: m,
      label: LABEL.get(m)!,
      value: value(m),
      to: LINK[m] ?? null,
      kind: ["game", "movie", "tv", "anime"].includes(m) ? m : null,
    }));
});
const size = computed(() => String(props.settings.size || "normal"));
</script>

<template>
  <WidgetFrame
    title="Numbers"
    :sample="sample"
    :link="{ to: '/statistics', label: 'Statistics' }"
  >
    <div
      v-if="tiles.length"
      class="tiles"
      :class="[size, { pulse: loading && !sample }]"
    >
      <component
        :is="t.to && !sample ? 'router-link' : 'div'"
        v-for="t in tiles"
        :key="t.key"
        :to="t.to && !sample ? t.to : undefined"
        class="tile"
        :class="t.kind ? `kind-${t.kind}` : ''"
      >
        <strong>{{ t.value }}</strong>
        <span>{{ t.label }}</span>
      </component>
    </div>
    <div v-else class="none">
      Pick the numbers to show in this widget's settings.
    </div>
  </WidgetFrame>
</template>

<style scoped>
.tiles {
  --min: 116px;
  --pad: 10px 14px;
  --num: 1.45rem;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(var(--min), 1fr));
  gap: 10px;
  grid-auto-rows: min-content;
  align-content: start;
  height: 100%;
  overflow: auto;
  scrollbar-width: thin;
}
.tiles.compact {
  --min: 92px;
  --pad: 7px 10px;
  --num: 1.15rem;
  gap: 8px;
}
.tiles.large {
  --min: 150px;
  --pad: 14px 18px;
  --num: 2rem;
}
.tile {
  --kind: var(--ui-border-strong);
  position: relative;
  color: inherit;
  text-decoration: none;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: var(--pad);
  border: 1px solid var(--ui-border-soft);
  border-radius: var(--ui-radius-card);
  background: var(--ui-surface);
  box-shadow: inset 3px 0 0 var(--kind);
}
strong {
  font-size: var(--num);
  font-weight: 800;
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
}
span {
  color: var(--ui-dim);
  font-size: 0.78rem;
}
a.tile:hover {
  border-color: var(--ui-accent-line);
}
.kind-game {
  --kind: var(--ui-kind-game);
}
.kind-movie {
  --kind: var(--ui-kind-movie);
}
.kind-tv {
  --kind: var(--ui-kind-tv);
}
.kind-anime {
  --kind: var(--ui-kind-anime);
}
.pulse {
  opacity: 0.55;
}
.none {
  display: grid;
  place-content: center;
  height: 100%;
  color: var(--ui-dim);
  font-size: 0.85rem;
}
</style>
