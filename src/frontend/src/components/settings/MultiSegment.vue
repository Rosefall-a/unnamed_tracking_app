<script setup lang="ts">
// Like SegmentedControl, but any number of options can be on at once: each
// button switches its own option.
const props = defineProps<{
  modelValue: string[];
  options: { value: string; label: string }[];
  disabled?: boolean;
}>();
const emit = defineEmits<{ "update:modelValue": [value: string[]] }>();

function toggle(value: string) {
  const on = props.modelValue.includes(value);
  emit(
    "update:modelValue",
    on
      ? props.modelValue.filter((v) => v !== value)
      : [...props.modelValue, value],
  );
}
</script>

<template>
  <div class="multi-segment" role="group">
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      class="segment"
      :class="{ active: modelValue.includes(option.value) }"
      :aria-pressed="modelValue.includes(option.value)"
      :disabled="disabled"
      @click="toggle(option.value)"
    >
      {{ option.label }}
    </button>
  </div>
</template>

<style scoped>
.multi-segment {
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
}
.segment:hover:not(:disabled) {
  color: var(--ui-heading);
}
.segment.active {
  background: color-mix(in srgb, var(--ui-accent) 18%, transparent);
  color: var(--ui-accent-bright);
  font-weight: 600;
}
.segment:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
