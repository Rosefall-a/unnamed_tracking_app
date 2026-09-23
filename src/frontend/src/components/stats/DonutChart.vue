<script setup lang="ts">
// A donut ("pie") chart with a legend. Slices share one circle whose
// circumference is the total, so every slice is drawn to scale, and the
// legend states each slice's exact count and share. Slices with a zero
// value are left out of the ring but kept out of the legend too, so the
// legend never lists something the ring does not show.
import { computed } from "vue";

const props = defineProps<{
  slices: { name: string; value: number; color?: string }[];
  centerLabel?: string;
  empty?: string;
}>();

const PALETTE = [
  "#d68a34",
  "#6fbf73",
  "#7ba7d9",
  "#d96f6f",
  "#9d8cd9",
  "#e8a552",
  "#5cc2b8",
  "#c78fbf",
  "#b5b35c",
  "#8a8a8a",
];
const RADIUS = 46;
const CIRC = 2 * Math.PI * RADIUS;

const shown = computed(() => props.slices.filter((s) => s.value > 0));
const total = computed(() => shown.value.reduce((sum, s) => sum + s.value, 0));
// thousands separators, and a smaller size once the number would touch the ring
const totalText = computed(() => total.value.toLocaleString());
const totalSize = computed(() =>
  totalText.value.length > 5 ? "14px" : "20px",
);

const arcs = computed(() => {
  let offset = 0;
  return shown.value.map((s, i) => {
    const length = (s.value / total.value) * CIRC;
    const arc = {
      name: s.name,
      color: s.color ?? PALETTE[i % PALETTE.length],
      dash: `${length} ${CIRC - length}`,
      offset: -offset,
      value: s.value,
      pct: Math.round((s.value / total.value) * 100),
    };
    offset += length;
    return arc;
  });
});
</script>

<template>
  <div v-if="arcs.length" class="donut">
    <svg
      viewBox="0 0 120 120"
      class="donut-svg"
      role="img"
      :aria-label="`${total} in total`"
    >
      <g transform="rotate(-90 60 60)">
        <circle
          cx="60"
          cy="60"
          :r="RADIUS"
          fill="none"
          stroke="#222"
          stroke-width="16"
        />
        <circle
          v-for="a in arcs"
          :key="a.name"
          cx="60"
          cy="60"
          :r="RADIUS"
          fill="none"
          :stroke="a.color"
          stroke-width="16"
          :stroke-dasharray="a.dash"
          :stroke-dashoffset="a.offset"
        >
          <title>{{ a.name }}: {{ a.value }} ({{ a.pct }}%)</title>
        </circle>
      </g>
      <text
        x="60"
        y="58"
        text-anchor="middle"
        class="donut-total"
        :style="{ fontSize: totalSize }"
      >
        {{ totalText }}
      </text>
      <text x="60" y="73" text-anchor="middle" class="donut-caption">
        {{ centerLabel ?? "total" }}
      </text>
    </svg>
    <ul class="donut-legend">
      <li v-for="a in arcs" :key="a.name">
        <span class="dot" :style="{ background: a.color }"></span>
        <span class="name">{{ a.name }}</span>
        <span class="num">{{ a.value.toLocaleString() }}</span>
        <span class="pct">{{ a.pct }}%</span>
      </li>
    </ul>
  </div>
  <p v-else class="donut-empty">{{ empty ?? "No data yet." }}</p>
</template>

<style scoped>
.donut {
  display: flex;
  align-items: center;
  gap: 18px;
  flex-wrap: wrap;
}
.donut-svg {
  width: 150px;
  height: 150px;
  flex-shrink: 0;
}
.donut-total {
  fill: #f2f2f2;
  font-size: 20px;
  font-weight: 800;
}
.donut-caption {
  fill: #666;
  font-size: 8px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.donut-legend {
  list-style: none;
  margin: 0;
  padding: 0;
  flex: 1;
  min-width: 140px;
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.donut-legend li {
  display: grid;
  grid-template-columns: 10px minmax(0, 1fr) auto 38px;
  align-items: center;
  gap: 8px;
  font-size: 0.78rem;
}
.dot {
  width: 10px;
  height: 10px;
  border-radius: 3px;
}
.name {
  color: #ddd;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.num {
  color: #ddd;
  font-variant-numeric: tabular-nums;
}
.pct {
  color: #9c9c9c;
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.donut-empty {
  margin: 0;
  color: #666;
  font-size: 0.82rem;
}
</style>
