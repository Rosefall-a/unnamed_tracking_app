<script setup lang="ts">
import { onMounted, onUnmounted, watch, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  shortcutForEvent,
  matchesShortcut,
  runPluginShortcut,
} from "../state/shortcuts";
import { isCommandPaletteOpen } from "../state/commandPalette";
import UiModal from "./UiModal.vue";
import ShortcutGroups from "./ShortcutGroups.vue";
import { shortcutsHelpOpen as open } from "../state/quickTour";

const route = useRoute();
const router = useRouter();
const shortcutError = ref("");
watch(
  () => route.fullPath,
  () => {
    open.value = false;
  },
);

function isTypingTarget(target: EventTarget | null): boolean {
  return (
    target instanceof HTMLElement &&
    (Boolean(target.closest("input, textarea, select, [role=combobox]")) ||
      target.isContentEditable)
  );
}

function visibleControl(name: string): HTMLElement | undefined {
  return Array.from(
    document.querySelectorAll<HTMLElement>(
      `#main-content [data-shortcut="${name}"]`,
    ),
  ).find(
    (element) =>
      element.getClientRects().length > 0 &&
      !element.matches(":disabled") &&
      !element.closest("[inert]"),
  );
}

function onKeydown(event: KeyboardEvent) {
  if (event.defaultPrevented || event.isComposing || event.repeat) return;
  if (event.getModifierState("AltGraph")) return;
  if (open.value) {
    if (matchesShortcut("app.help", event) || event.key === "Escape") {
      event.preventDefault();
      open.value = false;
    }
    return;
  }
  if (isCommandPaletteOpen.value) {
    if (matchesShortcut("app.search", event)) {
      event.preventDefault();
      isCommandPaletteOpen.value = false;
    }
    return;
  }
  if (
    document.querySelector(
      'dialog[open], [role="dialog"], [role="alertdialog"]',
    )
  ) {
    return;
  }
  const shortcut = shortcutForEvent(event, route.path);
  if (
    !shortcut ||
    (isTypingTarget(event.target) && shortcut.id !== "app.search")
  )
    return;
  if (shortcut.id === "app.help") {
    event.preventDefault();
    open.value = true;
    return;
  }
  if (shortcut.id === "app.search") {
    event.preventDefault();
    isCommandPaletteOpen.value = true;
    return;
  }
  if (shortcut.destination) {
    event.preventDefault();
    void router.push(shortcut.destination);
    return;
  }
  if (shortcut.id === "app.focus-search" || shortcut.control === "search") {
    event.preventDefault();
    const control = visibleControl("search");
    if (control) control.focus();
    else isCommandPaletteOpen.value = true;
  } else if (shortcut.id === "app.create" || shortcut.control === "create") {
    const control = visibleControl("create");
    if (!control) return;
    event.preventDefault();
    if (control instanceof HTMLInputElement) control.focus();
    else control.click();
  } else if (shortcut.pluginId) {
    event.preventDefault();
    void runPluginShortcut(shortcut.id).catch(() => {
      shortcutError.value =
        "This extension shortcut could not run. Check its permissions and runtime status in plugin settings.";
    });
  }
}

onMounted(() => window.addEventListener("keydown", onKeydown, true));
onUnmounted(() => {
  open.value = false;
  window.removeEventListener("keydown", onKeydown, true);
});
</script>

<template>
  <UiModal
    v-if="open"
    title="Keyboard shortcuts"
    data-tour="shortcut-help"
    size="wide"
    description="This page comes first. Expand another section to see its shortcuts. Keys pause while you type or use a dialog."
    @close="open = false"
  >
    <ShortcutGroups :path="route.path" />
  </UiModal>
  <UiModal
    v-if="shortcutError"
    title="Shortcut unavailable"
    @close="shortcutError = ''"
    ><p role="alert">{{ shortcutError }}</p></UiModal
  >
</template>
