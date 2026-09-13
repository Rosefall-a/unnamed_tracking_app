<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  getTVShow,
  updateTVShow,
  tvShowToInput,
  createSeason,
  updateSeason,
  deleteSeason,
} from "../services/tvShows";
import type { TVShow } from "../types/tv_show";
import TVShowFormModal from "../components/TVShowFormModal.vue";

const route = useRoute();
const router = useRouter();
const showId = route.params.id as string;

const show = ref<TVShow | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);
const showEditModal = ref(false);

function goBack() {
  if (window.history.length > 1) {
    router.back();
  } else {
    router.push("/tv");
  }
}

async function load() {
  loading.value = true;
  try {
    show.value = await getTVShow(showId);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to load show.";
  } finally {
    loading.value = false;
  }
}

async function toggleFavorite() {
  if (!show.value) return;
  const next = !show.value.favorite;
  show.value.favorite = next;
  try {
    await updateTVShow(show.value.id, {
      ...tvShowToInput(show.value),
      favorite: next,
    });
  } catch {
    show.value.favorite = !next;
  }
}

function onSaved(saved: TVShow) {
  show.value = saved;
  showEditModal.value = false;
}

function onDeleted() {
  router.push("/tv");
}

const firstAirYear = computed(() =>
  show.value?.firstAirDate ? show.value.firstAirDate.slice(0, 4) : null,
);
const episodeRuntimeLabel = computed(() => {
  const minutes = show.value?.episodeRuntimeMinutes;
  return minutes ? `${minutes}m episodes` : null;
});

// ---- seasons ----
const addingSeasonatFor = ref(false);
const newSeasonNumber = ref<number | null>(null);
const newSeasonName = ref("");
const newSeasonEpisodeCount = ref<number | null>(null);
const seasonError = ref<string | null>(null);

function openAddSeason() {
  const existing = show.value?.seasons ?? [];
  newSeasonNumber.value = existing.length
    ? Math.max(...existing.map((s) => s.seasonNumber)) + 1
    : 1;
  newSeasonName.value = "";
  newSeasonEpisodeCount.value = null;
  seasonError.value = null;
  addingSeasonatFor.value = true;
}

async function submitAddSeason() {
  if (!show.value || newSeasonNumber.value === null) return;
  seasonError.value = null;
  try {
    show.value = await createSeason(show.value.id, {
      seasonNumber: newSeasonNumber.value,
      name: newSeasonName.value.trim() || null,
      episodeCount: newSeasonEpisodeCount.value,
    });
    addingSeasonatFor.value = false;
  } catch (e) {
    seasonError.value =
      e instanceof Error ? e.message : "Failed to add season.";
  }
}

async function setEpisodesWatched(seasonId: string, value: number) {
  if (!show.value) return;
  const season = show.value.seasons.find((s) => s.id === seasonId);
  if (!season) return;
  const max = season.episodeCount ?? Infinity;
  const clamped = Math.max(0, Math.min(value, max));
  try {
    show.value = await updateSeason(show.value.id, seasonId, {
      episodesWatched: clamped,
    });
  } catch (e) {
    seasonError.value =
      e instanceof Error ? e.message : "Failed to update progress.";
  }
}

async function removeSeason(seasonId: string) {
  if (!show.value) return;
  try {
    show.value = await deleteSeason(show.value.id, seasonId);
  } catch (e) {
    seasonError.value =
      e instanceof Error ? e.message : "Failed to delete season.";
  }
}

onMounted(load);
</script>

