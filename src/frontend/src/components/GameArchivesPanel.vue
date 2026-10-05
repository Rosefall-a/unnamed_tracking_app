<script setup lang="ts" generic="T extends GameArchiveData">
// The same gallery shell as the media tabs, for named, versioned archives
// (Saves and Worlds). The page owns the cards; this owns everything around
// them: the title and count, search and sort, the big Add card, dropping files
// anywhere over the panel, and the Recently deleted list. Dropping a file
// starts a new archive; adding a version to an existing one stays on its card.
import { ref, computed, watch, onMounted, onBeforeUnmount } from "vue";
import type { GameArchiveData, TrashedArchive } from "../services/gameArchives";

const props = defineProps<{
  title: string;
  plural: string;
  singular: string;
  hint: string;
  archives: T[];
  trash: TrashedArchive[];
  loaded: boolean;
  uploading: boolean;
  error: string | null;
  // listen for drops on this panel only, for a page that holds two
  scoped?: boolean;
}>();

const emit = defineEmits<{
  files: [files: File[]];
  "bulk-delete": [archives: T[]];
  restore: [archive: TrashedArchive];
  problem: [message: string];
}>();

defineSlots<{
  card(props: {
    archive: T;
    selecting: boolean;
    selected: boolean;
    toggle: () => void;
  }): unknown;
  after(): unknown;
}>();

const picker = ref<HTMLInputElement | null>(null);
const rootEl = ref<HTMLElement | null>(null);
function openPicker() {
  picker.value?.click();
}
function onPicked(e: Event) {
  const input = e.target as HTMLInputElement;
  const files = Array.from(input.files ?? []);
  input.value = "";
  if (files.length) emit("files", files);
}

// ---- search and sort ----
const query = ref("");
const sort = ref<"updated" | "oldest" | "name">("updated");
const visible = computed(() => {
  let list = [...props.archives];
  const q = query.value.trim().toLowerCase();
  if (q)
    list = list.filter(
      (a) =>
        a.name.toLowerCase().includes(q) ||
        (a.note ?? "").toLowerCase().includes(q) ||
        (a.tags ?? []).some((t) => t.toLowerCase().includes(q)),
    );
  if (sort.value === "name") list.sort((a, b) => a.name.localeCompare(b.name));
  else
    list.sort((a, b) =>
      sort.value === "oldest"
        ? a.updated_at - b.updated_at
        : b.updated_at - a.updated_at,
    );
  return list;
});

// ---- select several, then delete them together ----
const selecting = ref(false);
const picked = ref<Set<string>>(new Set());
const pickedArchives = computed(() =>
  props.archives.filter((a) => picked.value.has(a.id)),
);
function toggleSelecting() {
  selecting.value = !selecting.value;
  picked.value = new Set();
}
function toggle(id: string) {
  const next = new Set(picked.value);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  picked.value = next;
}
function selectAll() {
  picked.value =
    picked.value.size === visible.value.length
      ? new Set()
      : new Set(visible.value.map((a) => a.id));
}
function bulkDelete() {
  if (!pickedArchives.value.length) return;
  emit("bulk-delete", pickedArchives.value);
  picked.value = new Set();
}
watch(
  () => props.archives.length,
  (n) => {
    if (!n) selecting.value = false;
    picked.value = new Set(
      [...picked.value].filter((id) => props.archives.some((a) => a.id === id)),
    );
  },
);

// ---- drop ----
const dragging = ref(false);
let depth = 0;
function hasFiles(e: DragEvent): boolean {
  return Array.from(e.dataTransfer?.types ?? []).includes("Files");
}
function onDragEnter(e: DragEvent) {
  if (!hasFiles(e)) return;
  e.preventDefault();
  depth++;
  dragging.value = true;
}
function onDragOver(e: DragEvent) {
  if (hasFiles(e)) e.preventDefault();
}
function onDragLeave(e: DragEvent) {
  if (!hasFiles(e)) return;
  depth = Math.max(0, depth - 1);
  if (depth === 0) dragging.value = false;
}
function onDrop(e: DragEvent) {
  if (!hasFiles(e)) return;
  e.preventDefault();
  depth = 0;
  dragging.value = false;
  const folder = Array.from(e.dataTransfer?.items ?? []).some(
    (i) =>
      (
        i as DataTransferItem & {
          webkitGetAsEntry?: () => { isDirectory?: boolean } | null;
        }
      ).webkitGetAsEntry?.()?.isDirectory,
  );
  if (folder) {
    emit("problem", "That is a folder. Zip it first, then drop the .zip.");
    return;
  }
  const files = Array.from(e.dataTransfer?.files ?? []);
  if (files.length) emit("files", files);
}
let target: HTMLElement | Window = window;
onMounted(() => {
  target = props.scoped && rootEl.value ? rootEl.value : window;
  const t = target as HTMLElement;
  t.addEventListener("dragenter", onDragEnter as (e: Event) => void);
  t.addEventListener("dragover", onDragOver as (e: Event) => void);
  t.addEventListener("dragleave", onDragLeave as (e: Event) => void);
  t.addEventListener("drop", onDrop as (e: Event) => void);
});
onBeforeUnmount(() => {
  const t = target as HTMLElement;
  t.removeEventListener("dragenter", onDragEnter as (e: Event) => void);
  t.removeEventListener("dragover", onDragOver as (e: Event) => void);
  t.removeEventListener("dragleave", onDragLeave as (e: Event) => void);
  t.removeEventListener("drop", onDrop as (e: Event) => void);
});

