<script setup lang="ts">
// The last 52 weeks as a grid, one square per day, shaded by how many
// episodes were checked off or achievements unlocked that day. Weeks are columns (Sunday at the
// top). Levels are quartiles of the busiest day, so a light user still
// sees a readable pattern. Months are named along the top. Hovering a square
// names the day and its count; clicking one opens a popup with the titles behind
// it, each a link.
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { fetchActivityDay, type ActivityDay } from "../../services/mediaStats";

const props = defineProps<{
  days: {
    date: string;
    count: number;
    episodes?: number;
    achievements?: number;
  }[];
}>();

const router = useRouter();

interface Cell {
  key: string;
  count: number;
  detail: string;
  level: number;
  inRange: boolean;
}

const MONTHS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

function describe(d: { episodes?: number; achievements?: number }): string {
  const parts: string[] = [];
  if (d.episodes)
    parts.push(`${d.episodes} episode${d.episodes === 1 ? "" : "s"}`);
  if (d.achievements)
    parts.push(
      `${d.achievements} achievement${d.achievements === 1 ? "" : "s"}`,
    );
  return parts.join(", ") || "nothing";
}

const weeks = computed<Cell[][]>(() => {
  const counts = new Map(props.days.map((d) => [d.date, d.count]));
  const details = new Map(props.days.map((d) => [d.date, describe(d)]));
  const max = Math.max(1, ...props.days.map((d) => d.count));
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const start = new Date(today);
  start.setDate(start.getDate() - 364);
  // begin on the Sunday on or before the start so columns are whole weeks
  start.setDate(start.getDate() - start.getDay());
  const out: Cell[][] = [];
  const cursor = new Date(start);
  while (cursor <= today) {
    const week: Cell[] = [];
    for (let i = 0; i < 7; i++) {
      const key = `${cursor.getFullYear()}-${String(cursor.getMonth() + 1).padStart(2, "0")}-${String(cursor.getDate()).padStart(2, "0")}`;
      const count = counts.get(key) ?? 0;
      const inRange = cursor <= today;
      week.push({
        key,
        count,
        detail: details.get(key) ?? "nothing",
        inRange,
        level: !count ? 0 : Math.min(4, Math.ceil((count / max) * 4)),
      });
      cursor.setDate(cursor.getDate() + 1);
    }
    out.push(week);
  }
  return out;
});

// A month is named above the first column it starts in. The first column is
// skipped when the next month begins right after it, so two names never overlap.
const monthLabels = computed<string[]>(() => {
  const labels = weeks.value.map(() => "");
  let previous = -1;
  weeks.value.forEach((week, index) => {
    const month = Number(week[0].key.slice(5, 7)) - 1;
    if (month !== previous) labels[index] = MONTHS[month];
    previous = month;
  });
  if (labels[0] && labels.slice(1, 3).some(Boolean)) labels[0] = "";
  return labels;
});

