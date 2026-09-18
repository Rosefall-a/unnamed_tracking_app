<script setup lang="ts">
// Shared between TVShowDetail.vue and AnimeDetail.vue — a season's
// per-episode checklist (title, air date, thumbnail where the provider
// has one, a watched toggle, a decimal rating). Episodes are already
// loaded/synced by the caller before this renders; this component is
// purely display + the two per-episode actions.
import { computed, ref, watch } from "vue";
import CheckIcon from "./CheckIcon.vue";
import { formatAiringCountdown } from "../utils/countdown";

export interface EpisodeVM {
  id: string;
  episodeNumber: number;
  title: string | null;
  description: string | null;
  airDate: string | null;
  stillUrl: string | null;
  watched: boolean;
  rating: number | null;
  note?: string | null;
  // true only for a synthetic row this component generated itself for
  // an episode that hasn't aired yet and so has no real row from the
  // backend — no id to act on, so its checkbox/rating/catch-up controls
  // are disabled rather than emitting an event nothing can handle
  isVirtual?: boolean;
}

const props = defineProps<{
  episodes: EpisodeVM[];
  loading: boolean;
  // if set, the episode with this number gets an "airs in..." badge
  // instead of the ordinary air date
  nextEpisodeNumber?: number | null;
  nextEpisodeAirAt?: number | null;
  // the season's known total, when known — lets the projected/virtual
  // rows below stop at a real ceiling instead of a fixed guess
  episodeCount?: number | null;
  // days between episodes for a show that doesn't air weekly
  intervalDays?: number | null;
}>();

// A newly-scheduled episode (confirmed next, or one of the weekly
// projections after it) has no row at all yet — the backend only pads
// placeholder rows for episodes that have actually aired. Synthesized
// here purely for display so "every episode until it's finished" is
// visible even before the real row exists; these can't be checked off
// or rated since there's nothing in the database to act on yet.
const MAX_SYNTHETIC_WEEKS = 12;
const displayEpisodes = computed<EpisodeVM[]>(() => {
  if (!props.nextEpisodeNumber || !props.nextEpisodeAirAt) return props.episodes;
  const maxReal = props.episodes.reduce((m, e) => Math.max(m, e.episodeNumber), 0);
  const ceiling =
    props.episodeCount && props.episodeCount > props.nextEpisodeNumber
      ? props.episodeCount
      : props.nextEpisodeNumber + MAX_SYNTHETIC_WEEKS - 1;
  if (maxReal >= ceiling) return props.episodes;
  const synthetic: EpisodeVM[] = [];
  for (let n = Math.max(maxReal + 1, props.nextEpisodeNumber); n <= ceiling; n++) {
    synthetic.push({
      id: `virtual-${n}`,
      episodeNumber: n,
      title: null,
      description: null,
      airDate: null,
      stillUrl: null,
      watched: false,
      rating: null,
      isVirtual: true,
    });
  }
  return [...props.episodes, ...synthetic];
});

const intervalSeconds = computed(() => (props.intervalDays ?? 7) * 24 * 60 * 60);
const cadenceLabel = computed(() => {
  const d = props.intervalDays ?? 7;
  if (d === 7) return "weekly";
  if (d === 1) return "daily";
  return `every ${d} days`;
});

// The exact next episode is a real, provider-confirmed date; anything
// after it is a weekly-cadence guess (no provider hands over a show's
// full future schedule) — same per-show cadence the calendar's own
// projected entries use, kept visually distinct via `isProjectedFor`.
function airAtFor(episodeNumber: number): number | null {
  if (!props.nextEpisodeAirAt || !props.nextEpisodeNumber) return null;
  if (episodeNumber < props.nextEpisodeNumber) return null;
  return (
    props.nextEpisodeAirAt +
    intervalSeconds.value * (episodeNumber - props.nextEpisodeNumber)
  );
}
function countdownFor(episodeNumber: number): string | null {
  const airAt = airAtFor(episodeNumber);
  return airAt === null ? null : formatAiringCountdown(airAt);
}
function isProjectedFor(episodeNumber: number): boolean {
  return !!props.nextEpisodeNumber && episodeNumber > props.nextEpisodeNumber;
}

