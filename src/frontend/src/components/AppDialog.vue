<script setup lang="ts">
// The one place confirm and prompt dialogs are drawn (see state/dialog.ts).
// Mounted once in App.vue. Enter accepts, Escape or a click outside
// cancels, and focus lands on the field (prompt) or the accept button.
import { ref, watch, nextTick } from "vue";
import { activeDialog, closeDialog } from "../state/dialog";

const value = ref("");
const inputEl = ref<HTMLInputElement | null>(null);
const acceptEl = ref<HTMLButtonElement | null>(null);

watch(activeDialog, async (d) => {
  if (!d) return;
  value.value = d.defaultValue;
  await nextTick();
  if (d.kind === "prompt") {
    inputEl.value?.focus();
    inputEl.value?.select();
  } else {
    acceptEl.value?.focus();
  }
});

function accept() {
  const d = activeDialog.value;
  if (!d) return;
  if (d.kind === "prompt") {
    const text = value.value.trim();
    if (!text) return;
    closeDialog(text);
  } else {
    closeDialog(true);
  }
}
function cancel() {
  closeDialog(activeDialog.value?.kind === "prompt" ? null : false);
}
</script>

<template>
  <div
    v-if="activeDialog"
    class="dialog-overlay"
    @click.self="cancel"
    @keydown.esc="cancel"
  >
    <div class="dialog" role="dialog" aria-modal="true" :aria-label="activeDialog.title ?? activeDialog.message">
      <h3 v-if="activeDialog.title" class="dialog-title">{{ activeDialog.title }}</h3>
      <p class="dialog-message">{{ activeDialog.message }}</p>
      <input
        v-if="activeDialog.kind === 'prompt'"
        ref="inputEl"
        v-model="value"
        class="dialog-input"
        type="text"
        :placeholder="activeDialog.placeholder"
        @keydown.enter.prevent="accept"
      />
      <div class="dialog-actions">
        <button type="button" class="dialog-cancel" @click="cancel">{{ activeDialog.cancelLabel }}</button>
        <button
          ref="acceptEl"
          type="button"
          class="dialog-accept"
          :class="{ danger: activeDialog.danger }"
          @click="accept"
        >
          {{ activeDialog.confirmLabel }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dialog-overlay {
  position: fixed;
  inset: 0;
  z-index: var(--ui-z-dialog);
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.dialog {
  width: 100%;
  max-width: 380px;
  background: #171717;
  border: 1px solid #2b2b2b;
  border-radius: 14px;
  padding: 22px;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.6);
  font-family: system-ui, sans-serif;
  color: #f2f2f2;
}
.dialog-title {
  margin: 0 0 8px;
  font-size: 1rem;
}
.dialog-message {
  margin: 0 0 16px;
  font-size: 0.88rem;
  line-height: 1.5;
  color: #dcdcdc;
}
.dialog-input {
  width: 100%;
  box-sizing: border-box;
  margin-bottom: 16px;
  background: #0d0d0d;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  color: #fff;
  padding: 9px 12px;
  font: inherit;
  font-size: 0.86rem;
}
.dialog-input:focus {
  outline: none;
  border-color: #d68a34;
}
.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.dialog-cancel {
  background: none;
  border: 1px solid #2b2b2b;
  color: #9c9c9c;
  border-radius: 8px;
  padding: 8px 14px;
  font-family: inherit;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
}
.dialog-cancel:hover {
  border-color: #3a3a3a;
  color: #ccc;
}
.dialog-accept {
  background: #d68a34;
  color: #0d0d0d;
  border: none;
  border-radius: 8px;
  padding: 8px 14px;
  font-family: inherit;
  font-weight: 700;
  font-size: 0.82rem;
  cursor: pointer;
}
.dialog-accept.danger {
  background: #dc2626;
  color: #fff;
}
</style>