function longDate(key: string): string {
  return new Date(`${key}T00:00:00`).toLocaleDateString(undefined, {
    weekday: "short",
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

// ---- hover: the day and what happened on it ----
const tip = ref<{ text: string; x: number; y: number } | null>(null);

function showTip(cell: Cell, event: Event) {
  if (!cell.inRange) return;
  const box = (event.currentTarget as HTMLElement).getBoundingClientRect();
  tip.value = {
    text:
      cell.detail === "nothing"
        ? `No activity on ${longDate(cell.key)}`
        : `${cell.detail} on ${longDate(cell.key)}`,
    x: box.left + box.width / 2,
    y: box.top,
  };
}
function hideTip() {
  tip.value = null;
}

// ---- click: a popup listing that day ----
const selected = ref<Cell | null>(null);
const dayData = ref<ActivityDay | null>(null);
const dayError = ref<string | null>(null);
const dayLoading = ref(false);
let requested = 0;

async function select(cell: Cell) {
  // a quiet day has nothing to list
  if (!cell.inRange || !cell.count) return;
  hideTip();
  selected.value = cell;
  dayData.value = null;
  dayError.value = null;
  dayLoading.value = true;
  const request = ++requested;
  try {
    const data = await fetchActivityDay(cell.key);
    if (request === requested) dayData.value = data;
  } catch (err) {
    if (request === requested)
      dayError.value =
        err instanceof Error ? err.message : "Could not load that day";
  } finally {
    if (request === requested) dayLoading.value = false;
  }
}

function close() {
  requested++;
  selected.value = null;
  dayData.value = null;
}
function onKey(event: KeyboardEvent) {
  if (event.key === "Escape" && selected.value) close();
}
onMounted(() => window.addEventListener("keydown", onKey));
onBeforeUnmount(() => window.removeEventListener("keydown", onKey));

const BASE: Record<string, string> = {
  movie: "/movies",
  tv: "/tv",
  anime: "/anime",
  game: "/games",
};
function open(kind: string, id: string) {
  close();
  router.push(`${BASE[kind] ?? "/games"}/${id}`);
}
</script>

<template>
  <div class="heat-wrap">
    <div class="heat-scroll">
      <div class="heat">
        <div v-for="(week, wi) in weeks" :key="wi" class="heat-week">
          <span class="heat-month" aria-hidden="true">{{
            monthLabels[wi]
          }}</span>
          <button
            v-for="cell in week"
            :key="cell.key"
            type="button"
            class="heat-cell"
            :class="[`l${cell.level}`, { off: !cell.inRange }]"
            :disabled="!cell.inRange"
            :aria-label="`${longDate(cell.key)}: ${cell.detail}`"
            @mouseenter="showTip(cell, $event)"
            @focus="showTip(cell, $event)"
            @mouseleave="hideTip"
            @blur="hideTip"
            @click="select(cell)"
          ></button>
        </div>
      </div>
    </div>

    <Teleport to="body">
      <div
        v-if="tip"
        class="heat-tip"
        role="tooltip"
        :style="{ left: `${tip.x}px`, top: `${tip.y}px` }"
      >
        {{ tip.text }}
      </div>

      <div v-if="selected" class="day-backdrop" @click.self="close">
        <div
          class="day-dialog"
          role="dialog"
          aria-modal="true"
          :aria-label="longDate(selected.key)"
        >
          <div class="day-head">
            <div>
              <strong>{{ longDate(selected.key) }}</strong>
              <div class="dim">{{ selected.detail }}</div>
            </div>
            <button
              type="button"
              class="day-close"
              aria-label="Close"
              @click="close"
            >
              ✕
            </button>
          </div>
          <p v-if="dayLoading" class="dim">Loading…</p>
          <p v-else-if="dayError" class="dim">{{ dayError }}</p>
          <template v-else-if="dayData">
            <ul v-if="dayData.episodes.length" class="day-list">
              <li v-for="e in dayData.episodes" :key="`${e.kind}-${e.id}`">
                <button type="button" @click="open(e.kind, e.id)">
                  {{ e.title }}
                </button>
                <span class="dim"
                  >{{ e.count }} episode{{ e.count === 1 ? "" : "s"
                  }}{{ e.detail ? `, ${e.detail}` : "" }}</span
                >
              </li>
            </ul>
            <ul v-if="dayData.games.length" class="day-list">
              <li v-for="g in dayData.games" :key="g.id">
                <button type="button" @click="open('game', g.id)">
                  {{ g.title }}
                </button>
                <span class="dim"
                  >{{ g.achievements.length }} achievement{{
                    g.achievements.length === 1 ? "" : "s"
                  }}: {{ g.achievements.join(", ") }}</span
                >
              </li>
            </ul>
            <p
              v-if="!dayData.episodes.length && !dayData.games.length"
              class="dim"
            >
              The details for this day are no longer available.
            </p>
          </template>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
/* fixed colours: the tooltip and popup are attached to the page body, where the
   colour variables a page defines for itself do not exist */
.heat-scroll {
  overflow-x: auto;
}
.heat {
  display: flex;
  gap: 3px;
  width: max-content;
}
.heat-week {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.heat-month {
  height: 14px;
  font-size: 0.68rem;
  line-height: 14px;
  color: #a8a8a8;
  /* the name sits over its column and may run into the empty ones after it */
  white-space: nowrap;
  overflow: visible;
  width: 12px;
}
.heat-cell {
  box-sizing: border-box;
  width: 12px;
  height: 12px;
  padding: 0;
  border: 0;
  border-radius: 3px;
  background: #1c1c1c;
  cursor: pointer;
}
.heat-cell:disabled {
  cursor: default;
}
.heat-cell:not(:disabled):hover {
  outline: 1px solid #a8a8a8;
}
.heat-cell:focus-visible {
  outline: 2px solid #d68a34;
  outline-offset: 1px;
}
.heat-cell.off {
  background: transparent;
}
.heat-cell.l1 {
  background: rgba(214, 138, 52, 0.28);
}
.heat-cell.l2 {
  background: rgba(214, 138, 52, 0.5);
}
.heat-cell.l3 {
  background: rgba(214, 138, 52, 0.75);
}
.heat-cell.l4 {
  background: #d68a34;
}
.heat-tip {
  position: fixed;
  z-index: 1000;
  transform: translate(-50%, calc(-100% - 8px));
  padding: 6px 10px;
  border-radius: 6px;
  background: #222222;
  border: 1px solid #2b2b2b;
  color: #f2f2f2;
  font-size: 0.75rem;
  font-weight: 600;
  white-space: nowrap;
  pointer-events: none;
}
.day-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1001;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background: rgba(0, 0, 0, 0.7);
}
.day-dialog {
  width: min(520px, 100%);
  max-height: min(70vh, 640px);
  overflow-y: auto;
  padding: 18px 20px;
  border-radius: 12px;
  background: #1a1a1a;
  border: 1px solid #2b2b2b;
  color: #f2f2f2;
  box-shadow: 0 18px 50px rgba(0, 0, 0, 0.5);
}
.day-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}
.day-close {
  background: none;
  border: 0;
  color: #a8a8a8;
  cursor: pointer;
  font-size: 1rem;
}
.day-list {
  list-style: none;
  margin: 0 0 10px;
  padding: 0;
  display: grid;
  gap: 8px;
}
.day-list li {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.day-list button {
  align-self: flex-start;
  background: none;
  border: 0;
  padding: 0;
  color: #d68a34;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
  text-align: left;
}
.day-list button:hover {
  text-decoration: underline;
}
.dim {
  color: #a8a8a8;
  font-size: 0.82rem;
}
</style>
