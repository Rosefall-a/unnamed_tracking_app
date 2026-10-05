<script setup lang="ts">
// A game's notes: markdown files you write about it. The tab opens as a grid
// of cards (name, the start of the note, when it was edited), a note opens in
// a reader, and writing happens in an editor with a formatting bar and a live
// preview. Long lines and long words wrap instead of running off the page.
import {
  ref,
  computed,
  watch,
  onMounted,
  onBeforeUnmount,
  nextTick,
} from "vue";
import { marked } from "marked";
import DOMPurify from "dompurify";
import { useConfirm } from "../state/dialog";
import {
  listGameNoteSummaries,
  fetchGameNote,
  createGameNote,
  saveGameNote,
  renameGameNote,
  deleteGameNote,
} from "../services/games";
import type { GameNoteSummary } from "../services/games";

const props = defineProps<{ gameId: string }>();
const confirm = useConfirm();

const notes = ref<GameNoteSummary[]>([]);
const loaded = ref(false);
const error = ref<string | null>(null);
const mode = ref<"list" | "read" | "edit">("list");

// ---- list: search and sort ----
const query = ref("");
const sort = ref<"recent" | "name" | "oldest">("recent");
const visible = computed(() => {
  const q = query.value.trim().toLowerCase();
  let list = notes.value.filter(
    (n) =>
      !q ||
      n.name.toLowerCase().includes(q) ||
      n.preview.toLowerCase().includes(q),
  );
  list = [...list];
  if (sort.value === "name") list.sort((a, b) => a.name.localeCompare(b.name));
  else
    list.sort((a, b) =>
      sort.value === "oldest"
        ? a.updated_at - b.updated_at
        : b.updated_at - a.updated_at,
    );
  return list;
});

async function load() {
  error.value = null;
  try {
    notes.value = await listGameNoteSummaries(props.gameId);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to load notes";
  } finally {
    loaded.value = true;
  }
}
watch(
  () => props.gameId,
  () => {
    loaded.value = false;
    mode.value = "list";
    void load();
  },
);
onMounted(load);

