<script setup lang="ts">
// Edit a save or a world: its name, a note and tags, and its versions. Every
// upload to a save is kept as a version, so this is where you download an
// older one or remove one you no longer want, and add a new one.
import UiModal from "./UiModal.vue";
import { ref, computed } from "vue";
import type { ArchiveVersion, GameArchiveData } from "../services/gameArchives";

const props = defineProps<{
  archive: GameArchiveData;
  // "save" or "world", for the wording
  noun: string;
  uploading?: boolean;
}>();

const emit = defineEmits<{
  close: [];
  save: [
    archive: GameArchiveData,
    patch: { name?: string; note?: string | null; tags?: string[] },
  ];
  delete: [archive: GameArchiveData];
  "add-version": [archive: GameArchiveData, files: File[]];
  "delete-version": [archive: GameArchiveData, version: ArchiveVersion];
}>();

const name = ref(props.archive.name);
const note = ref(props.archive.note ?? "");
const tags = ref<string[]>([...(props.archive.tags ?? [])]);
const tagDraft = ref("");
const tagInput = ref<HTMLInputElement | null>(null);
const picker = ref<HTMLInputElement | null>(null);

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

const dirty = computed(
  () =>
    tagDraft.value.trim() !== "" ||
    name.value.trim() !== props.archive.name ||
    note.value.trim() !== (props.archive.note ?? "") ||
    JSON.stringify(tags.value) !== JSON.stringify(props.archive.tags ?? []),
);

function save() {
  commitTag();
  const patch: { name?: string; note?: string | null; tags?: string[] } = {};
  if (name.value.trim() && name.value.trim() !== props.archive.name)
    patch.name = name.value.trim();
  if (note.value.trim() !== (props.archive.note ?? ""))
    patch.note = note.value.trim() || null;
  if (JSON.stringify(tags.value) !== JSON.stringify(props.archive.tags ?? []))
    patch.tags = tags.value;
  if (Object.keys(patch).length) emit("save", props.archive, patch);
  emit("close");
}
function remove() {
  emit("delete", props.archive);
  emit("close");
}
function onPicked(e: Event) {
  const input = e.target as HTMLInputElement;
  const files = Array.from(input.files ?? []);
  input.value = "";
  if (files.length) emit("add-version", props.archive, files);
}

const dateFormat = new Intl.DateTimeFormat(undefined, {
  month: "short",
  day: "numeric",
  year: "numeric",
  hour: "numeric",
  minute: "2-digit",
});
function size(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
  return `${(bytes / 1024 ** 3).toFixed(2)} GB`;
}
function displayName(filename: string): string {
  const i = filename.indexOf("_");
  return i > 0 ? filename.slice(i + 1) : filename;
}

function onKey(e: KeyboardEvent) {
  if (
    !e.isComposing &&
    e.key === "Enter" &&
    (e.ctrlKey || e.metaKey) &&
    dirty.value
  ) {
    e.preventDefault();
    save();
  }
}
</script>

<template>
  <UiModal
    :title="name.trim() || archive.name"
    :description="
      archive.versions.length +
      (archive.versions.length === 1 ? ' version' : ' versions')
    "
    size="wide"
    @close="emit('close')"
    @keydown="onKey"
  >
    <div class="aed-body">
      <section class="aed-group">
        <h4>Details</h4>
        <label class="aed-field">
          <span>Name</span>
          <input v-model="name" type="text" class="ui-field" maxlength="200" />
        </label>
        <label class="aed-field">
          <span>Note</span>
          <textarea
            v-model="note"
            class="ui-field"
            rows="3"
            :placeholder="`What is this ${noun}?`"
          ></textarea>
        </label>
        <div class="aed-field">
          <span>Tags</span>
          <div class="aed-tags ui-field" @click="tagInput?.focus()">
            <span v-for="t in tags" :key="t" class="aed-tag">
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
              :placeholder="tags.length ? '' : 'backup, before boss, 100%'"
              @keydown="onTagKey"
              @blur="commitTag"
            />
          </div>
        </div>
      </section>

      <section class="aed-group">
        <div class="aed-versions-head">
          <h4>Versions</h4>
          <button
            type="button"
            class="ui-btn ui-btn-secondary ui-btn-sm"
            :disabled="uploading"
            @click="picker?.click()"
          >
            {{ uploading ? "Uploading…" : "+ New version" }}
          </button>
          <input
            ref="picker"
            type="file"
            class="aed-input"
            @change="onPicked"
          />
        </div>
        <ul class="aed-versions">
          <li v-for="(v, i) in archive.versions" :key="v.id">
            <div class="aed-v-main">
              <strong>{{
                dateFormat.format(new Date(v.uploaded_at * 1000))
              }}</strong>
              <span>{{ displayName(v.filename) }} · {{ size(v.size) }}</span>
            </div>
            <span v-if="i === 0" class="aed-latest">Latest</span>
            <a :href="v.url" class="ui-btn ui-btn-ghost ui-btn-sm" download
              >Download</a
            >
            <button
              type="button"
              class="ui-btn ui-btn-danger-soft ui-btn-sm"
              :disabled="archive.versions.length <= 1"
              :title="
                archive.versions.length <= 1
                  ? `Delete the whole ${noun} to remove its last version`
                  : 'Move this version to the trash'
              "
              @click="emit('delete-version', archive, v)"
            >
              Delete
            </button>
          </li>
        </ul>
      </section>
    </div>

    <template #footer>
      <button type="button" class="ui-btn ui-btn-danger-soft" @click="remove">
        Delete {{ noun }}
      </button>
      <span class="aed-spacer"></span>
      <button type="button" class="ui-btn ui-btn-ghost" @click="emit('close')">
        Cancel
      </button>
      <button
        type="button"
        class="ui-btn ui-btn-primary"
        :disabled="!dirty"
        @click="save"
      >
        Save
      </button>
    </template>
  </UiModal>