const emit = defineEmits<{
  (e: "toggle-watched", episodeId: string): void;
  (e: "set-rating", episodeId: string, rating: number | null): void;
  (e: "bulk-set-watched", episodeIds: string[], watched: boolean): void;
  (e: "set-note", episodeId: string, note: string | null): void;
}>();

// Per-episode private note (thoughts, where you left off, a rewatch
// reminder) — edited inline under the title, saved with the button or
// Ctrl+Enter.
const editingNoteId = ref<string | null>(null);
const noteDraft = ref("");
function startNote(ep: EpisodeVM) {
  if (ep.isVirtual) return;
  editingNoteId.value = ep.id;
  noteDraft.value = ep.note ?? "";
}
function saveNote(ep: EpisodeVM) {
  const value = noteDraft.value.trim();
  editingNoteId.value = null;
  if ((ep.note ?? "") === value) return;
  emit("set-note", ep.id, value || null);
}

function onRatingInput(episodeId: string, event: Event) {
  const raw = (event.target as HTMLInputElement).value;
  emit("set-rating", episodeId, raw === "" ? null : Number(raw));
}

// Shift-click extends from the last checkbox clicked (anywhere in the
// full list, not just the current page) through the one just clicked,
// setting the whole range to match the just-clicked episode's new
// state — the standard file-manager/email range-select gesture, so
// catching up on a dozen episodes at once doesn't mean a dozen
// individual clicks.
const lastClickedId = ref<string | null>(null);

function onCheckboxClick(event: MouseEvent, ep: EpisodeVM) {
  if (ep.isVirtual) return;
  const targetWatched = !ep.watched;
  if (event.shiftKey && lastClickedId.value) {
    const ids = displayEpisodes.value.filter((e) => !e.isVirtual).map((e) => e.id);
    const fromIndex = ids.indexOf(lastClickedId.value);
    const toIndex = ids.indexOf(ep.id);
    if (fromIndex !== -1 && toIndex !== -1) {
      const [start, end] = [fromIndex, toIndex].sort((a, b) => a - b);
      emit("bulk-set-watched", ids.slice(start, end + 1), targetWatched);
      lastClickedId.value = ep.id;
      return;
    }
  }
  emit("toggle-watched", ep.id);
  lastClickedId.value = ep.id;
}

// "Catch up" — marks every episode from the start of the season through
// this one as watched in a single request, for jumping into a
// long-running show without checking off each prior episode by hand.
function markWatchedUpToHere(ep: EpisodeVM) {
  if (ep.isVirtual) return;
  const ids: string[] = [];
  for (const e of displayEpisodes.value) {
    if (e.isVirtual) break;
    ids.push(e.id);
    if (e.id === ep.id) break;
  }
  emit("bulk-set-watched", ids, true);
}

// Long-running shows (Naruto Shippuden-style, 500+ episodes) would
// otherwise dump every row into the DOM at once — paginate in fixed
// chunks instead. Most shows (well under 50 episodes) never hit this at
// all; the controls only render once there's more than one page.
const PAGE_SIZE = 50;
const page = ref(0);
const pageCount = computed(() =>
  Math.max(1, Math.ceil(displayEpisodes.value.length / PAGE_SIZE)),
);
// Land on whichever page has the next unwatched episode (i.e. roughly
// "where you left off") the first time a real episode list shows up,
// rather than always starting at episode 1 — re-picks only when the
// episode list itself changes (a different season, or the initial
// sync), not on every watched-toggle inside the current page.
watch(
  () => props.episodes,
  () => {
    const episodes = displayEpisodes.value;
    if (!episodes.length) {
      page.value = 0;
      return;
    }
    const firstUnwatchedIndex = episodes.findIndex((e) => !e.watched);
    const targetIndex = firstUnwatchedIndex === -1 ? episodes.length - 1 : firstUnwatchedIndex;
    page.value = Math.floor(targetIndex / PAGE_SIZE);
  },
  { immediate: true },
);
const pageStart = computed(() => page.value * PAGE_SIZE);
const visibleEpisodes = computed(() =>
  displayEpisodes.value.slice(pageStart.value, pageStart.value + PAGE_SIZE),
);
function goToPage(p: number) {
  page.value = Math.min(Math.max(p, 0), pageCount.value - 1);
}
</script>

