<script setup lang="ts">
import { useId } from "vue";
import PasswordInput from "../PasswordInput.vue";
import type { UiField, UiValue } from "../../services/pluginUi";

defineProps<{ field: UiField; error?: string; disabled?: boolean }>();
const value = defineModel<UiValue>();
const id = useId();
</script>

<template>
  <div
    class="plugin-field"
    :class="{ 'boolean-field': field.type === 'boolean' }"
  >
    <label :for="id"
      >{{ field.label
      }}<span v-if="field.required" aria-hidden="true"> *</span></label
    >
    <PasswordInput
      v-if="field.secret || field.type === 'password'"
      :id="id"
      :model-value="String(value ?? '')"
      mode="replace"
      :disabled="disabled"
      :required="field.required"
      :maxlength="field.validation?.max_length"
      :aria-invalid="Boolean(error)"
      :aria-describedby="`${id}-hint ${id}-error`"
      @update:model-value="value = $event"
    />
    <select
      v-else-if="field.type === 'select' || field.type === 'multiselect'"
      :id="id"
      v-model="value"
      :multiple="field.type === 'multiselect'"
      :disabled="disabled"
      :required="field.required"
      :aria-invalid="Boolean(error)"
      :aria-describedby="`${id}-hint ${id}-error`"
    >
      <option v-if="field.type === 'select' && !field.required" value="">
        Choose an option
      </option>
      <option
        v-for="option in field.options"
        :key="option.value"
        :value="option.value"
      >
        {{ option.label }}
      </option>
    </select>
    <textarea
      v-else-if="field.type === 'textarea'"
      :id="id"
      v-model="value as string"
      :disabled="disabled"
      :required="field.required"
      :maxlength="field.validation?.max_length"
      :aria-invalid="Boolean(error)"
      :aria-describedby="`${id}-hint ${id}-error`"
    />
    <input
      v-else-if="field.type === 'boolean'"
      :id="id"
      v-model="value"
      type="checkbox"
      :disabled="disabled"
      :aria-invalid="Boolean(error)"
      :aria-describedby="`${id}-hint ${id}-error`"
    />
    <input
      v-else-if="field.type === 'number'"
      :id="id"
      v-model.number="value"
      type="number"
      :min="field.validation?.minimum"
      :max="field.validation?.maximum"
      step="any"
      :disabled="disabled"
      :required="field.required"
      :aria-invalid="Boolean(error)"
      :aria-describedby="`${id}-hint ${id}-error`"
    />
    <input
      v-else
      :id="id"
      v-model="value"
      type="text"
      :disabled="disabled"
      :required="field.required"
      :maxlength="field.validation?.max_length"
      :autocomplete="field.secret ? 'new-password' : 'off'"
      :aria-invalid="Boolean(error)"
      :aria-describedby="`${id}-hint ${id}-error`"
    />
    <small :id="`${id}-hint`">{{ field.description }}</small>
    <p :id="`${id}-error`" class="field-error">{{ error }}</p>
  </div>
</template>

<style scoped>
.plugin-field {
  display: grid;
  gap: var(--ui-space-2);
  min-width: 0;
  margin-block: var(--ui-space-4);
}
label {
  font-weight: var(--ui-weight-heading);
}
input:not([type="checkbox"]),
textarea,
select {
  width: 100%;
  min-height: var(--ui-control-height);
  box-sizing: border-box;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-control);
  background: var(--ui-surface);
  color: var(--ui-text);
  padding: var(--ui-space-3);
  font: inherit;
}
textarea {
  min-height: 112px;
  resize: vertical;
}
small {
  color: var(--ui-dim);
}
.field-error {
  color: var(--ui-error);
  margin: 0;
}
.field-error:empty,
small:empty {
  display: none;
}
.boolean-field {
  grid-template-columns: 24px 1fr;
  align-items: center;
  min-height: var(--ui-control-height);
}
.boolean-field input {
  grid-column: 1;
  grid-row: 1;
  width: 20px;
  height: 20px;
  accent-color: var(--ui-accent);
}
.boolean-field label {
  grid-column: 2;
  grid-row: 1;
  padding-block: var(--ui-space-3);
  cursor: pointer;
}
.boolean-field small,
.boolean-field .field-error {
  grid-column: 2;
}
</style>
