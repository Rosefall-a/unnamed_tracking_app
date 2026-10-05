<script setup lang="ts">
// A game's notes: markdown files you write about it. The tab opens as a grid of
// cards (name, the start of the note, tags, checklist progress, dates), a note
// opens in a reader where its checklist can be ticked, and writing happens in
// an editor with a formatting bar and a live preview. A note can be pinned,
// tagged, tied to an achievement, started from a template, duplicated, moved to
// another game, and wound back to an earlier version.
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
import AchievementPicker from "./AchievementPicker.vue";
import { useConfirm } from "../state/dialog";
import {
  fetchGames,
  listGameNoteSummaries,
  fetchGameNote,
  createGameNote,
  saveGameNote,
  renameGameNote,
  deleteGameNote,
  updateNoteDetails,
  duplicateNote,
  moveNote,
  listNoteVersions,
  fetchNoteVersion,
  restoreNoteVersion,
} from "../services/games";
import type { GameNoteSummary, NoteVersion } from "../services/games";
import { NOTE_TEMPLATES } from "../utils/noteTemplates";
import type { Achievement, Game } from "../types/game";

const props = defineProps<{
  gameId: string;
  achievements?: Achievement[];
  // a note to open straight away, from a search result or a link
  openNote?: string | null;
}>();
const emit = defineEmits<{ "open-achievement": [achievementId: string] }>();
const confirm = useConfirm();

const achievementList = computed(() => props.achievements ?? []);
function achievementName(id: string | null): string | null {
  if (!id) return null;
  return achievementList.value.find((a) => a.id === id)?.name ?? null;
}

const notes = ref<GameNoteSummary[]>([]);
const loaded = ref(false);
const error = ref<string | null>(null);
const mode = ref<"list" | "read" | "edit">("list");
const busy = ref(false);

const notice = ref<string | null>(null);
let noticeTimer: number | undefined;
function flash(text: string) {
  notice.value = text;
  window.clearTimeout(noticeTimer);
  noticeTimer = window.setTimeout(() => (notice.value = null), 2600);
}

// ---------------------------------------------------------------- list ----
const query = ref("");
const sort = ref<"recent" | "created" | "name">("recent");
const activeTag = ref<string | null>(null);

