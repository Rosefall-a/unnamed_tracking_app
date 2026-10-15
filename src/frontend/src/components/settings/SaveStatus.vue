<script setup lang="ts">
import { computed } from "vue";
import { saveState } from "../../state/saveStatus";

const label = computed(() => {
  if (saveState.value === "saving") return "Saving…";
  if (saveState.value === "saved") return "All changes saved";
  if (saveState.value === "error") return "Couldn't save. Try again";
  return "";
});
</script>

<template>
  <div
    v-if="label"
    class="save-status"
    :class="saveState"
    role="status"
    aria-live="polite"
  >
    <span class="dot"></span>{{ label }}
  </div>
</template>

<style scoped>
.save-status {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 12.5px;
  font-weight: 600;
  background: color-mix(in srgb, var(--ui-wash-base) 5%, transparent);
  border: 1px solid var(--ui-border);
  color: var(--ui-dim-3);
}
.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #888;
}
.save-status.saving .dot {
  background: var(--ui-accent);
  animation: pulse 1s ease-in-out infinite;
}
.save-status.saved {
  color: var(--ui-good-text);
}
.save-status.saved .dot {
  background: var(--ui-success-bright);
}
.save-status.error {
  color: var(--ui-error-text);
  border-color: color-mix(in srgb, var(--ui-danger) 35%, transparent);
}
.save-status.error .dot {
  background: var(--ui-danger-bright);
}
@keyframes pulse {
  50% {
    opacity: 0.35;
  }
}
@media (prefers-reduced-motion: reduce) {
  .save-status.saving .dot {
    animation: none;
  }
}
</style>
