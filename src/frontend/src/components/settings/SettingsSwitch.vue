<script setup lang="ts">
// The on/off switch used in a SettingsRow. The row holds the visible name, so
// this only needs one for screen readers.
defineProps<{ modelValue: boolean; label: string; disabled?: boolean }>();
const emit = defineEmits<{ "update:modelValue": [value: boolean] }>();
</script>

<template>
  <button
    type="button"
    class="st-sw"
    :class="{ on: modelValue }"
    role="switch"
    :aria-checked="modelValue"
    :aria-label="label"
    :disabled="disabled"
    @click="emit('update:modelValue', !modelValue)"
  >
    <span></span>
  </button>
</template>

<style scoped>
.st-sw {
  position: relative;
  width: 40px;
  height: 22px;
  flex: 0 0 auto;
  border-radius: 999px;
  border: 1px solid #3a3a3a;
  background: #262626;
  cursor: pointer;
  padding: 0;
  transition:
    background 0.15s ease,
    border-color 0.15s ease;
}
.st-sw span {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #8a8a8a;
  transition:
    left 0.15s ease,
    background 0.15s ease;
}
.st-sw.on {
  background: var(--ui-accent);
  border-color: var(--ui-accent);
}
.st-sw.on span {
  left: 20px;
  background: var(--ui-on-accent);
}
.st-sw:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.st-sw:focus-visible {
  outline: 2px solid color-mix(in srgb, var(--ui-accent) 60%, transparent);
  outline-offset: 2px;
}
</style>
