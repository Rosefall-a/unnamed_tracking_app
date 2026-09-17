<script setup lang="ts">
// A small, centered yes/no confirmation — lighter-weight than
// MediaPreviewModal's full card layout, for a quick "do you also want
// to..." nudge (e.g. moving a show to Watching after checking off its
// first episode) rather than a real form or preview.
defineProps<{
  message: string;
  confirmLabel: string;
  cancelLabel: string;
}>();

const emit = defineEmits<{
  (e: "confirm"): void;
  (e: "cancel"): void;
}>();
</script>

<template>
  <div class="confirm-overlay" @click.self="emit('cancel')">
    <div class="confirm-popup">
      <p class="confirm-message">{{ message }}</p>
      <div class="confirm-actions">
        <button type="button" class="confirm-cancel" @click="emit('cancel')">
          {{ cancelLabel }}
        </button>
        <button type="button" class="confirm-accept" @click="emit('confirm')">
          {{ confirmLabel }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.confirm-overlay {
  position: fixed;
  inset: 0;
  z-index: 320;
  background: rgba(0, 0, 0, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.confirm-popup {
  width: 100%;
  max-width: 320px;
  background: #171717;
  border: 1px solid #2b2b2b;
  border-radius: 14px;
  padding: 20px;
}
.confirm-message {
  margin: 0 0 16px;
  font-size: 0.88rem;
  color: #f2f2f2;
  line-height: 1.5;
}
.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.confirm-cancel {
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
.confirm-cancel:hover {
  border-color: #3a3a3a;
  color: #ccc;
}
.confirm-accept {
  background: #d68a34;
  color: #0d0d0d;
  border: none;
  border-radius: 8px;
  padding: 8px 14px;
  font-weight: 700;
  font-size: 0.82rem;
  cursor: pointer;
}
</style>
