<script setup lang="ts">
import { ref, onMounted } from "vue";
import { fetchMovies } from "../services/movies";
import type { Movie } from "../types/movie";
import MovieFormModal from "../components/MovieFormModal.vue";

const movies = ref<Movie[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

const showModal = ref(false);
const editingMovie = ref<Movie | null>(null);

async function load() {
  loading.value = true;
  try {
    movies.value = await fetchMovies();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to load movies.";
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  editingMovie.value = null;
  showModal.value = true;
}

function openEdit(movie: Movie) {
  editingMovie.value = movie;
  showModal.value = true;
}

function onSaved(movie: Movie) {
  const index = movies.value.findIndex((m) => m.id === movie.id);
  if (index === -1) {
    movies.value.push(movie);
  } else {
    movies.value[index] = movie;
  }
  showModal.value = false;
}

function onDeleted(movieId: string) {
  movies.value = movies.value.filter((m) => m.id !== movieId);
  showModal.value = false;
}

onMounted(load);
</script>

<template>
  <main class="movies-page">
    <div class="header-row">
      <h1>Movies</h1>
      <button type="button" class="add-button" @click="openCreate">
        + Add Movie
      </button>
    </div>
    <p class="section-hint">Everything you're tracking on the big screen.</p>

    <p v-if="loading" class="empty-state">Loading…</p>
    <p v-else-if="error" class="empty-state error">{{ error }}</p>
    <p v-else-if="!movies.length" class="empty-state">
      No movies yet — add your first one.
    </p>

    <div v-else class="movies-grid">
      <button
        v-for="m in movies"
        :key="m.id"
        type="button"
        class="movie-tile"
        :class="{ 'has-poster': m.posterUrl }"
        @click="openEdit(m)"
      >
        <img
          v-if="m.posterUrl"
          :src="m.posterUrl"
          alt=""
          class="movie-tile-poster"
        />
        <span v-if="m.favorite" class="favorite-chip">★</span>
        <span class="movie-tile-title">{{ m.title }}</span>
        <span class="movie-tile-status">{{ m.status }}</span>
        <span v-if="m.ratingOverall !== null" class="movie-tile-rating"
          >★ {{ m.ratingOverall.toFixed(1) }}</span
        >
      </button>
    </div>

    <MovieFormModal
      v-if="showModal"
      :movie="editingMovie"
      @saved="onSaved"
      @deleted="onDeleted"
      @closed="showModal = false"
    />
  </main>
</template>

<style scoped>
.movies-page {
  min-height: 100vh;
  background: #121212;
  color: #fff;
  padding: 84px 24px 24px;
  font-family: system-ui, sans-serif;
  box-sizing: border-box;
}
.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
h1 {
  margin: 0;
}
.section-hint {
  color: #999;
  font-size: 0.85rem;
}
.empty-state {
  color: #777;
}
.empty-state.error {
  color: #fca5a5;
}
.add-button {
  background: #d68a34;
  border: none;
  color: #121212;
  font-weight: 700;
  border-radius: 8px;
  padding: 9px 14px;
  font-size: 0.85rem;
  cursor: pointer;
}
.movies-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
  margin-top: 20px;
}
.movie-tile {
  position: relative;
  aspect-ratio: 5 / 7;
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  border-radius: 10px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  align-items: flex-start;
  padding: 12px;
  cursor: pointer;
  color: #fff;
  text-align: left;
  gap: 4px;
}
.movie-tile:hover {
  border-color: #d68a34;
}
.movie-tile-poster {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  z-index: 0;
}
.movie-tile.has-poster::before {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(
    to top,
    rgba(0, 0, 0, 0.88) 0%,
    rgba(0, 0, 0, 0.45) 55%,
    rgba(0, 0, 0, 0.1) 100%
  );
  z-index: 1;
}
.movie-tile.has-poster > *:not(.movie-tile-poster) {
  position: relative;
  z-index: 2;
}
.favorite-chip {
  position: absolute;
  top: 10px;
  right: 10px;
  color: #d68a34;
  font-size: 0.95rem;
}
.movie-tile-title {
  font-weight: 600;
  font-size: 0.9rem;
}
.movie-tile-status {
  font-size: 0.72rem;
  color: #999;
  text-transform: capitalize;
}
.movie-tile-rating {
  font-size: 0.72rem;
  color: #d68a34;
}
</style>
