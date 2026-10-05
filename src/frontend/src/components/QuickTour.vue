<script setup lang="ts">
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from "vue";
import { useRoute, useRouter } from "vue-router";
import { currentUser } from "../state/auth";
import { isCommandPaletteOpen } from "../state/commandPalette";
import {
  quickTourActive,
  quickTourRun,
  shortcutsHelpOpen,
  stopQuickTour,
} from "../state/quickTour";
import { matchesTourShortcut, quickTourSteps } from "../utils/quickTour";
import AppIcon from "./AppIcon.vue";

const route = useRoute();
const router = useRouter();
const touch = window.matchMedia("(hover: none) and (pointer: coarse)").matches;
const steps = quickTourSteps(touch);
const index = ref(0);
const step = computed(() => steps[index.value]!);
const panel = ref<HTMLElement | null>(null);
const mountTarget = ref<HTMLElement | string>("body");
const preparing = ref(false);
const available = ref(false);
const complete = ref(false);
const error = ref("");
let highlighted: HTMLElement | null = null;
let observer: MutationObserver | undefined;
let frame = 0;
let generation = 0;
let opened = false;
let practiced = false;
let shortcutPending = false;
let readinessTimeout: number | undefined;
const inDialog = computed(() => mountTarget.value !== "body");
const canContinue = computed(() => !preparing.value && complete.value);

function visible(selector?: string): HTMLElement | undefined {
  if (!selector) return;
  return Array.from(document.querySelectorAll<HTMLElement>(selector)).find(
    (element) =>
      element.getClientRects().length > 0 && !element.closest("[inert]"),
  );
}
function clearHighlight() {
  highlighted?.removeAttribute("data-tour-highlight");
  highlighted = null;
}
function stateChanged() {
  if (!quickTourActive.value || preparing.value) return;
  const active = step.value;
  const targetInDialog = visible(active.openedTarget);
  const isOpened =
    active.shortcut === "search"
      ? isCommandPaletteOpen.value
      : active.shortcut === "help"
        ? shortcutsHelpOpen.value
        : Boolean(targetInDialog);
  if (isOpened) {
    opened = true;
    if (shortcutPending) practiced = true;
  }
  if (active.requirement === "read") complete.value = available.value;
  else if (active.requirement === "navigate")
    complete.value = route.path === active.destination;
  else if (active.destination)
    complete.value = shortcutPending && route.path === active.destination;
  else
    complete.value =
      opened && !isOpened && (active.requirement === "open-close" || practiced);
}
function refresh() {
  frame = 0;
  if (!quickTourActive.value) return;
  const dialogs = Array.from(
    document.querySelectorAll<HTMLDialogElement>("dialog[open]"),
  );
  const topDialog = dialogs.at(-1);
  // Keep the guide inside the real modal's focus boundary and browser top layer.
  mountTarget.value = topDialog || "body";
  const target = visible(step.value.openedTarget) || visible(step.value.target);
  available.value = Boolean(target);
  if (target !== highlighted) {
    clearHighlight();
    if (target) {
      highlighted = target;
      target.setAttribute("data-tour-highlight", "true");
      const bounds = target.getBoundingClientRect();
      if (
        bounds.top < 0 ||
        bounds.bottom > window.innerHeight - (topDialog ? 80 : 220)
      )
        target.scrollIntoView({
          block: bounds.height > window.innerHeight / 2 ? "start" : "center",
          behavior: "instant",
        });
    }
  }
  stateChanged();
}
function scheduleRefresh() {
  if (quickTourActive.value && !frame) frame = requestAnimationFrame(refresh);
}
async function prepare() {
  const request = ++generation;
  preparing.value = true;
  complete.value = available.value = false;
  opened = practiced = shortcutPending = false;
  error.value = "";
  clearHighlight();
  window.clearTimeout(readinessTimeout);
  try {
    if (step.value.path) await router.push(step.value.path);
    if (request !== generation || !quickTourActive.value) return;
    await nextTick();
    preparing.value = false;
    refresh();
    await nextTick();
    panel.value?.focus({ preventScroll: true });
    readinessTimeout = window.setTimeout(() => {
      if (request === generation && !available.value)
        error.value =
          "This control is unavailable right now. Retry this step or skip it.";
    }, 8000);
  } catch {
    if (request === generation) {
      preparing.value = false;
      error.value = "Could not open this page. Retry this step or skip it.";
    }
  }
}
function advance() {
  if (index.value === steps.length - 1) {
    stopQuickTour();
    return;
  }
  index.value++;
  void prepare();
}
function back() {
  if (!index.value || preparing.value) return;
  index.value--;
  void prepare();
}
function onKeydown(event: KeyboardEvent) {
  if (
    !quickTourActive.value ||
    event.repeat ||
    event.isComposing ||
    event.getModifierState("AltGraph")
  )
    return;
  if (event.key === "Escape" && !document.querySelector("dialog[open]")) {
    stopQuickTour();
    return;
  }
  if (step.value.shortcut && matchesTourShortcut(step.value.shortcut, event)) {
    const currentStep = step.value.id;
    queueMicrotask(() => {
      // The normal handler must consume the key. Ignored keys in text fields
      // or another modal cannot pass a practice step through later navigation.
      if (
        !quickTourActive.value ||
        step.value.id !== currentStep ||
        !event.defaultPrevented
      )
        return;
      shortcutPending = true;
      stateChanged();
    });
  }
}
function openTouchTool() {
  if (step.value.shortcut === "search") isCommandPaletteOpen.value = true;
  else if (step.value.shortcut === "help") shortcutsHelpOpen.value = true;
}
watch([() => route.fullPath, isCommandPaletteOpen, shortcutsHelpOpen], () => {
  stateChanged();
  scheduleRefresh();
});
watch([quickTourActive, quickTourRun], ([active]) => {
  if (!active) {
    generation++;
    observer?.disconnect();
    window.clearTimeout(readinessTimeout);
    cancelAnimationFrame(frame);
    frame = 0;
    clearHighlight();
    mountTarget.value = "body";
    return;
  }
  index.value = 0;
  observer?.observe(document.body, {
    childList: true,
    subtree: true,
    attributes: true,
    attributeFilter: ["open"],
  });
  void prepare();
});
watch(() => currentUser.value?.id, stopQuickTour);
onMounted(() => {
  observer = new MutationObserver(scheduleRefresh);
  // Run after the app's handlers so practice reflects an accepted shortcut.
  window.addEventListener("keydown", onKeydown);
  window.addEventListener("resize", scheduleRefresh);
  window.addEventListener("scroll", scheduleRefresh, true);
});
onBeforeUnmount(() => {
  stopQuickTour();
  generation++;
  observer?.disconnect();
  window.clearTimeout(readinessTimeout);
  cancelAnimationFrame(frame);
  window.removeEventListener("keydown", onKeydown);
  window.removeEventListener("resize", scheduleRefresh);
  window.removeEventListener("scroll", scheduleRefresh, true);
  clearHighlight();
});
</script>