const showTrash = ref(false);
function daysLeft(purgeAt: number): number {
  return Math.max(0, Math.ceil((purgeAt * 1000 - Date.now()) / 86_400_000));
}
</script>

<template>
  <div ref="rootEl" class="ga">
    <div class="ga-header">
      <div class="ga-title">
        <h2>{{ title }}</h2>
        <span class="ga-count">{{ archives.length }}</span>
      </div>
      <div class="ga-tools">
        <input
          v-if="archives.length"
          v-model="query"
          type="search"
          class="ui-field ga-search"
          :placeholder="`Search ${plural}`"
          :aria-label="`Search ${plural}`"
        />
        <select
          v-if="archives.length > 1"
          v-model="sort"
          class="ui-field ga-select"
          aria-label="Sort"
        >
          <option value="updated">Recently updated</option>
          <option value="oldest">Oldest first</option>
          <option value="name">Name</option>
        </select>
        <button
          v-if="archives.length"
          type="button"
          class="ui-btn ui-btn-ghost"
          :class="{ on: selecting }"
          @click="toggleSelecting"
        >
          {{ selecting ? "Done" : "Select" }}
        </button>
        <button
          v-if="trash.length"
          type="button"
          class="ui-btn ui-btn-ghost"
          :class="{ on: showTrash }"
          @click="showTrash = !showTrash"
        >
          Deleted ({{ trash.length }})
        </button>
      </div>
      <input
        ref="picker"
        type="file"
        multiple
        class="ga-input"
        @change="onPicked"
      />
    </div>

    <div v-if="selecting" class="ga-bulk">
      <span class="ga-bulk-count"
        >{{ picked.size }} of {{ visible.length }} selected</span
      >
      <button
        type="button"
        class="ui-btn ui-btn-ghost ui-btn-sm"
        @click="selectAll"
      >
        {{ picked.size === visible.length ? "Clear" : "Select all" }}
      </button>
      <span class="ga-bulk-sep"></span>
      <button
        type="button"
        class="ui-btn ui-btn-danger-soft ui-btn-sm"
        :disabled="!picked.size"
        @click="bulkDelete"
      >
        Delete
      </button>
    </div>

    <div v-if="error" class="ui-error-box ga-error">
      <span>{{ error }}</span>
      <button type="button" aria-label="Dismiss" @click="emit('problem', '')">
        ✕
      </button>
    </div>

    <ul v-if="showTrash && trash.length" class="ga-trash">
      <li v-for="t in trash" :key="t.id">
        <span class="ga-trash-name">{{ t.name }}</span>
        <span class="ga-trash-meta">purges in {{ daysLeft(t.purge_at) }}d</span>
        <button
          type="button"
          class="ui-btn ui-btn-ghost ui-btn-sm"
          @click="emit('restore', t)"
        >
          Restore
        </button>
      </li>
    </ul>

    <div class="ga-body">
      <div v-if="!loaded" class="ga-grid" aria-busy="true" aria-label="Loading">
        <div v-for="n in 3" :key="n" class="ga-skel"></div>
      </div>

      <button
        v-else-if="!archives.length"
        type="button"
        class="ga-empty"
        :disabled="uploading"
        @click="openPicker"
      >
        <span class="ga-plus">{{ uploading ? "…" : "+" }}</span>
        <strong>{{ uploading ? "Uploading" : `Add a ${singular}` }}</strong>
        <span>{{ hint }}</span>
      </button>

      <template v-else>
        <div class="ga-grid">
          <button
            type="button"
            class="ga-add"
            :disabled="uploading"
            @click="openPicker"
          >
            <span class="ga-add-thumb">
              <span v-if="uploading" class="ga-spin"></span>
              <span v-else class="ga-plus">+</span>
            </span>
            <span class="ga-add-body">
              <strong>{{
                uploading ? "Uploading" : `Add a ${singular}`
              }}</strong>
              <span class="ga-add-sub">Drop, paste, or click to browse</span>
            </span>
          </button>
          <slot
            v-for="a in visible"
            :key="a.id"
            name="card"
            :archive="a"
            :selecting="selecting"
            :selected="picked.has(a.id)"
            :toggle="() => toggle(a.id)"
          />
        </div>
        <div v-if="!visible.length" class="ga-none">
          <span>Nothing matches.</span>
          <button
            type="button"
            class="ui-btn ui-btn-ghost ui-btn-sm"
            @click="query = ''"
          >
            Clear search
          </button>
        </div>
      </template>

      <Transition name="fade">
        <div v-if="dragging" class="ga-drop" aria-hidden="true">
          <span class="ga-plus">+</span>
          <strong>Drop to add a {{ singular }}</strong>
        </div>
      </Transition>
    </div>

    <slot name="after" />
  </div>
