<script setup lang="ts">
// The last 52 weeks as a grid, one square per day, shaded by how many
// episodes were checked off that day. Weeks are columns (Sunday at the
// top). Levels are quartiles of the busiest day, so a light user still
// sees a readable pattern; the exact count is in each square's tooltip.
import { computed } from "vue";

const props = defineProps<{
  days: { date: string; count: number }[];
}>();

interface Cell {
  key: string;
  count: number;
  level: number;
  inRange: boolean;
}

const weeks = computed<Cell[][]>(() => {
  const counts = new Map(props.days.map((d) => [d.date, d.count]));
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
        inRange,
        level: !count ? 0 : Math.min(4, Math.ceil((count / max) * 4)),
      });
      cursor.setDate(cursor.getDate() + 1);
    }
    out.push(week);
  }
  return out;
});
</script>

<template>
  <div class="heat-scroll">
    <div class="heat">
      <div v-for="(week, wi) in weeks" :key="wi" class="heat-week">
        <span
          v-for="cell in week"
          :key="cell.key"
          class="heat-cell"
          :class="[`l${cell.level}`, { off: !cell.inRange }]"
          :title="cell.inRange ? `${cell.key}: ${cell.count} episode${cell.count === 1 ? '' : 's'}` : ''"
        ></span>
      </div>
    </div>
  </div>
</template>

<style scoped>
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
.heat-cell {
  width: 12px;
  height: 12px;
  border-radius: 3px;
  background: #1c1c1c;
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
</style>
