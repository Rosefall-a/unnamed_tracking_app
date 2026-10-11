<script setup lang="ts">
// A save or a world, shown as a card like a screenshot or a clip: a 16:9 top
// with an icon, the name and a line of facts underneath, and copy, download,
// add-version, edit and delete on hover.
import { computed, ref } from "vue";
import { copyLink } from "../utils/copyMedia";
import type { GameArchiveData } from "../services/gameArchives";

const props = defineProps<{
  archive: GameArchiveData;
  kind: "save" | "world";
  selecting?: boolean;
  selected?: boolean;
  // a new version is uploading
  uploading?: boolean;
}>();

const emit = defineEmits<{
  toggle: [archive: GameArchiveData];
  edit: [archive: GameArchiveData];
  delete: [archive: GameArchiveData];
  "add-version": [archive: GameArchiveData, files: File[]];
}>();

const latest = computed(() => props.archive.versions[0] ?? null);
const dateFormat = new Intl.DateTimeFormat(undefined, {
  month: "short",
  day: "numeric",
  year: "numeric",
});
function size(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
  return `${(bytes / 1024 ** 3).toFixed(2)} GB`;
}
const facts = computed(() => {
  const bits: string[] = [];
  if (latest.value) {
    bits.push(dateFormat.format(new Date(latest.value.uploaded_at * 1000)));
    bits.push(size(latest.value.size));
  }
  return bits;
});
const versionCount = computed(() => props.archive.versions.length);
const tags = computed(() => props.archive.tags ?? []);

const picker = ref<HTMLInputElement | null>(null);
function onPicked(e: Event) {
  const input = e.target as HTMLInputElement;
  const files = Array.from(input.files ?? []);
  input.value = "";
  if (files.length) emit("add-version", props.archive, files);
}
function onThumbClick() {
  if (props.selecting) emit("toggle", props.archive);
  else emit("edit", props.archive);
}
const copied = ref(false);
async function copy() {
  if (!latest.value) return;
  try {
    await copyLink(latest.value.url);
    copied.value = true;
    window.setTimeout(() => (copied.value = false), 1400);
  } catch {
    // the browser blocked the clipboard
  }
}
</script>

<template>
  <article class="ac" :class="{ selecting, selected }">
    <div class="ac-thumb" @click="onThumbClick">
      <span v-if="selecting" class="ac-check" aria-hidden="true">
        <svg
          v-if="selected"
          viewBox="0 0 24 24"
          width="14"
          height="14"
          fill="none"
          stroke="currentColor"
          stroke-width="3.2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <polyline points="20 6 9 17 4 12" />
        </svg>
      </span>

      <div class="ac-art">
        <svg
          v-if="kind === 'world'"
          viewBox="0 0 24 24"
          width="36"
          height="36"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M3 6l6-3 6 3 6-3v15l-6 3-6-3-6 3z" />
          <path d="M9 3v15M15 6v15" />
        </svg>
        <svg
          v-else
          viewBox="0 0 24 24"
          width="36"
          height="36"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M5 4h11l3 3v13H5z" />
          <path d="M8 4v5h7V4" />
          <rect x="8" y="14" width="8" height="6" rx="1" />
        </svg>
      </div>

      <span v-if="versionCount > 1" class="ac-versions"
        >{{ versionCount }} versions</span
      >
      <span v-if="uploading" class="ac-uploading">Uploading…</span>

      <div v-if="!selecting" class="ac-actions" @click.stop>
        <button
          type="button"
          :title="copied ? 'Copied' : 'Copy link'"
          @click="copy"
        >
          <svg
            viewBox="0 0 24 24"
            width="13"
            height="13"
            fill="none"
            stroke="currentColor"
            stroke-width="2.2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <rect x="9" y="9" width="11" height="11" rx="2" />
            <path d="M5 15V6a2 2 0 0 1 2-2h9" />
          </svg>
        </button>
        <a
          v-if="latest"
          :href="latest.url"
          title="Download the latest version"
          download
        >
          <svg
            viewBox="0 0 24 24"
            width="13"
            height="13"
            fill="none"
            stroke="currentColor"
            stroke-width="2.2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M12 4v11M7 11l5 5 5-5M5 20h14" />
          </svg>
        </a>
        <button
          type="button"
          title="Add a new version"
          :disabled="uploading"
          @click="picker?.click()"
        >
          <svg
            viewBox="0 0 24 24"
            width="13"
            height="13"
            fill="none"
            stroke="currentColor"
            stroke-width="2.4"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M12 5v14M5 12h14" />
          </svg>
        </button>
        <button
          type="button"
          title="Edit details"
          @click="emit('edit', archive)"
        >
          <svg
            viewBox="0 0 24 24"
            width="13"
            height="13"
            fill="none"
            stroke="currentColor"
            stroke-width="2.2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M12 20h9" />
            <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z" />
          </svg>
        </button>
        <button type="button" title="Delete" @click="emit('delete', archive)">
          <svg
            viewBox="0 0 24 24"
            width="13"
            height="13"
            fill="none"
            stroke="currentColor"
            stroke-width="2.2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14" />
          </svg>
        </button>
      </div>
      <input ref="picker" type="file" class="ac-input" @change="onPicked" />
    </div>

    <div class="ac-body">
      <p class="ac-title" :title="archive.name">{{ archive.name }}</p>
      <div class="ac-meta">
        <span v-for="f in facts" :key="f">{{ f }}</span>
        <span v-if="versionCount === 1" class="ac-faint">1 version</span>
        <span v-for="t in tags.slice(0, 2)" :key="t" class="ac-chip">{{
          t
        }}</span>
        <span v-if="tags.length > 2" class="ac-chip"
          >+{{ tags.length - 2 }}</span
        >
      </div>
      <slot />
    </div>
  </article>