<template>
  <Teleport :to="mountTarget">
    <section
      v-if="quickTourActive"
      ref="panel"
      class="quick-tour"
      :class="{ 'inside-dialog': inDialog }"
      role="region"
      aria-labelledby="tour-title"
      tabindex="-1"
      data-tour-guide
    >
      <header>
        <div>
          <p class="tour-progress" aria-live="polite">
            Step {{ index + 1 }} of {{ steps.length }}
          </p>
          <h2 id="tour-title">{{ step.title }}</h2>
        </div>
        <button
          type="button"
          class="tour-close"
          aria-label="End tour"
          @click="stopQuickTour"
        >
          <AppIcon name="close" />
        </button>
      </header>
      <p class="tour-description">{{ step.description }}</p>
      <p v-if="complete" class="tour-success" role="status">
        {{
          step.requirement === "read"
            ? "Continue when you are ready."
            : "Done — you tried the real control."
        }}
      </p>
      <p v-else-if="preparing" role="status">Opening this page…</p>
      <p v-if="error" class="ui-error" role="status">
        {{ error }}
        <button type="button" class="ui-btn ui-btn-ghost" @click="prepare">
          Retry
        </button>
      </p>
      <footer>
        <button
          type="button"
          class="ui-btn ui-btn-ghost"
          :disabled="index === 0 || preparing"
          @click="back"
        >
          Back
        </button>
        <button
          v-if="
            touch &&
            ['search', 'help'].includes(step.shortcut || '') &&
            !complete
          "
          type="button"
          class="ui-btn ui-btn-ghost"
          @click="openTouchTool"
        >
          {{
            step.shortcut === "search" ? "Open search" : "Open shortcut help"
          }}
        </button>
        <button
          v-if="!canContinue"
          type="button"
          class="ui-btn ui-btn-ghost"
          :disabled="preparing"
          @click="advance"
        >
          Skip step
        </button>
        <button
          type="button"
          class="ui-btn ui-btn-primary"
          :disabled="!canContinue"
          @click="advance"
        >
          {{ index === steps.length - 1 ? "Finish tour" : "Continue" }}
        </button>
      </footer>
    </section>
  </Teleport>
</template>

<style>
[data-tour-highlight] {
  outline: 3px solid var(--ui-accent);
  outline-offset: 4px;
}
</style>

<style scoped>
.quick-tour {
  position: fixed;
  right: 20px;
  bottom: 20px;
  z-index: 500;
  width: min(380px, calc(100vw - 32px));
  max-height: calc(100dvh - 40px);
  overflow: auto;
  padding: 16px;
  border: 2px solid var(--ui-accent);
  border-radius: var(--ui-radius-card);
  background: var(--ui-surface);
  color: var(--ui-text);
  box-shadow: var(--ui-elevation);
  font: inherit;
}
.quick-tour.inside-dialog {
  position: static;
  width: auto;
  max-height: 230px;
  margin: 0;
  flex-shrink: 0;
  border-width: 1px 0 0;
  border-radius: 0;
  background: var(--ui-surface-2);
  box-shadow: none;
}
header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
h2 {
  margin: 2px 0 0;
  font: var(--ui-weight-heading) var(--ui-font-heading)/1.3
    var(--ui-font-family);
}
.tour-progress {
  margin: 0;
  font-size: 12px;
  color: var(--ui-dim);
}
.tour-description {
  margin: 10px 0;
  font-size: 14px;
  line-height: 1.5;
}
.tour-success {
  margin: 8px 0;
  color: var(--ui-success);
  font-size: 12px;
}
.tour-close {
  min-width: 44px;
  min-height: 44px;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: var(--ui-radius-row);
  color: var(--ui-dim);
  background: transparent;
  cursor: pointer;
}
.tour-close:hover {
  color: var(--ui-text);
  background: var(--ui-surface-2);
}
footer {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}
footer .ui-btn {
  min-height: 44px;
  padding-inline: 12px;
}
footer .ui-btn-primary {
  margin-left: auto;
}
@media (max-width: 760px) {
  .quick-tour {
    right: 12px;
    bottom: calc(78px + env(safe-area-inset-bottom, 0px));
    width: calc(100vw - 24px);
    max-height: 38dvh;
    padding: 12px;
  }
  .quick-tour.inside-dialog {
    width: auto;
    max-height: 34dvh;
  }
  .tour-description {
    font-size: 13px;
    margin: 6px 0;
  }
}
</style>
