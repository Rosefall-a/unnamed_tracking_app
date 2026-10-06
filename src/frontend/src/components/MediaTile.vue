<script setup lang="ts" generic="T extends FileDetails">
// One uploaded file in a gallery. As a card (screenshots, clips) it is a
// 16:9 preview with the achievement it belongs to laid over the corner and
// a short caption underneath. As a row (soundtrack) it is a line with an
// inline player. Hover shows copy, download, edit and delete; editing opens
// a dialog instead of growing the card.
import { ref, computed, onBeforeUnmount } from "vue";
import MediaEditDialog from "./MediaEditDialog.vue";
import { originalName } from "../utils/copyMedia";
import { formatDuration, settleDuration } from "../utils/videoDuration";
import { captureFrame } from "../utils/videoThumbnail";
import { startPlaying, stoppedPlaying } from "../utils/nowPlaying";
import { formatMediaDate, SOURCE_LABEL, mediaSource } from "../utils/mediaDate";
import type { FileDetails, MediaItemUpdate } from "../services/media";
import type { Achievement } from "../types/game";
import type { GameProfile } from "../services/gameProfiles";

const props = defineProps<{
  item: T;
  readerUrl?: string;
  achievements?: Achievement[];
  showGameTitle?: boolean;
  row?: boolean;
  // picking files to act on together: a click selects instead of opening
  selecting?: boolean;
  selected?: boolean;
  // re-reads the date from the file, offered in the edit dialog
  detect?: (item: T) => Promise<"file" | "achievement" | "none">;
  // only passed when the game has "Track multiple accounts" enabled, lets
  // an already-uploaded screenshot be moved to a different account after
  // the fact instead of only being assignable at upload time
  profiles?: GameProfile[];
}>();

const emit = defineEmits<{
  delete: [item: T];
  save: [item: T, patch: MediaItemUpdate];
  preview: [item: T];
  toggle: [item: T];
  copy: [item: T];
  download: [item: T];
  "open-achievement": [achievementId: string];
  // a preview picture made for a clip that had none, to be saved
  thumbnail: [item: T, blob: Blob, duration: number];
}>();

const editing = ref(false);
const measured = ref("");
// the saved length when there is one, otherwise what the video reports
const length = computed(() =>
  props.item.duration ? formatDuration(props.item.duration) : measured.value,
);
async function onClipMetadata(e: Event) {
  const video = e.target as HTMLVideoElement;
  if (props.item.thumbnail_url) return;
  // no saved picture yet: make one from this video, once, and hand it up to be
  // kept, so the next visit shows a picture instead of loading the video
  measured.value = formatDuration(await settleDuration(video));
  const frame = await captureFrame(video);
  if (frame) emit("thumbnail", props.item, frame.blob, frame.duration);
}

const linkedName = computed(() => {
  const id = props.item.linked_achievement_id;
  if (!id) return null;
  return props.achievements?.find((a) => a.id === id)?.name ?? null;
});
const accountName = computed(() => {
  if (!props.item.profile_id || !props.profiles) return null;
  return (
    props.profiles.find((p) => p.id === props.item.profile_id)?.name ??
    "Unknown account"
  );
});

const added = computed(() => formatMediaDate(props.item));
const extension = computed(() => {
  const name = originalName(props.item.filename);
  const i = name.lastIndexOf(".");
  return i > 0 ? name.slice(i + 1, i + 5).toUpperCase() : "FILE";
});
function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
  return `${(bytes / 1024 ** 3).toFixed(2)} GB`;
}
const dateHint = computed(() => SOURCE_LABEL[mediaSource(props.item)]);
// the in-app title leads; the file's own name stays visible beneath it
const fileName = computed(() => originalName(props.item.filename));
const title = computed(() => props.item.title || fileName.value);
const shownTags = computed(() => props.item.tags.slice(0, 2));
const moreTags = computed(() => Math.max(0, props.item.tags.length - 2));