<template>
  <div class="episode-list">
    <p v-if="loading" class="episodes-loading">Loading episodes…</p>
    <p v-else-if="!displayEpisodes.length" class="episodes-unavailable">
      No episode data available for this season.
    </p>
    <template v-else>
      <div v-if="pageCount > 1" class="episode-pager">
        <button
          type="button"
          class="pager-btn"
          :disabled="page === 0"
          @click="goToPage(page - 1)"
        >
          ‹ Prev
        </button>
        <select :value="page" @change="goToPage(Number(($event.target as HTMLSelectElement).value))">
          <option v-for="p in pageCount" :key="p - 1" :value="p - 1">
            Episodes {{ (p - 1) * PAGE_SIZE + 1 }}–{{
              Math.min(p * PAGE_SIZE, displayEpisodes.length)
            }}
          </option>
        </select>
        <button
          type="button"
          class="pager-btn"
          :disabled="page === pageCount - 1"
          @click="goToPage(page + 1)"
        >
          Next ›
        </button>
      </div>
      <div
        v-for="ep in visibleEpisodes"
        :key="ep.id"
        class="episode-row"
        :class="{
          watched: ep.watched,
          virtual: ep.isVirtual,
          'next-up': countdownFor(ep.episodeNumber) && !isProjectedFor(ep.episodeNumber),
          projected: countdownFor(ep.episodeNumber) && isProjectedFor(ep.episodeNumber),
        }"
      >
      <button
        type="button"
        class="episode-checkbox"
        :disabled="ep.isVirtual"
        :title="
          ep.isVirtual
            ? 'Not aired yet'
            : ep.watched
              ? 'Mark unwatched (shift-click for a range)'
              : 'Mark watched (shift-click for a range)'
        "
        @click="onCheckboxClick($event, ep)"
      >
        <CheckIcon v-if="ep.watched" />
      </button>
      <div
        class="episode-thumb"
        :style="ep.stillUrl ? { backgroundImage: `url(${ep.stillUrl})` } : {}"
      >
        <span v-if="!ep.stillUrl">No image</span>
      </div>
      <div class="episode-info">
        <div class="episode-title-row">
          <span class="episode-number">Ep {{ ep.episodeNumber }}</span>
          <span class="episode-title">{{ ep.title || (ep.isVirtual ? "Not yet aired" : "Untitled") }}</span>
          <span
            v-if="countdownFor(ep.episodeNumber)"
            class="episode-countdown"
            :class="{ projected: isProjectedFor(ep.episodeNumber) }"
            :title="isProjectedFor(ep.episodeNumber) ? `Estimated from a ${cadenceLabel} schedule, not confirmed` : undefined"
            >{{ isProjectedFor(ep.episodeNumber) ? "Est. " : "" }}Airs in {{ countdownFor(ep.episodeNumber) }}</span
          >
          <span v-else-if="ep.airDate" class="episode-air">{{ ep.airDate }}</span>
        </div>
        <p v-if="ep.description" class="episode-desc">{{ ep.description }}</p>
        <div v-if="editingNoteId === ep.id" class="note-editor">
          <textarea
            v-model="noteDraft"
            rows="2"
            maxlength="2000"
            placeholder="Your notes on this episode…"
            autofocus
            @keydown.ctrl.enter="saveNote(ep)"
            @keydown.esc="editingNoteId = null"
          ></textarea>
          <div class="note-actions">
            <button type="button" class="note-save" @click="saveNote(ep)">Save note</button>
            <button type="button" class="note-cancel" @click="editingNoteId = null">Cancel</button>
          </div>
        </div>
        <p
          v-else-if="ep.note"
          class="episode-note"
          title="Click to edit"
          @click="startNote(ep)"
        >
          {{ ep.note }}
        </p>
        <button
          v-else-if="!ep.isVirtual"
          type="button"
          class="add-note-btn"
          @click="startNote(ep)"
        >
          + Note
        </button>
      </div>
      <button
        v-if="!ep.watched && !ep.isVirtual"
        type="button"
        class="catch-up-btn"
        title="Mark watched up to here"
        @click="markWatchedUpToHere(ep)"
      >
        Catch up ›
      </button>
      <div class="episode-rating">
        <span class="star">★</span>
        <input
          type="number"
          min="0"
          max="10"
          step="0.1"
          placeholder="–"
          :disabled="ep.isVirtual"
          :value="ep.rating ?? ''"
          @change="onRatingInput(ep.id, $event)"
        />
      </div>
      </div>
      <div v-if="pageCount > 1" class="episode-pager">
        <button
          type="button"
          class="pager-btn"
          :disabled="page === 0"
          @click="goToPage(page - 1)"
        >
          ‹ Prev
        </button>
        <span class="pager-label"
          >Page {{ page + 1 }} of {{ pageCount }}</span
        >
        <button
          type="button"
          class="pager-btn"
          :disabled="page === pageCount - 1"
          @click="goToPage(page + 1)"
        >
          Next ›
        </button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.episode-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.episode-pager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 4px 0;
}
.pager-btn {
  background: #1a1a1a;
  border: 1px solid #2b2b2b;
  color: #ccc;
  border-radius: 7px;
  padding: 6px 14px;
  font-family: inherit;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
}
.pager-btn:hover:not(:disabled) {
  border-color: rgba(214, 138, 52, 0.4);
  color: #d68a34;
}
.pager-btn:disabled {
  opacity: 0.4;
  cursor: default;
}
.pager-label {
  font-size: 0.78rem;
  color: #999;
  font-variant-numeric: tabular-nums;
}
.episode-pager select {
  background: #1a1a1a;
  border: 1px solid #2b2b2b;
  color: #f2f2f2;
  border-radius: 7px;
  padding: 6px 10px;
  font-family: inherit;
  font-size: 0.8rem;
}
.episodes-loading {
  color: #999;
  font-size: 0.85rem;
}
.episodes-unavailable {
  border: 1px dashed #2a2a2a;
  border-radius: 10px;
  padding: 24px;
  color: #666;
  font-size: 0.86rem;
  line-height: 1.6;
  text-align: center;
}
.episode-row {
  display: grid;
  grid-template-columns: 26px 140px 1fr auto auto;
  gap: 14px;
  align-items: center;
  background: #1a1a1a;
  border: 1px solid #202020;
  border-radius: 10px;
  padding: 10px;
  transition: border-color 0.15s ease;
}
.catch-up-btn {
  background: none;
  border: 1px solid #2b2b2b;
  color: #666;
  border-radius: 7px;
  padding: 5px 10px;
  font-family: inherit;
  font-size: 0.72rem;
  font-weight: 600;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}
