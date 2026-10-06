<script
  setup
  lang="ts"
  generic="
    T extends FileDetails,
    TR extends { id: string; filename: string; purge_at: number }
  "
>
// One screen for a game's Screenshots, Clips, Soundtrack, Docs or Modpack: the
// gallery is the page, and adding is part of it. Drop files anywhere over the
// page, press Add, or paste an image with Ctrl+V. An empty tab shows one big
// Add card; once there are files, Add sits in the header. The parent owns the
// data and does the upload. With `scoped`, dropping only works over this panel
// itself, for a page that holds more than one.
import { ref, computed, watch, onMounted, onBeforeUnmount } from "vue";
import MediaTile from "./MediaTile.vue";
import MediaEditDialog from "./MediaEditDialog.vue";
import AchievementPicker from "./AchievementPicker.vue";
import { settleDuration } from "../utils/videoDuration";
import {
  copyImage,
  copyLink,
  downloadMedia,
  originalName,
} from "../utils/copyMedia";
import {
  dateFromAchievementPref,
  isGuess,
  mediaSeconds,
  secondsFromDateInput,
  setDateFromAchievementPref,
  unlockSeconds,
} from "../utils/mediaDate";
import type {
  FileDetails,
  GameFileKind,
  MediaItemUpdate,
  MediaKind,
} from "../services/media";
import type { Achievement } from "../types/game";
import type { GameProfile } from "../services/gameProfiles";
import { documentReaderUrl } from "../state/pluginExtensions";

type MediaItem = T;
type Kind = MediaKind | GameFileKind;

const props = defineProps<{
  kind: Kind;
  gameId?: string;
  items: T[];
  trash: TR[];
  achievements?: Achievement[];
  profiles?: GameProfile[];
  loading: boolean;
  uploading: boolean;
  error: string | null;
  scoped?: boolean;
  // re-reads a file's date from the file itself; true when it found one
  detect?: (item: MediaItem) => Promise<"file" | "achievement" | "none">;
}>();

const emit = defineEmits<{
  files: [files: File[]];
  delete: [item: MediaItem];
  save: [item: MediaItem, patch: MediaItemUpdate];
  "bulk-save": [updates: { id: string; patch: MediaItemUpdate }[]];
  "bulk-delete": [items: MediaItem[]];
  "bulk-detect": [ids: string[]];
  restore: [item: TR];
  "open-achievement": [achievementId: string];
  thumbnail: [item: MediaItem, blob: Blob, duration: number];
  problem: [message: string];
}>();

const achievementList = computed(() => props.achievements ?? []);
const hasPreview = computed(
  () => props.kind === "screenshot" || props.kind === "clip",
);

const LABELS: Record<
  Kind,
  {
    title: string;
    plural: string;
    singular: string;
    accept: string;
    what: string;
  }
> = {
  screenshot: {
    title: "Screenshots",
    plural: "screenshots",
    singular: "screenshot",
    accept: "image/*",
    what: "images",
  },
  clip: {
    title: "Clips",
    plural: "clips",
    singular: "clip",
    accept: "video/*",
    what: "videos",
  },
  soundtrack: {
    title: "Soundtrack",
    plural: "tracks",
    singular: "track",
    accept: "audio/*",
    what: "audio files",
  },
  doc: {
    title: "Docs",
    plural: "docs",
    singular: "doc",
    accept: "*/*",
    what: "files of any kind",
  },
  modpack: {
    title: "Modpack",
    plural: "modpack files",
    singular: "modpack file",
    accept: "*/*",
    what: "files of any kind",
  },
  save: {
    title: "Saves",
    plural: "saves",
    singular: "save",
    accept: "*/*",
    what: "files of any kind",
  },
  world_save: {
    title: "Worlds",
    plural: "worlds",
    singular: "world",
    accept: "*/*",
    what: "files of any kind",
  },
};
const label = computed(() => LABELS[props.kind]);

const AUDIO_EXT = /\.(mp3|ogg|oga|opus|wav|flac|m4a|aac)$/i;
const VIDEO_EXT = /\.(mp4|webm|mkv|mov|avi|m4v)$/i;
const IMAGE_EXT = /\.(png|jpe?g|gif|webp|bmp|avif)$/i;
function fits(file: File): boolean {
  const t = file.type;
  if (props.kind === "screenshot")
    return t.startsWith("image/") || (!t && IMAGE_EXT.test(file.name));
  if (props.kind === "clip")
    return t.startsWith("video/") || (!t && VIDEO_EXT.test(file.name));
  if (props.kind === "soundtrack")
    return t.startsWith("audio/") || (!t && AUDIO_EXT.test(file.name));
  return true;
}

