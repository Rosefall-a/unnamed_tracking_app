<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { fetchAnime } from "../services/anime";
import type { Anime } from "../types/anime";
import AnimeFormModal from "../components/AnimeFormModal.vue";

const router = useRouter();

const shows = ref<Anime[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

const showCreateModal = ref(false);

async function load() {
  loading.value = true;
  try {
    shows.value = await fetchAnime();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to load anime.";
  } finally {
    loading.value = false;
  }
}

function openShow(show: Anime) {
  router.push(`/anime/${show.id}`);
}

function onCreated(show: Anime) {
  shows.value.push(show);
  showCreateModal.value = false;
}

onMounted(load);
</script>

<template>
  <main class="shows-page">
    <div class="header-row">
      <h1>Anime</h1>
      <button type="button" class="add-button" @click="showCreateModal = true">
        + Add Anime
      </button>
    </div>
    <p class="section-hint">Everything you're tracking from AniList and MAL.</p>

    <p v-if="loading" class="empty-state">Loading…</p>
    <p v-else-if="error" class="empty-state error">{{ error }}</p>
    <p v-else-if="!shows.length" class="empty-state">
      No anime yet — add your first one.
    </p>

    <div v-else class="shows-grid">
      <button
        v-for="s in shows"
        :key="s.id"
        type="button"
        class="show-tile"
        :class="{ 'has-poster': s.posterUrl }"
        @click="openShow(s)"
      >
        <img
          v-if="s.posterUrl"
          :src="s.posterUrl"
          alt=""
          class="show-tile-poster"
        />
        <span v-if="s.favorite" class="favorite-chip">★</span>
        <span class="show-tile-title">{{ s.title }}</span>
        <span class="show-tile-status">{{ s.status }}</span>
        <span v-if="s.seasons.length" class="show-tile-seasons"
          >{{ s.seasons.length }} season{{
            s.seasons.length === 1 ? "" : "s"
          }}</span
        >
      </button>
    </div>

    <AnimeFormModal
      v-if="showCreateModal"
      :show="null"
      @saved="onCreated"
      @closed="showCreateModal = false"
    />
  </main>
</template>

<style scoped>
.shows-page {
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
.shows-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
  margin-top: 20px;
}
.show-tile {
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
.show-tile:hover {
  border-color: #d68a34;
}
.show-tile-poster {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  z-index: 0;
}
.show-tile.has-poster::before {
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
.show-tile.has-poster > *:not(.show-tile-poster) {
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
.show-tile-title {
  font-weight: 600;
  font-size: 0.9rem;
}
.show-tile-status {
  font-size: 0.72rem;
  color: #999;
  text-transform: capitalize;
}
.show-tile-seasons {
  font-size: 0.72rem;
  color: #d68a34;
}
</style>
