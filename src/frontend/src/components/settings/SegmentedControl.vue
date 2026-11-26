<script setup lang="ts">
defineProps<{
  modelValue: string;
  options: { value: string; label: string }[];
}>();

const emit = defineEmits<{
  "update:modelValue": [value: string];
}>();
</script>

<template>
  <div class="segmented-control">
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      class="segment"
      :class="{ active: modelValue === option.value }"
      :aria-pressed="modelValue === option.value"
      @click="emit('update:modelValue', option.value)"
    >
      {{ option.label }}
    </button>
  </div>
</template>

<style scoped>
.segmented-control {
  display: inline-flex;
  flex-wrap: wrap;
  max-width: 100%;
  box-sizing: border-box;
  background: #141414;
  border: 1px solid #2b2b2b;
  border-radius: 8px;
  padding: 2px;
  gap: 2px;
}
.segment {
  background: none;
  border: none;
  border-radius: 6px;
  color: #b5b5b5;
  font: inherit;
  font-size: 13px;
  padding: 6px 11px;
  cursor: pointer;
  transition:
    background 0.15s ease,
    color 0.15s ease;
}
.segment:hover {
  color: var(--ui-heading);
}
.segment.active {
  background: color-mix(in srgb, var(--ui-accent) 18%, transparent);
  color: var(--ui-accent-bright);
  font-weight: 600;
}
</style>
