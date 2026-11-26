<script setup lang="ts">
import { useConfirm } from "../../state/dialog";
import { ref, computed, onMounted } from "vue";
import {
  DEFAULT_PREFERENCES,
  fetchPreferences,
  queuePreferences,
} from "../../services/preferences";
import {
  fetchMovieTrash,
  restoreMovie,
  purgeMovie,
  emptyMovieTrash,
} from "../../services/movies";
import type { TrashedMovie } from "../../services/movies";
import {
  fetchTVShowTrash,
  restoreTVShow,
  purgeTVShow,
  emptyTVShowTrash,
} from "../../services/tvShows";
import type { TrashedTVShow } from "../../services/tvShows";
import {
  fetchAnimeTrash,
  restoreAnime,
  purgeAnime,
  emptyAnimeTrash,
} from "../../services/anime";
import type { TrashedAnime } from "../../services/anime";
import { fetchGameTrash, restoreGame } from "../../services/gameTrash";
import type { TrashedGame } from "../../services/gameTrash";
import SegmentedControl from "./SegmentedControl.vue";
import SettingsRow from "./SettingsRow.vue";

const movieTrash = ref<TrashedMovie[]>([]);
const tvTrash = ref<TrashedTVShow[]>([]);
const animeTrash = ref<TrashedAnime[]>([]);
// games have their own trash on the server, kept for a fixed 7 days; they are
// listed here too so everything deleted is in one place
const gameTrash = ref<TrashedGame[]>([]);
const gameError = ref<string | null>(null);
const restoringGameId = ref<string | null>(null);
type Filter = "all" | "game" | Kind;
const filter = ref<Filter>("all");
const FILTERS = [
  { value: "all", label: "All" },
  { value: "game", label: "Games" },
  { value: "movie", label: "Movies" },
  { value: "tv", label: "TV" },
  { value: "anime", label: "Anime" },
];
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
    build("tv", "TV shows", tvTrash.value),
    build("anime", "Anime", animeTrash.value),
  ];
});

async function loadGames() {
  gameError.value = null;
  try {
    gameTrash.value = await fetchGameTrash();
  } catch (e) {
    gameError.value =
      e instanceof Error ? e.message : "Could not load deleted games";
  }
}

const shownGames = computed(() => {
  const q = search.value.trim().toLowerCase();
  return q
    ? gameTrash.value.filter((g) => g.title.toLowerCase().includes(q))
    : gameTrash.value;
});
const shownGroups = computed(() =>
  groups.value.filter((g) => filter.value === "all" || filter.value === g.kind),
);

function daysUntil(unixSeconds: number): number {
  return Math.max(0, Math.ceil((unixSeconds - Date.now() / 1000) / 86400));
}

async function restoreGameById(game: TrashedGame) {
  restoringGameId.value = game.id;
  gameError.value = null;
  try {
    await restoreGame(game.id);
    await loadGames();
  } catch (e) {
    gameError.value = e instanceof Error ? e.message : "Could not restore.";
  } finally {
    restoringGameId.value = null;
  }
}

async function loadAll() {
  loading.value = true;
  error.value = null;
  void loadGames();
  try {
    [movieTrash.value, tvTrash.value, animeTrash.value] = await Promise.all([
      fetchMovieTrash(),
      fetchTVShowTrash(),
      fetchAnimeTrash(),
    ]);
  } catch (e) {
    error.value =
      e instanceof Error ? e.message : "Could not load the media trash";
  } finally {
    loading.value = false;
    loadedOnce.value = true;
  }
}
// how long a deleted title stays before it is deleted for good; 0 keeps it until you delete it
const retentionDays = ref(DEFAULT_PREFERENCES.media_trash_retention_days);
const retentionSaved = ref(false);
const RETENTION_CHOICES = [
  { value: "0", label: "Never" },
  { value: "7", label: "7 days" },
  { value: "14", label: "14" },
  { value: "30", label: "30" },
  { value: "90", label: "90" },
];

