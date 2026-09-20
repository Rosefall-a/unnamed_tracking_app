<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useKeptAlive } from "../utils/useKeptAlive";
import {
  fetchAnime,
  updateAnime,
  deleteAnime,
  animeToInput,
  searchAnimeMetadata,
  createAnime,
  updateSeason,
} from "../services/anime";
import type { SeasonUpdateInput } from "../services/anime";
import type { Anime, AnimeStatus } from "../types/anime";
import MediaLibraryView from "../components/library/MediaLibraryView.vue";
import { displayTitle } from "../utils/displayTitle";
import type {
  LibraryCardVM,
  SearchResultVM,
  QuickAddForm,
  EditForm,
} from "../components/library/MediaLibraryView.vue";

const shows = ref<Anime[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

function seasonProgress(show: Anime): {
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
function currentSeason(show: Anime) {
  return show.seasons.find(
    (s) => s.episodeCount === null || s.episodesWatched < s.episodeCount,
  );
}

function toVM(show: Anime): LibraryCardVM {
  const { watched, total } = seasonProgress(show);
  return {
    id: show.id,
    title: displayTitle(show),
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
    format: show.format,
    releaseYear: show.firstAirDate ? show.firstAirDate.slice(0, 4) : null,
  };
}

const items = computed(() => shows.value.map(toVM));

// Only the very first load shows the loading state; a refresh when the
// page comes back swaps data in quietly, so titles never blink away.
async function load() {
  if (!shows.value.length) loading.value = true;
  try {
    shows.value = await fetchAnime();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to load anime.";
  } finally {
    loading.value = false;
  }
}
onMounted(load);
useKeptAlive(load);

function findShow(id: string): Anime {
  const show = shows.value.find((s) => s.id === id);
  if (!show) throw new Error(`Anime ${id} not in the loaded list`);
  return show;
}
function replaceShow(updated: Anime) {
  const idx = shows.value.findIndex((s) => s.id === updated.id);
  if (idx !== -1) shows.value[idx] = updated;
}

async function onToggleFavorite(id: string) {
  const show = findShow(id);
  const next = !show.favorite;
  show.favorite = next;
  try {
    replaceShow(
      await updateAnime(id, { ...animeToInput(show), favorite: next }),
    );
  } catch {
    show.favorite = !next;
  }
}

async function onSaveNote(id: string, note: string | null) {
  const show = findShow(id);
  replaceShow(await updateAnime(id, { ...animeToInput(show), note }));
}

// No cap on episodes watched — metadata's episode count is often wrong
// or stale, and a rewatch can genuinely outrun it too.
async function onAdvanceEpisode(id: string) {
  const show = findShow(id);
  const season = currentSeason(show);
  if (!season) return;
  replaceShow(
    await updateSeason(id, season.id, {
      episodesWatched: season.episodesWatched + 1,
    }),
  );
}

async function onSaveEdit(id: string, form: EditForm) {
  const show = findShow(id);
  replaceShow(
    await updateAnime(id, {
      ...animeToInput(show),
      status: form.status as AnimeStatus,
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
      await updateAnime(id, {
        ...animeToInput(show),
        status: status as AnimeStatus,
      }),
    );
  }
}
async function onBulkFavorite(ids: string[]) {
  for (const id of ids) {
    const show = findShow(id);
    replaceShow(
      await updateAnime(id, { ...animeToInput(show), favorite: true }),
    );
  }
}
async function onBulkDelete(ids: string[]) {
  for (const id of ids) {
    await deleteAnime(id);
  }
  shows.value = shows.value.filter((s) => !ids.includes(s.id));
}

async function search(
  query: string,
): Promise<{ results: SearchResultVM[]; providerErrors: string[] }> {
  const { results, providerErrors } = await searchAnimeMetadata(query);
  return {
    results: results.map((r) => ({
      title: r.title,
      poster: r.posterUrl,
      description: r.description,
      episodeTotal: r.episodeCount,
      releaseYear: r.firstAirDate ? r.firstAirDate.slice(0, 4) : null,
    })),
    providerErrors,
  };
}

async function createFromResult(
  result: SearchResultVM,
  form: QuickAddForm,
): Promise<void> {
  const { results } = await searchAnimeMetadata(result.title, 1);
  const match = results.find((r) => r.title === result.title) ?? results[0];
  // Pass the episode count through explicitly instead of leaving seasons
  // omitted (which auto-creates a default Season 1 with no count) — the
  // metadata search already knows the total, so there's no reason the
  // progress bar and "watched/total" label should come up unknown.
  const episodeCount = match?.episodeCount ?? result.episodeTotal ?? null;
  const created = await createAnime({
    title: result.title,
    description: match?.description ?? null,
    firstAirDate: match?.firstAirDate ?? null,
    episodeRuntimeMinutes: match?.episodeRuntimeMinutes ?? null,
    studios: match?.studios ?? [],
    genres: match?.genres ?? [],
    posterUrl: result.poster,
    backdropUrl: match?.backdropUrl ?? null,
    format: match?.format ?? null,
    anilistScore: match?.anilistScore ?? null,
    malScore: match?.malScore ?? null,
    externalId: match?.malId ?? null,
    // AniList is the primary provider, so provider_id is its id whenever
    // AniList matched (the common case) — kept separately from
    // externalId (MAL's) so episode sync has a fallback when Jikan is
    // unreachable or never matched this title.
    anilistId: match?.provider === "AniList" ? match.providerId : null,
    status: form.status as AnimeStatus,
    ratingOverall: form.score,
    startDate: form.startDate,
    endDate: form.endDate,
    seasons: [{ seasonNumber: 1, episodeCount }],
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
  return `/anime/${id}`;
}
</script>

<template>
  <MediaLibraryView
    kind="anime"
    add-label="+ Add Anime"
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
