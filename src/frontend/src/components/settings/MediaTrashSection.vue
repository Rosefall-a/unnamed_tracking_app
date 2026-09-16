<script setup lang="ts">
import { ref, onMounted } from "vue";
import { fetchMovieTrash, restoreMovie, purgeMovie } from "../../services/movies";
import type { TrashedMovie } from "../../services/movies";
import { fetchTVShowTrash, restoreTVShow, purgeTVShow } from "../../services/tvShows";
import type { TrashedTVShow } from "../../services/tvShows";
import { fetchAnimeTrash, restoreAnime, purgeAnime } from "../../services/anime";
import type { TrashedAnime } from "../../services/anime";

const movieTrash = ref<TrashedMovie[]>([]);
const tvTrash = ref<TrashedTVShow[]>([]);
const animeTrash = ref<TrashedAnime[]>([]);
const loading = ref(false);
const error = ref<string | null>(null);
const busyId = ref<string | null>(null);

async function loadAll() {
  loading.value = true;
  error.value = null;
  try {
    [movieTrash.value, tvTrash.value, animeTrash.value] = await Promise.all([
      fetchMovieTrash(),
      fetchTVShowTrash(),
      fetchAnimeTrash(),
    ]);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to load deleted media";
  } finally {
    loading.value = false;
  }
}
onMounted(loadAll);

function formatDate(epochSeconds: number): string {
  return new Date(epochSeconds * 1000).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

async function restore(kind: "movie" | "tv" | "anime", id: string) {
  busyId.value = id;
  error.value = null;
  try {
    if (kind === "movie") await restoreMovie(id);
    else if (kind === "tv") await restoreTVShow(id);
    else await restoreAnime(id);
    await loadAll();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to restore";
  } finally {
    busyId.value = null;
  }
}

async function purge(kind: "movie" | "tv" | "anime", id: string, title: string) {
  if (!window.confirm(`Permanently delete "${title}"? This can't be undone.`)) return;
  busyId.value = id;
  error.value = null;
  try {
    if (kind === "movie") await purgeMovie(id);
    else if (kind === "tv") await purgeTVShow(id);
    else await purgeAnime(id);
    await loadAll();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to permanently delete";
  } finally {
    busyId.value = null;
  }
}
</script>

<template>
  <section class="settings-section">
    <h2>Media Trash</h2>
    <p class="section-hint">
      A deleted movie, show, or anime entry moves here first. Nothing gets
      purged automatically — restore it to bring it back, or delete it again
      here to remove it for good.
    </p>

    <p v-if="loading">Loading…</p>
    <div v-if="error" class="form-error">{{ error }}</div>

    <template v-if="!loading">
      <div class="trash-group">
        <h3>Movies</h3>
        <p v-if="!movieTrash.length" class="empty-hint">Nothing in trash.</p>
        <ul v-else class="trash-list">
          <li v-for="item in movieTrash" :key="item.id" class="trash-row">
            <span class="trash-name">{{ item.title }}</span>
            <span class="trash-meta">deleted {{ formatDate(item.deleted_at) }}</span>
            <button
              type="button"
              class="secondary-button"
              :disabled="busyId === item.id"
              @click="restore('movie', item.id)"
            >
              Restore
            </button>
            <button
              type="button"
              class="danger-button"
              :disabled="busyId === item.id"
              @click="purge('movie', item.id, item.title)"
            >
              Delete forever
            </button>
          </li>
        </ul>
      </div>

      <div class="trash-group">
        <h3>TV Shows</h3>
        <p v-if="!tvTrash.length" class="empty-hint">Nothing in trash.</p>
        <ul v-else class="trash-list">
          <li v-for="item in tvTrash" :key="item.id" class="trash-row">
            <span class="trash-name">{{ item.title }}</span>
            <span class="trash-meta">deleted {{ formatDate(item.deleted_at) }}</span>
            <button
              type="button"
              class="secondary-button"
              :disabled="busyId === item.id"
              @click="restore('tv', item.id)"
            >
              Restore
            </button>
            <button
              type="button"
              class="danger-button"
              :disabled="busyId === item.id"
              @click="purge('tv', item.id, item.title)"
            >
              Delete forever
            </button>
          </li>
        </ul>
      </div>

      <div class="trash-group">
        <h3>Anime</h3>
        <p v-if="!animeTrash.length" class="empty-hint">Nothing in trash.</p>
        <ul v-else class="trash-list">
          <li v-for="item in animeTrash" :key="item.id" class="trash-row">
            <span class="trash-name">{{ item.title }}</span>
            <span class="trash-meta">deleted {{ formatDate(item.deleted_at) }}</span>
            <button
              type="button"
              class="secondary-button"
              :disabled="busyId === item.id"
              @click="restore('anime', item.id)"
            >
              Restore
            </button>
            <button
              type="button"
              class="danger-button"
              :disabled="busyId === item.id"
              @click="purge('anime', item.id, item.title)"
            >
              Delete forever
            </button>
          </li>
        </ul>
      </div>
    </template>
  </section>
</template>

<style scoped>
.settings-section h2 {
  margin: 0 0 8px;
  padding-left: 12px;
  border-left: 3px solid #d68a34;
  font-size: 1rem;
  color: #fff;
}
.section-hint {
  color: #999;
  font-size: 0.82rem;
  line-height: 1.6;
  margin: 0 0 20px;
}
.trash-group {
  margin-bottom: 20px;
}
.trash-group h3 {
  margin: 0 0 8px;
  font-size: 0.85rem;
  color: #ccc;
}
.empty-hint {
  color: #777;
  font-size: 0.82rem;
}
.trash-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.trash-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid #232323;
  border-radius: 8px;
  font-size: 0.82rem;
}
.trash-name {
  flex: 1;
  color: #ccc;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.trash-meta {
  color: #777;
  font-size: 0.76rem;
}
.secondary-button {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 6px 14px;
  font-weight: 600;
  font-size: 0.78rem;
  cursor: pointer;
}
.secondary-button:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.14);
}
.secondary-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.danger-button {
  background: rgba(220, 38, 38, 0.12);
  color: #fca5a5;
  border: 1px solid rgba(220, 38, 38, 0.3);
  border-radius: 8px;
  padding: 6px 14px;
  font-weight: 600;
  font-size: 0.78rem;
  cursor: pointer;
}
.danger-button:hover:not(:disabled) {
  background: rgba(220, 38, 38, 0.2);
}
.danger-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.form-error {
  color: #fca5a5;
  font-size: 13px;
  background: rgba(220, 38, 38, 0.1);
  border: 1px solid rgba(220, 38, 38, 0.3);
  border-radius: 8px;
  padding: 8px 10px;
  margin-bottom: 16px;
}
</style>