<template>
  <main v-if="loading" class="detail loading-state">
    <p>Loading…</p>
  </main>

  <main v-else-if="error" class="detail error-state">
    <p>{{ error }}</p>
  </main>

  <main v-else-if="show" class="detail">
    <div
      class="ambient-bg"
      :style="
        show.posterUrl ? { backgroundImage: `url(${show.posterUrl})` } : {}
      "
    ></div>

    <button
      type="button"
      class="back-arrow-button"
      title="Back"
      @click="goBack"
    >
      <svg
        viewBox="0 0 24 24"
        width="18"
        height="18"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <path d="M19 12H5" />
        <path d="M12 19l-7-7 7-7" />
      </svg>
    </button>

    <TVShowFormModal
      v-if="showEditModal"
      :show="show"
      @saved="onSaved"
      @deleted="onDeleted"
      @closed="showEditModal = false"
    />

    <section
      class="hero"
      :class="{ 'no-poster': !show.posterUrl }"
      :style="
        show.posterUrl ? { backgroundImage: `url(${show.posterUrl})` } : {}
      "
    >
      <div class="hero-overlay"></div>
      <div class="hero-actions">
        <button
          class="hero-icon-button"
          :class="{ active: show.favorite }"
          type="button"
          :title="show.favorite ? 'Remove from favorites' : 'Add to favorites'"
          @click="toggleFavorite"
        >
          <svg
            viewBox="0 0 24 24"
            width="16"
            height="16"
            :fill="show.favorite ? 'currentColor' : 'none'"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path
              d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.6l-1-1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 21l7.8-7.8 1-1a5.5 5.5 0 0 0 0-7.6z"
            />
          </svg>
        </button>
        <button class="edit-button" type="button" @click="showEditModal = true">
          Edit
        </button>
      </div>
      <div class="hero-inner">
        <h1>{{ show.title }}</h1>
        <div class="badges">
          <span class="badge status-badge">{{ show.status }}</span>
          <span v-if="show.ratingOverall !== null" class="badge rating-badge"
            >★ {{ show.ratingOverall.toFixed(1) }}</span
          >
          <span v-if="firstAirYear" class="badge">{{ firstAirYear }}</span>
          <span v-if="episodeRuntimeLabel" class="badge">{{
            episodeRuntimeLabel
          }}</span>
          <span v-if="show.seasons.length" class="badge"
            >{{ show.seasons.length }} season{{
              show.seasons.length === 1 ? "" : "s"
            }}</span
          >
        </div>
      </div>
    </section>

    <div class="body">
      <p v-if="show.description" class="description">{{ show.description }}</p>

      <div class="meta-grid">
        <div v-if="show.creators.length" class="meta-item">
          <span class="meta-label">Creators</span>
          <span class="meta-value">{{ show.creators.join(", ") }}</span>
        </div>
        <div v-if="show.studios.length" class="meta-item">
          <span class="meta-label">Studios</span>
          <span class="meta-value">{{ show.studios.join(", ") }}</span>
        </div>
        <div v-if="show.personalRank !== null" class="meta-item">
          <span class="meta-label">Personal rank</span>
          <span class="meta-value">#{{ show.personalRank }}</span>
        </div>
        <div v-if="show.rewatches > 0" class="meta-item">
          <span class="meta-label">Rewatches</span>
          <span class="meta-value">{{ show.rewatches }}</span>
        </div>
      </div>

      <div v-if="show.genres.length" class="chip-row">
        <span v-for="g in show.genres" :key="g" class="chip">{{ g }}</span>
      </div>
      <div v-if="show.tags.length" class="chip-row">
        <span v-for="t in show.tags" :key="t" class="chip chip-muted">{{
          t
        }}</span>
      </div>

      <section class="seasons-section">
        <div class="seasons-header">
          <h2>Seasons</h2>
          <button
            type="button"
            class="add-season-button"
            @click="openAddSeason"
          >
            + Add Season
          </button>
        </div>

        <p v-if="seasonError" class="error-text">{{ seasonError }}</p>

        <div v-if="addingSeasonatFor" class="add-season-form">
          <label class="field">
            <span>Number</span>
            <input
              v-model.number="newSeasonNumber"
              type="number"
              min="1"
              class="text-input"
            />
          </label>
          <label class="field">
            <span>Name (optional)</span>
            <input v-model="newSeasonName" type="text" class="text-input" />
          </label>
          <label class="field">
            <span>Episode count</span>
            <input
              v-model.number="newSeasonEpisodeCount"
              type="number"
              min="0"
              class="text-input"
            />
          </label>
          <div class="add-season-actions">
            <button
              type="button"
              class="secondary-button"
              @click="addingSeasonatFor = false"
            >
              Cancel
            </button>
            <button type="button" class="primary-btn" @click="submitAddSeason">
              Add
            </button>
          </div>
        </div>

        <p
          v-if="!show.seasons.length && !addingSeasonatFor"
          class="empty-state"
        >
          No seasons yet.
        </p>

        <div v-else class="seasons-list">
          <div
            v-for="season in show.seasons"
            :key="season.id"
            class="season-row"
          >
            <div class="season-info">
              <span class="season-title"
                >Season {{ season.seasonNumber
                }}<template v-if="season.name">
                  — {{ season.name }}</template
                ></span
              >
              <span class="season-sub">{{ season.status }}</span>
            </div>
            <div class="season-progress">
              <button
                type="button"
                class="stepper-btn"
                @click="
                  setEpisodesWatched(season.id, season.episodesWatched - 1)
                "
              >
                −
              </button>
              <span class="progress-value"
                >{{ season.episodesWatched
                }}<template v-if="season.episodeCount">
                  / {{ season.episodeCount }}</template
                ></span
              >
              <button
                type="button"
                class="stepper-btn"
                @click="
                  setEpisodesWatched(season.id, season.episodesWatched + 1)
                "
              >
                +
              </button>
            </div>
            <button
              type="button"
              class="remove-season-button"
              title="Remove season"
              @click="removeSeason(season.id)"
            >
              &times;
            </button>
          </div>
        </div>
      </section>
    </div>
  </main>
</template>