const allTags = computed(() => {
  const counts = new Map<string, number>();
  for (const n of notes.value)
    for (const t of n.tags) counts.set(t, (counts.get(t) ?? 0) + 1);
  return [...counts.entries()].sort((a, b) => a[0].localeCompare(b[0]));
});
const visible = computed(() => {
  const q = query.value.trim().toLowerCase();
  let list = notes.value.filter(
    (n) =>
      (!activeTag.value || n.tags.includes(activeTag.value)) &&
      (!q ||
        n.name.toLowerCase().includes(q) ||
        n.preview.toLowerCase().includes(q) ||
        n.tags.some((t) => t.toLowerCase().includes(q))),
  );
  list = [...list];
  list.sort((a, b) => {
    if (a.pinned !== b.pinned) return a.pinned ? -1 : 1;
    if (sort.value === "name") return a.name.localeCompare(b.name);
    if (sort.value === "created") return b.created_at - a.created_at;
    return b.updated_at - a.updated_at;
  });
  return list;
});
watch(allTags, (tags) => {
  if (activeTag.value && !tags.some(([t]) => t === activeTag.value))
    activeTag.value = null;
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
onMounted(async () => {
  await load();
  if (props.openNote) await openByName(props.openNote);
});
watch(
  () => props.openNote,
  (name) => {
    if (name) void openByName(name);
  },
);
async function openByName(name: string) {
  const found = notes.value.find((n) => n.name === name);
  if (found) await open(found);
}

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
function when(seconds: number): string {
  return seconds ? dateFormat.format(new Date(seconds * 1000)) : "";
}
function dates(n: GameNoteSummary): string {
  const created = when(n.created_at);
  const edited = when(n.updated_at);
  if (!created) return edited ? `Edited ${edited}` : "";
  return created === edited || !edited
    ? `Created ${created}`
    : `Created ${created} · edited ${edited}`;
}
function wordLabel(n: number): string {
  return `${n.toLocaleString()} word${n === 1 ? "" : "s"}`;
}

function render(text: string): string {
  return DOMPurify.sanitize(
    marked.parse(text || "", { breaks: true, gfm: true }) as string,
  );
}

// -------------------------------------------------- the card menu ----
const menuFor = ref<string | null>(null);
const showTemplates = ref(false);
function onDocumentClick(e: MouseEvent) {
  const t = e.target as HTMLElement;
  if (!t.closest?.(".np-menu, .np-menu-btn")) menuFor.value = null;
  if (!t.closest?.(".np-templates, .np-new")) showTemplates.value = false;
}
onMounted(() => document.addEventListener("click", onDocumentClick));
onBeforeUnmount(() => {
  document.removeEventListener("click", onDocumentClick);
  window.clearTimeout(noticeTimer);
});

// -------------------------------------------------------- the reader ----
const reading = ref<GameNoteSummary | null>(null);
const readingText = ref("");
// checkboxes in the rendered note are live: tick one and the note is saved
const renderedReading = computed(() => {
  let i = 0;
  return render(readingText.value).replace(
    /<input([^>]*?)disabled=""([^>]*?)type="checkbox"/g,
    // keep the checked attribute, drop disabled so a click reaches us
    (_whole, before: string, after: string) =>
      `<input data-task="${i++}"${before}${after}type="checkbox"`,
  );
});

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

async function onReaderClick(e: MouseEvent) {
  const box = e.target as HTMLInputElement;
  if (box?.dataset?.task === undefined || !reading.value) return;
  e.preventDefault();
  const index = Number(box.dataset.task);
  let seen = -1;
  const next = readingText.value.replace(
    /^(\s*[-*+]\s+\[)( |x|X)(\]\s)/gm,
    (whole, a: string, mark: string, c: string) => {
      seen += 1;
      if (seen !== index) return whole;
      return `${a}${mark === " " ? "x" : " "}${c}`;
    },
  );
  if (next === readingText.value) return;
  const name = reading.value.name;
  const before = readingText.value;
  readingText.value = next;
  try {
    await saveGameNote(props.gameId, name, next);
    await load();
    reading.value = notes.value.find((n) => n.name === name) ?? reading.value;
  } catch (err) {
    readingText.value = before;
    error.value = err instanceof Error ? err.message : "Failed to save note";
  }
}

// ---------------------------------------------------- pin and details ----
async function togglePin(note: GameNoteSummary) {
  try {
    const updated = await updateNoteDetails(props.gameId, note.name, {
      pinned: !note.pinned,
    });
    replace(updated);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to pin the note";
  }
}
function replace(updated: GameNoteSummary) {
  const i = notes.value.findIndex((n) => n.name === updated.name);
  if (i === -1) notes.value = [...notes.value, updated];
  else notes.value[i] = updated;
  if (reading.value?.name === updated.name) reading.value = updated;
}

// ------------------------------------------------------- the editor ----
const editingName = ref<string | null>(null);
const title = ref("");
const body = ref("");
const tags = ref<string[]>([]);
const tagDraft = ref("");
const tagInput = ref<HTMLInputElement | null>(null);
const linked = ref<string | null>(null);
const pinned = ref(false);
const saved = ref({
  title: "",
  body: "",
  tags: "[]",
  linked: null as string | null,
  pinned: false,
});
const showPreview = ref(false);
const area = ref<HTMLTextAreaElement | null>(null);

const dirty = computed(
  () =>
    title.value !== saved.value.title ||
    body.value !== saved.value.body ||
    JSON.stringify(tags.value) !== saved.value.tags ||
    linked.value !== saved.value.linked ||
    pinned.value !== saved.value.pinned,
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

function resetEditor(fields: {
  name: string | null;
  title: string;
  body: string;
  tags: string[];
  linked: string | null;
  pinned: boolean;
}) {
  editingName.value = fields.name;
  title.value = fields.title;
  body.value = fields.body;
  tags.value = [...fields.tags];
  tagDraft.value = "";
  linked.value = fields.linked;
  pinned.value = fields.pinned;
  saved.value = {
    title: fields.name === null ? "" : fields.title,
    body: fields.name === null ? "" : fields.body,
    tags: JSON.stringify(fields.name === null ? [] : fields.tags),
    linked: fields.name === null ? null : fields.linked,
    pinned: fields.name === null ? false : fields.pinned,
  };
  showPreview.value = false;
  mode.value = "edit";
  void nextTick(() => grow());
}
function startNew(templateKey?: string) {
  showTemplates.value = false;
  const template = NOTE_TEMPLATES.find((t) => t.key === templateKey);
  const draft = template ? null : loadDraft();
  resetEditor({
    name: null,
    title: template?.title ?? draft?.title ?? "",
    body: template?.body ?? draft?.body ?? "",
    tags: template?.tags ?? [],
    linked: null,
    pinned: false,
  });
}
async function startEdit(note: GameNoteSummary, text?: string) {
  menuFor.value = null;
  if (text === undefined) {
    try {
      text = await fetchGameNote(props.gameId, note.name);
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to load note";
      return;
    }
  }
  resetEditor({
    name: note.name,
    title: note.name,
    body: text,
    tags: note.tags,
    linked: note.linked_achievement_id,
    pinned: note.pinned,
  });
}

function grow() {
  const el = area.value;
  if (!el) return;
  el.style.height = "auto";
  el.style.height = `${Math.max(360, el.scrollHeight + 4)}px`;
}

function commitTag() {
  const t = tagDraft.value.trim().replace(/,$/, "").trim();
  tagDraft.value = "";
  if (t && !tags.value.some((x) => x.toLowerCase() === t.toLowerCase()))
    tags.value.push(t);
}
function onTagKey(e: KeyboardEvent) {
  if (e.key === "Enter" || e.key === ",") {
    e.preventDefault();
    commitTag();
  } else if (e.key === "Backspace" && !tagDraft.value && tags.value.length) {
    tags.value.pop();
  }
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
  commitTag();
  const name = title.value.trim();
  if (!name) {
    error.value = "Give the note a name first.";
    return;
  }
  busy.value = true;
  error.value = null;
  try {
    if (editingName.value) {
      if (body.value !== saved.value.body)
        await saveGameNote(props.gameId, editingName.value, body.value);
      if (editingName.value !== name)
        await renameGameNote(props.gameId, editingName.value, name);
    } else {
      await createGameNote(props.gameId, name, body.value);
      clearDraft();
    }
    // pin, tags and the achievement live beside the file
    const detailChanges: {
      pinned?: boolean;
      tags?: string[];
      linked_achievement_id?: string | null;
    } = {};
    if (pinned.value !== saved.value.pinned)
      detailChanges.pinned = pinned.value;
    if (JSON.stringify(tags.value) !== saved.value.tags)
      detailChanges.tags = tags.value;
    if (linked.value !== saved.value.linked)
      detailChanges.linked_achievement_id = linked.value;
    if (Object.keys(detailChanges).length)
      await updateNoteDetails(props.gameId, name, detailChanges);
    await load();
    const fresh = notes.value.find((n) => n.name === name) ?? null;
    reading.value = fresh;
    readingText.value = body.value;
    saved.value = {
      title: name,
      body: body.value,
      tags: JSON.stringify(tags.value),
      linked: linked.value,
      pinned: pinned.value,
    };
    editingName.value = name;
    mode.value = fresh ? "read" : "list";
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to save note";
  } finally {
    busy.value = false;
  }
}

// ------------------------------------------- delete, duplicate, move ----
async function remove(note: GameNoteSummary) {
  menuFor.value = null;
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

async function duplicate(note: GameNoteSummary) {
  menuFor.value = null;
  try {
    const copy = await duplicateNote(props.gameId, note.name);
    await load();
    flash(`Duplicated as "${copy.name}"`);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to duplicate";
  }
}

const moving = ref<GameNoteSummary | null>(null);
const gameChoices = ref<Game[]>([]);
const gameQuery = ref("");
const moveError = ref<string | null>(null);
const choicesShown = computed(() => {
  const q = gameQuery.value.trim().toLowerCase();
  return gameChoices.value
    .filter((g) => g.id !== props.gameId)
    .filter((g) => !q || g.title.toLowerCase().includes(q))
    .slice(0, 40);
});
async function startMove(note: GameNoteSummary) {
  menuFor.value = null;
  moving.value = note;
  gameQuery.value = "";
  moveError.value = null;
  if (!gameChoices.value.length) {
    try {
      gameChoices.value = await fetchGames();
    } catch (e) {
      moveError.value = e instanceof Error ? e.message : "Could not load games";
    }
  }
}
async function moveTo(target: Game) {
  const note = moving.value;
  if (!note) return;
  moveError.value = null;
  try {
    const result = await moveNote(props.gameId, note.name, target.id);
    moving.value = null;
    if (reading.value?.name === note.name) backToList();
    await load();
    flash(`Moved to ${result.game_title || target.title}`);
  } catch (e) {
    moveError.value = e instanceof Error ? e.message : "Failed to move";
  }
}

// ------------------------------------------------------------ history ----
const historyFor = ref<GameNoteSummary | null>(null);
const versions = ref<NoteVersion[]>([]);
const historyLoading = ref(false);
const previewing = ref<{ version: NoteVersion; text: string } | null>(null);
async function showHistory(note: GameNoteSummary) {
  menuFor.value = null;
  historyFor.value = note;
  previewing.value = null;
  historyLoading.value = true;
  try {
    versions.value = await listNoteVersions(props.gameId, note.name);
  } catch (e) {
    error.value =
      e instanceof Error ? e.message : "History could not be loaded";
    historyFor.value = null;
  } finally {
    historyLoading.value = false;
  }
}
async function previewVersion(v: NoteVersion) {
  if (!historyFor.value) return;
  try {
    previewing.value = {
      version: v,
      text: await fetchNoteVersion(props.gameId, historyFor.value.name, v.id),
    };
  } catch (e) {
    error.value =
      e instanceof Error ? e.message : "Could not open that version";
  }
}
async function restoreVersion() {
  const note = historyFor.value;
  const chosen = previewing.value;
  if (!note || !chosen) return;
  try {
    await restoreNoteVersion(props.gameId, note.name, chosen.version.id);
    historyFor.value = null;
    previewing.value = null;
    await load();
    const fresh = notes.value.find((n) => n.name === note.name);
    if (fresh) await open(fresh);
    flash(
      "Restored. The text it replaced is in the history, so you can undo this.",
    );
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Could not restore";
  }
}

// ------------------------------------------------------ formatting bar ----
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
            <option value="created">Newest created</option>
            <option value="name">Name</option>
          </select>
          <div class="np-new">
            <button
              type="button"
              class="ui-btn ui-btn-primary"
              @click="hasDraft ? startNew() : (showTemplates = !showTemplates)"
            >
              {{ hasDraft ? "Continue draft" : "+ New note" }}
            </button>
            <button
              v-if="hasDraft"
              type="button"
              class="ui-btn ui-btn-ghost np-more"
              aria-label="Start from a template"
              @click="showTemplates = !showTemplates"
            >
              ▾
            </button>
            <ul v-if="showTemplates" class="np-templates" role="menu">
              <li v-for="t in NOTE_TEMPLATES" :key="t.key">
                <button type="button" role="menuitem" @click="startNew(t.key)">
                  <strong>{{ t.label }}</strong>
                  <span>{{ t.hint }}</span>
                </button>
              </li>
              <li>
                <button type="button" role="menuitem" @click="startNew()">
                  <strong>Blank note</strong>
                  <span>Start from nothing</span>
                </button>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <div
        v-if="allTags.length"
        class="np-tagbar"
        role="group"
        aria-label="Filter by tag"
      >
        <button
          type="button"
          class="ui-chip"
          :class="{ on: !activeTag }"
          @click="activeTag = null"
        >
          All <span class="n">{{ notes.length }}</span>
        </button>
        <button
          v-for="[tag, n] in allTags"
          :key="tag"
          type="button"
          class="ui-chip"
          :class="{ on: activeTag === tag }"
          @click="activeTag = activeTag === tag ? null : tag"
        >
          {{ tag }} <span class="n">{{ n }}</span>
        </button>
      </div>

      <div v-if="error" class="ui-error-box">{{ error }}</div>
      <div v-if="!loaded" class="np-grid" aria-busy="true" aria-label="Loading">
        <div v-for="n in 3" :key="n" class="np-skel"></div>
      </div>

      <button
        v-else-if="!notes.length"
        type="button"
        class="np-empty"
        @click="startNew()"
      >
        <span class="np-plus">+</span>
        <strong>Write your first note</strong>
        <span
          >Boss tips, builds, routes, anything you want to remember. Pick a
          template from the New note button, or just click here.</span
        >
      </button>

      <div v-else class="np-grid">
        <article
          v-for="n in visible"
          :key="n.name"
          class="np-card"
          :class="{ pinned: n.pinned }"
          tabindex="0"
          @click="open(n)"
          @keydown.enter="open(n)"
        >
          <header class="np-card-top">
            <h3 class="np-card-title">{{ n.name }}</h3>
            <div class="np-card-btns" @click.stop>
              <button
                type="button"
                class="np-pin"
                :class="{ on: n.pinned }"
                :title="n.pinned ? 'Unpin' : 'Pin to the top'"
                :aria-pressed="n.pinned"
                @click="togglePin(n)"
              >
                <svg
                  viewBox="0 0 24 24"
                  width="14"
                  height="14"
                  stroke="currentColor"
                  stroke-width="1.8"
                  stroke-linejoin="round"
                  :fill="n.pinned ? 'currentColor' : 'none'"
                >
                  <path
                    d="M12 2l3 7 7 .6-5.3 4.7 1.6 7.2L12 17.8 5.7 21.5l1.6-7.2L2 9.6 9 9z"
                  />
                </svg>
              </button>
              <button
                type="button"
                class="np-menu-btn"
                aria-label="More"
                aria-haspopup="menu"
                @click="menuFor = menuFor === n.name ? null : n.name"
              >
                ⋯
              </button>
              <ul v-if="menuFor === n.name" class="np-menu" role="menu">
                <li>
                  <button type="button" role="menuitem" @click="startEdit(n)">
                    Edit
                  </button>
                </li>
                <li>
                  <button type="button" role="menuitem" @click="duplicate(n)">
                    Duplicate
                  </button>
                </li>
                <li>
                  <button type="button" role="menuitem" @click="startMove(n)">
                    Move to another game…
                  </button>
                </li>
                <li>
                  <button type="button" role="menuitem" @click="showHistory(n)">
                    History
                  </button>
                </li>
                <li>
                  <button
                    type="button"
                    role="menuitem"
                    class="danger"
                    @click="remove(n)"
                  >
                    Delete
                  </button>
                </li>
              </ul>
            </div>
          </header>
          <p class="np-card-excerpt">
            {{ excerpt(n.preview) || "Empty note" }}
          </p>
          <div
            v-if="n.tags.length || achievementName(n.linked_achievement_id)"
            class="np-card-chips"
          >
            <span
              v-if="achievementName(n.linked_achievement_id)"
              class="np-chip ach"
            >
              <svg
                viewBox="0 0 24 24"
                width="11"
                height="11"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d="M8 4h8v5a4 4 0 0 1-8 0z" />
                <path d="M8 4H5a2 2 0 0 0 0 4h1.5M16 4h3a2 2 0 0 1 0 4h-1.5" />
                <path d="M12 13v3" />
                <path d="M9 20h6" />
                <path d="M10 16.5h4l.8 3.5H9.2z" />
              </svg>
              {{ achievementName(n.linked_achievement_id) }}
            </span>
            <span v-for="t in n.tags.slice(0, 3)" :key="t" class="np-chip">{{
              t
            }}</span>
            <span v-if="n.tags.length > 3" class="np-chip"
              >+{{ n.tags.length - 3 }}</span
            >
          </div>
          <div
            v-if="n.tasks_total"
            class="np-progress"
            :title="`${n.tasks_done} of ${n.tasks_total} done`"
          >
            <span class="np-progress-bar"
              ><span
                :style="{ width: `${(n.tasks_done / n.tasks_total) * 100}%` }"
              ></span
            ></span>
            <span class="np-progress-n"
              >{{ n.tasks_done }}/{{ n.tasks_total }}</span
            >
          </div>
          <footer class="np-card-foot">
            <span>{{ dates(n) }}</span>
            <span>{{ wordLabel(n.words) }}</span>
          </footer>
        </article>
        <p v-if="!visible.length" class="np-none">No note matches that.</p>
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
          :class="{ on: reading.pinned }"
          @click="togglePin(reading)"
        >
          {{ reading.pinned ? "Pinned" : "Pin" }}
        </button>
        <button
          type="button"
          class="ui-btn ui-btn-secondary ui-btn-sm"
          @click="showHistory(reading)"
        >
          History
        </button>
        <button
          type="button"
          class="ui-btn ui-btn-secondary ui-btn-sm"
          @click="startEdit(reading, readingText)"
        >
          Edit
        </button>
        <div class="np-more-wrap">
          <button
            type="button"
            class="ui-btn ui-btn-ghost ui-btn-sm np-menu-btn"
            aria-label="More"
            @click="menuFor = menuFor === reading.name ? null : reading.name"
          >
            ⋯
          </button>
          <ul v-if="menuFor === reading.name" class="np-menu" role="menu">
            <li>
              <button type="button" role="menuitem" @click="duplicate(reading)">
                Duplicate
              </button>
            </li>
            <li>
              <button type="button" role="menuitem" @click="startMove(reading)">
                Move to another game…
              </button>
            </li>
            <li>
              <button
                type="button"
                role="menuitem"
                class="danger"
                @click="remove(reading)"
              >
                Delete
              </button>
            </li>
          </ul>
        </div>
      </div>
      <div v-if="error" class="ui-error-box">{{ error }}</div>
      <article class="np-page">
        <h1>{{ reading.name }}</h1>
        <p class="np-meta">
          <span>{{ dates(reading) }}</span>
          <span>{{
            wordLabel(readingText.split(/\s+/).filter(Boolean).length)
          }}</span>
          <span v-if="reading.tasks_total"
            >{{ reading.tasks_done }} of {{ reading.tasks_total }} done</span
          >
        </p>
        <div
          v-if="
            reading.tags.length ||
            achievementName(reading.linked_achievement_id)
          "
          class="np-page-chips"
        >
          <button
            v-if="achievementName(reading.linked_achievement_id)"
            type="button"
            class="np-chip ach link"
            title="Open this achievement"
            @click="emit('open-achievement', reading.linked_achievement_id!)"
          >
            <svg
              viewBox="0 0 24 24"
              width="11"
              height="11"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M8 4h8v5a4 4 0 0 1-8 0z" />
              <path d="M8 4H5a2 2 0 0 0 0 4h1.5M16 4h3a2 2 0 0 1 0 4h-1.5" />
              <path d="M12 13v3" />
              <path d="M9 20h6" />
              <path d="M10 16.5h4l.8 3.5H9.2z" />
            </svg>
            {{ achievementName(reading.linked_achievement_id) }}
          </button>
          <span v-for="t in reading.tags" :key="t" class="np-chip">{{
            t
          }}</span>
        </div>
        <!-- eslint-disable-next-line vue/no-v-html -->
        <div
          class="np-rendered"
          @click="onReaderClick"
          v-html="renderedReading"
        ></div>
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

        <div class="np-meta-edit">
          <div class="np-tags ui-field" @click="tagInput?.focus()">
            <span v-for="t in tags" :key="t" class="np-tag">
              {{ t }}
              <button
                type="button"
                :aria-label="`Remove ${t}`"
                @click.stop="tags = tags.filter((x) => x !== t)"
              >
                ✕
              </button>
            </span>
            <input
              ref="tagInput"
              v-model="tagDraft"
              type="text"
              :placeholder="tags.length ? '' : 'Add tags: boss, build, route'"
              aria-label="Tags"
              @keydown="onTagKey"
              @blur="commitTag"
            />
          </div>
          <AchievementPicker
            v-if="achievementList.length"
            :model-value="linked"
            :achievements="achievementList"
            @change="linked = $event"
          />
          <label class="np-pinbox">
            <input v-model="pinned" type="checkbox" />
            <span>Pin to the top</span>
          </label>
        </div>

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
            <!-- eslint-disable-next-line vue/no-v-html -->
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

    <Transition name="fade">
      <div v-if="notice" class="np-toast" role="status">{{ notice }}</div>
    </Transition>

    <Teleport to="body">
      <!-- move to another game -->
      <div v-if="moving" class="ui-backdrop" @click.self="moving = null">
        <div
          class="ui-modal np-dialog"
          role="dialog"
          aria-modal="true"
          aria-label="Move note"
        >
          <h3>Move "{{ moving.name }}"</h3>
          <p class="np-dialog-hint">
            Its tags and history go with it. The achievement it was tied to does
            not.
          </p>
          <input
            v-model="gameQuery"
            type="search"
            class="ui-field"
            placeholder="Search your games"
            autofocus
          />
          <p v-if="moveError" class="np-dialog-error">{{ moveError }}</p>
          <ul class="np-games">
            <li v-for="g in choicesShown" :key="g.id">
              <button type="button" @click="moveTo(g)">{{ g.title }}</button>
            </li>
            <li v-if="!choicesShown.length" class="np-games-empty">
              No game matches.
            </li>
          </ul>
          <div class="ui-modal-actions">
            <button
              type="button"
              class="ui-btn ui-btn-ghost"
              @click="moving = null"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>

      <!-- history -->
      <div
        v-if="historyFor"
        class="ui-backdrop"
        @click.self="historyFor = null"
      >
        <div
          class="ui-modal np-dialog np-history"
          role="dialog"
          aria-modal="true"
          aria-label="Note history"
        >
          <h3>History of "{{ historyFor.name }}"</h3>
          <p v-if="historyLoading" class="np-dialog-hint">Loading…</p>
          <p v-else-if="!versions.length" class="np-dialog-hint">
            No earlier versions yet. Each time you save a change, the text it
            replaces is kept here.
          </p>
          <div v-else class="np-history-body">
            <ul class="np-versions">
              <li v-for="v in versions" :key="v.id">
                <button
                  type="button"
                  :class="{ on: previewing?.version.id === v.id }"
                  @click="previewVersion(v)"
                >
                  <strong>{{
                    dateFormat.format(new Date(v.saved_at * 1000))
                  }}</strong>
                  <span
                    >{{
                      new Date(v.saved_at * 1000).toLocaleTimeString([], {
                        hour: "numeric",
                        minute: "2-digit",
                      })
                    }}
                    · {{ wordLabel(v.words) }}</span
                  >
                  <em>{{ v.preview }}</em>
                </button>
              </li>
            </ul>
            <div class="np-version-view">
              <!-- eslint-disable-next-line vue/no-v-html -->
              <div
                v-if="previewing"
                class="np-rendered"
                v-html="render(previewing.text)"
              ></div>
              <p v-else class="np-dialog-hint">Pick a version to read it.</p>
            </div>
          </div>
          <div class="ui-modal-actions">
            <button
              type="button"
              class="ui-btn ui-btn-ghost"
              @click="historyFor = null"
            >
              Close
            </button>
            <button
              type="button"
              class="ui-btn ui-btn-primary"
              :disabled="!previewing"
              @click="restoreVersion"
            >
              Restore this version
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.np {
  width: 100%;
  min-width: 0;
  position: relative;
}
.np-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 14px;
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
.np-new {
  position: relative;
  display: flex;
  gap: 4px;
}
.np-more {
  padding: 0 10px;
}
.np-templates {
  position: absolute;
  right: 0;
  top: calc(100% + 6px);
  z-index: var(--ui-z-popover, 350);
  width: 280px;
  list-style: none;
  margin: 0;
  padding: 6px;
  background: #171717;
  border: 1px solid #2b2b2b;
  border-radius: 12px;
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.5);
}
.np-templates button {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px 10px;
  border: none;
  border-radius: 8px;
  background: none;
  color: #ddd;
  text-align: left;
  font-family: inherit;
  cursor: pointer;
}
.np-templates button:hover {
  background: rgba(255, 255, 255, 0.06);
}
.np-templates button span {
  font-size: 0.74rem;
  color: #888;
}
.np-tagbar {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 16px;
}
.np-skel {
  min-height: 180px;
  border: 1px solid #262626;
  border-radius: 12px;
  background: linear-gradient(100deg, #181818 30%, #212121 50%, #181818 70%);
  background-size: 200% 100%;
  animation: shimmer 1.4s linear infinite;
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
  .np-skel {
    animation: none;
  }
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
  font-family: inherit;
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    background 0.15s ease;
  min-height: var(--ui-empty-min, 280px);
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
  font-size: 0.85rem;
}
.np-empty:hover {
  border-color: #d68a34;
  background: rgba(214, 138, 52, 0.06);
}
.np-empty strong {
  color: #f2f2f2;
  font-size: 1rem;
}
.np-starters {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
  margin-top: 10px;
}
.np-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(270px, 1fr));
  gap: 16px;
}
.np-card {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
  min-height: 180px;
  padding: 14px 16px 12px;
  background: #141414;
  border: 1px solid #262626;
  border-radius: 12px;
  cursor: pointer;
  transition: border-color 0.15s ease;
}
.np-card.pinned {
  border-color: rgba(214, 138, 52, 0.4);
}
.np-card:hover,
.np-card:focus-visible {
  border-color: rgba(214, 138, 52, 0.6);
  outline: none;
}
.np-card-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}
.np-card-title {
  margin: 0;
  flex: 1;
  min-width: 0;
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
.np-card-btns {
  position: relative;
  display: flex;
  gap: 2px;
  flex-shrink: 0;
}
.np-pin,
.np-menu-btn {
  width: 26px;
  height: 26px;
  border: none;
  border-radius: 7px;
  background: none;
  color: #6f6f6f;
  font-size: 1.1rem;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}
.np-pin {
  opacity: 0;
}
.np-pin.on,
.np-card:hover .np-pin,
.np-card:focus-within .np-pin {
  opacity: 1;
}
.np-pin.on {
  color: #d68a34;
}
.np-pin:hover,
.np-menu-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}
@media (hover: none) {
  .np-pin {
    opacity: 1;
  }
}
.np-menu {
  position: absolute;
  right: 0;
  top: calc(100% + 4px);
  z-index: var(--ui-z-popover, 350);
  min-width: 190px;
  list-style: none;
  margin: 0;
  padding: 6px;
  background: #171717;
  border: 1px solid #2b2b2b;
  border-radius: 12px;
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.5);
}
.np-menu button {
  width: 100%;
  padding: 8px 10px;
  border: none;
  border-radius: 8px;
  background: none;
  color: #ddd;
  font-family: inherit;
  font-size: 0.82rem;
  text-align: left;
  cursor: pointer;
}
.np-menu button:hover {
  background: rgba(255, 255, 255, 0.06);
}
.np-menu .danger {
  color: #d96f6f;
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
  -webkit-line-clamp: 4;
  line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.np-card-chips,
.np-page-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}
.np-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  max-width: 100%;
  background: rgba(255, 255, 255, 0.07);
  color: #aaa;
  border: none;
  border-radius: 999px;
  padding: 2px 9px;
  font-family: inherit;
  font-size: 0.7rem;
}
.np-chip.ach {
  background: rgba(214, 138, 52, 0.16);
  color: #d68a34;
}
.np-chip.link {
  cursor: pointer;
}
.np-chip.link:hover {
  background: rgba(214, 138, 52, 0.28);
}
.np-progress {
  display: flex;
  align-items: center;
  gap: 8px;
}
.np-progress-bar {
  flex: 1;
  height: 4px;
  border-radius: 999px;
  background: #262626;
  overflow: hidden;
}
.np-progress-bar span {
  display: block;
  height: 100%;
  background: #7fc08a;
  border-radius: 999px;
}
.np-progress-n {
  font-size: 0.72rem;
  color: #888;
  font-variant-numeric: tabular-nums;
}
.np-card-foot {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  color: #6f6f6f;
  font-size: 0.72rem;
  font-variant-numeric: tabular-nums;
}
.np-card-foot span:first-child {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.np-card-foot span:last-child {
  flex-shrink: 0;
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
.np-more-wrap {
  position: relative;
}
.np-more-wrap .np-menu-btn {
  width: auto;
  color: #bbb;
}
.np-status {
  font-size: 0.78rem;
  color: #d68a34;
}
.np-previewtoggle {
  display: none;
}
.ui-btn.on {
  color: #d68a34;
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
  flex-wrap: wrap;
  gap: 4px 14px;
  margin: 0 0 12px;
  color: #777;
  font-size: 0.8rem;
}
.np-page-chips {
  margin-bottom: 16px;
}
.np-page .np-rendered {
  padding-top: 16px;
  border-top: 1px solid #262626;
}

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
  cursor: pointer;
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
.np-meta-edit {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}
.np-tags {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  flex: 1 1 260px;
  height: auto;
  min-height: 38px;
  padding: 5px 8px;
  cursor: text;
}
.np-tags:focus-within {
  border-color: var(--ui-accent);
}
.np-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: rgba(255, 255, 255, 0.09);
  border-radius: 999px;
  padding: 2px 4px 2px 10px;
  font-size: 0.76rem;
  color: #ddd;
}
.np-tag button {
  width: 16px;
  height: 16px;
  border: none;
  border-radius: 50%;
  background: none;
  color: #999;
  font-size: 0.6rem;
  cursor: pointer;
  padding: 0;
}
.np-tag button:hover {
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
}
.np-tags input {
  flex: 1;
  min-width: 100px;
  background: none;
  border: none;
  outline: none;
  color: var(--ui-text);
  font: inherit;
  font-size: 0.85rem;
}
.np-pinbox {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.8rem;
  color: #9c9c9c;
  cursor: pointer;
}
.np-pinbox input {
  accent-color: #d68a34;
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
.np-toast {
  position: fixed;
  left: 50%;
  bottom: 28px;
  transform: translateX(-50%);
  z-index: var(--ui-z-dialog, 400);
  max-width: calc(100vw - 32px);
  background: #171717;
  border: 1px solid #2b2b2b;
  border-radius: 999px;
  padding: 8px 18px;
  font-size: 0.82rem;
  font-weight: 600;
  color: #f2f2f2;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.12s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.np-dialog {
  max-width: 460px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.np-dialog h3 {
  margin: 0;
  overflow-wrap: anywhere;
}
.np-dialog-hint {
  margin: 0;
  font-size: 0.82rem;
  color: #888;
}
.np-dialog-error {
  margin: 0;
  font-size: 0.82rem;
  color: #fca5a5;
}
.np-games {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 280px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.np-games button {
  width: 100%;
  padding: 9px 10px;
  border: none;
  border-radius: 8px;
  background: none;
  color: #ddd;
  font-family: inherit;
  font-size: 0.85rem;
  text-align: left;
  cursor: pointer;
}
.np-games button:hover {
  background: rgba(214, 138, 52, 0.14);
  color: #fff;
}
.np-games-empty {
  padding: 10px;
  color: #777;
  font-size: 0.82rem;
}
.np-history {
  max-width: 860px;
}
.np-history-body {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  gap: 16px;
  min-height: 260px;
  max-height: 55vh;
}
.np-versions {
  list-style: none;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.np-versions button {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px 10px;
  border: 1px solid transparent;
  border-radius: 8px;
  background: none;
  color: #ccc;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
}
.np-versions button:hover {
  background: rgba(255, 255, 255, 0.05);
}
.np-versions button.on {
  border-color: rgba(214, 138, 52, 0.5);
  background: rgba(214, 138, 52, 0.08);
}
.np-versions strong {
  font-size: 0.82rem;
  color: #f2f2f2;
}
.np-versions span {
  font-size: 0.72rem;
  color: #888;
}
.np-versions em {
  font-size: 0.74rem;
  font-style: normal;
  color: #777;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.np-version-view {
  min-width: 0;
  overflow-y: auto;
  padding: 12px 14px;
  background: #101010;
  border: 1px solid #262626;
  border-radius: 10px;
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
  .np-history-body {
    grid-template-columns: 1fr;
    max-height: none;
  }
}
</style>