function take(files: File[]) {
  if (!files.length) return;
  const good = files.filter(fits);
  const skipped = files.length - good.length;
  if (skipped) {
    emit(
      "problem",
      `${skipped} file${skipped === 1 ? "" : "s"} skipped: this tab takes ${label.value.what} only.`,
    );
  }
  if (good.length) emit("files", good);
}

// ---- add: button, drop anywhere, paste ----
const picker = ref<HTMLInputElement | null>(null);
function openPicker() {
  picker.value?.click();
}
function onPicked(e: Event) {
  const input = e.target as HTMLInputElement;
  take(Array.from(input.files ?? []));
  input.value = "";
}

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
  if (!hasFiles(e)) return;
  e.preventDefault();
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
  const items = Array.from(e.dataTransfer?.items ?? []);
  const folder = items.some(
    (i) =>
      (
        i as DataTransferItem & {
          webkitGetAsEntry?: () => { isDirectory?: boolean } | null;
        }
      ).webkitGetAsEntry?.()?.isDirectory,
  );
  if (folder) {
    emit("problem", "That is a folder. Drop the files inside it instead.");
    return;
  }
  take(Array.from(e.dataTransfer?.files ?? []));
}

function typing(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null;
  const tag = el?.tagName;
  return (
    tag === "INPUT" ||
    tag === "TEXTAREA" ||
    tag === "SELECT" ||
    !!el?.isContentEditable
  );
}
function onPaste(e: ClipboardEvent) {
  if (typing(e.target) || editing.value) return;
  const files = Array.from(e.clipboardData?.files ?? []);
  if (!files.length) return;
  e.preventDefault();
  // a pasted screenshot arrives as an unnamed "image.png"
  take(
    files.map((f) =>
      f.name === "image.png"
        ? new File([f], `pasted-${Date.now()}.png`, { type: f.type })
        : f,
    ),
  );
}

// ---- search, filter, sort ----
const query = ref("");
const filter = ref<string>("all");
const sort = ref<"newest" | "oldest" | "name">("newest");
const linkedIds = computed(
  () =>
    new Set(
      props.items
        .map((i) => i.linked_achievement_id)
        .filter((id): id is string => !!id),
    ),
);
const filterAchievements = computed(() =>
  achievementList.value.filter((a) => linkedIds.value.has(a.id)),
);
const linkedCount = computed(
  () => props.items.filter((i) => i.linked_achievement_id).length,
);
watch(
  () => props.kind,
  () => {
    filter.value = "all";
    query.value = "";
  },
);
watch(filterAchievements, (list) => {
  if (
    filter.value !== "all" &&
    filter.value !== "linked" &&
    !list.some((a) => a.id === filter.value)
  )
    filter.value = "all";
});

function achievementName(id: string | null): string | null {
  if (!id) return null;
  return achievementList.value.find((a) => a.id === id)?.name ?? null;
}
function haystack(i: MediaItem): string {
  return [
    i.title ?? "",
    originalName(i.filename),
    i.note ?? "",
    i.tags.join(" "),
    achievementName(i.linked_achievement_id ?? null) ?? "",
  ]
    .join(" ")
    .toLowerCase();
}
const visible = computed(() => {
  let list = [...props.items];
  if (filter.value === "linked")
    list = list.filter((i) => i.linked_achievement_id);
  else if (filter.value !== "all")
    list = list.filter((i) => i.linked_achievement_id === filter.value);
  const q = query.value.trim().toLowerCase();
  if (q) list = list.filter((i) => haystack(i).includes(q));
  if (sort.value === "name")
    list.sort((a, b) =>
      (a.title || originalName(a.filename)).localeCompare(
        b.title || originalName(b.filename),
      ),
    );
  else
    list.sort((a, b) =>
      sort.value === "oldest"
        ? mediaSeconds(a) - mediaSeconds(b)
        : mediaSeconds(b) - mediaSeconds(a),
    );
  return list;
});
const filtering = computed(
  () => filter.value !== "all" || !!query.value.trim(),
);
function clearFilters() {
  filter.value = "all";
  query.value = "";
}