</template>

<style scoped>
.ga {
  position: relative;
}
.ga-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 16px;
}
.ga-title {
  display: flex;
  align-items: center;
  gap: 10px;
}
.ga-title h2 {
  margin: 0;
  font-size: 1.1rem;
}
.ga-count {
  background: rgba(214, 138, 52, 0.16);
  color: #d68a34;
  font-size: 0.72rem;
  font-weight: 700;
  border-radius: 999px;
  padding: 2px 9px;
  font-variant-numeric: tabular-nums;
}
.ga-tools {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
.ga-input {
  display: none;
}
.ga-search {
  width: 180px;
}
.ga-select {
  max-width: 200px;
  color-scheme: dark;
}
.ga-select option {
  background: #171717;
  color: #f2f2f2;
}
.ui-btn.on {
  color: #d68a34;
  border-color: rgba(214, 138, 52, 0.5);
}
.ga-bulk {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
  padding: 10px 12px;
  background: #171717;
  border: 1px solid rgba(214, 138, 52, 0.4);
  border-radius: 12px;
}
.ga-bulk-count {
  font-size: 0.82rem;
  font-weight: 700;
  color: #d68a34;
  margin-right: 4px;
}
.ga-bulk-sep {
  flex: 1;
}
.ga-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.ga-error button {
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  padding: 0 2px;
}
.ga-skel {
  min-height: 150px;
  border: 1px solid #262626;
  border-radius: 12px;
  background: linear-gradient(100deg, #181818 30%, #212121 50%, #181818 70%);
  background-size: 200% 100%;
  animation: shimmer 1.4s linear infinite;
}
.ga-hint {
  color: #777;
  font-size: 14px;
}
.ga-body {
  position: relative;
  min-height: 140px;
}
.ga-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}
.ga-plus {
  font-size: 2rem;
  line-height: 1;
  font-weight: 300;
  color: #d68a34;
}
.ga-add,
.ga-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 20px;
  text-align: center;
  background: rgba(255, 255, 255, 0.02);
  border: 1.5px dashed #3a3a3a;
  border-radius: 12px;
  color: #999;
  font-family: inherit;
  font-size: 0.8rem;
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    background 0.15s ease;
}
.ga-add {
  align-self: stretch;
  padding: 0;
  overflow: hidden;
  text-align: left;
  align-items: stretch;
  justify-content: flex-start;
  gap: 0;
  border-width: 1px;
}
.ga-add-thumb {
  flex: 1 1 auto;
  aspect-ratio: 16 / 9;
  display: flex;
  align-items: center;
  justify-content: center;
}
.ga-add-body {
  min-height: 74px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 10px 12px 12px;
  border-top: 1px dashed #2b2b2b;
}
.ga-add-body strong {
  font-size: 0.84rem;
  font-weight: 600;
}
.ga-empty {
  width: 100%;
  min-height: var(--ui-empty-min, 280px);
  border-radius: 14px;
}
.ga-add strong,
.ga-empty strong {
  color: #f2f2f2;
  font-size: 0.95rem;
}
.ga-empty .ga-plus {
  font-size: 2.6rem;
}
.ga-add-sub {
  font-size: 0.74rem;
  color: #777;
}
.ga-add:hover:not(:disabled),
.ga-empty:hover:not(:disabled) {
  border-color: #d68a34;
  background: rgba(214, 138, 52, 0.06);
}
.ga-add:disabled,
.ga-empty:disabled {
  cursor: default;
}
.ga-spin {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 2px solid #3a3a3a;
  border-top-color: #d68a34;
  animation: ga-rot 0.8s linear infinite;
}
@keyframes ga-rot {
  to {
    transform: rotate(360deg);
  }
}
.ga-none {
  display: flex;
  align-items: center;
  gap: 12px;
  color: #777;
  font-size: 0.85rem;
  padding: 24px 0;
}
.ga-trash {
  list-style: none;
  margin: 0 0 16px;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.ga-trash li {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #151515;
  border: 1px solid #262626;
  border-radius: 8px;
  padding: 6px 10px;
  font-size: 0.8rem;
}
.ga-trash-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #ccc;
}
.ga-trash-meta {
  color: #777;
  font-size: 0.74rem;
}
.ga-drop {
  position: absolute;
  inset: 0;
  z-index: 5;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border: 2px dashed #d68a34;
  border-radius: 14px;
  background: rgba(20, 16, 10, 0.9);
  pointer-events: none;
}
.ga-drop strong {
  color: #f2f2f2;
  font-size: 1.05rem;
}

@keyframes shimmer {
  from {
    background-position: 200% 0;
  }
  to {
    background-position: -200% 0;
  }
}
@media (prefers-reduced-motion: reduce) {
  .ga-skel {
    animation: none !important;
  }
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.12s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
