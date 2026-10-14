<script setup lang="ts">
// The dialog around the Movie, TV and Anime edit forms. It matches the game form:
// a header with the poster and title, tabs, a body that scrolls inside one fixed
// height, and a footer with Delete, Look up metadata, Cancel and Save. Each form
// supplies its fields for the active tab (the default slot, which is given the tab)
// and its lookup panel (the `lookup` slot).
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = defineProps<{
  // "Movie", "TV show" or "Anime", for the kicker and the Add button
  noun: string;
  editing: boolean;
  saving: boolean;
  deleting: boolean;
  error: string | null;
  title: string;
  subtitle: string;
  poster: string | null;
  tabs: readonly string[];
}>();

const emit = defineEmits<{
  closed: [];
  save: [];
  delete: [];
}>();

const activeTab = defineModel<string>("tab", { required: true });
const lookupOpen = ref(false);
const tabsEl = ref<HTMLElement | null>(null);

// keep the current tab in view when the tab row scrolls (phones). Only the row is
// scrolled: scrollIntoView would also move the dialog.
watch(activeTab, () =>
  nextTick(() => {
    const row = tabsEl.value;
    const tab = row?.querySelector<HTMLElement>(".mf-tab.active");
    if (!row || !tab) return;
    if (tab.offsetLeft < row.scrollLeft) row.scrollLeft = tab.offsetLeft - 8;
    else if (
      tab.offsetLeft + tab.offsetWidth >
      row.scrollLeft + row.clientWidth
    )
      row.scrollLeft = tab.offsetLeft + tab.offsetWidth - row.clientWidth + 8;
  }),
);

function openArtwork() {
  if (props.tabs.includes("Artwork")) activeTab.value = "Artwork";
}

function onKey(e: KeyboardEvent) {
  if (e.key === "Escape" && !lookupOpen.value) emit("closed");
}
onMounted(() => window.addEventListener("keydown", onKey));
onBeforeUnmount(() => window.removeEventListener("keydown", onKey));
</script>

<template>
  <div class="mf-overlay" @click.self="emit('closed')">
    <div class="mf-card" role="dialog" aria-modal="true" :aria-label="noun">
      <header class="mf-header">
        <button
          type="button"
          class="mf-poster"
          :style="poster ? { backgroundImage: `url(${poster})` } : {}"
          aria-label="Open artwork"
          title="Artwork"
          @click="openArtwork"
        ></button>
        <div class="mf-titles">
          <div class="mf-kicker">{{ editing ? "Edit" : "Add" }} {{ noun }}</div>
          <h3>{{ title.trim() || `Untitled ${noun.toLowerCase()}` }}</h3>
          <p v-if="subtitle" class="sub">{{ subtitle }}</p>
        </div>
        <button
          type="button"
          class="mf-close"
          aria-label="Close"
          @click="emit('closed')"
        >
          &#10005;
        </button>
      </header>

      <nav ref="tabsEl" class="mf-tabs" :aria-label="`${noun} details`">
        <button
          v-for="tab in tabs"
          :key="tab"
          type="button"
          class="mf-tab"
          :class="{ active: activeTab === tab }"
          @click="activeTab = tab"
        >
          {{ tab }}
        </button>
      </nav>

      <div class="mf-body">
        <slot :tab="activeTab" />
        <p v-if="error" class="mf-error">{{ error }}</p>
      </div>

      <footer class="mf-footer">
        <button
          v-if="editing"
          type="button"
          class="mf-btn danger"
          :disabled="deleting || saving"
          @click="emit('delete')"
        >
          {{ deleting ? "Deleting…" : "Delete" }}
        </button>
        <button type="button" class="mf-btn" @click="lookupOpen = true">
          Look up metadata
        </button>
        <span class="mf-spacer"></span>
        <button type="button" class="mf-btn" @click="emit('closed')">
          Cancel
        </button>
        <button
          type="button"
          class="mf-btn solid"
          :disabled="saving || deleting"
          @click="emit('save')"
        >
          {{ saving ? "Saving…" : editing ? "Save changes" : `Add ${noun}` }}
        </button>
      </footer>

      <slot
        v-if="lookupOpen"
        name="lookup"
        :close="() => (lookupOpen = false)"
      />
    </div>
  </div>
</template>

