<script setup lang="ts">
import { useConfirm } from "../../state/dialog";
import { ref, computed, onMounted } from "vue";
import {
  fetchMovieTrash,
  restoreMovie,
  purgeMovie,
} from "../../services/movies";
import type { TrashedMovie } from "../../services/movies";
import {
  fetchTVShowTrash,
  restoreTVShow,
  purgeTVShow,
} from "../../services/tvShows";
import type { TrashedTVShow } from "../../services/tvShows";
import {
  fetchAnimeTrash,
  restoreAnime,
  purgeAnime,
} from "../../services/anime";
import type { TrashedAnime } from "../../services/anime";

const movieTrash = ref<TrashedMovie[]>([]);
const tvTrash = ref<TrashedTVShow[]>([]);
const animeTrash = ref<TrashedAnime[]>([]);
const loading = ref(false);
// the list stays on screen while it reloads after a restore or delete
const loadedOnce = ref(false);
const error = ref<string | null>(null);
const busyId = ref<string | null>(null);
const search = ref("");
const PAGE = 50;
const limits = ref<Record<Kind, number>>({
  movie: PAGE,
  tv: PAGE,
  anime: PAGE,
});

type Kind = "movie" | "tv" | "anime";
interface TrashRow {
  id: string;
  title: string;
  deleted_at: number;
}
const groups = computed<
  {
    kind: Kind;
    label: string;
    total: number;
    matches: number;
    rows: TrashRow[];
  }[]
>(() => {
  const q = search.value.trim().toLowerCase();
  const build = (kind: Kind, label: string, all: TrashRow[]) => {
    const found = q
      ? all.filter((r) => r.title.toLowerCase().includes(q))
      : all;
    return {
      kind,
      label,
      total: all.length,
      matches: found.length,
      rows: found.slice(0, limits.value[kind]),
    };
  };
  return [
    build("movie", "Movies", movieTrash.value),
    build("tv", "TV Shows", tvTrash.value),
    build("anime", "Anime", animeTrash.value),
  ];
});

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
    error.value =
      e instanceof Error ? e.message : "Failed to load deleted media";
  } finally {
    loading.value = false;
    loadedOnce.value = true;
  }
}
onMounted(loadAll);

function formatDate(epochSeconds: number): string {
  return new Date(epochSeconds * 1000).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

async function restore(kind: Kind, id: string) {
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

const confirm = useConfirm();
async function purge(kind: Kind, id: string, title: string) {
  const ok = await confirm({
    message: `Permanently delete "${title}"? This can't be undone.`,
    confirmLabel: "Delete forever",
    danger: true,
  });
  if (!ok) return;
  busyId.value = id;
  error.value = null;
  try {
    if (kind === "movie") await purgeMovie(id);
    else if (kind === "tv") await purgeTVShow(id);
    else await purgeAnime(id);
    await loadAll();
  } catch (e) {
    error.value =
      e instanceof Error ? e.message : "Failed to permanently delete";
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
      purged automatically. Restore it to bring it back, or delete it again here
      to remove it for good.
    </p>

    <p v-if="!loadedOnce">Loading…</p>
    <div v-if="error" class="form-error">{{ error }}</div>

    <template v-if="loadedOnce">
      <input
        v-model="search"
        type="search"
        class="trash-search"
        placeholder="Search deleted titles"
        aria-label="Search deleted titles"
      />
      <div v-for="group in groups" :key="group.kind" class="trash-group">
        <h3>
          {{ group.label }}
          <span v-if="group.total" class="trash-count">{{ group.total }}</span>
        </h3>
        <p v-if="!group.total" class="empty-hint">Nothing in trash.</p>
        <p v-else-if="!group.matches" class="empty-hint">
          Nothing here matches the search.
        </p>
        <ul v-else class="trash-list">
          <li v-for="item in group.rows" :key="item.id" class="trash-row">
            <span class="trash-name">{{ item.title }}</span>
            <span class="trash-meta"
              >deleted {{ formatDate(item.deleted_at) }}</span
            >
            <button
              type="button"
              class="secondary-button"
              :disabled="busyId === item.id"
              @click="restore(group.kind, item.id)"
            >
              Restore
            </button>
            <button
              type="button"
              class="danger-button"
              :disabled="busyId === item.id"
              @click="purge(group.kind, item.id, item.title)"
            >
              Delete forever
            </button>
          </li>
        </ul>
        <button
          v-if="group.matches > group.rows.length"
          type="button"
          class="secondary-button more-button"
          @click="limits[group.kind] += PAGE"
        >
          Show more ({{ group.matches - group.rows.length }} left)
        </button>
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
.trash-search {
  width: 100%;
  max-width: 360px;
  box-sizing: border-box;
  margin-bottom: 18px;
  background: #1a1a1a;
  color: #e5e5e5;
  border: 1px solid #2a2a2a;
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 0.85rem;
}
.trash-count {
  margin-left: 6px;
  font-size: 0.72rem;
  font-weight: 600;
  color: #8a8a8a;
}
.more-button {
  margin-top: 10px;
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