.episode-row:hover .catch-up-btn,
.episode-row:focus-within .catch-up-btn {
  opacity: 1;
}
.catch-up-btn:hover {
  color: #d68a34;
  border-color: rgba(214, 138, 52, 0.4);
}
.add-note-btn {
  align-self: flex-start;
  margin-top: 4px;
  background: none;
  border: none;
  padding: 0;
  color: #666;
  font-family: inherit;
  font-size: 0.72rem;
  font-weight: 600;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.15s ease, color 0.15s ease;
}
.episode-row:hover .add-note-btn,
.episode-row:focus-within .add-note-btn {
  opacity: 1;
}
.add-note-btn:hover {
  color: #d68a34;
}
.episode-note {
  margin: 6px 0 0;
  padding: 6px 10px;
  background: rgba(214, 138, 52, 0.08);
  border-left: 2px solid rgba(214, 138, 52, 0.6);
  border-radius: 4px;
  color: #d8c3a0;
  font-size: 0.78rem;
  line-height: 1.45;
  white-space: pre-wrap;
  cursor: text;
}
.note-editor {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 6px;
}
.note-editor textarea {
  width: 100%;
  box-sizing: border-box;
  background: #0d0d0d;
  border: 1px solid #3a3a3a;
  border-radius: 6px;
  color: #eee;
  padding: 7px 9px;
  font: inherit;
  font-size: 0.8rem;
  resize: vertical;
}
.note-editor textarea:focus {
  outline: none;
  border-color: #d68a34;
}
.note-actions {
  display: flex;
  gap: 8px;
}
.note-save,
.note-cancel {
  border: none;
  border-radius: 6px;
  padding: 5px 12px;
  font-family: inherit;
  font-size: 0.74rem;
  font-weight: 700;
  cursor: pointer;
}
.note-save {
  background: #d68a34;
  color: #14100a;
}
.note-cancel {
  background: rgba(255, 255, 255, 0.08);
  color: #ccc;
}
.episode-row.watched {
  border-color: rgba(214, 138, 52, 0.4);
}
.episode-row.next-up {
  border-color: rgba(214, 138, 52, 0.55);
  background: rgba(214, 138, 52, 0.06);
}
.episode-row.projected {
  border-color: rgba(214, 138, 52, 0.3);
  border-style: dashed;
}
.episode-row.virtual {
  opacity: 0.6;
}
.episode-row.virtual .episode-title {
  color: #999;
  font-style: italic;
}
.episode-checkbox:disabled,
.episode-rating input:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
.episode-countdown {
  font-size: 0.72rem;
  color: #d68a34;
  font-weight: 700;
  margin-left: auto;
  white-space: nowrap;
}
.episode-countdown.projected {
  color: #b8874a;
  font-weight: 600;
  opacity: 0.8;
}
.episode-checkbox {
  width: 20px;
  height: 20px;
  border-radius: 5px;
  border: 1.5px solid #2b2b2b;
  background: #222222;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #d68a34;
  font-size: 0.75rem;
  font-weight: 800;
  flex-shrink: 0;
  padding: 0;
}
.episode-row.watched .episode-checkbox {
  background: rgba(214, 138, 52, 0.16);
  border-color: #d68a34;
}
.episode-thumb {
  width: 140px;
  aspect-ratio: 16 / 9;
  border-radius: 7px;
  background-size: cover;
  background-position: center;
  background-color: #222222;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.68rem;
  color: #666;
  text-align: center;
}
.episode-info {
  min-width: 0;
}
.episode-title-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 4px;
  flex-wrap: wrap;
}
.episode-number {
  font-size: 0.76rem;
  color: #666;
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
}
.episode-title {
  font-weight: 700;
  font-size: 0.9rem;
  color: #fff;
}
.episode-air {
  font-size: 0.72rem;
  color: #666;
  margin-left: auto;
  white-space: nowrap;
}
.episode-desc {
  font-size: 0.8rem;
  color: #999;
  line-height: 1.5;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.episode-rating {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}
.episode-rating .star {
  color: #d68a34;
  font-size: 0.85rem;
}
.episode-rating input {
  width: 52px;
  background: #222222;
  border: 1px solid #2b2b2b;
  color: #fff;
  border-radius: 6px;
  padding: 5px 6px;
  font-family: inherit;
  font-size: 0.78rem;
  font-variant-numeric: tabular-nums;
}
</style>
