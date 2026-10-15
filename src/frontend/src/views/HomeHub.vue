<script setup lang="ts">
// Home is pages of widgets on a grid. This view holds the page tabs, the
// Customize mode (a working copy of the layout that is only saved on Done), and
// the side panel that shows either the widget gallery, one widget's settings, or
// the page options. The widgets themselves live in components/home.
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  provide,
  ref,
} from "vue";
import AccountChip from "../components/AccountChip.vue";
import HomeGrid from "../components/home/HomeGrid.vue";
import WidgetDrawer from "../components/home/WidgetDrawer.vue";
import WidgetSettings from "../components/home/WidgetSettings.vue";
import { addWidget, defaultLayout, moveWidget, settle } from "../home/layout";
import type {
  HomeLayout,
  HomePage,
  PageBackdrop,
  PageGap,
  WidgetInstance,
} from "../home/layout";
import { definitionOf } from "../home/registry";
import {
  flushPending,
  saveError,
  saveLayout,
  savedLayout,
  startDraft,
  updateWidgetSettings,
} from "../home/store";
import { UPDATE_WIDGET } from "../home/context";
import { onBeforeRouteLeave } from "vue-router";

const draft = ref<HomeLayout | null>(null);
const editing = computed(() => draft.value !== null);
const layout = computed(() => draft.value ?? savedLayout.value);

const pageId = ref<string>(layout.value.pages[0].id);
const page = computed<HomePage>(
  () =>
    layout.value.pages.find((p) => p.id === pageId.value) ??
    layout.value.pages[0],
);

// controls on a widget change its settings straight away, saved as you go
provide(UPDATE_WIDGET, (id, settings, variant) =>
  updateWidgetSettings(id, settings, variant),
);

type Panel = "add" | "page" | { settings: string } | null;
const panel = ref<Panel>(null);
const saving = ref(false);
const confirmReset = ref(false);

function startEditing() {
  draft.value = startDraft();
  panel.value = null;
}
function cancel() {
  draft.value = null;
  panel.value = null;
  confirmReset.value = false;
  if (!layout.value.pages.some((p) => p.id === pageId.value))
    pageId.value = layout.value.pages[0].id;
}
async function done() {
  if (!draft.value) return;
  saving.value = true;
  const ok = await saveLayout(draft.value);
  saving.value = false;
  if (ok) {
    draft.value = null;
    panel.value = null;
  }
}
function reset() {
  if (!confirmReset.value) {
    confirmReset.value = true;
    return;
  }
  draft.value = defaultLayout();
  pageId.value = draft.value.pages[0].id;
  confirmReset.value = false;
}

function mutatePage(change: (p: HomePage) => void) {
  if (!draft.value) return;
  const target = draft.value.pages.find((p) => p.id === pageId.value);
  if (target) change(target);
}
function setWidgets(widgets: WidgetInstance[]) {
  mutatePage((p) => (p.widgets = widgets));
}
// closes the gaps: everything slides up until it meets something
function tidy() {
  mutatePage((p) => (p.widgets = settle(p.widgets)));
}
function removeWidget(id: string) {
  mutatePage((p) => (p.widgets = p.widgets.filter((w) => w.id !== id)));
  if (typeof panel.value === "object" && panel.value?.settings === id)
    panel.value = null;
}

async function addFromGallery(
  type: string,
  variant: string | null,
  settings: Record<string, unknown>,
  size: { w: number; h: number },
) {
  if (!definitionOf(type)) return;
  let newId = "";
  mutatePage((p) => {
    p.widgets = addWidget(p.widgets, type, size, settings, variant);
    newId = p.widgets[p.widgets.length - 1].id;
  });
  await nextTick();
  document
    .querySelector(`[data-widget="${newId}"]`)
    ?.scrollIntoView({ behavior: "smooth", block: "center" });
}

