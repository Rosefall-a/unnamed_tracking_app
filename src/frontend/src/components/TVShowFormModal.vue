<script setup lang="ts">
import { ref, computed, watch } from "vue";
import {
  createTVShow,
  updateTVShow,
  deleteTVShow,
  searchTVShowMetadata,
  tvShowToInput,
} from "../services/tvShows";
import type { TVShowMetadataResult, SeasonInput } from "../services/tvShows";
import type { TVShow, TVShowStatus } from "../types/tv_show";
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
  show?: TVShow | null;
}>();

const emit = defineEmits<{
  saved: [show: TVShow];
  deleted: [showId: string];
  closed: [];
}>();

function blankFields() {
  return {
    title: "",
    description: "",
    firstAirDate: "",
    episodeRuntimeMinutes: null as number | null,
    creatorsInput: "",
    genresInput: "",
    tagsInput: "",
    status: "wishlist" as TVShowStatus,
    favorite: false,
    ratingOverall: null as number | null,
    personalRank: null as number | null,
    posterUrl: null as string | null,
    backdropUrl: null as string | null,
    tmdbScore: null as number | null,
    externalId: null as string | null,
  };
}

const fields = ref(blankFields());
const statusBucketModel = computed({
  get: () => statusBucket(fields.value.status),
  set: (bucket: string) => {
    fields.value.status = bucketToReal(bucket) as TVShowStatus;
  },
});
// staged from a metadata search result when creating a new show — bulk
// created alongside it so the user doesn't have to type each season in
// by hand. Never used on edit (seasons are managed from the detail page).
const stagedSeasons = ref<SeasonInput[]>([]);
const saving = ref(false);
const deleting = ref(false);
const error = ref<string | null>(null);

const search = useMetadataSearch<TVShowMetadataResult>({
  search: searchTVShowMetadata,
  noun: "show",
  keyHint: "TMDB or OMDb",
});

function loadFromShow(show: TVShow | null | undefined) {
  stagedSeasons.value = [];
  if (!show) {
    fields.value = blankFields();
    return;
  }
  fields.value = {
    title: show.title,
    description: show.description ?? "",
    firstAirDate: show.firstAirDate ?? "",
    episodeRuntimeMinutes: show.episodeRuntimeMinutes,
    creatorsInput: show.creators.join(", "),
    genresInput: show.genres.join(", "),
    tagsInput: show.tags.join(", "),
    status: show.status,
    favorite: show.favorite,
    ratingOverall: show.ratingOverall,
    personalRank: show.personalRank,
    posterUrl: show.posterUrl,
    backdropUrl: show.backdropUrl,
    tmdbScore: show.tmdbScore,
    externalId: show.externalId,
  };
}

watch(() => props.show, loadFromShow, { immediate: true });

function applyMetadata(result: TVShowMetadataResult) {
  const locked = new Set(props.show?.lockedFields ?? []);
  if (!locked.has("title")) fields.value.title = result.title;
  if (!locked.has("description"))
    fields.value.description = result.description ?? "";
  if (!locked.has("first_air_date"))
    fields.value.firstAirDate = result.firstAirDate ?? "";
  if (
    !locked.has("episode_runtime_minutes") &&
    result.episodeRuntimeMinutes !== null
  )
    fields.value.episodeRuntimeMinutes = result.episodeRuntimeMinutes;
  if (!locked.has("creators") && result.creators.length)
    fields.value.creatorsInput = result.creators.join(", ");
  if (!locked.has("genres") && result.genres.length)
    fields.value.genresInput = result.genres.join(", ");
  if (!locked.has("poster_url")) fields.value.posterUrl = result.posterUrl;
  if (!locked.has("backdrop_url"))
    fields.value.backdropUrl = result.backdropUrl;
  if (!locked.has("tmdb_score") && result.tmdbScore !== null)
    fields.value.tmdbScore = result.tmdbScore;
  // Not gated by locked_fields — this isn't a user-editable display
  // field, just the link episode sync/the airing check need. Picking a
  // search result is exactly how a show with a missing/wrong link (e.g.
  // added by hand, or one that lost it to the merge-ownership bug) gets
  // fixed, so always take the freshly-picked match's TVmaze id.
  fields.value.externalId = result.tvmazeId;
  stagedSeasons.value = result.seasons.map((s) => ({
    seasonNumber: s.seasonNumber,
    name: s.name,
    episodeCount: s.episodeCount,
    airDate: s.airDate,
    posterUrl: s.posterUrl,
  }));
  const seasonNote = result.seasons.length
    ? ` including ${result.seasons.length} season${result.seasons.length === 1 ? "" : "s"}`
    : "";
  search.applied(result, [...locked], seasonNote);
}

