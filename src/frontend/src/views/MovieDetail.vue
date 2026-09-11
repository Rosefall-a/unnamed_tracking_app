<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { getMovie, updateMovie, movieToInput } from "../services/movies";
import type { Movie } from "../types/movie";
import MovieFormModal from "../components/MovieFormModal.vue";

const route = useRoute();
const router = useRouter();
const movieId = route.params.id as string;

const movie = ref<Movie | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);
const showEditModal = ref(false);

function goBack() {
  if (window.history.length > 1) {
    router.back();
  } else {
    router.push("/movies");
  }
}

async function load() {
  loading.value = true;
  try {
    movie.value = await getMovie(movieId);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to load movie.";
  } finally {
    loading.value = false;
  }
}

async function toggleFavorite() {
  if (!movie.value) return;
  const next = !movie.value.favorite;
  movie.value.favorite = next;
  try {
    await updateMovie(movie.value.id, {
      ...movieToInput(movie.value),
      favorite: next,
    });
  } catch {
    movie.value.favorite = !next;
  }
}

function onSaved(saved: Movie) {
  movie.value = saved;
  showEditModal.value = false;
}

function onDeleted() {
  router.push("/movies");
}

const releaseYear = computed(() =>
  movie.value?.releaseDate ? movie.value.releaseDate.slice(0, 4) : null,
);
const runtimeLabel = computed(() => {
  const minutes = movie.value?.runtimeMinutes;
  if (!minutes) return null;
  const hrs = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return hrs > 0 ? `${hrs}h ${mins}m` : `${mins}m`;
});

onMounted(load);
</script>

<template>
  <main v-if="loading" class="detail loading-state">
    <p>Loading…</p>
  </main>

  <main v-else-if="error" class="detail error-state">
    <p>{{ error }}</p>
  </main>

  <main v-else-if="movie" class="detail">
    <div
      class="ambient-bg"
      :style="
        movie.posterUrl ? { backgroundImage: `url(${movie.posterUrl})` } : {}
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

    <MovieFormModal
      v-if="showEditModal"
      :movie="movie"
      @saved="onSaved"
      @deleted="onDeleted"
      @closed="showEditModal = false"
    />

    <section
      class="hero"
      :class="{ 'no-poster': !movie.posterUrl }"
      :style="
        movie.posterUrl ? { backgroundImage: `url(${movie.posterUrl})` } : {}
      "
    >
      <div class="hero-overlay"></div>
      <div class="hero-actions">
        <button
          class="hero-icon-button"
          :class="{ active: movie.favorite }"
          type="button"
          :title="movie.favorite ? 'Remove from favorites' : 'Add to favorites'"
          @click="toggleFavorite"
        >
          <svg
            viewBox="0 0 24 24"
            width="16"
            height="16"
            :fill="movie.favorite ? 'currentColor' : 'none'"
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
        <h1>{{ movie.title }}</h1>
        <div class="badges">
          <span class="badge status-badge">{{ movie.status }}</span>
          <span v-if="movie.ratingOverall !== null" class="badge rating-badge"
            >★ {{ movie.ratingOverall.toFixed(1) }}</span
          >
          <span v-if="releaseYear" class="badge">{{ releaseYear }}</span>
          <span v-if="runtimeLabel" class="badge">{{ runtimeLabel }}</span>
        </div>
      </div>
    </section>

    <div class="body">
      <p v-if="movie.description" class="description">
        {{ movie.description }}
      </p>

      <div class="meta-grid">
        <div v-if="movie.director" class="meta-item">
          <span class="meta-label">Director</span>
          <span class="meta-value">{{ movie.director }}</span>
        </div>
        <div v-if="movie.writer" class="meta-item">
          <span class="meta-label">Writer</span>
          <span class="meta-value">{{ movie.writer }}</span>
        </div>
        <div v-if="movie.studios.length" class="meta-item">
          <span class="meta-label">Studios</span>
          <span class="meta-value">{{ movie.studios.join(", ") }}</span>
        </div>
        <div v-if="movie.personalRank !== null" class="meta-item">
          <span class="meta-label">Personal rank</span>
          <span class="meta-value">#{{ movie.personalRank }}</span>
        </div>
        <div v-if="movie.rewatches > 0" class="meta-item">
          <span class="meta-label">Rewatches</span>
          <span class="meta-value">{{ movie.rewatches }}</span>
        </div>
      </div>

      <div v-if="movie.genres.length" class="chip-row">
        <span v-for="g in movie.genres" :key="g" class="chip">{{ g }}</span>
      </div>
      <div v-if="movie.tags.length" class="chip-row">
        <span v-for="t in movie.tags" :key="t" class="chip chip-muted">{{
          t
        }}</span>
      </div>
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
</style>