const settingsTarget = computed(() => {
  const p = panel.value;
  if (!p || typeof p !== "object") return null;
  const widget = page.value.widgets.find((w) => w.id === p.settings);
  const def = widget ? definitionOf(widget.type) : undefined;
  return widget && def ? { widget, def } : null;
});
function resizeWidget(w: number, h: number) {
  const target = settingsTarget.value?.widget;
  if (!target) return;
  setWidgets(
    moveWidget(page.value.widgets, target.id, {
      x: target.x,
      y: target.y,
      w,
      h,
    }),
  );
}
function changeWidget(
  settings: Record<string, unknown>,
  variant: string | null,
) {
  const id = settingsTarget.value?.widget.id;
  mutatePage((p) => {
    const w = p.widgets.find((item) => item.id === id);
    if (w) {
      w.settings = settings;
      w.variant = variant;
    }
  });
}

function addPage() {
  if (!draft.value || draft.value.pages.length >= 8) return;
  let n = draft.value.pages.length + 1;
  while (draft.value.pages.some((p) => p.id === `page-${n}`)) n += 1;
  draft.value.pages.push({
    id: `page-${n}`,
    name: `Page ${draft.value.pages.length + 1}`,
    options: { gap: "cozy", backdrop: "glow" },
    widgets: [],
  });
  pageId.value = `page-${n}`;
  panel.value = "page";
}
function deletePage() {
  if (!draft.value || draft.value.pages.length < 2) return;
  draft.value.pages = draft.value.pages.filter((p) => p.id !== pageId.value);
  pageId.value = draft.value.pages[0].id;
  panel.value = null;
}
function renamePage(name: string) {
  mutatePage((p) => (p.name = name));
}
function setGap(gap: PageGap) {
  mutatePage((p) => (p.options.gap = gap));
}
function setBackdrop(backdrop: PageBackdrop) {
  mutatePage((p) => (p.options.backdrop = backdrop));
}

function onKey(e: KeyboardEvent) {
  if (e.key === "Escape" && panel.value) panel.value = null;
}

// Edits are kept until Done, so leaving with some should not lose them silently,
// and a change made from a widget's own controls is saved as the page is left.
const dirty = computed(
  () =>
    draft.value !== null &&
    JSON.stringify(draft.value) !== JSON.stringify(savedLayout.value),
);
function warnLeaving(e: BeforeUnloadEvent) {
  if (dirty.value) e.preventDefault();
}
function onHide() {
  if (document.visibilityState === "hidden") flushPending();
}
onBeforeRouteLeave(
  () =>
    !dirty.value ||
    window.confirm(
      "You have changes to Home that are not saved. Leave anyway?",
    ),
);
onMounted(() => {
  window.addEventListener("keydown", onKey);
  window.addEventListener("beforeunload", warnLeaving);
  document.addEventListener("visibilitychange", onHide);
});
onBeforeUnmount(() => {
  window.removeEventListener("keydown", onKey);
  window.removeEventListener("beforeunload", warnLeaving);
  document.removeEventListener("visibilitychange", onHide);
  flushPending();
});

function retrySave() {
  void saveLayout(savedLayout.value);
}

// one-time welcome, shown on a first visit
const WELCOME_KEY = "seenWelcomeTour";
const showWelcome = ref(localStorage.getItem(WELCOME_KEY) !== "true");
function dismissWelcome() {
  showWelcome.value = false;
  try {
    localStorage.setItem(WELCOME_KEY, "true");
  } catch {
    // it just shows again next time
  }
}
const TOUR = [
  {
    title: "Make Home yours",
    body: "Press Customize to add, move and resize widgets, or to set up extra pages.",
  },
  {
    title: "Find anything fast",
    body: "Press Ctrl or Cmd and K anywhere to jump to a title, a collection or a setting.",
  },
  {
    title: "Press ? any time",
    body: "It lists every keyboard shortcut.",
  },
];
</script>

