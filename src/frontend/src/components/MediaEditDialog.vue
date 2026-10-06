<script setup lang="ts" generic="T extends FileDetails">
// Edit one uploaded file (a screenshot, clip, track or doc). The preview and
// the file's facts sit on the left; the details sit on the right in three
// groups: what it is (title, note), when it is from (date), and what it is
// tied to (achievement, account, tags). The title is only a name inside the
// app; the file keeps its own. It opens over the page, so the gallery behind
// it never reflows.
import { ref, computed, watch, onMounted, onBeforeUnmount } from "vue";
import AchievementPicker from "./AchievementPicker.vue";
import { copyLink, downloadMedia, originalName } from "../utils/copyMedia";
import { formatDuration, settleDuration } from "../utils/videoDuration";
import {
  SOURCE_LABEL,
  dateFromAchievementPref,
  dateInputValue,
  formatMediaDate,
  isGuess,
  mediaSource,
  secondsFromDateInput,
  setDateFromAchievementPref,
  unlockSeconds,
} from "../utils/mediaDate";
import type { FileDetails, MediaItemUpdate } from "../services/media";
import type { Achievement } from "../types/game";
import type { GameProfile } from "../services/gameProfiles";

const props = defineProps<{
  item: T;
  achievements?: Achievement[];
  profiles?: GameProfile[];
  // re-reads the date from the file; true when it found one
  detect?: (item: T) => Promise<"file" | "achievement" | "none">;
}>();

const emit = defineEmits<{
  close: [];
  save: [item: T, patch: MediaItemUpdate];
  delete: [item: T];
}>();

const list = computed(() => props.achievements ?? []);
const isMedia = computed(() =>
  ["screenshot", "clip", "soundtrack"].includes(props.item.kind),
);

const title = ref(props.item.title ?? "");
const tags = ref<string[]>([...props.item.tags]);
const tagDraft = ref("");
const note = ref(props.item.note ?? "");
const linked = ref(props.item.linked_achievement_id ?? "");
const profile = ref(props.item.profile_id ?? "");
const date = ref(dateInputValue(props.item));
const tagInput = ref<HTMLInputElement | null>(null);

// ---- the date ----
// A date chosen from an achievement keeps the exact moment, not just the day.
const fromAchievement = ref(dateFromAchievementPref());
const pending = ref<number | null>(null);
const unlock = computed(() =>
  unlockSeconds(list.value.find((a) => a.id === linked.value)),
);
const unlockLabel = computed(() =>
  unlock.value
    ? new Date(unlock.value * 1000).toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : "",
);
const dateChanged = computed(() => date.value !== dateInputValue(props.item));

const dateNote = computed(() => {
  if (detectMessage.value) return detectMessage.value;
  if (pending.value !== null) return SOURCE_LABEL.achievement;
  if (dateChanged.value) return SOURCE_LABEL.manual;
  return SOURCE_LABEL[mediaSource(props.item)];
});

function takeUnlockDate() {
  if (unlock.value === null) return;
  pending.value = unlock.value;
  date.value = new Date(unlock.value * 1000).toLocaleDateString("en-CA");
  detectMessage.value = "";
}
function onDateInput() {
  pending.value = null;
  detectMessage.value = "";
}
// Tying an achievement fills in its date when the date we have is only a
// guess, never over a date read from the file or set by hand.
function onLink(id: string | null) {
  linked.value = id ?? "";
  if (id && fromAchievement.value && isGuess(props.item) && !dateChanged.value)
    takeUnlockDate();
}
function onTogglePref() {
  setDateFromAchievementPref(fromAchievement.value);
  if (fromAchievement.value && unlock.value !== null && isGuess(props.item))
    takeUnlockDate();
}

const detecting = ref(false);
const detectMessage = ref("");
async function detectDate() {
  if (!props.detect) return;
  detecting.value = true;
  detectMessage.value = "";
  try {
    const found = await props.detect(props.item);
    if (found === "file") detectMessage.value = "Date read from the file.";
    else if (found === "achievement")
      detectMessage.value =
        "The file has no date in it, so it took the achievement's unlock time.";
    else if (linked.value)
      detectMessage.value =
        "The file has no date in it, and that achievement has no unlock time yet. Pick a date below.";
    else
      detectMessage.value =
        "The file has no date in it. Tie an achievement to use its unlock time, or pick a date below.";
    if (found !== "none") pending.value = null;
  } catch {
    detectMessage.value = "Could not read the file.";
  } finally {
    detecting.value = false;
  }
}
// the parent swaps in the updated item after a detect
watch(
  () => [props.item.taken_at, props.item.taken_source],
  () => (date.value = dateInputValue(props.item)),
);