function excerpt(text: string): string {
  return text
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/!\[[^\]]*\]\([^)]*\)/g, "")
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/^\s{0,3}#{1,6}\s*/gm, "")
    .replace(/^\s*[-*+]\s+\[[ xX]\]\s*/gm, "☐ ")
    .replace(/^\s*[-*+]\s+/gm, "• ")
    .replace(/[*_`>~]/g, "")
    .replace(/\n{2,}/g, "\n")
    .trim()
    .slice(0, 280);
}
const dateFormat = new Intl.DateTimeFormat(undefined, {
  month: "short",
  day: "numeric",
  year: "numeric",
});
function edited(seconds: number): string {
  return seconds ? dateFormat.format(new Date(seconds * 1000)) : "";
}
function wordLabel(n: number): string {
  return `${n.toLocaleString()} word${n === 1 ? "" : "s"}`;
}

function render(text: string): string {
  return DOMPurify.sanitize(
    marked.parse(text || "", { breaks: true, gfm: true }) as string,
  );
}

// ---- reader ----
const reading = ref<GameNoteSummary | null>(null);
const readingText = ref("");
const busy = ref(false);
const renderedReading = computed(() => render(readingText.value));

async function open(note: GameNoteSummary) {
  busy.value = true;
  error.value = null;
  try {
    readingText.value = await fetchGameNote(props.gameId, note.name);
    reading.value = note;
    mode.value = "read";
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to load note";
  } finally {
    busy.value = false;
  }
}
function backToList() {
  mode.value = "list";
  reading.value = null;
}

// ---- editor ----
const editingName = ref<string | null>(null);
const title = ref("");
const body = ref("");
const savedTitle = ref("");
const savedBody = ref("");
const showPreview = ref(false);
const area = ref<HTMLTextAreaElement | null>(null);
const dirty = computed(
  () => title.value !== savedTitle.value || body.value !== savedBody.value,
);
const bodyWords = computed(
  () => body.value.split(/\s+/).filter(Boolean).length,
);
const previewHtml = computed(() => render(body.value));

const draftKey = computed(() => `noteDraft:${props.gameId}`);
function loadDraft(): { title: string; body: string } | null {
  try {
    const raw = localStorage.getItem(draftKey.value);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}
function storeDraft() {
  if (editingName.value !== null) return;
  try {
    if (title.value.trim() || body.value.trim())
      localStorage.setItem(
        draftKey.value,
        JSON.stringify({ title: title.value, body: body.value }),
      );
    else localStorage.removeItem(draftKey.value);
  } catch {
    // the draft just will not survive a reload
  }
}
function clearDraft() {
  try {
    localStorage.removeItem(draftKey.value);
  } catch {
    // nothing to clear
  }
}
const hasDraft = computed(() => {
  void mode.value;
  const d = loadDraft();
  return !!d && (d.title.trim() !== "" || d.body.trim() !== "");
});
watch([title, body], storeDraft);

function startNew() {
  editingName.value = null;
  const draft = loadDraft();
  title.value = draft?.title ?? "";
  body.value = draft?.body ?? "";
  savedTitle.value = "";
  savedBody.value = "";
  showPreview.value = false;
  mode.value = "edit";
  void nextTick(() => grow());
}
async function startEdit(note: GameNoteSummary, text?: string) {
  if (text === undefined) {
    try {
      text = await fetchGameNote(props.gameId, note.name);
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to load note";
      return;
    }
  }
  editingName.value = note.name;
  title.value = note.name;
  body.value = text;
  savedTitle.value = note.name;
  savedBody.value = text;
  showPreview.value = false;
  mode.value = "edit";
  void nextTick(() => grow());
}

function grow() {
  const el = area.value;
  if (!el) return;
  el.style.height = "auto";
  el.style.height = `${Math.max(360, el.scrollHeight + 4)}px`;
}

async function leaveEditor() {
  if (dirty.value) {
    const ok = await confirm({
      title: "Discard changes?",
      message:
        editingName.value === null
          ? "This note has not been saved. Your text is kept as a draft you can come back to."
          : "The changes to this note have not been saved.",
      confirmLabel: editingName.value === null ? "Leave" : "Discard",
      danger: editingName.value !== null,
    });
    if (!ok) return;
  }
  mode.value = reading.value && editingName.value ? "read" : "list";
  if (mode.value === "list") reading.value = null;
}

async function save() {
  const name = title.value.trim();
  if (!name) {
    error.value = "Give the note a name first.";
    return;
  }
  busy.value = true;
  error.value = null;
  try {
    if (editingName.value) {
      await saveGameNote(props.gameId, editingName.value, body.value);
      if (editingName.value !== name)
        await renameGameNote(props.gameId, editingName.value, name);
    } else {
      await createGameNote(props.gameId, name, body.value);
      clearDraft();
    }
    savedTitle.value = name;
    savedBody.value = body.value;
    await load();
    const fresh = notes.value.find((n) => n.name === name) ?? null;
    reading.value = fresh;
    readingText.value = body.value;
    mode.value = fresh ? "read" : "list";
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to save note";
  } finally {
    busy.value = false;
  }
}

async function remove(note: GameNoteSummary) {
  const ok = await confirm({
    title: "Delete note",
    message: `Delete "${note.name}"? This cannot be undone.`,
    confirmLabel: "Delete",
    danger: true,
  });
  if (!ok) return;
  busy.value = true;
  error.value = null;
  try {
    await deleteGameNote(props.gameId, note.name);
    if (reading.value?.name === note.name) backToList();
    await load();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to delete note";
  } finally {
    busy.value = false;
  }
}

// ---- formatting bar ----
function surround(before: string, after = before, placeholder = "text") {
  const el = area.value;
  if (!el) return;
  const { selectionStart: a, selectionEnd: b } = el;
  const chosen = body.value.slice(a, b) || placeholder;
  body.value = `${body.value.slice(0, a)}${before}${chosen}${after}${body.value.slice(b)}`;
  void nextTick(() => {
    el.focus();
    el.setSelectionRange(a + before.length, a + before.length + chosen.length);
    grow();
  });
}
function linePrefix(prefix: string) {
  const el = area.value;
  if (!el) return;
  const a = body.value.lastIndexOf("\n", el.selectionStart - 1) + 1;
  const end = body.value.indexOf("\n", el.selectionEnd);
  const stop = end === -1 ? body.value.length : end;
  const lines = body.value.slice(a, stop).split("\n");
  const next = lines
    .map((l) => (l.startsWith(prefix) ? l : prefix + l))
    .join("\n");
  body.value = body.value.slice(0, a) + next + body.value.slice(stop);
  void nextTick(() => {
    el.focus();
    grow();
  });
}
const BAR: { label: string; title: string; run: () => void }[] = [
  { label: "B", title: "Bold", run: () => surround("**") },
  { label: "I", title: "Italic", run: () => surround("*") },
  { label: "H", title: "Heading", run: () => linePrefix("## ") },
  { label: "•", title: "Bulleted list", run: () => linePrefix("- ") },
  { label: "☐", title: "Checklist", run: () => linePrefix("- [ ] ") },
  { label: "❝", title: "Quote", run: () => linePrefix("> ") },
  { label: "</>", title: "Code", run: () => surround("`") },
  {
    label: "🔗",
    title: "Link",
    run: () => surround("[", "](https://)", "link"),
  },
];

function onKey(e: KeyboardEvent) {
  if (mode.value !== "edit") return;
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
    e.preventDefault();
    if (dirty.value || editingName.value === null) void save();
  }
}
onMounted(() => document.addEventListener("keydown", onKey));
onBeforeUnmount(() => document.removeEventListener("keydown", onKey));
</script>