// ---- copy, download, delete with undo, notices ----
const notice = ref<{ text: string; undo?: () => void } | null>(null);
let noticeTimer: number | undefined;
function flash(text: string, undo?: () => void, ms = 2200) {
  notice.value = { text, undo };
  window.clearTimeout(noticeTimer);
  noticeTimer = window.setTimeout(() => (notice.value = null), ms);
}
async function copy(item: MediaItem) {
  try {
    if (item.kind === "screenshot") {
      flash(
        (await copyImage(item.url)) === "image"
          ? "Image copied"
          : "Link copied",
      );
    } else {
      await copyLink(item.url);
      flash("Link copied");
    }
  } catch {
    emit("problem", "Could not copy. Your browser blocked clipboard access.");
  }
}
function download(item: MediaItem) {
  downloadMedia(item.url, originalName(item.filename));
}
function remove(item: MediaItem) {
  if (lightboxId.value === item.id) lightboxId.value = null;
  emit("delete", item);
  flash(
    "Moved to Deleted",
    () => {
      const gone = props.trash.find((t) => t.filename === item.filename);
      if (gone) emit("restore", gone);
      notice.value = null;
    },
    6000,
  );
}

// ---- viewer ----
const lightboxId = ref<string | null>(null);
const lightboxIndex = computed(() =>
  visible.value.findIndex((i) => i.id === lightboxId.value),
);
const lightboxItem = computed(() =>
  lightboxIndex.value === -1 ? null : visible.value[lightboxIndex.value],
);
function open(item: MediaItem) {
  if (item.kind === "screenshot" || item.kind === "clip")
    lightboxId.value = item.id;
  else editingId.value = item.id;
}
function step(delta: number) {
  const n = visible.value.length;
  if (!n || lightboxIndex.value === -1) return;
  lightboxId.value = visible.value[(lightboxIndex.value + delta + n) % n].id;
}
const editingId = ref<string | null>(null);
const editing = computed(
  () => props.items.find((i) => i.id === editingId.value) ?? null,
);
function onKey(e: KeyboardEvent) {
  if (!lightboxItem.value || editing.value) return;
  if (e.key === "Escape") lightboxId.value = null;
  else if (e.key === "ArrowRight") step(1);
  else if (e.key === "ArrowLeft") step(-1);
}
// The patch for tying a file to an achievement. When the setting is on and
// the file's date is only a guess, the achievement's unlock time becomes its
// date; a date read from the file or set by hand is never replaced.
const dateFromAchievement = ref(dateFromAchievementPref());
watch(dateFromAchievement, (on) => setDateFromAchievementPref(on));
function tiePatch(
  item: MediaItem,
  achievementId: string | null,
): MediaItemUpdate {
  const patch: MediaItemUpdate = { linked_achievement_id: achievementId };
  if (!achievementId || !dateFromAchievement.value || !isGuess(item))
    return patch;
  const when = unlockSeconds(
    achievementList.value.find((a) => a.id === achievementId),
  );
  if (when !== null) {
    patch.taken_at = when;
    patch.taken_source = "achievement";
  }
  return patch;
}
function retie(item: MediaItem, achievementId: string | null) {
  emit("save", item, tiePatch(item, achievementId));
}
function onSave(item: MediaItem, patch: MediaItemUpdate) {
  emit("save", item, patch);
}

