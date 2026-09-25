<script setup lang="ts">
import { ref } from "vue";

withDefaults(
  defineProps<{
    modelValue: string;
    autocomplete?: string;
    required?: boolean;
    placeholder?: string;
    disabled?: boolean;
  }>(),
  {
    autocomplete: "current-password",
    required: false,
    placeholder: "",
    disabled: false,
  },
);

const emit = defineEmits<{
  "update:modelValue": [value: string];
}>();

const showPassword = ref(false);
</script>

<template>
  <div class="password-input">
    <input
      :value="modelValue"
      :type="showPassword ? "text" : "password""
      :autocomplete="autocomplete"
      :required="required"
      :placeholder="placeholder"
      :disabled="disabled"
      @input="emit("update:modelValue", ($event.target as HTMLInputElement).value)"
    />
    <button
      type="button"
      class="visibility-button"
      :aria-label="showPassword ? "Hide password" : "Show password""
      :title="showPassword ? "Hide password" : "Show password""
      :disabled="disabled"
      @click="showPassword = !showPassword"
    >
      <svg
        v-if="showPassword"
        viewBox="0 0 24 24"
        aria-hidden="true"
        focusable="false"
      >
        <path d="M3 3l18 18M10.6 10.6a2 2 0 102.8 2.8M9.9 4.3A10.8 10.8 0 0112 4c5.2 0 8.8 3.5 10 8a10.8 10.8 0 01-3.1 5.2M6.2 6.2A10.9 10.9 0 002 12c1.2 4.5 4.8 8 10 8 1.5 0 2.9-.3 4.1-.9" />
      </svg>
      <svg
        v-else
        viewBox="0 0 24 24"
        aria-hidden="true"
        focusable="false"
      >
        <path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z" />
        <circle cx="12" cy="12" r="2.5" />
      </svg>
    </button>
  </div>
</template>

<style scoped>
.password-input {
  position: relative;
  width: 100%;
}

.password-input input {
  width: 100%;
  box-sizing: border-box;
  padding-right: 42px;
}

.visibility-button {
  position: absolute;
  top: 50%;
  right: 8px;
  width: 30px;
  height: 30px;
  transform: translateY(-50%);
  display: grid;
  place-items: center;
  padding: 0;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #888;
  cursor: pointer;
}

.visibility-button:hover {
  color: #d68a34;
  background: rgba(255, 255, 255, 0.06);
}

.visibility-button:focus-visible {
  outline: 2px solid #d68a34;
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
