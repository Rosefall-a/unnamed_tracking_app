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
  background: var(--ui-bg);
  border: 1px solid var(--ui-border-strong);
  border-radius: var(--ui-radius-control);
  padding: 3px;
  gap: 2px;
}
.segment {
  background: none;
  border: none;
  border-radius: 6px;
  color: var(--ui-dim);
  font-size: 0.82rem;
  font-weight: 600;
  padding: 8px 14px;
  cursor: pointer;
  transition:
    background 0.15s ease,
    color 0.15s ease;
}
.segment:hover {
  color: var(--ui-text);
}
.segment.active {
  background: var(--ui-accent);
  color: var(--ui-on-accent);
}
</style>
