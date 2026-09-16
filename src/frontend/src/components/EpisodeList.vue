<script setup lang="ts">
// Shared between TVShowDetail.vue and AnimeDetail.vue — a season's
// per-episode checklist (title, air date, thumbnail where the provider
// has one, a watched toggle, a decimal rating). Episodes are already
// loaded/synced by the caller before this renders; this component is
// purely display + the two per-episode actions.
import { computed, ref, watch } from "vue";

export interface EpisodeVM {
  id: string;
  episodeNumber: number;
  title: string | null;
  description: string | null;
  airDate: string | null;
  stillUrl: string | null;
  watched: boolean;
  rating: number | null;
}

const props = defineProps<{
  episodes: EpisodeVM[];
  loading: boolean;
}>();

const emit = defineEmits<{
  (e: "toggle-watched", episodeId: string): void;
  (e: "set-rating", episodeId: string, rating: number | null): void;
}>();

function onRatingInput(episodeId: string, event: Event) {
  const raw = (event.target as HTMLInputElement).value;
  emit("set-rating", episodeId, raw === "" ? null : Number(raw));
}

// Long-running shows (Naruto Shippuden-style, 500+ episodes) would
// otherwise dump every row into the DOM at once — paginate in fixed
// chunks instead. Most shows (well under 50 episodes) never hit this at
// all; the controls only render once there's more than one page.
const PAGE_SIZE = 50;
const page = ref(0);
const pageCount = computed(() =>
  Math.max(1, Math.ceil(props.episodes.length / PAGE_SIZE)),
);
// Land on whichever page has the next unwatched episode (i.e. roughly
// "where you left off") the first time a real episode list shows up,
// rather than always starting at episode 1 — re-picks only when the
// episode list itself changes (a different season, or the initial
// sync), not on every watched-toggle inside the current page.
watch(
  () => props.episodes,
  (episodes) => {
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
  props.episodes.slice(pageStart.value, pageStart.value + PAGE_SIZE),
);
function goToPage(p: number) {
  page.value = Math.min(Math.max(p, 0), pageCount.value - 1);
}
</script>

<template>
  <div class="episode-list">
    <p v-if="loading" class="episodes-loading">Loading episodes…</p>
    <p v-else-if="!episodes.length" class="episodes-unavailable">
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
              Math.min(p * PAGE_SIZE, episodes.length)
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
        :class="{ watched: ep.watched }"
      >
      <button
        type="button"
        class="episode-checkbox"
        :title="ep.watched ? 'Mark unwatched' : 'Mark watched'"
        @click="emit('toggle-watched', ep.id)"
      >
        <span v-if="ep.watched">✓</span>
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
          <span class="episode-title">{{ ep.title || "Untitled" }}</span>
          <span v-if="ep.airDate" class="episode-air">{{ ep.airDate }}</span>
        </div>
        <p v-if="ep.description" class="episode-desc">{{ ep.description }}</p>
      </div>
      <div class="episode-rating">
        <span class="star">★</span>
        <input
          type="number"
          min="0"
          max="10"
          step="0.1"
          placeholder="–"
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
  grid-template-columns: 26px 140px 1fr auto;
  gap: 14px;
  align-items: center;
  background: #1a1a1a;
  border: 1px solid #202020;
  border-radius: 10px;
  padding: 10px;
  transition: border-color 0.15s ease;
}
.episode-row.watched {
  border-color: rgba(214, 138, 52, 0.4);
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
