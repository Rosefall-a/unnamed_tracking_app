<script setup lang="ts">
import { ref, watch, nextTick } from "vue";
import UiModal from "./UiModal.vue";
import { activeDialog, closeDialog } from "../state/dialog";
const value = ref("");
const inputEl = ref<HTMLInputElement | null>(null);
const acceptEl = ref<HTMLButtonElement | null>(null);
watch(activeDialog, async (request) => {
  if (!request) return;
  value.value = request.defaultValue;
  await nextTick();
  if (request.kind === "prompt") {
    inputEl.value?.focus();
    inputEl.value?.select();
  } else acceptEl.value?.focus();
});
function accept() {
  const request = activeDialog.value;
  if (!request) return;
  if (request.kind === "prompt") {
    const text = value.value.trim();
    if (text) closeDialog(text);
  } else closeDialog(true);
}
function cancel() {
  closeDialog(activeDialog.value?.kind === "prompt" ? null : false);
}
</script>
<template>
  <UiModal
    v-if="activeDialog"
    :title="
      activeDialog.title ??
      (activeDialog.kind === 'prompt' ? 'Enter a value' : 'Confirm')
    "
    @close="cancel"
  >
    <p class="dialog-message">{{ activeDialog.message }}</p>
    <label v-if="activeDialog.kind === 'prompt'" class="dialog-label">
      <span>{{ activeDialog.placeholder || "Value" }}</span>
      <input
        ref="inputEl"
        v-model="value"
        class="ui-field dialog-input"
        type="text"
        :placeholder="activeDialog.placeholder"
        @keydown.enter.prevent="accept"
      />
    </label>
    <template #footer>
      <button type="button" class="ui-btn ui-btn-ghost" @click="cancel">
        {{ activeDialog.cancelLabel }}
      </button>
      <button
        ref="acceptEl"
        type="button"
        class="ui-btn"
        :class="activeDialog.danger ? 'ui-btn-danger' : 'ui-btn-primary'"
        @click="accept"
      >
        {{ activeDialog.confirmLabel }}
      </button>
    </template>
  </UiModal>
</template>
<style scoped>
.dialog-message {
  color: var(--ui-dim);
  margin: 0 0 16px;
  overflow-wrap: anywhere;
}
.dialog-label {
  display: grid;
  gap: 8px;
}
.dialog-input {
  width: 100%;
}
</style>