<template>
  <div class="np">
    <!-- list -->
    <template v-if="mode === 'list'">
      <div class="np-head">
        <div class="np-title">
          <h2>Notes</h2>
          <span class="np-count">{{ notes.length }}</span>
        </div>
        <div class="np-tools">
          <input
            v-if="notes.length"
            v-model="query"
            type="search"
            class="ui-field np-search"
            placeholder="Search notes"
            aria-label="Search notes"
          />
          <select
            v-if="notes.length > 1"
            v-model="sort"
            class="ui-field np-select"
            aria-label="Sort"
          >
            <option value="recent">Recently edited</option>
            <option value="oldest">Oldest first</option>
            <option value="name">Name</option>
          </select>
          <button type="button" class="ui-btn ui-btn-primary" @click="startNew">
            {{ hasDraft ? "Continue draft" : "+ New note" }}
          </button>
        </div>
      </div>

      <div v-if="error" class="ui-error-box">{{ error }}</div>
      <p v-if="!loaded" class="np-hint">Loading…</p>

      <button
        v-else-if="!notes.length"
        type="button"
        class="np-empty"
        @click="startNew"
      >
        <span class="np-plus">+</span>
        <strong>Write your first note</strong>
        <span
          >Boss tips, builds, routes, anything you want to remember. Markdown
          works.</span
        >
      </button>

      <div v-else class="np-grid">
        <article
          v-for="n in visible"
          :key="n.name"
          class="np-card"
          tabindex="0"
          @click="open(n)"
          @keydown.enter="open(n)"
        >
          <h3 class="np-card-title">{{ n.name }}</h3>
          <p class="np-card-excerpt">
            {{ excerpt(n.preview) || "Empty note" }}
          </p>
          <footer class="np-card-foot">
            <span v-if="edited(n.updated_at)">{{ edited(n.updated_at) }}</span>
            <span>{{ wordLabel(n.words) }}</span>
          </footer>
          <div class="np-card-actions" @click.stop>
            <button type="button" title="Edit" @click="startEdit(n)">
              Edit
            </button>
            <button
              type="button"
              class="danger"
              title="Delete"
              @click="remove(n)"
            >
              Delete
            </button>
          </div>
        </article>
        <p v-if="!visible.length" class="np-none">
          No note matches that search.
        </p>
      </div>
    </template>

    <!-- reader -->
    <template v-else-if="mode === 'read' && reading">
      <div class="np-bar">
        <button
          type="button"
          class="ui-btn ui-btn-ghost ui-btn-sm"
          @click="backToList"
        >
          ← All notes
        </button>
        <span class="np-spacer"></span>
        <button
          type="button"
          class="ui-btn ui-btn-secondary ui-btn-sm"
          @click="startEdit(reading, readingText)"
        >
          Edit
        </button>
        <button
          type="button"
          class="ui-btn ui-btn-danger-soft ui-btn-sm"
          @click="remove(reading)"
        >
          Delete
        </button>
      </div>
      <div v-if="error" class="ui-error-box">{{ error }}</div>
      <article class="np-page">
        <h1>{{ reading.name }}</h1>
        <p class="np-meta">
          <span v-if="edited(reading.updated_at)"
            >Edited {{ edited(reading.updated_at) }}</span
          >
          <span>{{
            wordLabel(readingText.split(/\s+/).filter(Boolean).length)
          }}</span>
        </p>
        <div class="np-rendered" v-html="renderedReading"></div>
      </article>
    </template>

    <!-- editor -->
    <template v-else-if="mode === 'edit'">
      <div class="np-bar">
        <button
          type="button"
          class="ui-btn ui-btn-ghost ui-btn-sm"
          @click="leaveEditor"
        >
          ← Back
        </button>
        <span class="np-status">{{
          dirty ? "Unsaved changes" : editingName ? "Saved" : ""
        }}</span>
        <span class="np-spacer"></span>
        <button
          type="button"
          class="ui-btn ui-btn-secondary ui-btn-sm np-previewtoggle"
          :class="{ on: showPreview }"
          @click="showPreview = !showPreview"
        >
          {{ showPreview ? "Write" : "Preview" }}
        </button>
        <button
          type="button"
          class="ui-btn ui-btn-primary ui-btn-sm"
          :disabled="busy || !title.trim() || (editingName !== null && !dirty)"
          @click="save"
        >
          {{ busy ? "Saving…" : editingName ? "Save changes" : "Create note" }}
        </button>
      </div>
      <div v-if="error" class="ui-error-box">{{ error }}</div>

      <div class="np-editor">
        <input
          v-model="title"
          type="text"
          class="np-name"
          maxlength="120"
          placeholder="Note name"
          aria-label="Note name"
          autocomplete="off"
        />
        <div class="np-format" role="toolbar" aria-label="Formatting">
          <button
            v-for="b in BAR"
            :key="b.title"
            type="button"
            :title="b.title"
            :aria-label="b.title"
            @click="b.run"
          >
            {{ b.label }}
          </button>
          <span class="np-words">{{ wordLabel(bodyWords) }}</span>
        </div>
        <div class="np-panes" :class="{ preview: showPreview }">
          <textarea
            ref="area"
            v-model="body"
            class="np-text"
            placeholder="Write here. Markdown works: **bold**, # headings, - lists, - [ ] checklists."
            spellcheck="true"
            @input="grow"
          ></textarea>
          <div class="np-live">
            <p class="np-live-label">Preview</p>
            <div
              v-if="body.trim()"
              class="np-rendered"
              v-html="previewHtml"
            ></div>
            <p v-else class="np-hint">Nothing to preview yet.</p>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.np {
  width: 100%;
  min-width: 0;
}
.np-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 16px;
}
.np-title {
  display: flex;
  align-items: center;
  gap: 10px;
}
.np-title h2 {
  margin: 0;
  font-size: 1.1rem;
}
.np-count {
  background: rgba(214, 138, 52, 0.16);
  color: #d68a34;
  font-size: 0.72rem;
  font-weight: 700;
  border-radius: 999px;
  padding: 2px 9px;
  font-variant-numeric: tabular-nums;
}
.np-tools {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
.np-search {
  width: 180px;
}
.np-select {
  max-width: 200px;
  color-scheme: dark;
}
.np-select option {
  background: #171717;
  color: #f2f2f2;
}
.np-hint {
  color: #777;
  font-size: 0.85rem;
  margin: 0;
}
.np-plus {
  font-size: 2.4rem;
  line-height: 1;
  font-weight: 300;
  color: #d68a34;
}
.np-empty {
  width: 100%;
  min-height: 260px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 24px;
  text-align: center;
  background: rgba(255, 255, 255, 0.02);
  border: 1.5px dashed #3a3a3a;
  border-radius: 14px;
  color: #999;
  font-family: inherit;
  font-size: 0.85rem;
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    background 0.15s ease;
}
.np-empty strong {
  color: #f2f2f2;
  font-size: 1rem;
}
.np-empty:hover {
  border-color: #d68a34;
  background: rgba(214, 138, 52, 0.06);
}
.np-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}
.np-card {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
  min-height: 170px;
  padding: 16px 16px 12px;
  background: #141414;
  border: 1px solid #262626;
  border-radius: 12px;
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    transform 0.15s ease;
}
.np-card:hover,
.np-card:focus-visible {
  border-color: rgba(214, 138, 52, 0.5);
  outline: none;
}
.np-card-title {
  margin: 0;
  font-size: 0.98rem;
  font-weight: 700;
  color: #f2f2f2;
  overflow-wrap: anywhere;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.np-card-excerpt {
  margin: 0;
  flex: 1;
  color: #9c9c9c;
  font-size: 0.84rem;
  line-height: 1.5;
  white-space: pre-line;
  overflow-wrap: anywhere;
  display: -webkit-box;
  -webkit-line-clamp: 5;
  line-clamp: 5;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.np-card-foot {
  display: flex;
  gap: 12px;
  color: #6f6f6f;
  font-size: 0.74rem;
  font-variant-numeric: tabular-nums;
}
.np-card-actions {
  position: absolute;
  top: 10px;
  right: 10px;
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.15s ease;
}
.np-card:hover .np-card-actions,
.np-card:focus-within .np-card-actions {
  opacity: 1;
}
@media (hover: none) {
  .np-card-actions {
    opacity: 1;
  }
}
.np-card-actions button {
  height: 26px;
  padding: 0 10px;
  border: none;
  border-radius: 7px;
  background: rgba(15, 15, 15, 0.85);
  color: #ddd;
  font-family: inherit;
  font-size: 0.72rem;
  font-weight: 700;
  cursor: pointer;
}
.np-card-actions button:hover {
  background: #d68a34;
  color: #14100a;
}
.np-card-actions .danger:hover {
  background: #d96f6f;
  color: #fff;
}
.np-none {
  grid-column: 1 / -1;
  color: #777;
  font-size: 0.85rem;
  margin: 0;
}

.np-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 18px;
}
.np-spacer {
  flex: 1;
}
.np-status {
  font-size: 0.78rem;
  color: #d68a34;
}
.np-previewtoggle {
  display: none;
}

.np-page {
  max-width: 760px;
  margin: 0 auto;
  min-width: 0;
}
.np-page h1 {
  margin: 0 0 8px;
  font-size: 1.7rem;
  line-height: 1.2;
  overflow-wrap: anywhere;
}
.np-meta {
  display: flex;
  gap: 14px;
  margin: 0 0 22px;
  padding-bottom: 16px;
  border-bottom: 1px solid #262626;
  color: #777;
  font-size: 0.8rem;
}

/* the rendered markdown, shared by the reader and the preview */
.np-rendered {
  color: #ddd;
  font-size: 0.95rem;
  line-height: 1.7;
  overflow-wrap: anywhere;
  word-break: break-word;
  min-width: 0;
}
.np-rendered :deep(h1),
.np-rendered :deep(h2),
.np-rendered :deep(h3),
.np-rendered :deep(h4) {
  color: #fff;
  line-height: 1.25;
  margin: 1.4em 0 0.5em;
}
.np-rendered :deep(h1) {
  font-size: 1.5rem;
}
.np-rendered :deep(h2) {
  font-size: 1.25rem;
}
.np-rendered :deep(h3) {
  font-size: 1.08rem;
}
.np-rendered :deep(*:first-child) {
  margin-top: 0;
}
.np-rendered :deep(p) {
  margin: 0 0 0.9em;
}
.np-rendered :deep(a) {
  color: #d68a34;
}
.np-rendered :deep(ul),
.np-rendered :deep(ol) {
  margin: 0 0 0.9em;
  padding-left: 1.4em;
}
.np-rendered :deep(li) {
  margin: 0.2em 0;
}
.np-rendered :deep(li:has(input[type="checkbox"])) {
  list-style: none;
  margin-left: -1.2em;
}
.np-rendered :deep(input[type="checkbox"]) {
  margin-right: 8px;
  accent-color: #d68a34;
}
.np-rendered :deep(blockquote) {
  margin: 0 0 0.9em;
  padding: 2px 0 2px 14px;
  border-left: 3px solid #d68a34;
  color: #aaa;
}
.np-rendered :deep(code) {
  background: #1b1b1b;
  padding: 2px 6px;
  border-radius: 5px;
  font-size: 0.88em;
}
.np-rendered :deep(pre) {
  background: #111;
  border: 1px solid #262626;
  padding: 12px 14px;
  border-radius: 10px;
  overflow-x: auto;
  margin: 0 0 0.9em;
}
.np-rendered :deep(pre code) {
  background: none;
  padding: 0;
}
.np-rendered :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
}
.np-rendered :deep(table) {
  display: block;
  max-width: 100%;
  overflow-x: auto;
  border-collapse: collapse;
  margin: 0 0 0.9em;
}
.np-rendered :deep(th),
.np-rendered :deep(td) {
  border: 1px solid #2b2b2b;
  padding: 6px 10px;
}
.np-rendered :deep(hr) {
  border: none;
  border-top: 1px solid #2b2b2b;
  margin: 1.4em 0;
}