// ---- a track plays right on its card ----
const audio = ref<HTMLAudioElement | null>(null);
const playing = ref(false);
const progress = ref(0);
function onAudioMetadata() {
  if (audio.value && Number.isFinite(audio.value.duration))
    measured.value = formatDuration(audio.value.duration);
}
function onAudioTime() {
  const a = audio.value;
  progress.value = a && a.duration ? (a.currentTime / a.duration) * 100 : 0;
}
function togglePlay() {
  const a = audio.value;
  if (!a) return;
  if (a.paused) {
    startPlaying(a);
    void a.play();
  } else a.pause();
}
onBeforeUnmount(() => {
  if (audio.value) {
    audio.value.pause();
    stoppedPlaying(audio.value);
  }
});

function onThumbClick() {
  if (props.selecting) emit("toggle", props.item);
  else if (props.item.kind === "soundtrack") togglePlay();
  else emit("preview", props.item);
}
</script>

<template>
  <article class="tile" :class="{ row, selecting, selected }">
    <div class="thumb" @click="onThumbClick">
      <span v-if="selecting" class="check" aria-hidden="true">
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
      <img
        v-if="item.kind === 'screenshot'"
        :src="item.url"
        alt=""
        loading="lazy"
      />
      <img
        v-else-if="item.kind === 'clip' && item.thumbnail_url"
        :src="item.thumbnail_url"
        alt=""
        loading="lazy"
      />
      <video
        v-else-if="item.kind === 'clip'"
        :src="`${item.url}#t=0.1`"
        preload="metadata"
        muted
        playsinline
        @loadedmetadata="onClipMetadata"
      ></video>
      <div v-else-if="item.kind !== 'soundtrack'" class="doc-icon">
        <svg
          viewBox="0 0 24 24"
          width="26"
          height="26"
          fill="none"
          stroke="currentColor"
          stroke-width="1.7"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path
            d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"
          />
          <path d="M14 2v6h6" />
        </svg>
        <strong>{{ extension }}</strong>
      </div>
      <div v-else class="audio-art">
        <svg
          class="note-icon"
          viewBox="0 0 24 24"
          width="34"
          height="34"
          fill="none"
          stroke="currentColor"
          stroke-width="1.7"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M9 18V5l12-2v13" />
          <circle cx="6" cy="18" r="3" />
          <circle cx="18" cy="16" r="3" />
        </svg>
        <audio
          ref="audio"
          :src="item.url"
          preload="metadata"
          @loadedmetadata="onAudioMetadata"
          @timeupdate="onAudioTime"
          @play="playing = true"
          @pause="playing = false"
          @ended="
            playing = false;
            progress = 0;
          "
        ></audio>
        <span v-if="progress" class="track-progress" aria-hidden="true">
          <span :style="{ width: `${progress}%` }"></span>
        </span>
      </div>

      <span v-if="length" class="length">{{ length }}</span>
      <span
        v-if="item.kind === 'clip' || item.kind === 'soundtrack'"
        class="play"
        :class="{ on: playing }"
        aria-hidden="true"
      >
        <svg
          v-if="!playing"
          viewBox="0 0 24 24"
          width="18"
          height="18"
          fill="currentColor"
        >
          <path d="M8 5v14l11-7z" />
        </svg>
        <svg
          v-else
          viewBox="0 0 24 24"
          width="18"
          height="18"
          fill="currentColor"
        >
          <path d="M7 5h4v14H7zM13 5h4v14h-4z" />
        </svg>
      </span>

      <div v-if="!row && !selecting" class="actions" @click.stop>
        <button
          type="button"
          :title="item.kind === 'screenshot' ? 'Copy image' : 'Copy link'"
          @click="emit('copy', item)"
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
        <button type="button" title="Download" @click="emit('download', item)">
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
        </button>
        <button type="button" title="Edit details" @click="editing = true">
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
        <button type="button" title="Delete" @click="emit('delete', item)">
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

      <button
        v-if="!row && linkedName && !selecting"
        type="button"
        class="ach"
        :title="`Achievement: ${linkedName}`"
        :aria-label="`Open achievement ${linkedName}`"
        @click.stop="emit('open-achievement', item.linked_achievement_id!)"
      >
        <svg
          viewBox="0 0 24 24"
          width="13"
          height="13"
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
      </button>
    </div>

    <div class="body">
      <p v-if="showGameTitle && item.game_title" class="game">
        {{ item.game_title }}
      </p>
      <p class="title" :title="title">{{ title }}</p>
      <p v-if="item.title" class="file" :title="fileName">{{ fileName }}</p>
      <div class="meta">
        <span v-if="added" :title="dateHint">{{ added }}</span>
        <span v-if="item.size && item.kind !== 'screenshot'">{{
          formatSize(item.size)
        }}</span>
        <span v-if="accountName" class="chip strong">{{ accountName }}</span>
        <span v-for="t in shownTags" :key="t" class="chip">{{ t }}</span>
        <span v-if="moreTags" class="chip">+{{ moreTags }}</span>
        <button
          v-if="row && linkedName"
          type="button"
          class="chip link"
          @click="emit('open-achievement', item.linked_achievement_id!)"
        >
          {{ linkedName }}
        </button>
      </div>
    </div>

    <audio
      v-if="row && item.kind === 'soundtrack'"
      class="player"
      :src="item.url"
      controls
      preload="none"
    ></audio>
    <div v-if="row && !selecting" class="row-actions">
      <button type="button" title="Copy link" @click="emit('copy', item)">
        Copy link
      </button>
      <button type="button" @click="emit('download', item)">Download</button>
      <button type="button" @click="editing = true">Edit</button>
      <button
        type="button"
        class="danger"
        title="Delete"
        @click="emit('delete', item)"
      >
        Delete
      </button>
    </div>

    <a
      v-if="readerUrl && !selecting"
      :href="readerUrl"
      class="reader-link ui-btn ui-btn-secondary"
      target="_blank"
      rel="noopener noreferrer"
      @click.stop
    >
      Open reader
    </a>
    <MediaEditDialog
      v-if="editing"
      :item="item"
      :achievements="achievements"
      :profiles="profiles"
      :detect="detect"
      @close="editing = false"
      @save="(...args) => emit('save', ...args)"
      @delete="emit('delete', $event)"
    />
  </article>