// ---- select several, then act on them together ----
const selecting = ref(false);
const picked = ref<Set<string>>(new Set());
const bulkDate = ref("");
const pickedItems = computed(() =>
  props.items.filter((i) => picked.value.has(i.id)),
);
function toggleSelecting() {
  selecting.value = !selecting.value;
  picked.value = new Set();
  bulkDate.value = "";
}
function toggle(item: MediaItem) {
  const next = new Set(picked.value);
  if (next.has(item.id)) next.delete(item.id);
  else next.add(item.id);
  picked.value = next;
}
function selectAll() {
  picked.value =
    picked.value.size === visible.value.length
      ? new Set()
      : new Set(visible.value.map((i) => i.id));
}
function applyDate() {
  const seconds = secondsFromDateInput(bulkDate.value);
  if (seconds === null || !picked.value.size) return;
  emit(
    "bulk-save",
    [...picked.value].map((id) => ({ id, patch: { taken_at: seconds } })),
  );
  flash(`Date set on ${picked.value.size}`);
  bulkDate.value = "";
}
function bulkTie(id: string | null) {
  if (!picked.value.size) return;
  emit(
    "bulk-save",
    pickedItems.value.map((item) => ({
      id: item.id,
      patch: tiePatch(item, id),
    })),
  );
  flash(
    id
      ? `Tied ${picked.value.size} to the achievement`
      : `Untied ${picked.value.size}`,
  );
}
// each picked file takes the unlock time of the achievement it is tied to
const pickedWithUnlock = computed(() =>
  pickedItems.value.filter(
    (i) =>
      unlockSeconds(
        achievementList.value.find((a) => a.id === i.linked_achievement_id),
      ) !== null,
  ),
);
function bulkAchievementDates() {
  const updates = pickedWithUnlock.value.map((item) => ({
    id: item.id,
    patch: {
      taken_at: unlockSeconds(
        achievementList.value.find((a) => a.id === item.linked_achievement_id),
      ),
      taken_source: "achievement" as const,
    },
  }));
  if (!updates.length) return;
  emit("bulk-save", updates);
  flash(`Date taken from the achievement on ${updates.length}`);
}
function bulkDetect() {
  if (!picked.value.size) return;
  emit("bulk-detect", [...picked.value]);
  flash("Reading dates from the files");
}
function bulkRemove() {
  const items = pickedItems.value;
  if (!items.length) return;
  emit("bulk-delete", items);
  flash(`Moved ${items.length} to Deleted`);
  picked.value = new Set();
}
// leaving a tab or losing every file ends selecting
watch(
  () => [props.kind, props.items.length],
  () => {
    if (!props.items.length) selecting.value = false;
    picked.value = new Set(
      [...picked.value].filter((id) => props.items.some((i) => i.id === id)),
    );
  },
);

const showTrash = ref(false);
function daysLeft(purgeAt: number): number {
  return Math.max(0, Math.ceil((purgeAt * 1000 - Date.now()) / 86_400_000));
}

const rootEl = ref<HTMLElement | null>(null);
let dropTarget: HTMLElement | Window = window;
onMounted(() => {
  dropTarget = props.scoped && rootEl.value ? rootEl.value : window;
  const t = dropTarget as HTMLElement;
  t.addEventListener("dragenter", onDragEnter as (e: Event) => void);
  t.addEventListener("dragover", onDragOver as (e: Event) => void);
  t.addEventListener("dragleave", onDragLeave as (e: Event) => void);
  t.addEventListener("drop", onDrop as (e: Event) => void);
  if (!props.scoped) document.addEventListener("paste", onPaste);
  document.addEventListener("keydown", onKey);
});
onBeforeUnmount(() => {
  const t = dropTarget as HTMLElement;
  t.removeEventListener("dragenter", onDragEnter as (e: Event) => void);
  t.removeEventListener("dragover", onDragOver as (e: Event) => void);
  t.removeEventListener("dragleave", onDragLeave as (e: Event) => void);
  t.removeEventListener("drop", onDrop as (e: Event) => void);
  document.removeEventListener("paste", onPaste);
  document.removeEventListener("keydown", onKey);
  window.clearTimeout(noticeTimer);
});
</script>

