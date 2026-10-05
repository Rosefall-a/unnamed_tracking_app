<script setup lang="ts">
import { computed, ref, useAttrs } from "vue";

defineOptions({ inheritAttrs: false });
const attrs = useAttrs();

const props = withDefaults(
  defineProps<{
    modelValue: string;
    autocomplete?: string;
    required?: boolean;
    placeholder?: string;
    disabled?: boolean;
    readonly?: boolean;
    mode?: "new" | "replace";
    inputAriaLabel?: string;
  }>(),
  {
    autocomplete: "new-password",
    required: false,
    placeholder: "",
    disabled: false,
    readonly: false,
    mode: "new",
    inputAriaLabel: "",
  },
);

const emit = defineEmits<{
  "update:modelValue": [value: string];
}>();

const showSecret = ref(false);
const secretLabel = computed(() =>
  props.mode === "replace" ? "secret" : "password",
);
const showLabel = computed(() => `Show ${secretLabel.value}`);
const hideLabel = computed(() => `Hide ${secretLabel.value}`);
</script>

<template>
  <div class="password-input">
    <input
      v-bind="attrs"
      class="password-input-field"
      :value="modelValue"
      :type="showSecret ? 'text' : 'password'"
      :autocomplete="autocomplete"
      :required="required"
      :placeholder="placeholder"
      :disabled="disabled"
      :readonly="readonly"
      :aria-label="
        inputAriaLabel || (attrs['aria-label'] as string) || undefined
      "
      @input="
        emit('update:modelValue', ($event.target as HTMLInputElement).value)
      "
    />
    <button
      type="button"
      class="visibility-button"
      :aria-label="showSecret ? hideLabel : showLabel"
      :title="showSecret ? hideLabel : showLabel"
      :disabled="disabled"
      @click="showSecret = !showSecret"
    >
      <svg
        v-if="showSecret"
        viewBox="0 0 24 24"
        aria-hidden="true"
        focusable="false"
      >
        <path
          d="M3 3l18 18M10.6 10.6a2 2 0 102.8 2.8M9.9 4.3A10.8 10.8 0 0112 4c5.2 0 8.8 3.5 10 8a10.8 10.8 0 01-3.1 5.2M6.2 6.2A10.9 10.9 0 002 12c1.2 4.5 4.8 8 10 8 1.5 0 2.9-.3 4.1-.9"
        />
      </svg>
      <svg v-else viewBox="0 0 24 24" aria-hidden="true" focusable="false">
        <path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z" />
        <circle cx="12" cy="12" r="2.5" />
      </svg>
    </button>
  </div>
</template>

<style scoped>
.password-input {
  position: relative;
  display: block;
  width: 100%;
  min-width: 0;
}

.password-input-field {
  display: block;
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
  background: var(--ui-bg);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-control);
  color: var(--ui-text);
  padding: 10px 52px 10px 12px;
  min-height: 44px;
  font: inherit;
}

.password-input-field:focus {
  outline: none;
  border-color: var(--ui-accent);
}

.password-input-field:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.password-input-field:read-only {
  cursor: text;
}

.visibility-button {
  position: absolute;
  top: 50%;
  right: 1px;
  width: 44px;
  height: 44px;
  transform: translateY(-50%);
  display: grid;
  place-items: center;
  padding: 0;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--ui-dim);
  cursor: pointer;
}

.visibility-button:hover:not(:disabled) {
  color: var(--ui-accent);
  background: var(--ui-surface-2);
}

.visibility-button:focus-visible {
  outline: 2px solid var(--ui-accent);
  outline-offset: 1px;
}

.visibility-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.visibility-button svg {
  width: 18px;
  height: 18px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}
</style>

<style>
/* Edge supplies its own password reveal control; the component owns the only reveal button. */
input.password-input-field::-ms-reveal,
input.password-input-field::-ms-clear {
  display: none;
}
</style>