.np-editor {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}
.np-name {
  width: 100%;
  box-sizing: border-box;
  background: none;
  border: none;
  border-bottom: 1px solid #2b2b2b;
  padding: 6px 0 12px;
  color: #fff;
  font: inherit;
  font-size: 1.6rem;
  font-weight: 800;
}
.np-name::placeholder {
  color: #4a4a4a;
}
.np-name:focus {
  outline: none;
  border-bottom-color: #d68a34;
}
.np-format {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}
.np-format button {
  min-width: 32px;
  height: 30px;
  padding: 0 8px;
  border: 1px solid #2b2b2b;
  border-radius: 7px;
  background: none;
  color: #aaa;
  font-family: inherit;
  font-size: 0.82rem;
  font-weight: 700;
  cursor: pointer;
}
.np-format button:hover {
  color: #fff;
  border-color: #444;
}
.np-words {
  margin-left: auto;
  color: #6f6f6f;
  font-size: 0.76rem;
  font-variant-numeric: tabular-nums;
}
.np-panes {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}
.np-text {
  width: 100%;
  min-height: 360px;
  box-sizing: border-box;
  padding: 14px 16px;
  background: #101010;
  border: 1px solid #2b2b2b;
  border-radius: 12px;
  color: #f0f0f0;
  font: inherit;
  font-size: 0.95rem;
  line-height: 1.65;
  resize: none;
  overflow: hidden;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.np-text:focus {
  outline: none;
  border-color: #d68a34;
}
.np-text::placeholder {
  color: #4f4f4f;
}
.np-live {
  min-width: 0;
  min-height: 360px;
  padding: 14px 16px;
  background: #141414;
  border: 1px solid #262626;
  border-radius: 12px;
}
.np-live-label {
  margin: 0 0 10px;
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #d68a34;
}
@media (max-width: 900px) {
  .np-panes {
    grid-template-columns: 1fr;
  }
  .np-previewtoggle {
    display: inline-flex;
  }
  .np-panes .np-live {
    display: none;
  }
  .np-panes.preview .np-text {
    display: none;
  }
  .np-panes.preview .np-live {
    display: block;
  }
}
</style>
