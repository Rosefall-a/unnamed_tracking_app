<script setup lang="ts">
// How complete your library's details are: how many titles have a rating, a
// release date, genres or tags, and (for games) a time to beat. Real counts, so
// you can see what is worth filling in.
import { computed } from "vue";
import WidgetFrame from "../WidgetFrame.vue";
import { titlesOf } from "../../../home/data";
import type { HomeTitle } from "../../../home/data";
import { narrow } from "../../../home/select";
import type { WidgetProps } from "../../../home/registry";

const props = defineProps<WidgetProps>();

// every check there is; the widget's settings choose which ones to show
const CHECKS: Record<
  string,
  { label: string; test: (t: HomeTitle) => boolean; gamesOnly?: boolean }
> = {
  rated: { label: "Rated", test: (t) => t.rating !== null },
  release: { label: "Has a release date", test: (t) => t.release > 0 },
  genres: { label: "Has genres or tags", test: (t) => t.genres.length > 0 },
  time: {
    label: "Has a time to beat",
    test: (t) => t.hours !== null && t.hours > 0,
    gamesOnly: true,
  },
  maker: {
    label: "Has a developer or studio",
    test: (t) => t.makers.length > 0,
  },
  art: { label: "Has a cover", test: (t) => !!t.art },
  platform: {
    label: "Has a platform",
    test: (t) => !!t.platform,
    gamesOnly: true,
  },
};

const STATUS: Record<string, (t: HomeTitle) => boolean> = {
  any: () => true,
  active: (t) => t.group === "active",
  queue: (t) => t.group === "queue",
  wishlist: (t) => t.group === "wishlist",
  done: (t) => t.group === "done",
};

const rows = computed(() => {
  if (props.sample)
    return [
      { label: "Rated", have: 86, total: 128 },
      { label: "Has a release date", have: 120, total: 128 },
      { label: "Has genres or tags", have: 101, total: 128 },
      { label: "Has a time to beat", have: 64, total: 90 },
    ];
  const list = narrow(
    titlesOf(props.settings.kinds).filter(
      STATUS[String(props.settings.status)] ?? STATUS.any,
    ),
    props.settings,
  );
  const chosen = Array.isArray(props.settings.checks)
    ? (props.settings.checks as string[])
    : [];
  return chosen
    .filter((key) => CHECKS[key])
    .map((key) => {
      const c = CHECKS[key];
      const pool = c.gamesOnly ? list.filter((t) => t.kind === "game") : list;
      return {
        label:
          c.gamesOnly && list.some((t) => t.kind !== "game")
            ? `${c.label} (games)`
            : c.label,
        have: pool.filter(c.test).length,
        total: pool.length,
      };
    })
    .filter((r) => r.total > 0);
});
const total = computed(() => rows.value.reduce((n, r) => n + r.total, 0));
const have = computed(() => rows.value.reduce((n, r) => n + r.have, 0));
const overall = computed(() =>
  total.value ? Math.round((have.value / total.value) * 100) : 0,
);
</script>

<template>
  <WidgetFrame title="Library health" surface :sample="sample">
    <div v-if="rows.length" class="wrap">
      <div class="head">
        <strong>{{ overall }}%</strong>
        <span>of details filled in</span>
      </div>
      <ul class="rows">
        <li v-for="r in rows" :key="r.label">
          <span class="line">
            <span>{{ r.label }}</span>
            <em>{{ r.have }} of {{ r.total }}</em>
          </span>
          <span class="bar"
            ><span
              :style="{ width: `${r.total ? (r.have / r.total) * 100 : 0}%` }"
            ></span
          ></span>
        </li>
      </ul>
    </div>
    <div v-else class="none">
      {{
        loading
          ? "Loading"
          : "Nothing matches. Change what it looks at, or the checks, in this widget's settings."
      }}
    </div>
  </WidgetFrame>
</template>

<style scoped>
.wrap {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.head {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.head strong {
  font-size: 1.8rem;
  font-weight: 800;
  line-height: 1;
}
.head span {
  color: var(--ui-dim);
  font-size: 0.82rem;
}
.rows {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.line {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
  font-size: 0.82rem;
}
em {
  color: var(--ui-dim);
  font-size: 0.76rem;
  font-style: normal;
  font-variant-numeric: tabular-nums;
}
.bar {
  display: block;
  height: 5px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--ui-surface-3);
}
.bar span {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: var(--ui-accent);
}
.none {
  display: grid;
  place-content: center;
  height: 100%;
  color: var(--ui-dim);
  font-size: 0.84rem;
}
</style>
