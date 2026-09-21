<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useKeptAlive } from "../utils/useKeptAlive";
import {
  fetchTVShows,
  updateTVShow,
  deleteTVShow,
  tvShowToInput,
  searchTVShowMetadata,
  createTVShow,
  updateSeason,
} from "../services/tvShows";
import type { SeasonUpdateInput } from "../services/tvShows";
import type { TVShow, TVShowStatus } from "../types/tv_show";
import MediaLibraryView from "../components/library/MediaLibraryView.vue";
import { statusBucket, bucketToReal } from "../utils/mediaStatus";
import type {
  LibraryCardVM,
  SearchResultVM,
  QuickAddForm,
  EditForm,
} from "../components/library/MediaLibraryView.vue";

const shows = ref<TVShow[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

function seasonProgress(show: TVShow): {
  watched: number;
  total: number | null;
} {
  const watched = show.seasons.reduce((sum, s) => sum + s.episodesWatched, 0);
  const known = show.seasons.every((s) => s.episodeCount !== null);
  const total = known
    ? show.seasons.reduce((sum, s) => sum + (s.episodeCount ?? 0), 0)
    : null;
  return { watched, total };
}
// The season currently being watched: the first one not yet fully watched.
function currentSeason(show: TVShow) {
  return show.seasons.find(
    (s) => s.episodeCount === null || s.episodesWatched < s.episodeCount,
  );
}

function toVM(show: TVShow): LibraryCardVM {
  const { watched, total } = seasonProgress(show);
  return {
    id: show.id,
    title: show.title,
    poster: show.posterUrl,
    status: show.status,
    favorite: show.favorite,
    score: show.ratingOverall,
    personalRank: show.personalRank,
    note: show.note,
    genres: show.genres,
    isEpisodic: true,
    watched,
    total,
    progressLabel: total !== null ? `${watched}/${total}` : `${watched}/–`,
    canAdvance: !!currentSeason(show),
    releaseYear: show.firstAirDate ? show.firstAirDate.slice(0, 4) : null,
    addedAt: Date.parse(show.createdAt) || null,
  };
}

const items = computed(() => shows.value.map(toVM));

// Only the very first load shows the loading state; a refresh when the
// page comes back swaps data in quietly, so titles never blink away.
async function load() {
  if (!shows.value.length) loading.value = true;
  try {
    shows.value = await fetchTVShows();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to load TV shows.";
  } finally {
    loading.value = false;
  }
}
onMounted(load);
useKeptAlive(load);

function findShow(id: string): TVShow {
  const show = shows.value.find((s) => s.id === id);
  if (!show) throw new Error(`TV show ${id} not in the loaded list`);
  return show;
}
function replaceShow(updated: TVShow) {
  const idx = shows.value.findIndex((s) => s.id === updated.id);
  if (idx !== -1) shows.value[idx] = updated;
}

async function onToggleFavorite(id: string) {
  const show = findShow(id);
  const next = !show.favorite;
  show.favorite = next;
  try {
    replaceShow(
      await updateTVShow(id, { ...tvShowToInput(show), favorite: next }),
    );
  } catch {
    show.favorite = !next;
  }
}

async function onSaveNote(id: string, note: string | null) {
  const show = findShow(id);
  replaceShow(await updateTVShow(id, { ...tvShowToInput(show), note }));
}

// No cap on episodes watched — metadata's episode count is often wrong
// or stale, and a rewatch can genuinely outrun it too.
async function onAdvanceEpisode(id: string) {
  const show = findShow(id);
  const season = currentSeason(show);
  if (!season) return;
  const updated = await updateSeason(id, season.id, {
    episodesWatched: season.episodesWatched + 1,
  });
  replaceShow(updated);
  // pressing + on a show that is still Plan to Watch or On Hold means it has
  // been started (or picked up again), so it moves to Watching
  const bucket = statusBucket(updated.status);
  if (bucket === "plan" || bucket === "hold") {
    replaceShow(
      await updateTVShow(id, {
        ...tvShowToInput(updated),
        status: bucketToReal("watching") as TVShowStatus,
      }),
    );
  }
}

async function onSaveEdit(id: string, form: EditForm) {
  const show = findShow(id);
  replaceShow(
    await updateTVShow(id, {
      ...tvShowToInput(show),
      status: form.status as TVShowStatus,
      ratingOverall: form.score,
    }),
  );
  // The small edit modal's "episodes watched" and "total episodes" are
  // flat numbers; apply them to the current season the same way the
  // quick "+" button does, rather than pretending a show-level episode
  // count exists as its own field. Falls back to the last season once
  // everything is already watched (currentSeason has nothing left to
  // pick) so the fields stay editable after a show is fully caught up.
  const updatedShow = findShow(id);
  const season =
    currentSeason(updatedShow) ??
    updatedShow.seasons[updatedShow.seasons.length - 1];
  if (season) {
    const watchedDelta = form.watched - seasonProgress(updatedShow).watched;
    const totalChanged = form.totalEpisodes !== season.episodeCount;
    const seasonUpdates: SeasonUpdateInput = {};
    if (watchedDelta !== 0) {
      seasonUpdates.episodesWatched = Math.max(
        0,
        season.episodesWatched + watchedDelta,
      );
    }
    if (totalChanged) {
      seasonUpdates.episodeCount = form.totalEpisodes;
    }
    if (Object.keys(seasonUpdates).length > 0) {
      replaceShow(await updateSeason(id, season.id, seasonUpdates));
    }
  }
}

async function onBulkSetStatus(ids: string[], status: string) {
  for (const id of ids) {
    const show = findShow(id);
    replaceShow(
      await updateTVShow(id, {
        ...tvShowToInput(show),
        status: status as TVShowStatus,
      }),
    );
  }
}
async function onBulkFavorite(ids: string[]) {
  for (const id of ids) {
    const show = findShow(id);
    replaceShow(
      await updateTVShow(id, { ...tvShowToInput(show), favorite: true }),
    );
  }
}
async function onBulkDelete(ids: string[]) {
  for (const id of ids) {
    await deleteTVShow(id);
  }
  shows.value = shows.value.filter((s) => !ids.includes(s.id));
}

async function search(
  query: string,
): Promise<{ results: SearchResultVM[]; providerErrors: string[] }> {
  const { results, providerErrors } = await searchTVShowMetadata(query);
  return {
    results: results.map((r) => ({
      title: r.title,
      poster: r.posterUrl,
      description: r.description,
      episodeTotal: r.seasons.length
        ? r.seasons.reduce((sum, s) => sum + (s.episodeCount ?? 0), 0)
        : null,
      releaseYear: r.firstAirDate ? r.firstAirDate.slice(0, 4) : null,
    })),
    providerErrors,
  };
}

async function createFromResult(
  result: SearchResultVM,
  form: QuickAddForm,
): Promise<void> {
  const { results } = await searchTVShowMetadata(result.title, 1);
  const match = results.find((r) => r.title === result.title) ?? results[0];
  // TMDB results carry a real per-season breakdown; TVmaze's don't (it has
  // no season-level endpoint wired up here) — fall back to a single
  // Season 1 using the flat episode total so there's always somewhere for
  // "episodes watched" to land, regardless of which provider found it.
  const seasons =
    match?.seasons && match.seasons.length > 0
      ? match.seasons
      : [{ seasonNumber: 1, episodeCount: result.episodeTotal ?? undefined }];
  const created = await createTVShow({
    title: result.title,
    description: match?.description ?? null,
    firstAirDate: match?.firstAirDate ?? null,
    episodeRuntimeMinutes: match?.episodeRuntimeMinutes ?? null,
    creators: match?.creators ?? [],
    studios: match?.studios ?? [],
    genres: match?.genres ?? [],
    posterUrl: result.poster,
    backdropUrl: match?.backdropUrl ?? null,
    tmdbScore: match?.tmdbScore ?? null,
    // Only TVmaze IDs are useful here — that's the only provider the
    // episode sync knows how to call back into. tvmazeId survives even
    // when TMDB/OMDb "owns" the merged search result (see search.py's
    // _merge_or_append), unlike providerId which only reflects whichever
    // provider happened to match the title first.
    externalId: match?.tvmazeId ?? null,
    status: form.status as TVShowStatus,
    ratingOverall: form.score,
    startDate: form.startDate,
    endDate: form.endDate,
    seasons,
  });
  let finalShow = created;
  const firstSeason = created.seasons[0];
  if (firstSeason && form.watched > 0) {
    finalShow = await updateSeason(created.id, firstSeason.id, {
      episodesWatched: form.watched,
    });
  }
  shows.value.push(finalShow);
}

function detailRoute(id: string): string {
  return `/tv/${id}`;
}
</script>

<template>
  <MediaLibraryView
    kind="tv"
    add-label="+ Add Show"
    :items="items"
    :loading="loading"
    :error="error"
    :detail-route="detailRoute"
    :search="search"
    :create-from-result="createFromResult"
    @toggle-favorite="onToggleFavorite"
    @advance-episode="onAdvanceEpisode"
    @save-note="onSaveNote"
    @save-edit="onSaveEdit"
    @bulk-set-status="onBulkSetStatus"
    @bulk-favorite="onBulkFavorite"
    @bulk-delete="onBulkDelete"
  />
</template>
