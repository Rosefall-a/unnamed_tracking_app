<script setup lang="ts">
// How long your backlog is, in hours, from the time to beat on the titles that
// have one. It says how many titles that covers and how many have no figure, so
// the total is never presented as more than it is, and lists the quickest ones to
// finish.
import { computed } from "vue";
import WidgetFrame from "../WidgetFrame.vue";
import { titlesOf } from "../../../home/data";
import type { HomeTitle } from "../../../home/data";
import { sampleTitles } from "../../../home/samples";
import type { WidgetProps } from "../../../home/registry";

const props = defineProps<WidgetProps>();

const POOL: Record<string, (t: HomeTitle) => boolean> = {
  backlog: (t) => t.group === "queue",
  waiting: (t) => t.group === "queue" || t.group === "wishlist",
  unfinished: (t) => t.group !== "done" && t.group !== "dropped",
};

const list = computed(() =>
  props.sample
    ? sampleTitles(8, ["game"]).map((t, i) => ({ ...t, hours: 4 + i * 5 }))
    : titlesOf(props.settings.kinds).filter(
        POOL[String(props.settings.pool)] ?? POOL.backlog,
      ),
);
const timed = computed(() =>
  list.value.filter((t) => t.hours !== null && t.hours > 0),
);
const total = computed(() =>
  Math.round(timed.value.reduce((n, t) => n + (t.hours ?? 0), 0)),
);
const quickest = computed(() =>
  [...timed.value]
    .sort((a, b) => (a.hours ?? 0) - (b.hours ?? 0))
    .slice(0, Number(props.settings.count) || 4),
);
const missing = computed(() => list.value.length - timed.value.length);
const days = computed(() =>
  (total.value / 24).toFixed(total.value >= 240 ? 0 : 1),
);
</script>

<template>
  <WidgetFrame title="Backlog length" surface :sample="sample">
    <div v-if="list.length" class="wrap">
      <div class="big">
        <strong>{{ total.toLocaleString() }}</strong>
        <span>hours to clear</span>
        <small>about {{ days }} days of non-stop play</small>
      </div>
      <p class="cover">
        From {{ timed.length }} of {{ list.length }} titles<template
          v-if="missing"
        >
          ({{ missing }} with no time to beat)</template
        >.
      </p>
      <ul v-if="quickest.length" class="quick">
        <li v-for="t in quickest" :key="t.key">
          <component
            :is="sample ? 'span' : 'router-link'"
            :to="sample ? undefined : t.to"
            class="row"
          >
            <span class="name">{{ t.title }}</span>
            <span class="h">{{ Math.round((t.hours ?? 0) * 10) / 10 }} h</span>
          </component>
        </li>
      </ul>
    </div>
    <div v-else class="none">
      {{
        loading
          ? "Loading"
          : "Nothing waiting. Change what counts with the controls above."
      }}
    </div>
  </WidgetFrame>
</template>

<style scoped>
.wrap {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.big {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 4px 8px;
}
.big strong {
  font-size: 2.2rem;
  font-weight: 800;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}
.big span {
  color: var(--ui-text);
  font-size: 0.9rem;
  font-weight: 600;
}
.big small {
  flex-basis: 100%;
  color: var(--ui-faint);
  font-size: 0.74rem;
}
.cover {
  margin: 0;
  color: var(--ui-dim);
  font-size: 0.78rem;
}
.quick {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin: 4px 0 0;
  padding: 0;
  list-style: none;
}
.row {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 4px 6px;
  border-radius: var(--ui-radius-control);
  color: var(--ui-text);
  font-size: 0.82rem;
  text-decoration: none;
}
a.row:hover {
  background: var(--ui-surface-2);
}
.name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.h {
  flex: none;
  color: var(--ui-accent);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.none {
  display: grid;
  place-content: center;
  height: 100%;
  color: var(--ui-dim);
  font-size: 0.84rem;
  text-align: center;
}
</style>
