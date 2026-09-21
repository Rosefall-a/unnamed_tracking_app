<script setup lang="ts">
// The one checkmark glyph used everywhere a checkbox-style control shows
// a "checked" state — swaps in for the plain unicode "✓" character,
// which renders inconsistently across fonts/platforms (weight, baseline,
// sometimes a different glyph entirely). Uses currentColor so it always
// matches whatever text color the surrounding button already sets.
withDefaults(defineProps<{ size?: number }>(), { size: 13 });
</script>

<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 16 16"
    fill="none"
    aria-hidden="true"
    class="check-icon"
  >
    <path
      d="M3 8.5L6.2 11.7L13 4.5"
      stroke="currentColor"
      stroke-width="2.2"
      stroke-linecap="round"
      stroke-linejoin="round"
    />
  </svg>
</template>

<style scoped>
.check-icon {
  display: block;
}
</style>