</template>

<style scoped>
.tile {
  background: #141414;
  border: 1px solid #262626;
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition:
    border-color 0.15s ease,
    transform 0.15s ease;
}
.tile:hover {
  border-color: #3a3a3a;
}
.thumb {
  position: relative;
  aspect-ratio: 16 / 9;
  background: #0a0a0a;
  cursor: pointer;
  overflow: hidden;
}
.thumb img,
.thumb video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.25s ease;
}
.tile:hover .thumb img,
.tile:hover .thumb video {
  transform: scale(1.03);
}
.thumb::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(
    to bottom,
    rgba(0, 0, 0, 0.45),
    transparent 40%,
    transparent 60%,
    rgba(0, 0, 0, 0.55)
  );
  opacity: 0;
  transition: opacity 0.15s ease;
  pointer-events: none;
}
.tile:hover .thumb::after,
.tile:focus-within .thumb::after {
  opacity: 1;
}
.play {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.25);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  padding-left: 2px;
  z-index: 1;
  pointer-events: none;
}
.check {
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
.tile.selected {
  border-color: #d68a34;
  box-shadow: 0 0 0 1px #d68a34;
}
.tile.selected .check {
  background: #d68a34;
  border-color: #d68a34;
}
.tile.selecting .thumb::after {
  opacity: 0;
}
.file {
  margin: -2px 0 0;
  font-size: 0.72rem;
  color: #777;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.length {
  position: absolute;
  right: 8px;
  bottom: 8px;
  z-index: 1;
  padding: 2px 7px;
  border-radius: 6px;
  background: rgba(15, 15, 15, 0.82);
  color: #eee;
  font-size: 0.7rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  pointer-events: none;
}
.actions {
  position: absolute;
  top: 8px;
  right: 8px;
  display: flex;
  gap: 4px;
  z-index: 2;
  opacity: 0;
  transition: opacity 0.15s ease;
}
.tile:hover .actions,
.tile:focus-within .actions {
  opacity: 1;
}
@media (hover: none) {
  .actions {
    opacity: 1;
  }
}
.actions button {
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
  backdrop-filter: blur(4px);
}
.actions button:hover {
  background: #d68a34;
  color: #14100a;
}
.actions button:last-child:hover {
  background: #d96f6f;
  color: #fff;
}
.ach {
  position: absolute;
  left: 8px;
  bottom: 8px;
  z-index: 2;
  width: 26px;
  height: 26px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 50%;
  background: rgba(15, 15, 15, 0.82);
  color: #d68a34;
  padding: 0;
  cursor: pointer;
  backdrop-filter: blur(4px);
}
.ach:hover {
  background: #d68a34;
  color: #14100a;
}
.body {
  min-height: 74px;
  box-sizing: border-box;
  padding: 10px 12px 12px;
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
}
.game {
  margin: 0;
  font-size: 0.7rem;
  font-weight: 700;
  color: #d68a34;
}
.title {
  margin: 0;
  font-size: 0.84rem;
  font-weight: 600;
  color: #e8e8e8;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 5px 6px;
  font-size: 0.72rem;
  color: #777;
  min-width: 0;
}
.chip {
  background: rgba(255, 255, 255, 0.07);
  color: #aaa;
  border-radius: 999px;
  padding: 1px 8px;
  font-size: 0.68rem;
  border: none;
  font-family: inherit;
}
.chip.strong {
  background: rgba(255, 255, 255, 0.14);
  color: #fff;
  font-weight: 700;
}
.chip.link {
  background: rgba(214, 138, 52, 0.16);
  color: #d68a34;
  cursor: pointer;
}

/* soundtrack row */
.tile.row {
  flex-direction: row;
  align-items: center;
  gap: 14px;
  padding: 8px 12px 8px 8px;
  flex-wrap: wrap;
}
.row .thumb {
  width: 52px;
  aspect-ratio: 1;
  flex-shrink: 0;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #d68a34;
  background: rgba(214, 138, 52, 0.1);
  cursor: default;
}
.audio-art {
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
.audio-art .note-icon {
  opacity: 0.55;
  transform: translateY(-14px);
}
.track-progress {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 3px;
  background: rgba(255, 255, 255, 0.12);
}
.track-progress span {
  display: block;
  height: 100%;
  background: #d68a34;
}
.play.on {
  background: #d68a34;
  color: #14100a;
  border-color: #d68a34;
}
.doc-icon {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  color: #d68a34;
}
.doc-icon strong {
  font-size: 0.7rem;
  letter-spacing: 0.06em;
}
.thumb:has(.doc-icon) {
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(214, 138, 52, 0.08);
}
.row .thumb::after {
  display: none;
}
.row .body {
  flex: 1 1 200px;
  padding: 0;
}
.row .player {
  flex: 2 1 260px;
  height: 36px;
  min-width: 0;
}
.row-actions {
  display: flex;
  gap: 6px;
}
.row-actions button {
  height: 28px;
  padding: 0 10px;
  border: 1px solid #2b2b2b;
  border-radius: 8px;
  background: none;
  color: #aaa;
  font-family: inherit;
  font-size: 0.74rem;
  font-weight: 600;
  cursor: pointer;
}
.row-actions button:hover {
  color: #fff;
  border-color: #444;
}
.row-actions .danger:hover {
  color: #d96f6f;
  border-color: rgba(217, 111, 111, 0.5);
}
</style>
