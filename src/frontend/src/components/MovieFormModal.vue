<script setup lang="ts">
import { ref, computed, watch } from "vue";
import {
  createMovie,
  updateMovie,
  deleteMovie,
  searchMovieMetadata,
  movieToInput,
} from "../services/movies";
import type { MovieMetadataResult } from "../services/movies";
import type { Movie, MovieStatus } from "../types/movie";
import {
  formatDuration,
  parseProgressMinutes,
} from "../utils/watchProgress";
import {
  STATUS_BUCKETS,
  statusBucket,
  bucketToReal,
} from "../utils/mediaStatus";
import MediaFormShell from "./MediaFormShell.vue";
import MediaMetadataSearch from "./MediaMetadataSearch.vue";
import { useMetadataSearch } from "../utils/useMetadataSearch";
import { splitList } from "../utils/formLists";

const props = defineProps<{
  movie?: Movie | null;
}>();

const emit = defineEmits<{
  saved: [movie: Movie];
  deleted: [movieId: string];
  closed: [];
}>();

function blankFields() {
  return {
    title: "",
    description: "",
    releaseDate: "",
    runtimeMinutes: null as number | null,
    progressInput: "",
    director: "",
    writer: "",
    studiosInput: "",
    genresInput: "",
    tagsInput: "",
    status: "wishlist" as MovieStatus,
    favorite: false,
    ratingOverall: null as number | null,
    personalRank: null as number | null,
    posterUrl: null as string | null,
    backdropUrl: null as string | null,
    tmdbScore: null as number | null,
  };
}

const fields = ref(blankFields());
const statusBucketModel = computed({
  get: () => statusBucket(fields.value.status),
  set: (bucket: string) => {
    fields.value.status = bucketToReal(bucket) as MovieStatus;
  },
});
const saving = ref(false);
const deleting = ref(false);
const error = ref<string | null>(null);

const search = useMetadataSearch<MovieMetadataResult>({
  search: (query) => searchMovieMetadata(query, 8, true),
  details: (title) => searchMovieMetadata(title, 3),
  noun: "movie",
  keyHint: "TMDB or OMDb",
});

function loadFromMovie(movie: Movie | null | undefined) {
  if (!movie) {
    fields.value = blankFields();
    return;
  }
  fields.value = {
    title: movie.title,
    description: movie.description ?? "",
    releaseDate: movie.releaseDate ?? "",
    runtimeMinutes: movie.runtimeMinutes,
    progressInput:
      movie.progressMinutes === null
        ? ""
        : formatDuration(movie.progressMinutes),
    director: movie.director ?? "",
    writer: movie.writer ?? "",
    studiosInput: movie.studios.join(", "),
    genresInput: movie.genres.join(", "),
    tagsInput: movie.tags.join(", "),
    status: movie.status,
    favorite: movie.favorite,
    ratingOverall: movie.ratingOverall,
    personalRank: movie.personalRank,
    posterUrl: movie.posterUrl,
    backdropUrl: movie.backdropUrl,
    tmdbScore: movie.tmdbScore,
  };
}

watch(() => props.movie, loadFromMovie, { immediate: true });

function applyMetadata(result: MovieMetadataResult) {
  const locked = new Set(props.movie?.lockedFields ?? []);
  if (!locked.has("title")) fields.value.title = result.title;
  if (!locked.has("description"))
    fields.value.description = result.description ?? "";
  if (!locked.has("release_date"))
    fields.value.releaseDate = result.releaseDate ?? "";
  if (!locked.has("runtime_minutes") && result.runtimeMinutes !== null)
    fields.value.runtimeMinutes = result.runtimeMinutes;
  if (!locked.has("director")) fields.value.director = result.director ?? "";
  if (!locked.has("writer")) fields.value.writer = result.writer ?? "";
  if (!locked.has("studios") && result.studios.length)
    fields.value.studiosInput = result.studios.join(", ");
  if (!locked.has("genres") && result.genres.length)
    fields.value.genresInput = result.genres.join(", ");
  if (!locked.has("poster_url")) fields.value.posterUrl = result.posterUrl;
  if (!locked.has("backdrop_url"))
    fields.value.backdropUrl = result.backdropUrl;
  if (!locked.has("tmdb_score") && result.tmdbScore !== null)
    fields.value.tmdbScore = result.tmdbScore;
  search.applied(result, [...locked]);
}

// what the search box lists for each match
const searchResults = computed(() =>
  search.results.value.map((result) => ({
    key: `${result.provider}-${result.providerId}`,
    title: result.title,
    provider: result.provider,
    detail: result.releaseDate?.slice(0, 4),
  })),
);

async function pickResult(key: string) {
  const result = search.results.value.find(
    (r) => `${r.provider}-${r.providerId}` === key,
  );
  if (result) applyMetadata(await search.resolve(result));
}

