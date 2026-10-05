<script setup lang="ts">
import { ref } from "vue";

const props = defineProps<{ busy: boolean }>();
const emit = defineEmits<{ package: [file: File] }>();
const dragDepth = ref(0);
const error = ref("");

function draggingFile(event: DragEvent) {
  return event.dataTransfer?.types.includes("Files") ?? false;
}

function enter(event: DragEvent) {
  if (!draggingFile(event)) return;
  event.preventDefault();
  dragDepth.value += 1;
}

function leave(event: DragEvent) {
  if (!draggingFile(event)) return;
  dragDepth.value = Math.max(0, dragDepth.value - 1);
}

function over(event: DragEvent) {
  if (!draggingFile(event)) return;
  event.preventDefault();
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = props.busy ? "none" : "copy";
  }
}

function drop(event: DragEvent) {
  if (!draggingFile(event)) return;
  event.preventDefault();
  dragDepth.value = 0;
  if (props.busy) return;
  error.value = "";
  const files = event.dataTransfer?.files;
  if (!files || files.length !== 1) {
    error.value = "Drop one plugin package at a time.";
    return;
  }
  const file = files[0];
  if (!/\.(utp|upt|zip)$/i.test(file.name)) {
    error.value = "Choose a .utp, .upt or .zip plugin package.";
    return;
  }
  if (file.size > 64 * 1024 * 1024) {
    error.value = "Plugin packages must be 64 MiB or smaller.";
    return;
  }
  emit("package", file);
}
</script>

<template>
  <div
    class="package-drop-zone"
    :class="{ 'drop-active': dragDepth > 0 && !busy }"
    role="region"
    aria-label="Plugin package drop area"
    :aria-busy="busy"
    @dragenter="enter"
    @dragleave="leave"
    @dragover="over"
    @drop="drop"
  >
    <slot />
    <p class="drop-hint" role="status">
      {{
        busy
          ? "Inspecting plugin package…"
          : "Drop a .utp or .upt package here to review it."
      }}
    </p>
    <p v-if="error" class="drop-error" role="alert">{{ error }}</p>
  </div>
</template>

<style scoped>
.package-drop-zone {
  transition:
    border-color 120ms ease,
    background-color 120ms ease;
}
.package-drop-zone.drop-active {
  border-color: var(--ui-accent);
  background: var(--ui-accent-soft);
  outline: 2px solid var(--ui-accent);
  outline-offset: 2px;
}
.drop-hint,
.drop-error {
  flex-basis: 100%;
  margin: 0;
  font-size: var(--ui-font-small);
  overflow-wrap: anywhere;
}
.drop-hint {
  color: var(--ui-dim);
}
.drop-error {
  color: var(--ui-danger);
}
@media (prefers-reduced-motion: reduce) {
  .package-drop-zone {
    transition: none;
  }
}
</style>
