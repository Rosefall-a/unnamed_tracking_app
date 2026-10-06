<script setup lang="ts">
// Vertical columns on one shared scale. Every column has its value above
// it and its label below, and the tallest column sets the height of all
// of them, so nothing is exaggerated. Scrolls sideways when there are more
// columns than fit (a long run of release years, say).
import { computed } from "vue";

const props = defineProps<{
  columns: { label: string; value: number }[];
  empty?: string;
}>();

const max = computed(() => Math.max(1, ...props.columns.map((c) => c.value)));
</script>

<template>
  <div v-if="columns.length" class="col-scroll">
    <div class="col-chart" :style="{ minWidth: columns.length * 34 + 'px' }">
      <div v-for="c in columns" :key="c.label" class="col">
        <span class="col-value">{{ c.value || "" }}</span>
        <span class="col-bar-wrap">
          <span
            class="col-bar"
            :style="{ height: (c.value / max) * 100 + '%' }"
          ></span>
        </span>
        <span class="col-label">{{ c.label }}</span>
      </div>
    </div>
  </div>
  <p v-else class="col-empty">{{ empty ?? "No data yet." }}</p>
</template>

<style scoped>
.col-scroll {
  overflow-x: auto;
}
.col-chart {
  display: flex;
  align-items: stretch;
  gap: 6px;
  height: 150px;
}
.col {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}
.col-value {
  height: 14px;
  font-size: 0.68rem;
  color: #9c9c9c;
  font-variant-numeric: tabular-nums;
}
.col-bar-wrap {
  flex: 1;
  width: 100%;
  display: flex;
  align-items: flex-end;
}
.col-bar {
  display: block;
  width: 100%;
  min-height: 2px;
  border-radius: 4px 4px 0 0;
  background: linear-gradient(180deg, #d68a34, #e8a552);
}
.col-label {
  font-size: 0.66rem;
  color: #666;
  white-space: nowrap;
}
.col-empty {
  margin: 0;
  color: #666;
  font-size: 0.82rem;
}
</style>