<template>
  <main
    class="home"
    :class="{
      glow: page.options.backdrop === 'glow',
      editing,
      shifted: panel !== null && panel !== 'add' && editing,
    }"
  >
    <AccountChip fixed />

    <div v-if="showWelcome" class="tour-backdrop" @click.self="dismissWelcome">
      <div
        class="tour-dialog"
        role="dialog"
        aria-modal="true"
        aria-label="Welcome"
      >
        <h2>Welcome to your library</h2>
        <p class="tour-intro">
          A quick look at what is here. This will not show again.
        </p>
        <div class="tour-steps">
          <div v-for="step in TOUR" :key="step.title">
            <h3>{{ step.title }}</h3>
            <p>{{ step.body }}</p>
          </div>
        </div>
        <button type="button" class="solid" @click="dismissWelcome">
          Let's go
        </button>
      </div>
    </div>

    <div class="content">
      <!-- page tabs and the Customize button: on the greeting's line when there is
           one page, so they take no space of their own and nothing moves when you
           start editing -->
      <div class="top" :class="{ inline: layout.pages.length > 1 }">
        <nav
          v-if="layout.pages.length > 1 || editing"
          class="tabs"
          aria-label="Home pages"
        >
          <button
            v-for="p in layout.pages"
            :key="p.id"
            type="button"
            class="tab"
            :class="{ on: p.id === page.id }"
            @click="pageId = p.id"
          >
            {{ p.name }}
          </button>
          <button
            v-if="editing && layout.pages.length < 8"
            type="button"
            class="tab add"
            @click="addPage"
          >
            + Page
          </button>
        </nav>
        <button
          v-if="!editing"
          type="button"
          class="ghost customize"
          @click="startEditing"
        >
          Customize
        </button>
      </div>

      <!-- the editing tools float at the bottom, so they are always in reach and
           never push the page around -->
      <div
        v-if="editing"
        class="toolbar"
        :class="{ aside: panel !== null && panel !== 'add' }"
        role="toolbar"
        aria-label="Edit Home"
      >
        <span v-if="saveError" class="err">{{ saveError }}</span>
        <span v-else-if="dirty" class="unsaved">Unsaved changes</span>
        <button type="button" class="ghost" @click="panel = 'add'">
          Add widget
        </button>
        <button
          type="button"
          class="ghost"
          title="Close the gaps between widgets"
          @click="tidy"
        >
          Tidy up
        </button>
        <button type="button" class="ghost" @click="panel = 'page'">
          Page options
        </button>
        <button
          type="button"
          class="ghost"
          :class="{ warn: confirmReset }"
          @click="reset"
        >
          {{ confirmReset ? "Click again to reset" : "Reset" }}
        </button>
        <button type="button" class="ghost" @click="cancel">Cancel</button>
        <button type="button" class="solid" :disabled="saving" @click="done">
          {{ saving ? "Saving" : "Done" }}
        </button>
      </div>

      <p v-if="saveError && !editing" class="notice" role="alert">
        Your last change to Home was not saved: {{ saveError }}
        <button type="button" @click="retrySave">Try again</button>
      </p>

      <HomeGrid
        :page="page"
        :editing="editing"
        @update:widgets="setWidgets"
        @settings="(id) => (panel = { settings: id })"
        @remove="removeWidget"
      />

      <p v-if="!page.widgets.length" class="blank">
        <strong>This page is empty</strong>
        <span v-if="editing">Press Add widget to put something on it.</span>
        <span v-else>Press Customize, then Add widget.</span>
      </p>
    </div>

    <aside
      v-if="panel !== null && editing"
      class="side"
      :class="{ wide: panel === 'add' }"
    >
      <WidgetDrawer
        v-if="panel === 'add'"
        @add="addFromGallery"
        @close="panel = null"
      />
      <WidgetSettings
        v-else-if="settingsTarget"
        :key="settingsTarget.widget.id"
        :def="settingsTarget.def"
        :settings="settingsTarget.widget.settings"
        :variant="settingsTarget.widget.variant"
        :w="settingsTarget.widget.w"
        :h="settingsTarget.widget.h"
        @change="changeWidget"
        @resize="resizeWidget"
        @remove="removeWidget(settingsTarget.widget.id)"
        @close="panel = null"
      />
      <div v-else-if="panel === 'page'" class="pageopts">
        <header>
          <h3>Page options</h3>
          <button
            type="button"
            class="x"
            aria-label="Close"
            @click="panel = null"
          >
            &#10005;
          </button>
        </header>
        <div class="fields">
          <label class="field">
            <span class="label">Name</span>
            <input
              type="text"
              maxlength="40"
              :value="page.name"
              @input="
                renamePage(($event.target as HTMLInputElement).value || 'Home')
              "
            />
          </label>
          <label class="field">
            <span class="label">Space between widgets</span>
            <select
              :value="page.options.gap"
              @change="
                setGap(($event.target as HTMLSelectElement).value as PageGap)
              "
            >
              <option value="tight">Tight</option>
              <option value="cozy">Cozy</option>
              <option value="roomy">Roomy</option>
            </select>
          </label>
          <label class="field">
            <span class="label">Background</span>
            <select
              :value="page.options.backdrop"
              @change="
                setBackdrop(
                  ($event.target as HTMLSelectElement).value as PageBackdrop,
                )
              "
            >
              <option value="glow">Soft glow</option>
              <option value="none">Plain</option>
            </select>
          </label>
          <button
            v-if="layout.pages.length > 1"
            type="button"
            class="ghost danger"
            @click="deletePage"
          >
            Delete this page
          </button>
        </div>
      </div>
    </aside>
  </main>
