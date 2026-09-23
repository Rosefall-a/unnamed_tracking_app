<script setup lang="ts">
// One headline number, in the same card the library pages' Stats tab uses:
// gradient surface, accent value, small icon in the corner, uppercase
// label. `sub` is the exact detail line (what the number is made of).
import { computed } from "vue";

const props = defineProps<{
  value: string | number;
  label: string;
  sub?: string;
  icon?:
    | "grid"
    | "check"
    | "heart"
    | "clock"
    | "play"
    | "star"
    | "flame"
    | "trophy"
    | "calendar";
}>();

const PATHS: Record<string, string> = {
  grid: "M4.5 3h4a1.5 1.5 0 0 1 1.5 1.5v4A1.5 1.5 0 0 1 8.5 10h-4A1.5 1.5 0 0 1 3 8.5v-4A1.5 1.5 0 0 1 4.5 3zM15.5 3h4A1.5 1.5 0 0 1 21 4.5v4a1.5 1.5 0 0 1-1.5 1.5h-4A1.5 1.5 0 0 1 14 8.5v-4A1.5 1.5 0 0 1 15.5 3zM4.5 14h4a1.5 1.5 0 0 1 1.5 1.5v4A1.5 1.5 0 0 1 8.5 21h-4A1.5 1.5 0 0 1 3 19.5v-4A1.5 1.5 0 0 1 4.5 14zM15.5 14h4a1.5 1.5 0 0 1 1.5 1.5v4a1.5 1.5 0 0 1-1.5 1.5h-4a1.5 1.5 0 0 1-1.5-1.5v-4a1.5 1.5 0 0 1 1.5-1.5z",
  check: "M20 6 9 17l-5-5",
  heart:
    "M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8l1.1 1.1L12 21.2l7.8-7.7 1.1-1.1a5.5 5.5 0 0 0 0-7.8z",
  clock: "M12 6v6l4 2M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z",
  play: "M6 4l14 8-14 8z",
  star: "M12 2l3.1 6.3 6.9 1-5 4.9 1.2 6.8L12 17.8 5.8 21l1.2-6.8-5-4.9 6.9-1z",
  flame: "M12 2c1 4-3 5-3 9a5 5 0 0 0 10 0c0-3-2-4-2-6-1 1-2 1-2-1z",
  trophy:
    "M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0zM17 5h3v2a3 3 0 0 1-3 3M7 5H4v2a3 3 0 0 0 3 3",
  calendar:
    "M5 4h14a2 2 0 0 1 2 2v13a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2zM3 10h18M8 2v4M16 2v4",
};
const path = computed(() => PATHS[props.icon ?? "grid"]);
</script>

<template>
  <div class="stat-card">
    <svg
      class="stat-icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true"
    >
      <path :d="path" />
    </svg>
    <div class="stat-value">{{ value }}</div>
    <div class="stat-label">{{ label }}</div>
    <div v-if="sub" class="stat-sub">{{ sub }}</div>
  </div>
</template>

<style scoped>
.stat-card {
  position: relative;
  overflow: hidden;
  background: linear-gradient(160deg, #1a1a1a 0%, #222222 130%);
  border: 1px solid #202020;
  border-radius: 12px;
  padding: 18px 20px;
  transition: border-color 0.15s ease;
  min-width: 0;
}
.stat-card:hover {
  border-color: rgba(214, 138, 52, 0.4);
}
.stat-icon {
  position: absolute;
  top: 14px;
  right: 14px;
  width: 20px;
  height: 20px;
  color: #d68a34;
  opacity: 0.55;
}
.stat-value {
  font-size: 1.9rem;
  font-weight: 800;
  color: #d68a34;
  font-variant-numeric: tabular-nums;
  line-height: 1.1;
}
.stat-label {
  margin-top: 6px;
  font-size: 0.76rem;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 700;
}
.stat-sub {
  margin-top: 4px;
  font-size: 0.72rem;
  color: #9c9c9c;
}
</style>