// ---- facts about the file ----
const facts = ref<{ label: string; value: string }[]>([]);
const dimensions = ref("");
const length = ref("");
function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
  return `${(bytes / 1024 ** 3).toFixed(2)} GB`;
}
const KIND_NAME: Record<string, string> = {
  screenshot: "Screenshot",
  clip: "Clip",
  soundtrack: "Track",
  doc: "Document",
  modpack: "Modpack",
};
watch(
  [() => props.item, dimensions, length],
  () => {
    const rows: { label: string; value: string }[] = [
      { label: "Type", value: KIND_NAME[props.item.kind] ?? props.item.kind },
    ];
    if (props.item.size)
      rows.push({ label: "Size", value: formatSize(props.item.size) });
    if (dimensions.value)
      rows.push({ label: "Dimensions", value: dimensions.value });
    if (length.value) rows.push({ label: "Length", value: length.value });
    rows.push({
      label: "Uploaded",
      value: formatMediaDate({ created_at: props.item.created_at }),
    });
    facts.value = rows;
  },
  { immediate: true },
);
function onImageLoad(e: Event) {
  const img = e.target as HTMLImageElement;
  dimensions.value = `${img.naturalWidth} × ${img.naturalHeight}`;
}
async function onVideoMeta(e: Event) {
  const v = e.target as HTMLVideoElement;
  length.value = formatDuration(await settleDuration(v));
  dimensions.value = `${v.videoWidth} × ${v.videoHeight}`;
}
function onAudioMeta(e: Event) {
  length.value = formatDuration((e.target as HTMLAudioElement).duration);
}
const extension = computed(() => {
  const name = originalName(props.item.filename);
  const i = name.lastIndexOf(".");
  return i > 0 ? name.slice(i + 1, i + 6).toUpperCase() : "FILE";
});

const copied = ref(false);
async function copyTheLink() {
  try {
    await copyLink(props.item.url);
    copied.value = true;
    window.setTimeout(() => (copied.value = false), 1500);
  } catch {
    // the browser blocked the clipboard; nothing useful to show
  }
}

// ---- tags ----
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

// ---- save ----
const dirty = computed(
  () =>
    tagDraft.value.trim() !== "" ||
    title.value.trim() !== (props.item.title ?? "") ||
    dateChanged.value ||
    JSON.stringify(tags.value) !== JSON.stringify(props.item.tags) ||
    note.value.trim() !== (props.item.note ?? "") ||
    linked.value !== (props.item.linked_achievement_id ?? "") ||
    profile.value !== (props.item.profile_id ?? ""),
);

function save() {
  commitTag();
  const patch: MediaItemUpdate = {};
  if (title.value.trim() !== (props.item.title ?? ""))
    patch.title = title.value.trim() || null;
  if (dateChanged.value) {
    if (pending.value !== null) {
      patch.taken_at = pending.value;
      patch.taken_source = "achievement";
    } else {
      const seconds = secondsFromDateInput(date.value);
      if (seconds !== null) patch.taken_at = seconds;
    }
  }
  if (JSON.stringify(tags.value) !== JSON.stringify(props.item.tags))
    patch.tags = tags.value;
  if (note.value.trim() !== (props.item.note ?? ""))
    patch.note = note.value.trim() || null;
  if (linked.value !== (props.item.linked_achievement_id ?? ""))
    patch.linked_achievement_id = linked.value || null;
  if (profile.value !== (props.item.profile_id ?? ""))
    patch.profile_id = profile.value || null;
  if (Object.keys(patch).length) emit("save", props.item, patch);
  emit("close");
}
function remove() {
  emit("delete", props.item);
  emit("close");
}

function onKey(e: KeyboardEvent) {
  if (e.key === "Escape") emit("close");
  else if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) save();
}
onMounted(() => document.addEventListener("keydown", onKey));
onBeforeUnmount(() => document.removeEventListener("keydown", onKey));
</script>