</template>

<style scoped>
.home {
  position: relative;
  min-height: 100vh;
  padding: 76px var(--ui-edge-right) 40px var(--ui-edge-left);
  background: var(--ui-bg);
  color: var(--ui-text);
  font-family: system-ui, sans-serif;
  transition: padding-right 0.2s;
}
.home.editing {
  /* room under the last widget for the floating tools */
  padding-bottom: 120px;
}
.home.glow::before {
  content: "";
  position: fixed;
  top: -120px;
  left: -120px;
  width: 620px;
  height: 620px;
  background: radial-gradient(
    circle,
    color-mix(in srgb, var(--ui-accent) 9%, transparent) 0%,
    transparent 70%
  );
  pointer-events: none;
}
@media (min-width: 1200px) {
  .home.shifted {
    padding-right: 504px;
  }
}
.content {
  position: relative;
}
.top {
  position: absolute;
  top: 0;
  right: 0;
  z-index: 25;
  display: flex;
  align-items: center;
  gap: 10px;
}
.top.inline {
  position: static;
  justify-content: space-between;
  margin-bottom: 12px;
}
.unsaved {
  color: var(--ui-accent);
  font-size: 0.8rem;
  font-weight: 600;
}
.toolbar {
  position: fixed;
  bottom: 18px;
  left: 50%;
  z-index: 60;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
  max-width: calc(100vw - 24px);
  padding: 8px 10px;
  border: 1px solid var(--ui-border-strong);
  border-radius: 14px;
  background: color-mix(in srgb, var(--ui-popover) 94%, transparent);
  backdrop-filter: blur(10px);
  box-shadow: 0 16px 40px
    color-mix(in srgb, var(--ui-scrim-base) 55%, transparent);
  transform: translateX(-50%);
}
@media (min-width: 1200px) {
  /* centred on the part of the page the side panel leaves free */
  .toolbar.aside {
    left: calc((100% - 480px) / 2);
  }
}
.notice {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 0 0 14px;
  padding: 8px 12px;
  border: 1px solid color-mix(in srgb, var(--ui-danger) 50%, transparent);
  border-radius: var(--ui-radius-control);
  background: color-mix(in srgb, var(--ui-danger) 12%, transparent);
  color: var(--ui-error-text);
  font-size: 0.84rem;
}
.notice button {
  padding: 4px 10px;
  border: 1px solid currentColor;
  border-radius: 6px;
  background: transparent;
  color: inherit;
  font: inherit;
  cursor: pointer;
}
.tabs {
  display: flex;
  gap: 4px;
  padding: 4px;
  border-radius: 10px;
  background: var(--ui-surface);
}
.tab {
  padding: 7px 16px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: var(--ui-dim);
  font: inherit;
  font-size: 0.84rem;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}
