<script setup lang="ts">
withDefaults(
  defineProps<{
    modelValue: boolean;
    label: string;
    disabled?: boolean;
    // why the option cannot be changed right now, shown while it is greyed out
    reason?: string;
  }>(),
  { disabled: false, reason: "" },
);

const emit = defineEmits<{
  "update:modelValue": [value: boolean];
}>();
</script>

<template>
  <button
    type="button"
    class="toggle-button"
    :class="{ on: modelValue }"
    role="switch"
    :aria-checked="modelValue"
    :disabled="disabled"
    @click="emit('update:modelValue', !modelValue)"
  >
    <span class="toggle-track"><span class="toggle-knob"></span></span>
    <span class="toggle-label"
      ><slot>{{ label }}</slot
      ><span v-if="disabled && reason" class="toggle-reason">{{
        reason
      }}</span></span
    >
  </button>
</template>

<style scoped>
.toggle-button {
  display: flex;
  align-items: center;
  gap: 10px;
  background: none;
  border: none;
  padding: 0;
  margin-bottom: 14px;
  cursor: pointer;
  text-align: left;
  color: var(--ui-text-soft);
  font: inherit;
  font-size: 0.82rem;
  line-height: 1.5;
}
.toggle-button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
.toggle-track {
  flex-shrink: 0;
  width: 34px;
  height: 20px;
  border-radius: 999px;
  background: var(--ui-border-strong);
  position: relative;
  transition: background 0.15s ease;
}
.toggle-button.on .toggle-track {
  background: var(--ui-accent);
}
.toggle-knob {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #fff;
  transition: transform 0.15s ease;
}
.toggle-button.on .toggle-knob {
  transform: translateX(14px);
}
.toggle-label {
  flex: 1;
}
.toggle-reason {
  display: block;
  margin-top: 2px;
  color: var(--ui-dim-2);
  font-size: 0.74rem;
}
.toggle-label :deep(strong) {
  color: var(--ui-heading);
}
</style>