</template>

<style scoped>
.aed {
  max-width: 560px;
  max-height: 90vh;
  padding: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.aed-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 22px 14px;
  border-bottom: 1px solid var(--ui-surface-2);
}
.aed-head-text {
  min-width: 0;
}
.aed-head h3 {
  margin: 0;
  font-size: 1.05rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.aed-head p {
  margin: 3px 0 0;
  font-size: 0.78rem;
  color: var(--ui-faint);
}
.aed-x {
  width: 30px;
  height: 30px;
  border: none;
  border-radius: var(--ui-radius-control);
  background: none;
  color: var(--ui-dim);
  cursor: pointer;
}
.aed-x:hover {
  background: color-mix(in srgb, var(--ui-text) 8%, transparent);
  color: var(--ui-text);
}
.aed-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 22px;
  padding: 20px 22px;
}
.aed-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.aed-group h4 {
  margin: 0;
  font-size: 0.7rem;
  font-weight: var(--ui-weight-title);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ui-accent-text);
}
.aed-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.aed-field > span {
  font-size: 0.74rem;
  font-weight: 700;
  color: var(--ui-dim);
}
.aed-field input.ui-field,
.aed-field textarea {
  width: 100%;
}
.aed-tags {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  height: auto;
  min-height: 38px;
  padding: 5px 8px;
  cursor: text;
}
.aed-tags:focus-within {
  border-color: var(--ui-accent);
}
.aed-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: color-mix(in srgb, var(--ui-text) 9%, transparent);
  border-radius: 999px;
  padding: 2px 4px 2px 10px;
  font-size: 0.76rem;
  color: var(--ui-text);
}
.aed-tag button {
  width: 16px;
  height: 16px;
  border: none;
  border-radius: 50%;
  background: none;
  color: var(--ui-dim);
  font-size: 0.6rem;
  cursor: pointer;
  padding: 0;
}
.aed-tag button:hover {
  background: color-mix(in srgb, var(--ui-text) 15%, transparent);
  color: var(--ui-text);
}
.aed-tags input {
  flex: 1;
  min-width: 90px;
  background: none;
  border: none;
  outline: none;
  color: var(--ui-text);
  font: inherit;
  font-size: 0.85rem;
}
.aed-versions-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.aed-input {
  display: none;
}
.aed-versions {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 240px;
  overflow-y: auto;
}
.aed-versions li {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  background: var(--ui-surface);
  border: 1px solid var(--ui-surface-2);
  border-radius: var(--ui-radius-row);
}
.aed-v-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.aed-v-main strong {
  font-size: 0.82rem;
  color: #f0f0f0;
}
.aed-v-main span {
  font-size: 0.74rem;
  color: var(--ui-dim);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.aed-latest {
  font-size: 0.68rem;
  font-weight: var(--ui-weight-title);
  color: var(--ui-accent-text);
  background: color-mix(in srgb, var(--ui-accent) 14%, transparent);
  border-radius: 999px;
  padding: 2px 8px;
}
.aed-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 22px;
  border-top: 1px solid var(--ui-surface-2);
  background: var(--ui-popover, var(--ui-surface));
}
.aed-spacer {
  flex: 1;
}
</style>