<template>
  <div ref="rootEl" class="game-media">
    <div class="gm-header">
      <div class="gm-title">
        <h2>{{ label.title }}</h2>
        <span class="gm-count">{{ items.length }}</span>
      </div>
      <div v-if="items.length" class="gm-tools">
        <input
          v-model="query"
          type="search"
          class="ui-field gm-search"
          :placeholder="`Search ${label.plural}`"
          :aria-label="`Search ${label.plural}`"
        />
        <select
          v-if="linkedCount"
          v-model="filter"
          class="ui-field gm-select"
          aria-label="Filter by achievement"
        >
          <option value="all">All {{ label.plural }}</option>
          <option value="linked">
            Tied to an achievement ({{ linkedCount }})
          </option>
          <option v-for="a in filterAchievements" :key="a.id" :value="a.id">
            {{ a.name }}
          </option>
        </select>
        <select
          v-if="items.length > 1"
          v-model="sort"
          class="ui-field gm-select"
          aria-label="Sort"
        >
          <option value="newest">Newest first</option>
          <option value="oldest">Oldest first</option>
          <option value="name">Name</option>
        </select>
        <button
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
      <button
        v-else-if="trash.length"
        type="button"
        class="ui-btn ui-btn-ghost"
        :class="{ on: showTrash }"
        @click="showTrash = !showTrash"
      >
        Deleted ({{ trash.length }})
      </button>
      <input
        ref="picker"
        type="file"
        multiple
        :accept="label.accept"
        class="gm-input"
        @change="onPicked"
      />
    </div>

    <div v-if="selecting" class="gm-bulk">
      <span class="gm-bulk-count"
        >{{ picked.size }} of {{ visible.length }} selected</span
      >
      <button
        type="button"
        class="ui-btn ui-btn-ghost ui-btn-sm"
        @click="selectAll"
      >
        {{ picked.size === visible.length ? "Clear" : "Select all" }}
      </button>
      <span class="gm-bulk-sep"></span>
      <input
        v-model="bulkDate"
        type="date"
        class="ui-field gm-bulk-date"
        aria-label="Date to set"
      />
      <button
        type="button"
        class="ui-btn ui-btn-secondary ui-btn-sm"
        :disabled="!picked.size || !bulkDate"
        @click="applyDate"
      >
        Set date
      </button>
      <button
        v-if="detect"
        type="button"
        class="ui-btn ui-btn-secondary ui-btn-sm"
        :disabled="!picked.size"
        @click="bulkDetect"
      >
        Detect dates
      </button>
      <button
        v-if="achievementList.length"
        type="button"
        class="ui-btn ui-btn-secondary ui-btn-sm"
        :disabled="!pickedWithUnlock.length"
        :title="
          pickedWithUnlock.length
            ? 'Use the unlock time of each file\'s achievement'
            : 'Pick files that are tied to an unlocked achievement'
        "
        @click="bulkAchievementDates"
      >
        Use achievement dates
      </button>
      <AchievementPicker
        v-if="achievementList.length"
        compact
        :model-value="null"
        :achievements="achievementList"
        @change="bulkTie"
      />
      <label v-if="achievementList.length" class="gm-bulk-check">
        <input v-model="dateFromAchievement" type="checkbox" />
        <span>Tying also sets the date</span>
      </label>
      <button
        type="button"
        class="ui-btn ui-btn-danger-soft ui-btn-sm"
        :disabled="!picked.size"
        @click="bulkRemove"
      >
        Delete
      </button>
    </div>

    <div v-if="error" class="ui-error-box gm-error">
      <span>{{ error }}</span>
      <button
        type="button"
        class="gm-error-x"
        aria-label="Dismiss"
        @click="emit('problem', '')"
      >
        ✕
      </button>
    </div>

    <ul v-if="showTrash && trash.length" class="gm-trash">
      <li v-for="t in trash" :key="t.id">
        <span class="gm-trash-name">{{ originalName(t.filename) }}</span>
        <span class="gm-trash-meta">purges in {{ daysLeft(t.purge_at) }}d</span>
        <button
          type="button"
          class="ui-btn ui-btn-ghost ui-btn-sm"
          @click="emit('restore', t)"
        >
          Restore
        </button>
      </li>
    </ul>

    <div class="gm-body" :class="{ dropping: dragging }">
      <div
        v-if="loading && !items.length"
        class="gm-grid"
        aria-busy="true"
        aria-label="Loading"
      >
        <div v-for="n in 3" :key="n" class="gm-skel"></div>
      </div>

      <button
        v-else-if="!items.length"
        type="button"
        class="gm-empty"
        :disabled="uploading"
        @click="openPicker"
      >
        <span class="gm-plus">{{ uploading ? "…" : "+" }}</span>
        <strong>{{ uploading ? "Uploading" : `Add ${label.plural}` }}</strong>
        <span
          >Drop {{ label.what }} anywhere on this page, paste, or click to
          browse.</span
        >
      </button>

      <template v-else>
        <div class="gm-grid">
          <button
            type="button"
            class="gm-add-card"
            :disabled="uploading"
            @click="openPicker"
          >
            <span class="gm-add-thumb">
              <span v-if="uploading" class="gm-spin"></span>
              <span v-else class="gm-plus">+</span>
            </span>
            <span class="gm-add-body">
              <strong>{{
                uploading ? "Uploading" : `Add ${label.plural}`
              }}</strong>
              <span class="gm-add-sub">Drop, paste, or click to browse</span>
            </span>
          </button>
          <MediaTile
            v-for="item in visible"
            :key="item.id"
            :item="item"
            :reader-url="
              kind === 'doc' && gameId
                ? documentReaderUrl(gameId, item)
                : undefined
            "
            :selecting="selecting"
            :selected="picked.has(item.id)"
            :detect="detect"
            :achievements="achievementList"
            :profiles="profiles"
            @toggle="toggle"
            @preview="open"
            @delete="remove"
            @save="onSave"
            @copy="copy"
            @download="download"
            @open-achievement="emit('open-achievement', $event)"
            @thumbnail="
              (item, blob, duration) => emit('thumbnail', item, blob, duration)
            "
          />
        </div>
        <div v-if="!visible.length && filtering" class="gm-none">
          <span>Nothing matches.</span>
          <button
            type="button"
            class="ui-btn ui-btn-ghost ui-btn-sm"
            @click="clearFilters"
          >
            Clear filters
          </button>
        </div>
      </template>

      <Transition name="fade">
        <div v-if="dragging" class="gm-drop" aria-hidden="true">
          <span class="gm-plus">+</span>
          <strong>Drop to add {{ label.plural }}</strong>
        </div>
      </Transition>
    </div>

    <Transition name="fade">
      <div v-if="notice" class="gm-toast" role="status">
        <span>{{ notice.text }}</span>
        <button v-if="notice.undo" type="button" @click="notice.undo()">
          Undo
        </button>
      </div>
    </Transition>

    <MediaEditDialog
      v-if="editing"
      :item="editing"
      :achievements="achievementList"
      :profiles="profiles"
      :detect="detect"
      @close="editingId = null"
      @save="onSave"
      @delete="remove"
    />

    <Teleport to="body">
      <div
        v-if="lightboxItem && hasPreview && !editing"
        class="gm-lightbox"
        @click.self="lightboxId = null"
      >
        <button
          v-if="visible.length > 1"
          type="button"
          class="gm-nav gm-prev"
          aria-label="Previous"
          @click="step(-1)"
        >
          ‹
        </button>
        <figure class="gm-figure">
          <img
            v-if="lightboxItem.kind === 'screenshot'"
            :src="lightboxItem.url"
            alt=""
          />
          <video
            v-else
            :key="lightboxItem.id"
            :src="lightboxItem.url"
            controls
            autoplay
            @loadedmetadata="settleDuration($event.target as HTMLVideoElement)"
          ></video>
          <figcaption>
            <div class="gm-cap-main">
              <span class="gm-pos"
                >{{ lightboxIndex + 1 }} / {{ visible.length }}</span
              >
              <AchievementPicker
                v-if="achievementList.length"
                compact
                up
                :model-value="lightboxItem.linked_achievement_id ?? null"
                :achievements="achievementList"
                @change="retie(lightboxItem, $event)"
              />
              <button
                v-if="lightboxItem.linked_achievement_id"
                type="button"
                class="gm-open"
                title="Open this achievement"
                @click="
                  emit('open-achievement', lightboxItem.linked_achievement_id!)
                "
              >
                Open ↗
              </button>
              <span v-if="lightboxItem.note" class="gm-note">{{
                lightboxItem.note
              }}</span>
            </div>
            <div class="gm-cap-actions">
              <button
                type="button"
                class="ui-btn ui-btn-ghost ui-btn-sm"
                @click="copy(lightboxItem)"
              >
                Copy
              </button>
              <button
                type="button"
                class="ui-btn ui-btn-ghost ui-btn-sm"
                @click="download(lightboxItem)"
              >
                Download
              </button>
              <button
                type="button"
                class="ui-btn ui-btn-ghost ui-btn-sm"
                @click="editingId = lightboxItem.id"
              >
                Edit
              </button>
              <button
                type="button"
                class="ui-btn ui-btn-secondary ui-btn-sm"
                @click="lightboxId = null"
              >
                Close
              </button>
            </div>
          </figcaption>
        </figure>
        <button
          v-if="visible.length > 1"
          type="button"
          class="gm-nav gm-next"
          aria-label="Next"
          @click="step(1)"
        >
          ›
        </button>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.game-media {
  position: relative;
}
.gm-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 16px;
}
.gm-title {
  display: flex;
  align-items: center;
  gap: 10px;
}
.gm-title h2 {
  margin: 0;
  font-size: 1.1rem;
}
.gm-count {
  background: color-mix(in srgb, var(--ui-accent) 16%, transparent);
  color: var(--ui-accent-text);
  font-size: 0.72rem;
  font-weight: 700;
  border-radius: 999px;
  padding: 2px 9px;
  font-variant-numeric: tabular-nums;
}
.gm-tools {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
.gm-input {
  display: none;
}
.gm-search {
  width: 180px;
}
.gm-select {
  max-width: 220px;
  color-scheme: dark;
}
.gm-select option {
  background: var(--ui-surface);
  color: var(--ui-text);
}
.ui-btn.on {
  color: var(--ui-accent-text);
  border-color: color-mix(in srgb, var(--ui-accent) 50%, transparent);
}
.gm-bulk {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
  padding: 10px 12px;
  background: var(--ui-surface);
  border: 1px solid color-mix(in srgb, var(--ui-accent) 40%, transparent);
  border-radius: var(--ui-radius-card);
}
.gm-bulk-count {
  font-size: 0.82rem;
  font-weight: 700;
  color: var(--ui-accent-text);
  margin-right: 4px;
}
.gm-bulk-check {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.74rem;
  color: var(--ui-dim);
  cursor: pointer;
}
.gm-bulk-check input {
  accent-color: var(--ui-accent-text);
}
.gm-bulk-sep {
  flex: 1;
}
.gm-bulk-date {
  height: 30px;
  width: 150px;
  font-size: 0.8rem;
  color-scheme: dark;
}
.gm-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.gm-error-x {
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  padding: 0 2px;
}
.gm-skel {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--ui-surface-2);
  border-radius: var(--ui-radius-card);
  overflow: hidden;
  background: var(--ui-surface);
}
.gm-skel::before,
.gm-skel::after {
  content: "";
  background: linear-gradient(100deg, #181818 30%, #212121 50%, #181818 70%);
  background-size: 200% 100%;
  animation: shimmer 1.4s linear infinite;
}
.gm-skel::before {
  aspect-ratio: 16 / 9;
}
.gm-skel::after {
  height: 74px;
  border-top: 1px solid var(--ui-surface-2);
}
.gm-hint {
  color: var(--ui-faint);
  font-size: 14px;
}
.gm-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}
.gm-spin {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 2px solid var(--ui-border-strong);
  border-top-color: var(--ui-accent-text);
  animation: gm-rot 0.8s linear infinite;
}
@keyframes gm-rot {
  to {
    transform: rotate(360deg);
  }
}
.gm-none {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--ui-faint);
  font-size: 0.85rem;
  padding: 24px 0;
}
.gm-plus {
  font-size: 1.6rem;
  line-height: 1;
  font-weight: 300;
  color: var(--ui-accent-text);
}
.gm-empty {
  width: 100%;
  min-height: var(--ui-empty-min, 280px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 24px;
  text-align: center;
  background: color-mix(in srgb, var(--ui-text) 2%, transparent);
  border: 1.5px dashed var(--ui-border-strong);
  border-radius: var(--ui-radius-dialog);
  color: var(--ui-dim);
  font-family: inherit;
  font-size: 0.85rem;
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    background 0.15s ease;
}
.gm-empty strong {
  color: var(--ui-text);
  font-size: 1rem;
}
.gm-empty:hover:not(:disabled) {
  border-color: var(--ui-accent-text);
  background: color-mix(in srgb, var(--ui-accent) 6%, transparent);
}
.gm-empty:disabled {
  cursor: default;
}
.gm-empty .gm-plus {
  font-size: 2.6rem;
}
.gm-trash {
  list-style: none;
  margin: 0 0 16px;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.gm-trash li {
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--ui-surface);
  border: 1px solid var(--ui-surface-2);
  border-radius: var(--ui-radius-control);
  padding: 6px 10px;
  font-size: 0.8rem;
}
.gm-trash-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--ui-text);
}
.gm-trash-meta {
  color: var(--ui-faint);
  font-size: 0.74rem;
}
.gm-body {
  position: relative;
}
.gm-body.dropping {
  min-height: 260px;
}
.gm-drop {
  position: absolute;
  inset: 0;
  z-index: 5;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border: 2px dashed var(--ui-accent-text);
  border-radius: var(--ui-radius-dialog);
  background: rgba(20, 16, 10, 0.9);
  pointer-events: none;
}
.gm-drop strong {
  color: var(--ui-text);
  font-size: 1.05rem;
}
.gm-drop .gm-plus {
  font-size: 2.4rem;
}
.gm-toast {
  position: fixed;
  left: 50%;
  bottom: 28px;
  transform: translateX(-50%);
  z-index: var(--ui-z-dialog, 400);
  display: flex;
  align-items: center;
  gap: 14px;
  background: var(--ui-surface);
  border: 1px solid var(--ui-border);
  border-radius: 999px;
  padding: 8px 16px;
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--ui-text);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
}
.gm-toast button {
  background: none;
  border: none;
  color: var(--ui-accent-text);
  font: inherit;
  font-weight: var(--ui-weight-title);
  cursor: pointer;
  padding: 0;
}
.gm-lightbox {
  position: fixed;
  inset: 0;
  z-index: var(--ui-z-modal, 300);
  background: color-mix(in srgb, var(--ui-bg) 92%, transparent);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 24px;
  box-sizing: border-box;
}
.gm-figure {
  margin: 0;
  max-width: 100%;
  max-height: 100%;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.gm-figure img,
.gm-figure video {
  max-width: 100%;
  max-height: calc(100vh - 130px);
  object-fit: contain;
  border-radius: var(--ui-radius-control);
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.6);
  background: var(--ui-surface);
}
.gm-figure figcaption {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
}
.gm-cap-main {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  min-width: 0;
  color: var(--ui-text);
  font-size: 0.82rem;
}
.gm-cap-actions {
  display: flex;
  gap: 8px;
}
.gm-open {
  background: none;
  border: none;
  color: var(--ui-accent-text);
  font: inherit;
  font-size: 0.78rem;
  font-weight: 700;
  cursor: pointer;
  padding: 0;
}
.gm-add-card {
  align-self: stretch;
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
  text-align: left;
  background: color-mix(in srgb, var(--ui-text) 2%, transparent);
  border: 1px dashed var(--ui-border-strong);
  border-radius: var(--ui-radius-card);
  color: var(--ui-dim);
  font-family: inherit;
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    background 0.15s ease;
}
.gm-add-thumb {
  flex: 1 1 auto;
  aspect-ratio: 16 / 9;
  display: flex;
  align-items: center;
  justify-content: center;
}
.gm-add-body {
  min-height: 74px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 10px 12px 12px;
  border-top: 1px dashed var(--ui-border);
}
.gm-add-body strong {
  color: var(--ui-text);
  font-size: 0.84rem;
  font-weight: 600;
}
.gm-add-card .gm-plus {
  font-size: 2.2rem;
}
.gm-add-sub {
  font-size: 0.72rem;
  color: var(--ui-faint);
}
.gm-add-card:hover:not(:disabled) {
  border-color: var(--ui-accent-text);
  background: color-mix(in srgb, var(--ui-accent) 6%, transparent);
}
.gm-add-card:disabled {
  cursor: default;
}
.gm-pos {
  color: var(--ui-faint);
  font-variant-numeric: tabular-nums;
}
.gm-nav {
  flex-shrink: 0;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: 1px solid var(--ui-border);
  background: color-mix(in srgb, var(--ui-text) 6%, transparent);
  color: var(--ui-text);
  font-size: 1.6rem;
  line-height: 1;
  cursor: pointer;
}
.gm-nav:hover {
  background: var(--ui-accent);
  color: var(--ui-on-accent);
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
  .gm-skel,
  .gm-skel::before,
  .gm-skel::after {
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
@media (max-width: 640px) {
  .gm-tools {
    width: 100%;
  }
  .gm-search {
    flex: 1 1 100%;
    width: auto;
  }
  .gm-nav {
    position: absolute;
    bottom: 16px;
    width: 40px;
    height: 40px;
  }
  .gm-prev {
    left: 16px;
  }
  .gm-next {
    right: 16px;
  }
}
</style>