</template>

<style scoped>
.ac {
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: #141414;
  border: 1px solid #262626;
  border-radius: 12px;
  overflow: hidden;
  transition: border-color 0.15s ease;
}
.ac:hover {
  border-color: #3a3a3a;
}
.ac.selected {
  border-color: #d68a34;
  box-shadow: 0 0 0 1px #d68a34;
}
.ac-thumb {
  position: relative;
  aspect-ratio: 16 / 9;
  background: #0a0a0a;
  cursor: pointer;
  overflow: hidden;
}
.ac-art {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #d68a34;
  background: radial-gradient(
    circle at 50% 40%,
    rgba(214, 138, 52, 0.18),
    rgba(214, 138, 52, 0.05) 70%
  );
}
.ac-art svg {
  opacity: 0.7;
}
.ac-versions,
.ac-uploading {
  position: absolute;
  right: 8px;
  bottom: 8px;
  z-index: 1;
  padding: 2px 8px;
  border-radius: 6px;
  background: rgba(15, 15, 15, 0.82);
  color: #eee;
  font-size: 0.7rem;
  font-weight: 700;
  pointer-events: none;
}
.ac-uploading {
  left: 8px;
  right: auto;
  color: #d68a34;
}
.ac-input {
  display: none;
}
.ac-check {
  position: absolute;
  left: 8px;
  top: 8px;
  z-index: 3;
  width: 22px;
  height: 22px;
  border-radius: 6px;
  border: 2px solid rgba(255, 255, 255, 0.85);
  background: rgba(15, 15, 15, 0.6);
  color: #14100a;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}
.ac.selected .ac-check {
  background: #d68a34;
  border-color: #d68a34;
}
.ac-actions {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 2;
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.15s ease;
}
.ac:hover .ac-actions,
.ac:focus-within .ac-actions {
  opacity: 1;
}
@media (hover: none) {
  .ac-actions {
    opacity: 1;
  }
}
.ac-actions button,
.ac-actions a {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  border: none;
  background: rgba(15, 15, 15, 0.78);
  color: #eee;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  cursor: pointer;
  text-decoration: none;
  backdrop-filter: blur(4px);
}
.ac-actions button:hover,
.ac-actions a:hover {
  background: #d68a34;
  color: #14100a;
}
.ac-actions button:disabled {
  opacity: 0.5;
  cursor: default;
}
.ac-actions button:last-of-type:hover {
  background: #d96f6f;
  color: #fff;
}
.ac-body {
  min-height: 74px;
  box-sizing: border-box;
  padding: 10px 12px 12px;
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
}
.ac-title {
  margin: 0;
  font-size: 0.84rem;
  font-weight: 600;
  color: #e8e8e8;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ac-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 5px 6px;
  font-size: 0.72rem;
  color: #777;
  min-width: 0;
}
.ac-faint {
  color: #666;
}
.ac-chip {
  background: rgba(255, 255, 255, 0.07);
  color: #aaa;
  border-radius: 999px;
  padding: 1px 8px;
  font-size: 0.68rem;
}
</style>