<style scoped>
.detail {
  min-height: 100vh;
  background: #121212;
  color: #fff;
  font-family: system-ui, sans-serif;
  position: relative;
  overflow: hidden;
}
.loading-state,
.error-state {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #999;
}
.ambient-bg {
  position: fixed;
  inset: 0;
  background-size: cover;
  background-position: center;
  filter: blur(80px);
  opacity: 0.25;
  transform: scale(1.2);
  z-index: 0;
}
.hero,
.body {
  position: relative;
  z-index: 1;
}
.hero {
  position: relative;
  background-size: cover;
  background-position: center;
  background-color: #1a1a1a;
  min-height: 360px;
  display: flex;
  align-items: flex-end;
}
.hero.no-poster {
  background: linear-gradient(160deg, #241a10, #121212 70%);
}
.hero-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    180deg,
    rgba(18, 18, 18, 0) 40%,
    rgba(18, 18, 18, 0.85) 85%,
    #121212 100%
  );
}
.hero-inner {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px 28px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 18px;
}
.hero-inner h1 {
  margin: 0;
  font-size: 2.4rem;
  text-shadow: 0 2px 12px rgba(0, 0, 0, 0.6);
}
.badges {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.badge {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 999px;
  padding: 4px 14px;
  font-size: 13px;
  text-transform: capitalize;
  color: #ddd;
}
.rating-badge {
  color: #d68a34;
}
.back-arrow-button {
  position: fixed;
  top: 16px;
  left: 62px;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(20, 20, 20, 0.55);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 100;
  transition: background 0.15s ease;
}
.back-arrow-button:hover {
  background: rgba(40, 40, 40, 0.85);
}
.hero-actions {
  position: absolute;
  bottom: 20px;
  right: 24px;
  z-index: 2;
  display: flex;
  align-items: center;
  gap: 8px;
}
.hero-icon-button {
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.25);
  color: #fff;
  border-radius: 50%;
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition:
    background 0.15s ease,
    color 0.15s ease;
}
.hero-icon-button:hover {
  background: rgba(0, 0, 0, 0.7);
}
.hero-icon-button.active {
  color: #d68a34;
  border-color: rgba(214, 138, 52, 0.5);
}
.edit-button {
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.25);
  color: #fff;
  border-radius: 8px;
  padding: 8px 16px;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s ease;
}
.edit-button:hover {
  background: rgba(0, 0, 0, 0.7);
}
.body {
  max-width: 1200px;
  margin: 0 auto;
  padding: 28px 24px 60px;
  display: flex;
  flex-direction: column;
  gap: 22px;
}
.description {
  color: #ccc;
  line-height: 1.6;
  max-width: 720px;
  margin: 0;
}
.meta-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px 24px;
}
.meta-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.meta-label {
  font-size: 0.72rem;
  color: #888;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.meta-value {
  color: #eee;
  font-size: 0.9rem;
}
.chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.chip {
  background: rgba(214, 138, 52, 0.16);
  color: #d68a34;
  border-radius: 999px;
  padding: 4px 12px;
  font-size: 0.78rem;
}
.chip-muted {
  background: rgba(255, 255, 255, 0.08);
  color: #ccc;
}
.error-text {
  color: #fca5a5;
  font-size: 0.85rem;
  margin: 0;
}
.seasons-section {
  border-top: 1px solid #2a2a2a;
  padding-top: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.seasons-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.seasons-header h2 {
  margin: 0;
  font-size: 1.1rem;
}
.add-season-button {
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  color: #d68a34;
  border-radius: 8px;
  padding: 7px 12px;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
}
.add-season-button:hover {
  border-color: #d68a34;
}
.add-season-form {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  flex-wrap: wrap;
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  border-radius: 10px;
  padding: 14px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.field span {
  font-size: 0.75rem;
  color: #999;
}
.text-input {
  background: #111;
  border: 1px solid #2a2a2a;
  border-radius: 8px;
  color: #fff;
  padding: 7px 10px;
  font-size: 0.85rem;
  font-family: inherit;
  width: 140px;
}
.add-season-actions {
  display: flex;
  gap: 8px;
}
.primary-btn {
  background: #d68a34;
  color: #121212;
  border: none;
  border-radius: 8px;
  padding: 8px 16px;
  font-weight: 700;
  font-size: 0.85rem;
  cursor: pointer;
}
.secondary-button {
  background: #111;
  border: 1px solid #2a2a2a;
  color: #ccc;
  border-radius: 8px;
  padding: 8px 14px;
  font-size: 0.85rem;
  cursor: pointer;
}
.empty-state {
  color: #777;
  font-size: 0.85rem;
}
.seasons-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.season-row {
  display: flex;
  align-items: center;
  gap: 14px;
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  border-radius: 10px;
  padding: 10px 14px;
}
.season-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
}
.season-title {
  font-size: 0.9rem;
  font-weight: 600;
}
.season-sub {
  font-size: 0.72rem;
  color: #999;
  text-transform: capitalize;
}
.season-progress {
  display: flex;
  align-items: center;
  gap: 8px;
}
.stepper-btn {
  width: 26px;
  height: 26px;
  border-radius: 6px;
  background: #111;
  border: 1px solid #2a2a2a;
  color: #fff;
  cursor: pointer;
  font-size: 1rem;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}
.stepper-btn:hover {
  border-color: #d68a34;
  color: #d68a34;
}
.progress-value {
  font-size: 0.85rem;
  color: #d68a34;
  font-variant-numeric: tabular-nums;
  min-width: 48px;
  text-align: center;
}
.remove-season-button {
  background: none;
  border: none;
  color: #666;
  font-size: 1.2rem;
  cursor: pointer;
  line-height: 1;
  padding: 4px;
}
.remove-season-button:hover {
  color: #fca5a5;
}
</style>
