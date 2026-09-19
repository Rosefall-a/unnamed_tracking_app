<script setup lang="ts">
// A horizontal bar list: one row per name, bar length proportional to the
// largest value, exact value at the right. Rows are plain divs so long
// names wrap to an ellipsis instead of pushing the layout.
import { computed } from "vue";

const props = defineProps<{
  rows: { name: string; value: number; label?: string; hint?: string }[];
  empty?: string;
}>();

const max = computed(() => Math.max(1, ...props.rows.map((r) => r.value)));
</script>

<template>
  <div v-if="rows.length" class="bar-list">
    <div v-for="r in rows" :key="r.name" class="bar-row" :title="r.hint">
      <span class="bar-name">{{ r.name }}</span>
      <span class="bar-track"
        ><span
          class="bar-fill"
          :style="{ width: (r.value / max) * 100 + '%' }"
        ></span
      ></span>
      <span class="bar-value">{{ r.label ?? r.value }}</span>
    </div>
  </div>
  <p v-else class="bar-empty">{{ empty ?? "No data yet." }}</p>
</template>

<style scoped>
.bar-list {
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.bar-row {
  display: grid;
  grid-template-columns: minmax(80px, 34%) minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  font-size: 0.8rem;
}
.bar-name {
  color: #ddd;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.bar-track {
  height: 9px;
  border-radius: 999px;
  background: #222;
  overflow: hidden;
}
.bar-fill {
  display: block;
  height: 100%;
  border-radius: 999px;
  min-width: 3px;
  background: linear-gradient(90deg, #d68a34, #e8a552);
}
.bar-value {
  color: #9c9c9c;
  font-variant-numeric: tabular-nums;
  min-width: 2ch;
  text-align: right;
}
.bar-empty {
  margin: 0;
  color: #666;
  font-size: 0.82rem;
}
</style>