async function submit() {
  if (!fields.value.title.trim()) {
    error.value = "Title is required.";
    return;
  }
  const progressMinutes = parseProgressMinutes(fields.value.progressInput);
  if (progressMinutes !== null && Number.isNaN(progressMinutes)) {
    error.value = "Left off at: try 72, 1:12 or 1h 12m.";
    return;
  }
  // a position in a movie you hadn't started means you're watching it
  if (progressMinutes && statusBucket(fields.value.status) === "plan") {
    fields.value.status = "in progress";
  }
  saving.value = true;
  error.value = null;
  try {
    const input = {
      progressMinutes: progressMinutes || null,
      title: fields.value.title.trim(),
      description: fields.value.description.trim() || null,
      releaseDate: fields.value.releaseDate || null,
      runtimeMinutes: fields.value.runtimeMinutes,
      director: fields.value.director.trim() || null,
      writer: fields.value.writer.trim() || null,
      studios: splitList(fields.value.studiosInput),
      genres: splitList(fields.value.genresInput),
      tags: splitList(fields.value.tagsInput),
      status: fields.value.status,
      favorite: fields.value.favorite,
      ratingOverall: fields.value.ratingOverall,
      personalRank: fields.value.personalRank,
      posterUrl: fields.value.posterUrl,
      backdropUrl: fields.value.backdropUrl,
      tmdbScore: fields.value.tmdbScore,
    };
    const saved = props.movie
      ? await updateMovie(props.movie.id, {
          // keep the fields this form doesn't show
          ...movieToInput(props.movie),
          ...input,
        })
      : await createMovie(input);
    emit("saved", saved);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to save movie.";
  } finally {
    saving.value = false;
  }
}

async function remove() {
  if (!props.movie) return;
  deleting.value = true;
  error.value = null;
  try {
    await deleteMovie(props.movie.id);
    emit("deleted", props.movie.id);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to delete movie.";
  } finally {
    deleting.value = false;
  }
}
</script>

<template>
  <MediaFormShell
    noun="Movie"
    :editing="!!movie"
    :saving="saving"
    :deleting="deleting"
    :error="error"
    @closed="emit('closed')"
    @save="submit"
    @delete="remove"
  >
    <MediaMetadataSearch
      v-model:query="search.query.value"
      label="Search TMDB / OMDb"
      noun="movie"
      :results="searchResults"
      :searching="search.searching.value"
      :message="search.message.value"
      :warnings="search.warnings.value"
      @search="search.run"
      @pick="pickResult"
    />

    <img
      v-if="fields.posterUrl"
      :src="fields.posterUrl"
      alt=""
      class="poster-preview"
    />

    <label class="field">
      <span>Title</span>
      <input
        v-model="fields.title"
        type="text"
        class="text-input"
        placeholder="The Matrix"
      />
    </label>

    <label class="field">
      <span>Description</span>
      <textarea
        v-model="fields.description"
        class="text-input textarea-input"
        rows="3"
      ></textarea>
    </label>

    <div class="field-row">
      <label class="field">
        <span>Release date</span>
        <input v-model="fields.releaseDate" type="date" class="text-input" />
      </label>
      <label class="field">
        <span>Runtime (minutes)</span>
        <input
          v-model.number="fields.runtimeMinutes"
          type="number"
          min="0"
          class="text-input"
        />
      </label>
      <label class="field">
        <span>Left off at</span>
        <input
          v-model="fields.progressInput"
          type="text"
          inputmode="numeric"
          placeholder="not started, or 1h 12m"
          class="text-input"
        />
      </label>
    </div>

    <div class="field-row">
      <label class="field">
        <span>Director</span>
        <input v-model="fields.director" type="text" class="text-input" />
      </label>
      <label class="field">
        <span>Writer</span>
        <input v-model="fields.writer" type="text" class="text-input" />
      </label>
    </div>

    <label class="field">
      <span>Studios (comma-separated)</span>
      <input v-model="fields.studiosInput" type="text" class="text-input" />
    </label>

    <label class="field">
      <span>Genres (comma-separated)</span>
      <input v-model="fields.genresInput" type="text" class="text-input" />
    </label>

    <label class="field">
      <span>Tags (comma-separated)</span>
      <input v-model="fields.tagsInput" type="text" class="text-input" />
    </label>

    <div class="field-row">
      <label class="field">
        <span>Status</span>
        <select v-model="statusBucketModel" class="text-input">
          <option v-for="s in STATUS_BUCKETS" :key="s.key" :value="s.key">
            {{ s.label }}
          </option>
        </select>
      </label>
      <label class="field">
        <span>Overall rating (0-10)</span>
        <input
          v-model.number="fields.ratingOverall"
          type="number"
          min="0"
          max="10"
          step="0.1"
          class="text-input"
        />
      </label>
    </div>

    <div class="field-row">
      <label class="field checkbox-field">
        <input v-model="fields.favorite" type="checkbox" />
        <span>Favorite</span>
      </label>
      <label class="field">
        <span>Personal rank</span>
        <input
          v-model.number="fields.personalRank"
          type="number"
          min="1"
          class="text-input"
        />
      </label>
    </div>

    <label class="field">
      <span>TMDB / IMDb score (0-10)</span>
      <input
        v-model.number="fields.tmdbScore"
        type="number"
        min="0"
        max="10"
        step="0.1"
        class="text-input"
      />
    </label>
  </MediaFormShell>
</template>

<style scoped src="../styles/shared/mediaForm.css"></style>

<style scoped></style>
