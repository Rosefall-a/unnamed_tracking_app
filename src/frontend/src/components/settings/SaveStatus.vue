<script setup lang="ts">
import { computed } from "vue";
import { saveState } from "../../state/saveStatus";

const label = computed(() => {
  if (saveState.value === "saving") return "Saving…";
  if (saveState.value === "saved") return "All changes saved";
  if (saveState.value === "settled") return "Saved";
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
  background: color-mix(in srgb, var(--ui-text) 5%, transparent);
  border: 1px solid var(--ui-border);
  color: var(--ui-dim);
}
.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--ui-dim);
}
.save-status.saving .dot {
  background: var(--ui-accent);
  animation: pulse 1s ease-in-out infinite;
}
.save-status.saved .dot {
  background: var(--ui-good);
}
.save-status.error {
  color: var(--ui-error);
  border-color: color-mix(in srgb, var(--ui-error) 35%, var(--ui-border));
}
.save-status.error .dot {
  background: var(--ui-error);
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