.tab:hover {
  color: var(--ui-text);
}
.tab.on {
  background: var(--ui-accent);
  color: var(--ui-on-accent);
}
.tab.add {
  color: var(--ui-faint);
}
.ghost,
.solid {
  height: 36px;
  padding: 0 14px;
  border-radius: var(--ui-radius-control);
  font: inherit;
  font-size: 0.84rem;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}
.ghost {
  border: 1px solid var(--ui-border);
  background: transparent;
  color: var(--ui-dim);
}
.ghost:hover {
  border-color: var(--ui-accent-line);
  color: var(--ui-text);
}
.ghost.warn,
.ghost.danger {
  border-color: color-mix(in srgb, var(--ui-danger) 60%, transparent);
  color: var(--ui-error-text);
}
.solid {
  border: 1px solid var(--ui-accent);
  background: var(--ui-accent);
  color: var(--ui-on-accent);
}
.solid:hover:not(:disabled) {
  filter: brightness(1.08);
}
.solid:disabled {
  opacity: 0.6;
  cursor: default;
}
.customize {
  opacity: 0.9;
}
.err {
  color: var(--ui-error-text);
  font-size: 0.8rem;
}
.blank {
  display: grid;
  place-content: center;
  gap: 4px;
  min-height: 220px;
  margin: 0;
  border: 1px dashed var(--ui-border);
  border-radius: var(--ui-radius-card);
  color: var(--ui-dim);
  font-size: 0.88rem;
  text-align: center;
}
.blank strong {
  color: var(--ui-text);
  font-size: 1rem;
}
.side {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  z-index: var(--ui-z-drawer);
  width: min(480px, 100vw);
  background: var(--ui-popover);
  border-left: 1px solid var(--ui-border);
  box-shadow: -18px 0 40px
    color-mix(in srgb, var(--ui-scrim-base) 35%, transparent);
}
.side.wide {
  width: min(820px, 100vw);
}
.pageopts header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 20px 14px;
  border-bottom: 1px solid var(--ui-border-soft);
}
.pageopts h3 {
  margin: 0;
  font-size: 1.05rem;
}
.x {
  width: 30px;
  height: 30px;
  border: 0;
  border-radius: 8px;
  background: none;
  color: var(--ui-dim);
  cursor: pointer;
}
.x:hover {
  background: var(--ui-surface-2);
  color: var(--ui-text);
}
.fields {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 18px 20px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.label {
  color: var(--ui-dim);
  font-size: 0.74rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.field input,
.field select {
  padding: 9px 11px;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-control);
  background: var(--ui-bg-2);
  color: var(--ui-text);
  font: inherit;
  font-size: 0.88rem;
}
.field input:focus,
.field select:focus {
  outline: none;
  border-color: var(--ui-accent);
}
.tour-backdrop {
  position: fixed;
  inset: 0;
  z-index: var(--ui-z-modal);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background: color-mix(in srgb, var(--ui-scrim-base) 65%, transparent);
}
.tour-dialog {
  width: 100%;
  max-width: 460px;
  max-height: 85vh;
  overflow-y: auto;
  padding: 28px;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-dialog);
  background: var(--ui-surface);
  box-sizing: border-box;
}
.tour-dialog h2 {
  margin: 0 0 4px;
  font-size: 1.3rem;
}
.tour-intro {
  margin: 0 0 20px;
  color: var(--ui-dim);
  font-size: 0.85rem;
}
.tour-steps {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-bottom: 22px;
}
.tour-steps h3 {
  margin: 0 0 2px;
  font-size: 0.95rem;
  color: var(--ui-accent);
}
.tour-steps p {
  margin: 0;
  color: var(--ui-dim);
  font-size: 0.86rem;
  line-height: 1.45;
}
@media (max-width: 760px) {
  .home {
    padding: 76px 16px 32px;
  }
  .customize {
    display: none;
  }
}
</style>
