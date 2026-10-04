<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, useId } from "vue";
import AppIcon from "./AppIcon.vue";
import { containModalTab } from "../services/focus";

const props = withDefaults(
  defineProps<{ title: string; description?: string; dismissible?: boolean }>(),
  { dismissible: true },
);
const emit = defineEmits<{ close: [] }>();
const dialog = ref<HTMLDialogElement | null>(null);
const titleId = useId();
let previousFocus: HTMLElement | null = null;
let previousOverflow = "";
function dismiss() {
  if (props.dismissible) emit("close");
}
function backdrop(event: MouseEvent) {
  if (event.target !== dialog.value || !dialog.value) return;
  const bounds = dialog.value.getBoundingClientRect();
  if (
    event.clientX < bounds.left ||
    event.clientX > bounds.right ||
    event.clientY < bounds.top ||
    event.clientY > bounds.bottom
  )
    dismiss();
}
onMounted(() => {
  previousFocus =
    document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null;
  previousOverflow = document.body.style.overflow;
  document.body.style.overflow = "hidden";
  dialog.value?.showModal();
});
onBeforeUnmount(() => {
  dialog.value?.close();
  document.body.style.overflow = previousOverflow;
  if (previousFocus?.isConnected) previousFocus.focus({ preventScroll: true });
});
</script>

<template>
  <Teleport to="body">
    <dialog
      ref="dialog"
      class="ui-modal"
      :aria-labelledby="titleId"
      @cancel.prevent="dismiss"
      @click="backdrop"
      @keydown="containModalTab($event, dialog)"
    >
      <header class="modal-header">
        <div>
          <h2 :id="titleId">{{ title }}</h2>
          <p v-if="description">{{ description }}</p>
        </div>
        <button
          type="button"
          class="modal-close"
          :disabled="!dismissible"
          aria-label="Close dialog"
          @click="dismiss"
        >
          <AppIcon name="close" />
        </button>
      </header>
      <div class="modal-body"><slot /></div>
      <footer v-if="$slots.footer" class="modal-footer">
        <slot name="footer" />
      </footer>
    </dialog>
  </Teleport>
</template>

<style scoped>
.ui-modal {
  box-sizing: border-box;
  width: min(640px, calc(100vw - 32px));
  max-height: calc(100dvh - 32px);
  margin: auto;
  padding: 0;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-dialog);
  background: var(--ui-surface);
  color: var(--ui-text);
  box-shadow: var(--ui-elevation);
  font: var(--ui-font-body)/1.5 var(--ui-font-family);
  overflow: auto;
}
.ui-modal[open] {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.ui-modal::backdrop {
  background: var(--ui-overlay);
}
.modal-header {
  flex-shrink: 0;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 24px;
}
.modal-header h2 {
  margin: 0;
  font: var(--ui-weight-heading) var(--ui-font-heading)/1.4
    var(--ui-font-family);
  overflow-wrap: anywhere;
}
.modal-header p {
  margin: 8px 0 0;
  color: var(--ui-dim);
  font-size: var(--ui-font-small);
}
.modal-close {
  flex-shrink: 0;
  width: var(--ui-control-height);
  height: var(--ui-control-height);
  display: grid;
  place-items: center;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-control);
  background: var(--ui-surface);
  color: var(--ui-dim);
  cursor: pointer;
}
.modal-body {
  padding: 0 24px 24px;
  overflow-y: auto;
  min-height: 0;
}
.modal-footer {
  flex-shrink: 0;
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
  padding: 16px 24px;
  border-top: 1px solid var(--ui-border-soft);
}
@media (max-width: 760px) {
  .ui-modal {
    width: calc(100vw - 20px);
    max-height: calc(100dvh - 20px);
    border-radius: 28px;
  }
  .modal-header {
    padding: 20px;
  }
  .modal-body {
    padding: 0 20px 20px;
  }
  .modal-footer {
    padding: 16px 20px;
  }
}
</style>
