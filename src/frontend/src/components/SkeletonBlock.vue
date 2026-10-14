<script setup lang="ts">
withDefaults(
  defineProps<{
    width?: string;
    height?: string;
    radius?: string;
  }>(),
  { width: "100%", height: "16px", radius: "6px" },
);
</script>

<template>
  <div
    class="skeleton-block"
    :style="{ width, height, borderRadius: radius }"
  ></div>
</template>

<style scoped>
.skeleton-block {
  background: linear-gradient(
    90deg,
    var(--ui-surface) 25%,
    var(--ui-surface-3) 37%,
    var(--ui-surface) 63%
  );
  background-size: 400% 100%;
  animation: skeleton-shimmer 1.4s ease infinite;
}
@keyframes skeleton-shimmer {
  0% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0 50%;
  }
}
</style>