<template>
  <Teleport to="body">
    <div class="ui-backdrop" @click.self="emit('close')">
      <div
        class="ui-modal med"
        role="dialog"
        aria-modal="true"
        aria-label="Edit details"
      >
        <header class="med-head">
          <div class="med-head-text">
            <h3>{{ title.trim() || originalName(item.filename) }}</h3>
            <p :title="originalName(item.filename)">
              {{ originalName(item.filename) }}
            </p>
          </div>
          <button
            type="button"
            class="med-x"
            aria-label="Close"
            @click="emit('close')"
          >
            ✕
          </button>
        </header>

        <div class="med-body">
          <aside class="med-side">
            <div class="med-preview" :class="{ doc: !isMedia }">
              <img
                v-if="item.kind === 'screenshot'"
                :src="item.url"
                alt=""
                @load="onImageLoad"
              />
              <video
                v-else-if="item.kind === 'clip'"
                :src="item.url"
                controls
                preload="metadata"
                @loadedmetadata="onVideoMeta"
              ></video>
              <audio
                v-else-if="item.kind === 'soundtrack'"
                :src="item.url"
                controls
                preload="metadata"
                @loadedmetadata="onAudioMeta"
              ></audio>
              <div v-else class="med-doc">
                <svg
                  viewBox="0 0 24 24"
                  width="34"
                  height="34"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.6"
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
            </div>

            <div class="med-quick">
              <button
                type="button"
                class="ui-btn ui-btn-ghost ui-btn-sm"
                @click="copyTheLink"
              >
                {{ copied ? "Copied" : "Copy link" }}
              </button>
              <button
                type="button"
                class="ui-btn ui-btn-ghost ui-btn-sm"
                @click="downloadMedia(item.url, originalName(item.filename))"
              >
                Download
              </button>
            </div>

            <dl class="med-facts">
              <div v-for="f in facts" :key="f.label">
                <dt>{{ f.label }}</dt>
                <dd>{{ f.value }}</dd>
              </div>
            </dl>
          </aside>

          <div class="med-main">
            <section class="med-group">
              <h4>Details</h4>
              <label class="med-field">
                <span>Title</span>
                <input
                  v-model="title"
                  type="text"
                  class="ui-field"
                  maxlength="200"
                  placeholder="A name for this in the app"
                />
              </label>
              <label class="med-field">
                <span>Note</span>
                <textarea
                  v-model="note"
                  class="ui-field"
                  rows="3"
                  placeholder="What is this?"
                ></textarea>
              </label>
            </section>

            <section class="med-group">
              <h4>When</h4>
              <div class="med-field">
                <span>Date</span>
                <div class="med-date">
                  <input
                    v-model="date"
                    type="date"
                    class="ui-field"
                    @input="onDateInput"
                  />
                  <button
                    v-if="detect && isMedia"
                    type="button"
                    class="ui-btn ui-btn-ghost"
                    :disabled="detecting"
                    @click="detectDate"
                  >
                    {{ detecting ? "Reading…" : "Detect from file" }}
                  </button>
                </div>
                <small class="med-hint">{{ dateNote }}</small>
                <button
                  v-if="unlock !== null && pending === null"
                  type="button"
                  class="med-link"
                  @click="takeUnlockDate"
                >
                  Use the achievement's unlock date, {{ unlockLabel }}
                </button>
              </div>
            </section>

            <section class="med-group">
              <h4>Connections</h4>
              <div v-if="list.length" class="med-field">
                <span>Achievement</span>
                <AchievementPicker
                  :model-value="linked || null"
                  :achievements="list"
                  @change="onLink"
                />
                <label class="med-check">
                  <input
                    v-model="fromAchievement"
                    type="checkbox"
                    @change="onTogglePref"
                  />
                  <span
                    >Take the date from the achievement when I tie one. Only
                    replaces a guessed date.</span
                  >
                </label>
              </div>
              <label v-if="profiles && profiles.length" class="med-field">
                <span>Account</span>
                <select v-model="profile" class="ui-field">
                  <option value="">None</option>
                  <option v-for="p in profiles" :key="p.id" :value="p.id">
                    {{ p.name }}
                  </option>
                </select>
              </label>
              <div class="med-field">
                <span>Tags</span>
                <div class="med-tags ui-field" @click="tagInput?.focus()">
                  <span v-for="t in tags" :key="t" class="med-tag">
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
                    :placeholder="
                      tags.length ? '' : 'boss fight, funny, glitch'
                    "
                    @keydown="onTagKey"
                    @blur="commitTag"
                  />
                </div>
              </div>
            </section>
          </div>
        </div>

        <footer class="med-actions">
          <button
            type="button"
            class="ui-btn ui-btn-danger-soft"
            @click="remove"
          >
            Delete
          </button>
          <span class="med-spacer"></span>
          <button
            type="button"
            class="ui-btn ui-btn-ghost"
            @click="emit('close')"
          >
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
        </footer>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.med {
  max-width: 880px;
  max-height: 92vh;
  padding: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.med-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 22px 14px;
  border-bottom: 1px solid #262626;
}
.med-head-text {
  min-width: 0;
}
.med-head h3 {
  margin: 0;
  font-size: 1.05rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.med-head p {
  margin: 3px 0 0;
  font-size: 0.78rem;
  color: #777;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.med-x {
  flex-shrink: 0;
  width: 30px;
  height: 30px;
  border: none;
  border-radius: 8px;
  background: none;
  color: #888;
  cursor: pointer;
}
.med-x:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}
.med-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  gap: 24px;
  padding: 20px 22px;
}
.med-side {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}
.med-preview {
  border-radius: 10px;
  overflow: hidden;
  background: #000;
  display: flex;
  align-items: center;
  justify-content: center;
}
.med-preview img,
.med-preview video {
  display: block;
  width: 100%;
  max-height: 260px;
  object-fit: contain;
}
.med-preview audio {
  width: 100%;
  margin: 14px;
}
.med-preview.doc {
  background: rgba(214, 138, 52, 0.08);
  min-height: 150px;
}
.med-doc {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: #d68a34;
}
.med-doc strong {
  font-size: 0.82rem;
  letter-spacing: 0.06em;
}
.med-quick {
  display: flex;
  gap: 8px;
}
.med-facts {
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 0.8rem;
}
.med-facts div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}
.med-facts dt {
  color: #777;
}
.med-facts dd {
  margin: 0;
  color: #ddd;
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.med-main {
  display: flex;
  flex-direction: column;
  gap: 22px;
  min-width: 0;
}
.med-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.med-group h4 {
  margin: 0;
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #d68a34;
}
.med-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.med-field > span {
  font-size: 0.74rem;
  font-weight: 700;
  color: #9c9c9c;
}
.med-field input.ui-field,
.med-field textarea {
  width: 100%;
}
.med-field select {
  width: 100%;
  color-scheme: dark;
}
.med-date {
  display: flex;
  gap: 8px;
}
.med-date input {
  flex: 1;
  min-width: 0;
  color-scheme: dark;
}
.med-hint {
  font-size: 0.74rem;
  color: #777;
}
.med-link {
  align-self: flex-start;
  background: none;
  border: none;
  padding: 0;
  color: #d68a34;
  font: inherit;
  font-size: 0.78rem;
  font-weight: 700;
  cursor: pointer;
  text-align: left;
}
.med-link:hover {
  text-decoration: underline;
}
.med-check {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 0.76rem;
  color: #888;
  cursor: pointer;
}
.med-check input {
  margin-top: 2px;
  accent-color: #d68a34;
}
.med-tags {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  height: auto;
  min-height: 38px;
  padding: 5px 8px;
  cursor: text;
}
.med-tags:focus-within {
  border-color: var(--ui-accent);
}
.med-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: rgba(255, 255, 255, 0.09);
  border-radius: 999px;
  padding: 2px 4px 2px 10px;
  font-size: 0.76rem;
  color: #ddd;
}
.med-tag button {
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
.med-tag button:hover {
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
}
.med-tags input {
  flex: 1;
  min-width: 90px;
  background: none;
  border: none;
  outline: none;
  color: var(--ui-text);
  font: inherit;
  font-size: 0.85rem;
}
.med-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 22px;
  border-top: 1px solid #262626;
  background: var(--ui-popover, #171717);
}
.med-spacer {
  flex: 1;
}
@media (max-width: 760px) {
  .med-body {
    grid-template-columns: 1fr;
    gap: 18px;
  }
}
</style>
