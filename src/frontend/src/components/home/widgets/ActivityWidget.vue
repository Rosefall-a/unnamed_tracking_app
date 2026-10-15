<script setup lang="ts">
// Two views of when things happen in your library. "activity" is a grid of days,
// a column for each week, darker where more titles were added (or games were
// played); "growth" is a bar for each month of how many titles you added. Counts
// are real days and titles; nothing is estimated.
import { computed, onBeforeUnmount, ref, watch } from "vue";
import WidgetFrame from "../WidgetFrame.vue";
import { homeData, titlesOf } from "../../../home/data";
import type { WidgetProps } from "../../../home/registry";

const props = defineProps<WidgetProps>();

const mode = computed(() => String(props.settings.mode));
const DAY = 86_400_000;

function dayKey(t: number): string {
  const d = new Date(t);
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
}

// the days that count: when a title was added, and for games when it was last played
const moments = computed<number[]>(() => {
  if (props.sample) {
    const out: number[] = [];
    for (let i = 0; i < 400; i++)
      if ((i * 7) % 5 < 2) out.push(Date.now() - i * DAY * 0.9);
    return out;
  }
  const list: number[] = [];
  const what = String(props.settings.what);
  for (const t of titlesOf(props.settings.kinds)) {
    if (what !== "played" && t.addedAt) list.push(t.addedAt);
    if (what !== "added" && t.kind === "game" && t.touchedAt)
      list.push(t.touchedAt);
  }
  return list;
});

// ---- the grid of days ----
const gridEl = ref<HTMLElement | null>(null);
const weeks = ref(26);
function measure() {
  const el = gridEl.value;
  if (!el) return;
  weeks.value = Math.max(
    8,
    Math.min(53, Math.floor((el.clientWidth + 3) / 15)),
  );
}
let observer: ResizeObserver | null = null;
watch(gridEl, (el) => {
  observer?.disconnect();
  observer = null;
  if (!el) return;
  observer = new ResizeObserver(measure);
  observer.observe(el);
  measure();
});
onBeforeUnmount(() => observer?.disconnect());

const days = computed(() => {
  const counts = new Map<string, number>();
  for (const m of moments.value)
    counts.set(dayKey(m), (counts.get(dayKey(m)) ?? 0) + 1);
  const today = new Date();
  const end = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  // columns run Sunday to Saturday, the last column ending today's week
  const start = new Date(
    end.getTime() - ((weeks.value - 1) * 7 + end.getDay()) * DAY,
  );
  const out: { key: string; n: number; date: Date; future: boolean }[] = [];
  for (let i = 0; i < weeks.value * 7; i++) {
    const date = new Date(start.getTime() + i * DAY);
    out.push({
      key: dayKey(date.getTime()),
      n: counts.get(dayKey(date.getTime())) ?? 0,
      date,
      future: date.getTime() > end.getTime(),
    });
  }
  return out;
});
const peak = computed(() => Math.max(1, ...days.value.map((d) => d.n)));
const level = (n: number) =>
  n === 0 ? 0 : Math.min(4, Math.ceil((n / peak.value) * 4));
const busyDays = computed(() => days.value.filter((d) => d.n > 0).length);
const tip = (d: { n: number; date: Date }) =>
  `${d.n} ${d.n === 1 ? "title" : "titles"} on ${d.date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}`;

// ---- the bars by month ----
const months = computed(() => {
  const now = new Date();
  const out: { label: string; n: number }[] = [];
  for (let i = 11; i >= 0; i--) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    out.push({
      label: d.toLocaleDateString(undefined, { month: "short" }),
      n: 0,
    });
  }
  const first = new Date(now.getFullYear(), now.getMonth() - 11, 1).getTime();
  for (const m of moments.value) {
    if (m < first) continue;
    const d = new Date(m);
    const idx =
      (d.getFullYear() - new Date(first).getFullYear()) * 12 +
      d.getMonth() -
      new Date(first).getMonth();
    if (idx >= 0 && idx < 12) out[idx].n += 1;
  }
  return out;
});
const monthTop = computed(() => Math.max(1, ...months.value.map((m) => m.n)));
const monthTotal = computed(() => months.value.reduce((n, m) => n + m.n, 0));

const heading = computed(() =>
  mode.value === "growth" ? "Added by month" : "Activity",
);
const known = computed(() => !!homeData.games.value || props.sample);
</script>

<template>
  <WidgetFrame :title="heading" surface :sample="sample">
    <template v-if="known">
      <div v-if="mode !== 'growth'" class="wrap">
        <div ref="gridEl" class="days" :style="{ '--weeks': weeks }">
          <span
            v-for="d in days"
            :key="d.key"
            class="day"
            :class="[`l${level(d.n)}`, { future: d.future }]"
            :title="d.future ? '' : tip(d)"
          ></span>
        </div>
        <p class="legend">
          {{ busyDays }} active {{ busyDays === 1 ? "day" : "days" }} in the
          last {{ weeks }} weeks
          <span class="scale"
            >Less <i class="day l0"></i><i class="day l1"></i
            ><i class="day l2"></i><i class="day l3"></i
            ><i class="day l4"></i> More</span
          >
        </p>
      </div>
      <div v-else class="wrap">
        <p class="legend">{{ monthTotal }} added in the last year</p>
        <div class="months">
          <div v-for="(m, i) in months" :key="i" class="m">
            <span class="n">{{ m.n || "" }}</span>
            <span class="bar"
              ><span :style="{ height: `${(m.n / monthTop) * 100}%` }"></span
            ></span>
            <span class="x">{{ m.label }}</span>
          </div>
        </div>
      </div>
    </template>
    <div v-else class="none">Loading</div>
  </WidgetFrame>
</template>

<style scoped>
.wrap {
  display: flex;
  flex-direction: column;
  gap: 10px;
  height: 100%;
}
.days {
  display: grid;
  grid-auto-flow: column;
  grid-template-rows: repeat(7, 12px);
  grid-auto-columns: 12px;
  gap: 3px;
  align-content: start;
  overflow: hidden;
}
.day {
  display: block;
  width: 12px;
  height: 12px;
  border-radius: 3px;
  background: var(--ui-surface-3);
}
.day.l1 {
  background: color-mix(in srgb, var(--ui-accent) 28%, var(--ui-surface-3));
}
.day.l2 {
  background: color-mix(in srgb, var(--ui-accent) 52%, var(--ui-surface-3));
}
.day.l3 {
  background: color-mix(in srgb, var(--ui-accent) 76%, var(--ui-surface-3));
}
.day.l4 {
  background: var(--ui-accent);
}
.day.future {
  visibility: hidden;
}
.legend {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin: 0;
  color: var(--ui-dim);
  font-size: 0.78rem;
}
.scale {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  color: var(--ui-faint);
  font-size: 0.7rem;
}
.scale .day {
  width: 10px;
  height: 10px;
}
.months {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 6px;
}
.m {
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
  font-size: 0.68rem;
}
.none {
  display: grid;
  place-content: center;
  height: 100%;
  color: var(--ui-dim);
  font-size: 0.84rem;
}
</style>
