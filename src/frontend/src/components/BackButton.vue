<script setup lang="ts">
// The round back arrow, one look on every page that has one (title pages,
// a single list). The page decides where it sits; `fixed` pins it to the
// spot beside the sidebar's menu button for pages with no top bar.
import { computed } from "vue";
import {
  effectiveSidebarMode,
  sidebarWidth,
  navigationViewport,
} from "../state/sidebarMode";

defineEmits<{ click: [] }>();
defineProps<{ fixed?: boolean }>();

// `fixed` is positioned relative to the viewport, so it doesn't follow the
// page's own margin — it has to know the sidebar's actual on-screen width
// itself, or pinned/rail modes park it right underneath the sidebar. The
// 40px gap matches the page content's own left padding (see Settings.vue's
// `.settings-page`), so the arrow lines up with the title under it instead
// of hugging the sidebar edge tighter than the content does.
const fixedLeft = computed(() => {
  if (effectiveSidebarMode.value === "pinned")
    return `${sidebarWidth.value + 52}px`;
  if (effectiveSidebarMode.value === "rail") return "116px";
  if (navigationViewport.value === "phone") return "20px";
  return "62px";
});
</script>

<template>
  <button
    type="button"
    class="back-button"
    :class="{ 'back-button-fixed': fixed }"
    :style="fixed ? { left: fixedLeft } : undefined"
    title="Back"
    aria-label="Back"
    @click="$emit('click')"
  >
    <svg
      viewBox="0 0 24 24"
      width="18"
      height="18"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <path d="M19 12H5" />
      <path d="M12 19l-7-7 7-7" />
    </svg>
  </button>
</template>

<style scoped>
.back-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: var(--ui-control-height);
  height: var(--ui-control-height);
  flex-shrink: 0;
  border-radius: 50%;
  border: 1px solid color-mix(in srgb, var(--ui-text) 14%, transparent);
  background: var(--ui-surface);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  color: var(--ui-text);
  cursor: pointer;
  transition: background 0.15s ease;
}
.back-button:hover {
  background: var(--ui-surface-2);
}
.back-button-fixed {
  position: fixed;
  top: 16px;
  z-index: 100;
  transition: left 0.18s ease;
}
</style>
