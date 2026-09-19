<script setup lang="ts">
// The round back arrow, one look on every page that has one (title pages,
// a single list). The page decides where it sits.
defineEmits<{ click: [] }>();
</script>

<template>
  <button type="button" class="back-button" title="Back" aria-label="Back" @click="$emit('click')">
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M19 12H5" />
      <path d="M12 19l-7-7 7-7" />
    </svg>
  </button>
</template>

<style scoped>
.back-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  flex-shrink: 0;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(20, 20, 20, 0.55);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  color: #fff;
  cursor: pointer;
  transition: background 0.15s ease;
}
.back-button:hover {
  background: rgba(40, 40, 40, 0.85);
}
</style>
