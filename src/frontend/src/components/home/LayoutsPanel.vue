<script setup lang="ts">
// Customize mode's Layouts panel: start a page from a ready-made one, go back to
// an earlier version of Home, or keep a copy of the layout as a file. Nothing
// here is saved until Done, like every other change in Customize.
import { computed, onMounted, ref } from "vue";
import { normaliseLayout } from "../../home/layout";
import type { HomeLayout, HomePage } from "../../home/layout";
import { STARTER_PAGES, starterPage } from "../../home/starters";
import type { StarterPage } from "../../home/starters";
import { fetchHomeLayoutHistory } from "../../services/preferences";
import type { HomeLayoutVersion } from "../../services/preferences";

const MAX_PAGES = 8;

const props = defineProps<{ layout: HomeLayout }>();
const emit = defineEmits<{
  (e: "add-page", page: HomePage): void;
  (e: "replace", layout: HomeLayout, what: string): void;
  (e: "close"): void;
}>();

const full = computed(() => props.layout.pages.length >= MAX_PAGES);
function addStarter(starter: StarterPage) {
  if (full.value) return;
  emit("add-page", starterPage(starter, props.layout));
}

const versions = ref<HomeLayoutVersion[]>([]);
const loadingVersions = ref(true);
const versionsError = ref<string | null>(null);
onMounted(async () => {
  try {
    versions.value = await fetchHomeLayoutHistory();
  } catch (e) {
    versionsError.value =
      e instanceof Error ? e.message : "Could not load earlier layouts.";
  } finally {
    loadingVersions.value = false;
  }
});

function when(seconds: number): string {
  return new Date(seconds * 1000).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}
function summary(raw: unknown): string {
  const layout = normaliseLayout(raw);
  const widgets = layout.pages.reduce((n, p) => n + p.widgets.length, 0);
  const pages = layout.pages.length;
  return `${pages} page${pages === 1 ? "" : "s"}, ${widgets} widget${widgets === 1 ? "" : "s"}`;
}
function useVersion(version: HomeLayoutVersion) {
  emit(
    "replace",
    normaliseLayout(version.layout),
    `the layout from before ${when(version.replaced_at)}`,
  );
}

function download() {
  const blob = new Blob([JSON.stringify(props.layout, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `home-layout-${new Date().toISOString().slice(0, 10)}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

const fileError = ref<string | null>(null);
async function loadFile(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = "";
  fileError.value = null;
  if (!file) return;
  try {
    const raw = JSON.parse(await file.text()) as { pages?: unknown };
    // normaliseLayout falls back to the default for anything it cannot read,
    // which would quietly replace Home; say so instead
    if (!Array.isArray(raw?.pages) || !raw.pages.length)
      throw new Error("not a layout");
    if (raw.pages.length > MAX_PAGES)
      throw new Error(`it has more than ${MAX_PAGES} pages`);
    emit("replace", normaliseLayout(raw), `the layout in ${file.name}`);
  } catch (e) {
    const why =
      e instanceof SyntaxError
        ? "not a layout"
        : String(e instanceof Error ? e.message : e);
    fileError.value = `That file could not be used: ${why}.`;
  }
}
</script>

<template>
  <div class="pageopts">
    <header>
      <h3>Layouts</h3>
      <button type="button" class="x" aria-label="Close" @click="emit('close')">
        &#10005;
      </button>
    </header>
    <div class="fields">
      <section class="field">
        <span class="label">Add a ready-made page</span>
        <p v-if="full" class="hint">
          Home holds {{ MAX_PAGES }} pages at most.
        </p>
        <button
          v-for="starter in STARTER_PAGES"
          :key="starter.id"
          type="button"
          class="choice"
          :disabled="full"
          @click="addStarter(starter)"
        >
          <strong>{{ starter.name }}</strong>
          <span>{{ starter.description }}</span>
        </button>
      </section>

      <section class="field">
        <span class="label">Earlier versions</span>
        <p v-if="loadingVersions" class="hint">Loading…</p>
        <p v-else-if="versionsError" class="err">{{ versionsError }}</p>
        <p v-else-if="!versions.length" class="hint">
          Each time you save Home, the layout it replaces is kept here, up to
          15.
        </p>
        <ul v-else class="versions">
          <li v-for="v in versions" :key="v.replaced_at">
            <span>
              <strong>Before {{ when(v.replaced_at) }}</strong>
              <span class="hint">{{ summary(v.layout) }}</span>
            </span>
            <button type="button" class="ghost" @click="useVersion(v)">
              Use this
            </button>
          </li>
        </ul>
      </section>

      <section class="field">
        <span class="label">Keep a copy</span>
        <p class="hint">
          Download this layout as a file, or load one back. A loaded layout
          replaces what is on screen until you press Done or Cancel.
        </p>
        <div class="row">
          <button type="button" class="ghost" @click="download">
            Download layout
          </button>
          <label class="ghost upload">
            Load from file
            <input
              type="file"
              accept="application/json,.json"
              @change="loadFile"
            />
          </label>
        </div>
        <p v-if="fileError" class="err" role="alert">{{ fileError }}</p>
      </section>
    </div>
  </div>
</template>

<style scoped>
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
.pageopts {
  height: 100%;
  overflow-y: auto;
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
.hint {
  margin: 0;
  color: var(--ui-faint);
  font-size: 0.8rem;
}
.err {
  margin: 0;
  color: var(--ui-error-text);
  font-size: 0.8rem;
}
.ghost {
  height: 36px;
  padding: 0 14px;
  border-radius: var(--ui-radius-control);
  font: inherit;
  font-size: 0.84rem;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  border: 1px solid var(--ui-border);
  background: transparent;
  color: var(--ui-dim);
}
.ghost:hover {
  border-color: var(--ui-accent-line);
  color: var(--ui-text);
}
.choice {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 10px 12px;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-row);
  background: var(--ui-bg-2);
  color: var(--ui-text);
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.choice span {
  color: var(--ui-dim);
  font-size: 0.8rem;
}
.choice:hover:not(:disabled) {
  border-color: var(--ui-accent-line);
}
.choice:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.versions {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.versions li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 10px;
  border: 1px solid var(--ui-border-soft);
  border-radius: var(--ui-radius-row);
}
.versions li > span {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 0.86rem;
}
.row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.upload {
  display: inline-flex;
  align-items: center;
}
.upload input {
  display: none;
}
</style>
