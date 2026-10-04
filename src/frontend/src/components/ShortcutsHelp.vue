<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { NAVIGATION_SHORTCUTS } from "../utils/shortcuts";
import { isCommandPaletteOpen } from "../state/commandPalette";
import UiModal from "./UiModal.vue";
import ShortcutGroups from "./ShortcutGroups.vue";

const open = ref(false);
const route = useRoute();
const router = useRouter();
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
      !element.matches(":disabled, [inert]"),
  );
}

function onKeydown(event: KeyboardEvent) {
  if (event.defaultPrevented || event.isComposing || event.repeat) return;
  if (isTypingTarget(event.target) || event.ctrlKey || event.metaKey) {
    return;
  }
  if (open.value) {
    if (event.key === "?" || event.key === "Escape") {
      event.preventDefault();
      open.value = false;
    }
    return;
  }
  if (
    isCommandPaletteOpen.value ||
    document.querySelector(
      'dialog[open], [role="dialog"], [role="alertdialog"]',
    )
  ) {
    return;
  }
  if (event.key === "?") {
    event.preventDefault();
    open.value = true;
    return;
  }
  const key = event.key.toLowerCase();
  if (event.altKey) {
    if (event.shiftKey || event.getModifierState("AltGraph")) return;
    // Option on macOS can produce a symbol rather than the underlying letter.
    const letter = /^[a-z]$/.test(key)
      ? key
      : /^Key[A-Z]$/.test(event.code)
        ? event.code.slice(3).toLowerCase()
        : "";
    const navigation = NAVIGATION_SHORTCUTS.find((item) => item.key === letter);
    if (navigation) {
      event.preventDefault();
      void router.push(navigation.path);
    }
    return;
  }
  if (event.key === "/") {
    event.preventDefault();
    const control = visibleControl("search");
    if (control) control.focus();
    else isCommandPaletteOpen.value = true;
  } else if (key === "n") {
    const control = visibleControl("create");
    if (!control) return;
    event.preventDefault();
    if (control instanceof HTMLInputElement) control.focus();
    else control.click();
  }
}

onMounted(() => window.addEventListener("keydown", onKeydown, true));
onUnmounted(() => window.removeEventListener("keydown", onKeydown, true));
</script>

<template>
  <UiModal
    v-if="open"
    title="Keyboard shortcuts"
    size="wide"
    description="This page comes first. Expand another section to see its shortcuts. Keys pause while you type or use a dialog."
    @close="open = false"
  >
    <ShortcutGroups :path="route.path" />
  </UiModal>
</template>
