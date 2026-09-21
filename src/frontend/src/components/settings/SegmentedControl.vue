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
  <div class="segmented-control" role="group">
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      class="segment"
      :class="{ active: modelValue === option.value }"
      @click="emit('update:modelValue', option.value)"
    >
      {{ option.label }}
    </button>
  </div>
</template>

<style scoped>
.segmented-control {
  display: flex;
  width: fit-content;
  max-width: 100%;
  box-sizing: border-box;
  overflow-x: auto;
  scrollbar-width: thin;
  background: #111;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  padding: 3px;
  gap: 2px;
}
.segment {
  flex: 0 0 auto;
  white-space: nowrap;
  background: none;
  border: none;
  border-radius: 6px;
  color: #999;
  font-size: 0.82rem;
  font-weight: 600;
  padding: 8px 14px;
  cursor: pointer;
  transition:
    background 0.15s ease,
    color 0.15s ease;
}
.segment:hover {
  color: #fff;
}
.segment.active {
  background: #d68a34;
  color: #111;
}
@media (max-width: 760px) {
  .segmented-control {
    width: 100%;
  }
  .segment {
    flex: 1 0 auto;
    min-width: max-content;
  }
}
</style>
