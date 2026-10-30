<script setup lang="ts">
// How you score things: a bar for each rating from 1 to 10 and your average. Only
// titles you have rated count.
import { computed } from "vue";
import WidgetFrame from "../WidgetFrame.vue";
import { titlesOf } from "../../../home/data";
import type { WidgetProps } from "../../../home/registry";

const props = defineProps<WidgetProps>();

const SAMPLE = [0, 1, 2, 4, 6, 12, 22, 30, 18, 7];

const buckets = computed(() => {
  const counts = Array<number>(10).fill(0);
  if (props.sample) SAMPLE.forEach((n, i) => (counts[i] = n));
  else
    for (const t of titlesOf(props.settings.kinds))
      if (t.rating !== null && t.rating > 0)
        counts[Math.min(9, Math.max(0, Math.ceil(t.rating) - 1))] += 1;
  return counts;
});
const total = computed(() => buckets.value.reduce((a, b) => a + b, 0));
const top = computed(() => Math.max(1, ...buckets.value));
const average = computed(() => {
  if (props.sample) return "7.4";
  const rated = titlesOf(props.settings.kinds).filter(
    (t) => t.rating !== null && t.rating > 0,
  );
  if (!rated.length) return "–";
  return (
    rated.reduce((n, t) => n + (t.rating ?? 0), 0) / rated.length
  ).toFixed(1);
});
</script>

<template>
  <WidgetFrame title="Your ratings" surface :sample="sample">
    <div v-if="total" class="wrap">
      <div class="head">
        <strong>{{ average }}</strong>
        <span>average of {{ total }} rated</span>
      </div>
      <div
        class="chart"
        role="img"
        :aria-label="`Ratings from 1 to 10, ${total} rated`"
      >
        <div v-for="(n, i) in buckets" :key="i" class="col">
          <span class="n">{{ n || "" }}</span>
          <span class="bar"
            ><span :style="{ height: `${(n / top) * 100}%` }"></span
          ></span>
          <span class="x">{{ i + 1 }}</span>
        </div>
      </div>
    </div>
    <div v-else class="none">
      <strong>{{ loading ? "Loading" : "Nothing rated yet" }}</strong>
      <span v-if="!loading">Rate a few titles and the spread shows here.</span>
    </div>
  </WidgetFrame>
</template>

<style scoped>
.wrap {
  display: flex;
  flex-direction: column;
  gap: 10px;
  height: 100%;
}
.head {
  flex: none;
  display: flex;
  align-items: baseline;
  gap: 10px;
}
.head strong {
  font-size: 1.8rem;
  font-weight: 800;
  line-height: 1;
}
.head span {
  color: var(--ui-dim);
  font-size: 0.8rem;
}
.chart {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: repeat(10, 1fr);
  gap: 6px;
}
.col {
  display: grid;
  grid-template-rows: auto 1fr auto;
  justify-items: center;
  gap: 4px;
  min-height: 0;
}
.bar {
  width: 100%;
  display: flex;
  align-items: flex-end;
  min-height: 0;
  border-radius: 4px;
  background: var(--ui-surface-3);
  overflow: hidden;
}
.bar span {
  width: 100%;
  border-radius: 4px 4px 0 0;
  background: var(--ui-accent);
}
.n {
  min-height: 1em;
  color: var(--ui-dim);
  font-size: 0.68rem;
  font-variant-numeric: tabular-nums;
}
.x {
  color: var(--ui-faint);
  font-size: 0.7rem;
}
.none {
  display: grid;
  place-content: center;
  gap: 4px;
  height: 100%;
  text-align: center;
  color: var(--ui-dim);
  font-size: 0.84rem;
}
.none strong {
  color: var(--ui-text);
}
</style>