// what the search box lists for each match
const searchResults = computed(() =>
  search.results.value.map((result) => ({
    key: `${result.provider}-${result.providerId}`,
    title: result.title,
    provider: result.provider,
    detail: result.firstAirDate?.slice(0, 4),
  })),
);

function pickResult(key: string) {
  const result = search.results.value.find(
    (r) => `${r.provider}-${r.providerId}` === key,
  );
  if (result) applyMetadata(result);
}

async function submit() {
  if (!fields.value.title.trim()) {
    error.value = "Title is required.";
    return;
  }
  saving.value = true;
  error.value = null;
  try {
    const input = {
      title: fields.value.title.trim(),
      description: fields.value.description.trim() || null,
      firstAirDate: fields.value.firstAirDate || null,
      episodeRuntimeMinutes: fields.value.episodeRuntimeMinutes,
      creators: splitList(fields.value.creatorsInput),
      genres: splitList(fields.value.genresInput),
      tags: splitList(fields.value.tagsInput),
      status: fields.value.status,
      favorite: fields.value.favorite,
      ratingOverall: fields.value.ratingOverall,
      personalRank: fields.value.personalRank,
      posterUrl: fields.value.posterUrl,
      backdropUrl: fields.value.backdropUrl,
      tmdbScore: fields.value.tmdbScore,
      externalId: fields.value.externalId,
      seasons: props.show ? undefined : stagedSeasons.value,
    };
    const saved = props.show
      ? await updateTVShow(props.show.id, {
          // keep the fields this form doesn't show
          ...tvShowToInput(props.show),
          ...input,
        })
      : await createTVShow(input);
    emit("saved", saved);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to save show.";
  } finally {
    saving.value = false;
  }
}

async function remove() {
  if (!props.show) return;
  deleting.value = true;
  error.value = null;
  try {
    await deleteTVShow(props.show.id);
    emit("deleted", props.show.id);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to delete show.";
  } finally {
    deleting.value = false;
  }
}
</script>

<template>
  <MediaFormShell
    noun="TV Show"
    :editing="!!show"
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
      noun="show"
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
        placeholder="Breaking Bad"
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
        <span>First air date</span>
        <input v-model="fields.firstAirDate" type="date" class="text-input" />
      </label>
      <label class="field">
        <span>Episode runtime (minutes)</span>
        <input
          v-model.number="fields.episodeRuntimeMinutes"
          type="number"
          min="0"
          class="text-input"
        />
      </label>
    </div>

    <label class="field">
      <span>Creators (comma-separated)</span>
      <input v-model="fields.creatorsInput" type="text" class="text-input" />
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

    <p v-if="!show && stagedSeasons.length" class="hint">
      {{ stagedSeasons.length }} season{{
        stagedSeasons.length === 1 ? "" : "s"
      }}
      will be created with this show.
    </p>
  </MediaFormShell>
</template>

<style scoped src="../styles/shared/mediaForm.css"></style>

<style scoped>
.hint {
  font-size: 0.78rem;
  color: #999;
  margin: 0;
}
</style>
