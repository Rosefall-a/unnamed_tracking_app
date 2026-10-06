<script setup lang="ts">
import { ref, computed, watch } from "vue";
import {
  createAnime,
  updateAnime,
  deleteAnime,
  searchAnimeMetadata,
  animeToInput,
} from "../services/anime";
import type { AnimeMetadataResult } from "../services/anime";
import type { Anime, AnimeStatus } from "../types/anime";
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
  show?: Anime | null;
}>();

const emit = defineEmits<{
  saved: [show: Anime];
  deleted: [showId: string];
  closed: [];
}>();

function blankFields() {
  return {
    title: "",
    description: "",
    firstAirDate: "",
    episodeRuntimeMinutes: null as number | null,
    studiosInput: "",
    genresInput: "",
    tagsInput: "",
    status: "wishlist" as AnimeStatus,
    favorite: false,
    ratingOverall: null as number | null,
    personalRank: null as number | null,
    posterUrl: null as string | null,
    backdropUrl: null as string | null,
    anilistScore: null as number | null,
    malScore: null as number | null,
    externalId: null as string | null,
    anilistId: null as string | null,
  };
}

const fields = ref(blankFields());
const statusBucketModel = computed({
  get: () => statusBucket(fields.value.status),
  set: (bucket: string) => {
    fields.value.status = bucketToReal(bucket) as AnimeStatus;
  },
});
const saving = ref(false);
const deleting = ref(false);
const error = ref<string | null>(null);

const search = useMetadataSearch<AnimeMetadataResult>({
  search: searchAnimeMetadata,
  noun: "anime",
});

function loadFromShow(show: Anime | null | undefined) {
  if (!show) {
    fields.value = blankFields();
    return;
  }
  fields.value = {
    title: show.title,
    description: show.description ?? "",
    firstAirDate: show.firstAirDate ?? "",
    episodeRuntimeMinutes: show.episodeRuntimeMinutes,
    studiosInput: show.studios.join(", "),
    genresInput: show.genres.join(", "),
    tagsInput: show.tags.join(", "),
    status: show.status,
    favorite: show.favorite,
    ratingOverall: show.ratingOverall,
    personalRank: show.personalRank,
    posterUrl: show.posterUrl,
    backdropUrl: show.backdropUrl,
    anilistScore: show.anilistScore,
    malScore: show.malScore,
    externalId: show.externalId,
    anilistId: show.anilistId,
  };
}

watch(() => props.show, loadFromShow, { immediate: true });

function applyMetadata(result: AnimeMetadataResult) {
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
  if (!locked.has("studios") && result.studios.length)
    fields.value.studiosInput = result.studios.join(", ");
  if (!locked.has("genres") && result.genres.length)
    fields.value.genresInput = result.genres.join(", ");
  if (!locked.has("poster_url")) fields.value.posterUrl = result.posterUrl;
  if (!locked.has("backdrop_url"))
    fields.value.backdropUrl = result.backdropUrl;
  if (!locked.has("anilist_score") && result.anilistScore !== null)
    fields.value.anilistScore = result.anilistScore;
  if (!locked.has("mal_score") && result.malScore !== null)
    fields.value.malScore = result.malScore;
  // Not gated by locked_fields — these aren't a user-editable display
  // field, just the link episode sync/airing checks need. Picking a
  // search result is exactly how a show with a missing/wrong link (e.g.
  // added by hand, or from before this app tracked these ids) gets
  // fixed, so always take the freshly-picked match's ids.
  fields.value.externalId = result.malId;
  fields.value.anilistId =
    result.provider === "AniList" ? result.providerId : null;
  search.applied(result, [...locked]);
}

// what the search box lists for each match
const searchResults = computed(() =>
  search.results.value.map((result) => ({
    key: `${result.provider}-${result.providerId}`,
    title: result.title,
    provider: result.provider,
    detail: [
      result.firstAirDate?.slice(0, 4),
      result.episodeCount ? `${result.episodeCount} ep` : null,
    ]
      .filter(Boolean)
      .join(" · "),
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
      studios: splitList(fields.value.studiosInput),
      genres: splitList(fields.value.genresInput),
      tags: splitList(fields.value.tagsInput),
      status: fields.value.status,
      favorite: fields.value.favorite,
      ratingOverall: fields.value.ratingOverall,
      personalRank: fields.value.personalRank,
      posterUrl: fields.value.posterUrl,
      backdropUrl: fields.value.backdropUrl,
      anilistScore: fields.value.anilistScore,
      malScore: fields.value.malScore,
      externalId: fields.value.externalId,
      anilistId: fields.value.anilistId,
    };
    const saved = props.show
      ? await updateAnime(props.show.id, {
          // keep the fields this form doesn't show
          ...animeToInput(props.show),
          ...input,
        })
      : await createAnime(input);
    emit("saved", saved);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to save anime.";
  } finally {
    saving.value = false;
  }
}

async function remove() {
  if (!props.show) return;
  deleting.value = true;
  error.value = null;
  try {
    await deleteAnime(props.show.id);
    emit("deleted", props.show.id);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to delete anime.";
  } finally {
    deleting.value = false;
  }
}
</script>

<template>
  <MediaFormShell
    noun="Anime"
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
      label="Search AniList / MyAnimeList"
      noun="anime"
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
        placeholder="Fullmetal Alchemist: Brotherhood"
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

    <div class="field-row">
      <label class="field">
        <span>AniList score (0-10)</span>
        <input
          v-model.number="fields.anilistScore"
          type="number"
          min="0"
          max="10"
          step="0.1"
          class="text-input"
        />
      </label>
      <label class="field">
        <span>MAL score (0-10)</span>
        <input
          v-model.number="fields.malScore"
          type="number"
          min="0"
          max="10"
          step="0.1"
          class="text-input"
        />
      </label>
    </div>
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