onMounted(async () => {
  await loadAll();
  try {
    retentionDays.value = (await fetchPreferences()).media_trash_retention_days;
  } catch {
    // the default (7 days) stays shown
  }
});

async function setRetention(days: number) {
  const previous = retentionDays.value;
  retentionDays.value = days;
  error.value = null;
  try {
    await queuePreferences({ media_trash_retention_days: days });
    retentionSaved.value = true;
    setTimeout(() => (retentionSaved.value = false), 1500);
  } catch (e) {
    retentionDays.value = previous;
    error.value = e instanceof Error ? e.message : "Could not save.";
  }
}

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
    error.value =
      e instanceof Error ? e.message : "Could not restore the title";
  } finally {
    busyId.value = null;
  }
}

const confirm = useConfirm();
async function purge(kind: Kind, id: string, title: string) {
  const ok = await confirm({
    message: `Delete "${title}" permanently? This cannot be undone.`,
    confirmLabel: "Delete",
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
    error.value = e instanceof Error ? e.message : "Could not delete the title";
  } finally {
    busyId.value = null;
  }
}

async function emptyGroup(kind: Kind, label: string, count: number) {
  const ok = await confirm({
    message: `Delete all ${count} ${label} in the trash permanently? This cannot be undone.`,
    confirmLabel: "Empty trash",
    danger: true,
  });
  if (!ok) return;
  busyId.value = kind;
  error.value = null;
  try {
    if (kind === "movie") await emptyMovieTrash();
    else if (kind === "tv") await emptyTVShowTrash();
    else await emptyAnimeTrash();
    await loadAll();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Could not empty the trash";
  } finally {
    busyId.value = null;
  }
}
</script>

<template>
  <section class="settings-section">
    <div class="trash-head">
      <h2>Trash</h2>
      <SegmentedControl
        :model-value="filter"
        :options="FILTERS"
        @update:model-value="filter = $event as Filter"
      />
    </div>
    <p class="section-hint">
      One trash for everything you delete. Restore puts a title back exactly as
      it was.
    </p>
    <SettingsRow
      label="Delete games for good after"
      hint="Their screenshots, clips, saves and notes go with them"
    >
      <span class="st-muted">7 days</span>
    </SettingsRow>
    <SettingsRow label="Delete movies, shows and anime for good after">
      <span class="retention">
        <span v-if="retentionSaved" class="saved-note">Saved</span>
        <SegmentedControl
          :model-value="String(retentionDays)"
          :options="RETENTION_CHOICES"
          @update:model-value="setRetention(Number($event))"
        />
      </span>
    </SettingsRow>
    <p v-if="!loadedOnce" class="st-muted">Loading…</p>
    <div v-if="error" class="form-error">{{ error }}</div>
    <div v-if="gameError" class="form-error">{{ gameError }}</div>
    <template v-if="loadedOnce">
      <input
        v-model="search"
        type="search"
        class="trash-search"
        placeholder="Search deleted titles"
        aria-label="Search deleted titles"
      />
      <div v-if="filter === 'all' || filter === 'game'" class="trash-group">
        <h3 class="trash-group-title">
          <span>
            Games
            <span v-if="gameTrash.length" class="trash-count">{{
              gameTrash.length
            }}</span>
          </span>
        </h3>
        <p v-if="!gameTrash.length" class="empty-hint">Trash is empty.</p>
        <p v-else-if="!shownGames.length" class="empty-hint">No matches.</p>
        <ul v-else class="trash-list">
          <li v-for="game in shownGames" :key="game.id" class="trash-row">
            <span class="trash-name">{{ game.title }}</span>
            <span class="trash-meta"
              >Deleted for good in {{ daysUntil(game.purge_at) }} days</span
            >
            <button
              type="button"
              class="secondary-button"
              :disabled="restoringGameId === game.id"
              @click="restoreGameById(game)"
            >
              {{ restoringGameId === game.id ? "Restoring…" : "Restore" }}
            </button>
          </li>
        </ul>
      </div>
      <div v-for="group in shownGroups" :key="group.kind" class="trash-group">
        <h3 class="trash-group-title">
          <span>
            {{ group.label }}
            <span v-if="group.total" class="trash-count">{{
              group.total
            }}</span>
          </span>
          <button
            v-if="group.total"
            type="button"
            class="danger-button"
            :disabled="busyId !== null"
            @click="emptyGroup(group.kind, group.label, group.total)"
          >
            Empty trash
          </button>
        </h3>
        <p v-if="!group.total" class="empty-hint">Trash is empty.</p>
        <p v-else-if="!group.matches" class="empty-hint">No matches.</p>
        <ul v-else class="trash-list">
          <li v-for="item in group.rows" :key="item.id" class="trash-row">
            <span class="trash-name">{{ item.title }}</span>
            <span class="trash-meta"
              >Deleted {{ formatDate(item.deleted_at) }}</span
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
              Delete
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
.trash-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px 12px;
}
.trash-head h2 {
  margin: 0;
}
.retention {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}
.settings-section h2 {
  margin: 0 0 8px;
  padding-left: 12px;
  border-left: 3px solid var(--ui-accent);
  font-size: 1rem;
  color: var(--ui-heading);
}
.section-hint {
  color: var(--ui-dim-3);
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
  color: var(--ui-text-soft);
}
.retention-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 18px;
  font-size: 0.85rem;
  color: var(--ui-text-soft);
}
.retention-select {
  background: var(--ui-surface);
  color: var(--ui-text-strong);
  border: 1px solid var(--ui-border);
  border-radius: 8px;
  padding: 7px 10px;
  font-size: 0.85rem;
}
.saved-note {
  color: #8fbf8f;
  font-size: 0.8rem;
}
.trash-group-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.trash-search {
  width: 100%;
  max-width: 360px;
  box-sizing: border-box;
  margin-bottom: 18px;
  background: var(--ui-surface);
  color: var(--ui-text-strong);
  border: 1px solid var(--ui-border);
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 0.85rem;
}
.trash-count {
  margin-left: 6px;
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--ui-dim-2);
}
.more-button {
  margin-top: 10px;
}
.empty-hint {
  color: var(--ui-faint-2);
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
  background: color-mix(in srgb, var(--ui-wash-base) 3%, transparent);
  border: 1px solid var(--ui-surface-2);
  border-radius: 8px;
  font-size: 0.82rem;
}
.trash-name {
  flex: 1;
  color: var(--ui-text-soft);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.trash-meta {
  color: var(--ui-faint-2);
  font-size: 0.76rem;
}
.secondary-button {
  background: color-mix(in srgb, var(--ui-wash-base) 8%, transparent);
  color: var(--ui-heading);
  border: none;
  border-radius: 8px;
  padding: 6px 14px;
  font-weight: 600;
  font-size: 0.78rem;
  cursor: pointer;
}
.secondary-button:hover:not(:disabled) {
  background: color-mix(in srgb, var(--ui-wash-base) 14%, transparent);
}
.secondary-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.danger-button {
  background: color-mix(in srgb, var(--ui-danger) 12%, transparent);
  color: var(--ui-error-text);
  border: 1px solid color-mix(in srgb, var(--ui-danger) 30%, transparent);
  border-radius: 8px;
  padding: 6px 14px;
  font-weight: 600;
  font-size: 0.78rem;
  cursor: pointer;
}
.danger-button:hover:not(:disabled) {
  background: color-mix(in srgb, var(--ui-danger) 20%, transparent);
}
.danger-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.form-error {
  color: var(--ui-error-text);
  font-size: 13px;
  background: color-mix(in srgb, var(--ui-danger) 10%, transparent);
  border: 1px solid color-mix(in srgb, var(--ui-danger) 30%, transparent);
  border-radius: 8px;
  padding: 8px 10px;
  margin-bottom: 16px;
}
</style>