<style scoped>
.mf-overlay {
  --surface: var(--ui-surface);
  --surface-2: var(--ui-surface-2);
  --border: var(--ui-border);
  --border-soft: var(--ui-border-soft);
  --accent: var(--ui-accent);
  --accent-soft: var(--ui-accent-soft);
  --accent-line: var(--ui-accent-line);
  --danger: var(--ui-danger-muted);
  --text: var(--ui-text);
  --text-dim: var(--ui-dim);
  --text-faint: #666;
  position: fixed;
  inset: 0;
  z-index: var(--ui-z-modal, 100);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background: color-mix(in srgb, var(--ui-scrim-base) 70%, transparent);
  color: var(--text);
}
.mf-overlay * {
  box-sizing: border-box;
}
.mf-card {
  position: relative;
  display: flex;
  flex-direction: column;
  width: min(880px, 100%);
  /* one height for every tab, so the dialog does not jump when the tab changes */
  height: min(720px, 92vh);
  overflow: hidden;
  background: var(--ui-popover, var(--ui-popover));
  border: 1px solid var(--border);
  border-radius: var(--ui-radius-dialog, 14px);
}
.mf-header {
  flex: none;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  background: linear-gradient(160deg, var(--accent-soft), transparent 70%);
  border-bottom: 1px solid var(--border-soft);
}
.mf-poster {
  flex: none;
  width: 64px;
  height: 90px;
  padding: 0;
  border: 1px solid var(--border);
  border-radius: 8px;
  background-color: var(--surface);
  background-size: cover;
  background-position: center;
  cursor: pointer;
}
.mf-poster:hover {
  border-color: var(--accent-line);
}
.mf-titles {
  flex: 1;
  min-width: 0;
}
.mf-kicker {
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--accent);
}
.mf-titles h3 {
  margin: 2px 0 0;
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.mf-titles .sub {
  margin: 2px 0 0;
  font-size: 0.8rem;
  color: var(--text-faint);
}
.mf-close {
  flex: none;
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: 8px;
  background: none;
  color: var(--text-dim);
  font-size: 1rem;
  cursor: pointer;
}
.mf-close:hover {
  background: var(--surface-2);
  color: var(--text);
}
.mf-tabs {
  flex: none;
  display: flex;
  gap: 4px;
  align-self: flex-start;
  max-width: calc(100% - 40px);
  margin: 12px 20px 0;
  padding: 5px;
  /* the same bar as the tabs on the game and media pages */
  background: var(--surface);
  border-radius: 10px;
  overflow-x: auto;
  scrollbar-width: none;
}
.mf-tabs::-webkit-scrollbar {
  display: none;
}
.mf-tab {
  flex: none;
  padding: 8px 16px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: var(--text-dim);
  font: inherit;
  font-size: 0.84rem;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}
.mf-tab:hover {
  color: var(--text);
}
.mf-tab.active {
  background: var(--accent);
  color: var(--ui-on-accent);
}
.mf-tab:focus-visible,
.mf-btn:focus-visible,
.mf-poster:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: -2px;
}
.mf-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 16px 20px 20px;
}
.mf-error {
  margin: 14px 0 0;
  padding: 8px 12px;
  border: 1px solid color-mix(in srgb, var(--ui-danger-muted) 40%, transparent);
  border-radius: 8px;
  background: color-mix(in srgb, var(--ui-danger-muted) 12%, transparent);
  color: var(--danger);
  font-size: 0.82rem;
}
.mf-footer {
  flex: none;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  border-top: 1px solid var(--border-soft);
  background: var(--surface);
}
.mf-spacer {
  flex: 1;
}
.mf-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 36px;
  padding: 0 14px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: transparent;
  color: var(--text-dim);
  font: inherit;
  font-size: 0.84rem;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}
.mf-btn:hover {
  color: var(--text);
  border-color: var(--accent-line);
}
.mf-btn.solid {
  background: var(--accent);
  border-color: var(--accent);
  color: var(--ui-on-accent);
}
.mf-btn.solid:hover {
  filter: brightness(1.08);
}
.mf-btn:disabled {
  opacity: 0.6;
  cursor: default;
}
.mf-btn.danger {
  color: var(--danger);
}
@media (max-width: 720px) {
  .mf-footer {
    flex-wrap: wrap;
  }
}
</style>
