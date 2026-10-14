<script setup lang="ts">
// The edit form for a movie, a TV show or an anime, in the same layout as the game
// form: tabs inside one fixed height, a "Look up metadata" button on every tab, and
// an Artwork tab. The three kinds share every field they have in common; the few
// that belong to one kind (director, creators, AniList score) show only for it.
import { computed, ref, watch } from "vue";
import MediaFormShell from "./MediaFormShell.vue";
import MediaLookupPanel from "./MediaLookupPanel.vue";
import { useMetadataSearch } from "../utils/useMetadataSearch";
import { makeOffer, listText } from "../utils/mediaLookup";
import type { LookupApply, LookupChange } from "../utils/mediaLookup";
import { numberOrNull } from "../utils/numberInput";
import { splitList } from "../utils/formLists";
import { PRIORITY_OPTIONS, priorityRank } from "../utils/priority";
import {
  STATUS_BUCKETS,
  statusBucket,
  bucketToReal,
} from "../utils/mediaStatus";
import { formatDuration, parseProgressMinutes } from "../utils/watchProgress";
import {
  createMovie,
  deleteMovie,
  movieToInput,
  searchMovieMetadata,
  updateMovie,
} from "../services/movies";
import type { MovieMetadataResult } from "../services/movies";
import {
  createTVShow,
  deleteTVShow,
  searchTVShowMetadata,
  tvShowToInput,
  updateTVShow,
} from "../services/tvShows";
import type { SeasonInput, TVShowMetadataResult } from "../services/tvShows";
import {
  animeToInput,
  createAnime,
  deleteAnime,
  searchAnimeMetadata,
  updateAnime,
} from "../services/anime";
import type { AnimeMetadataResult } from "../services/anime";
import type { Movie } from "../types/movie";
import type { TVShow } from "../types/tv_show";
import type { Anime } from "../types/anime";

type Kind = "movie" | "tv" | "anime";
type Item = Movie | TVShow | Anime;
type Result = MovieMetadataResult | TVShowMetadataResult | AnimeMetadataResult;

const props = defineProps<{
  kind: Kind;
  item?: Item | null;
}>();

const emit = defineEmits<{
  saved: [item: Item];
  deleted: [id: string];
  closed: [];
}>();

const NOUN: Record<Kind, string> = {
  movie: "Movie",
  tv: "TV show",
  anime: "Anime",
};
const noun = computed(() => NOUN[props.kind]);

const tabs = computed(() =>
  props.kind === "movie"
    ? ["Basics", "Details", "Ratings", "Artwork", "Notes"]
    : ["Basics", "Details", "Ratings", "Artwork", "Notes", "Advanced"],
);
const activeTab = ref("Basics");

// ---- the fields: every kind's, only the ones that kind has are shown or sent ----
function blankFields() {
  return {
    title: "",
    description: "",
    status: "wishlist" as string,
    favorite: false,
    priority: "",
    rewatches: 0 as number | null,
    startDate: "",
    endDate: "",
    progressInput: "",
    releaseDate: "",
    firstAirDate: "",
    runtimeMinutes: null as number | null,
    episodeRuntimeMinutes: null as number | null,
    director: "",
    writer: "",
    creatorsInput: "",
    studiosInput: "",
    countriesInput: "",
    languagesInput: "",
    genresInput: "",
    tagsInput: "",
    featuresInput: "",
    ageRating: "",
    source: "",
    format: "",
    airingIntervalDays: null as number | null,
    ratingOverall: null as number | null,
    ratingStory: null as number | null,
    ratingPerformance: null as number | null,
    ratingSoundtrack: null as number | null,
    personalRank: null as number | null,
    tmdbScore: null as number | null,
    anilistScore: null as number | null,
    malScore: null as number | null,
    posterUrl: "",
    backdropUrl: "",
    note: "",
    externalId: "",
    anilistId: "",
  };
}
const fields = ref(blankFields());
// staged from a lookup when a TV show is created, so its seasons need not be typed in
const stagedSeasons = ref<SeasonInput[]>([]);

function loadFrom(item: Item | null | undefined) {
  stagedSeasons.value = [];
  const f = blankFields();
  if (item) {
    f.title = item.title;
    f.description = item.description ?? "";
    f.status = item.status;
    f.favorite = item.favorite;
    // an older HIGH, MEDIUM or LOW shows as its 1 to 5 number
    f.priority = String(priorityRank(item.priority) ?? "");
    f.rewatches = item.rewatches;
    f.startDate = item.startDate ?? "";
    f.endDate = item.endDate ?? "";
    f.studiosInput = listText(item.studios);
    f.countriesInput = listText(item.countries);
    f.languagesInput = listText(item.languages);
    f.genresInput = listText(item.genres);
    f.tagsInput = listText(item.tags);
    f.featuresInput = listText(item.features);
    f.ageRating = item.ageRating ?? "";
    f.source = item.source ?? "";
    f.ratingOverall = item.ratingOverall;
    f.ratingStory = item.ratingStory;
    f.ratingPerformance = item.ratingPerformance;
    f.ratingSoundtrack = item.ratingSoundtrack;
    f.personalRank = item.personalRank;
    f.posterUrl = item.posterUrl ?? "";
    f.backdropUrl = item.backdropUrl ?? "";
    f.note = item.note ?? "";
    if (props.kind === "movie") {
      const m = item as Movie;
      f.releaseDate = m.releaseDate ?? "";
      f.runtimeMinutes = m.runtimeMinutes;
      f.director = m.director ?? "";
      f.writer = m.writer ?? "";
      f.tmdbScore = m.tmdbScore;
      f.progressInput =
        m.progressMinutes === null ? "" : formatDuration(m.progressMinutes);
    } else if (props.kind === "tv") {
      const s = item as TVShow;
      f.firstAirDate = s.firstAirDate ?? "";
      f.episodeRuntimeMinutes = s.episodeRuntimeMinutes;
      f.creatorsInput = listText(s.creators);
      f.tmdbScore = s.tmdbScore;
      f.airingIntervalDays = s.airingIntervalDays;
      f.externalId = s.externalId ?? "";
    } else {
      const a = item as Anime;
      f.firstAirDate = a.firstAirDate ?? "";
      f.episodeRuntimeMinutes = a.episodeRuntimeMinutes;
      f.format = a.format ?? "";
      f.anilistScore = a.anilistScore;
      f.malScore = a.malScore;
      f.airingIntervalDays = a.airingIntervalDays;
      f.externalId = a.externalId ?? "";
      f.anilistId = a.anilistId ?? "";
    }
  }
  fields.value = f;
}
watch(() => props.item, loadFrom, { immediate: true });

const statusModel = computed({
  get: () => statusBucket(fields.value.status),
  set: (bucket: string) => {
    fields.value.status = bucketToReal(bucket);
  },
});

const subtitle = computed(() => {
  const f = fields.value;
  const year = (props.kind === "movie" ? f.releaseDate : f.firstAirDate).slice(
    0,
    4,
  );
  const detail =
    props.kind === "movie"
      ? f.runtimeMinutes
        ? `${f.runtimeMinutes} min`
        : ""
      : props.kind === "anime"
        ? f.format
        : "";
  return [year, detail].filter(Boolean).join(" · ");
});

const saving = ref(false);
const deleting = ref(false);
const error = ref<string | null>(null);

// ---- look up metadata ----
const search = useMetadataSearch<Result>({
  search: (query) =>
    props.kind === "movie"
      ? searchMovieMetadata(query, 8, true)
      : props.kind === "tv"
        ? searchTVShowMetadata(query, 8, true)
        : searchAnimeMetadata(query),
  details: (title) =>
    props.kind === "movie"
      ? searchMovieMetadata(title, 3)
      : searchTVShowMetadata(title, 3),
  noun: props.kind === "tv" ? "show" : props.kind,
  keyHint: props.kind === "anime" ? undefined : "TMDB or OMDb",
});
// anime has no separate details read: its list results already carry everything
if (props.kind === "anime") {
  (search as { resolve: (r: Result) => Promise<Result> }).resolve = async (r) =>
    r;
}

function runSearch(query: string) {
  search.query.value = query;
  return search.run();
}

// the backend's name for each field, so a field an admin changed by hand is not offered
const BACKEND_NAME: Record<string, string> = {
  releaseDate: "release_date",
  firstAirDate: "first_air_date",
  runtimeMinutes: "runtime_minutes",
  episodeRuntimeMinutes: "episode_runtime_minutes",
  studiosInput: "studios",
  genresInput: "genres",
  creatorsInput: "creators",
  posterUrl: "poster_url",
  backdropUrl: "backdrop_url",
  tmdbScore: "tmdb_score",
  anilistScore: "anilist_score",
  malScore: "mal_score",
};
const NUMBER_FIELDS = new Set([
  "runtimeMinutes",
  "episodeRuntimeMinutes",
  "tmdbScore",
  "anilistScore",
  "malScore",
]);

const lookupCurrent = computed<Record<string, string>>(() => {
  const f = fields.value;
  const text = (v: unknown) => (v == null ? "" : String(v));
  return {
    title: f.title,
    description: f.description,
    releaseDate: f.releaseDate,
    firstAirDate: f.firstAirDate,
    runtimeMinutes: text(f.runtimeMinutes),
    episodeRuntimeMinutes: text(f.episodeRuntimeMinutes),
    director: f.director,
    writer: f.writer,
    creatorsInput: f.creatorsInput,
    studiosInput: f.studiosInput,
    countriesInput: f.countriesInput,
    languagesInput: f.languagesInput,
    genresInput: f.genresInput,
    format: f.format,
    tmdbScore: text(f.tmdbScore),
    anilistScore: text(f.anilistScore),
    malScore: text(f.malScore),
  };
});

function describe(r: Result) {
  const date =
    "releaseDate" in r
      ? r.releaseDate
      : "firstAirDate" in r
        ? r.firstAirDate
        : null;
  const episodes =
    "episodeCount" in r && r.episodeCount ? `${r.episodeCount} ep` : null;
  return {
    key: `${r.provider}-${r.providerId}`,
    title: r.title,
    provider: r.provider,
    detail: [date?.slice(0, 4), episodes].filter(Boolean).join(" · "),
    image: r.posterUrl,
  };
}

function buildChanges(match: Result, poster: string | null): LookupChange[] {
  const out: LookupChange[] = [];
  const locked = new Set(props.item?.lockedFields ?? []);
  const raw = makeOffer(!props.item, lookupCurrent.value, out);
  const offer = (
    key: string,
    label: string,
    to: string | number | null | undefined,
    value: unknown = to,
  ) => {
    if (locked.has(BACKEND_NAME[key] ?? key)) return;
    raw(key, label, to, value);
  };
  const m = match as Partial<
    MovieMetadataResult & TVShowMetadataResult & AnimeMetadataResult
  >;
  offer("title", "Title", match.title);
  offer("description", "Description", m.description);
  if (props.kind === "movie") {
    offer("releaseDate", "Release date", m.releaseDate);
    offer("runtimeMinutes", "Runtime (minutes)", m.runtimeMinutes);
    offer("director", "Director", m.director);
    offer("writer", "Writer", m.writer);
  } else {
    offer("firstAirDate", "First air date", m.firstAirDate);
    offer("episodeRuntimeMinutes", "Episode runtime", m.episodeRuntimeMinutes);
  }
  if (props.kind === "tv")
    offer("creatorsInput", "Creators", listText(m.creators));
  if (props.kind === "anime") offer("format", "Format", m.format);
  offer("studiosInput", "Studios", listText(m.studios));
  offer("countriesInput", "Countries", listText(m.countries));
  offer("languagesInput", "Languages", listText(m.languages));
  offer("genresInput", "Genres", listText(m.genres));
  if (props.kind === "anime") {
    offer("anilistScore", "AniList score", m.anilistScore);
    offer("malScore", "MAL score", m.malScore);
  } else {
    offer("tmdbScore", "TMDB score", m.tmdbScore);
  }
  if (
    poster &&
    !locked.has("poster_url") &&
    poster !== fields.value.posterUrl
  ) {
    out.push({
      key: "posterUrl",
      label: "Poster",
      from: fields.value.posterUrl ? "Current poster" : "",
      to: "New poster",
      value: poster,
      image: poster,
      fromImage: fields.value.posterUrl || null,
      checked: !props.item || !fields.value.posterUrl,
    });
  }
  if (
    m.backdropUrl &&
    !locked.has("backdrop_url") &&
    m.backdropUrl !== fields.value.backdropUrl
  ) {
    out.push({
      key: "backdropUrl",
      label: "Backdrop",
      from: fields.value.backdropUrl ? "Current backdrop" : "",
      to: "New backdrop",
      value: m.backdropUrl,
      image: m.backdropUrl,
      fromImage: fields.value.backdropUrl || null,
      checked: !props.item || !fields.value.backdropUrl,
    });
  }
  lastMatch = match;
  return out;
}
let lastMatch: Result | null = null;

const lookupNote = ref<string | null>(null);
function applyChanges(
  changes: LookupApply[],
  provider: string,
  close: () => void,
) {
  const f = fields.value as Record<string, unknown>;
  for (const { key, value } of changes) {
    f[key] = NUMBER_FIELDS.has(key)
      ? numberOrNull(Number(value))
      : String(value ?? "");
  }
  // The links episode sync and the airing check need are not shown fields: picking
  // a result is how a title with a missing or wrong link gets fixed, so they are
  // always taken from the match that was applied from.
  const match = lastMatch as Partial<
    TVShowMetadataResult & AnimeMetadataResult
  > | null;
  if (match && changes.length) {
    if (props.kind === "tv" && match.tvmazeId)
      fields.value.externalId = match.tvmazeId;
    if (props.kind === "anime") {
      if (match.malId) fields.value.externalId = match.malId;
      if (match.provider === "AniList" && match.providerId)
        fields.value.anilistId = match.providerId;
    }
    if (props.kind === "tv" && !props.item && match.seasons) {
      stagedSeasons.value = match.seasons.map((s) => ({
        seasonNumber: s.seasonNumber,
        name: s.name,
        episodeCount: s.episodeCount,
        airDate: s.airDate,
        posterUrl: s.posterUrl,
      }));
    }
  }
  lookupNote.value = changes.length
    ? `Filled ${changes.length} field${changes.length === 1 ? "" : "s"} from ${provider}. Review them, then save.`
    : null;
  close();
}

// ---- saving ----
async function submit() {
  const f = fields.value;
  if (!f.title.trim()) {
    error.value = "Title is required.";
    activeTab.value = "Basics";
    return;
  }
  let progressMinutes: number | null = null;
  if (props.kind === "movie") {
    const parsed = parseProgressMinutes(f.progressInput);
    if (parsed !== null && Number.isNaN(parsed)) {
      error.value = "Left off at: try 72, 1:12 or 1h 12m.";
      activeTab.value = "Basics";
      return;
    }
    progressMinutes = parsed || null;
    // a position in a movie you hadn't started means you're watching it
    if (progressMinutes && statusBucket(f.status) === "plan")
      f.status = "in progress";
  }
  saving.value = true;
  error.value = null;
  const base = {
    title: f.title.trim(),
    description: f.description.trim() || null,
    status: f.status,
    favorite: f.favorite,
    priority: f.priority || null,
    rewatches: numberOrNull(f.rewatches) ?? 0,
    startDate: f.startDate || null,
    endDate: f.endDate || null,
    studios: splitList(f.studiosInput),
    countries: splitList(f.countriesInput),
    languages: splitList(f.languagesInput),
    genres: splitList(f.genresInput),
    tags: splitList(f.tagsInput),
    features: splitList(f.featuresInput),
    ageRating: f.ageRating.trim() || null,
    source: f.source.trim() || null,
    ratingOverall: numberOrNull(f.ratingOverall),
    ratingStory: numberOrNull(f.ratingStory),
    ratingPerformance: numberOrNull(f.ratingPerformance),
    ratingSoundtrack: numberOrNull(f.ratingSoundtrack),
    personalRank: numberOrNull(f.personalRank),
    posterUrl: f.posterUrl.trim() || null,
    backdropUrl: f.backdropUrl.trim() || null,
    note: f.note.trim() || null,
  };
  try {
    let saved: Item;
    if (props.kind === "movie") {
      const input = {
        ...base,
        status: f.status as Movie["status"],
        progressMinutes,
        releaseDate: f.releaseDate || null,
        runtimeMinutes: numberOrNull(f.runtimeMinutes),
        director: f.director.trim() || null,
        writer: f.writer.trim() || null,
        tmdbScore: numberOrNull(f.tmdbScore),
      };
      saved = props.item
        ? await updateMovie(props.item.id, {
            // keep the fields this form doesn't show
            ...movieToInput(props.item as Movie),
            ...input,
          })
        : await createMovie(input);
    } else if (props.kind === "tv") {
      const input = {
        ...base,
        status: f.status as TVShow["status"],
        firstAirDate: f.firstAirDate || null,
        episodeRuntimeMinutes: numberOrNull(f.episodeRuntimeMinutes),
        creators: splitList(f.creatorsInput),
        tmdbScore: numberOrNull(f.tmdbScore),
        airingIntervalDays: numberOrNull(f.airingIntervalDays),
        externalId: f.externalId.trim() || null,
        seasons: props.item ? undefined : stagedSeasons.value,
      };
      saved = props.item
        ? await updateTVShow(props.item.id, {
            ...tvShowToInput(props.item as TVShow),
            ...input,
          })
        : await createTVShow(input);
    } else {
      const input = {
        ...base,
        status: f.status as Anime["status"],
        firstAirDate: f.firstAirDate || null,
        episodeRuntimeMinutes: numberOrNull(f.episodeRuntimeMinutes),
        format: f.format.trim() || null,
        anilistScore: numberOrNull(f.anilistScore),
        malScore: numberOrNull(f.malScore),
        airingIntervalDays: numberOrNull(f.airingIntervalDays),
        externalId: f.externalId.trim() || null,
        anilistId: f.anilistId.trim() || null,
      };
      saved = props.item
        ? await updateAnime(props.item.id, {
            ...animeToInput(props.item as Anime),
            ...input,
          })
        : await createAnime(input);
    }
    emit("saved", saved);
  } catch (e) {
    error.value =
      e instanceof Error
        ? e.message
        : `Could not save ${noun.value.toLowerCase()}.`;
  } finally {
    saving.value = false;
  }
}

async function remove() {
  if (!props.item) return;
  deleting.value = true;
  error.value = null;
  try {
    if (props.kind === "movie") await deleteMovie(props.item.id);
    else if (props.kind === "tv") await deleteTVShow(props.item.id);
    else await deleteAnime(props.item.id);
    emit("deleted", props.item.id);
  } catch (e) {
    error.value =
      e instanceof Error
        ? e.message
        : `Could not delete ${noun.value.toLowerCase()}.`;
  } finally {
    deleting.value = false;
  }
}
</script>

<template>
  <MediaFormShell
    v-model:tab="activeTab"
    :noun="noun"
    :editing="!!item"
    :saving="saving"
    :deleting="deleting"
    :error="error"
    :title="fields.title"
    :subtitle="subtitle"
    :poster="fields.posterUrl || null"
    :tabs="tabs"
    @closed="emit('closed')"
    @save="submit"
    @delete="remove"
  >
    <template #default="{ tab }">
      <p v-if="lookupNote" class="mf-note">{{ lookupNote }}</p>

      <div v-if="tab === 'Basics'">
        <p class="mf-section">Identity</p>
        <div class="mf-grid">
          <label class="mf-field full">
            <span>Title</span>
            <input v-model="fields.title" type="text" required />
          </label>
        </div>

        <p class="mf-section">Library</p>
        <div class="mf-grid">
          <label class="mf-field">
            <span>Status</span>
            <select v-model="statusModel">
              <option v-for="s in STATUS_BUCKETS" :key="s.key" :value="s.key">
                {{ s.label }}
              </option>
            </select>
          </label>
          <label class="mf-field">
            <span>Priority</span>
            <select v-model="fields.priority">
              <option value="">None</option>
              <option
                v-for="option in PRIORITY_OPTIONS"
                :key="option.value"
                :value="option.value"
              >
                {{ option.label }}
              </option>
            </select>
          </label>
          <label class="mf-field">
            <span>Started</span>
            <input v-model="fields.startDate" type="date" />
          </label>
          <label class="mf-field">
            <span>Finished</span>
            <input v-model="fields.endDate" type="date" />
          </label>
          <label v-if="kind === 'movie'" class="mf-field">
            <span>Left off at</span>
            <input
              v-model="fields.progressInput"
              type="text"
              inputmode="numeric"
              placeholder="Not started, or 1h 12m"
            />
          </label>
          <label class="mf-field">
            <span>Rewatches</span>
            <input v-model.number="fields.rewatches" type="number" min="0" />
          </label>
          <label class="mf-check">
            <input v-model="fields.favorite" type="checkbox" />
            <span>Favorite</span>
          </label>
        </div>
      </div>

      <div v-else-if="tab === 'Details'">
        <p class="mf-section">About</p>
        <div class="mf-grid">
          <label class="mf-field full">
            <span>Description</span>
            <textarea v-model="fields.description" rows="5"></textarea>
          </label>
          <template v-if="kind === 'movie'">
            <label class="mf-field">
              <span>Release date</span>
              <input v-model="fields.releaseDate" type="date" />
            </label>
            <label class="mf-field">
              <span>Runtime (minutes)</span>
              <input
                v-model.number="fields.runtimeMinutes"
                type="number"
                min="0"
              />
            </label>
            <label class="mf-field">
              <span>Director</span>
              <input v-model="fields.director" type="text" />
            </label>
            <label class="mf-field">
              <span>Writer</span>
              <input v-model="fields.writer" type="text" />
            </label>
          </template>
          <template v-else>
            <label class="mf-field">
              <span>First air date</span>
              <input v-model="fields.firstAirDate" type="date" />
            </label>
            <label class="mf-field">
              <span>Episode runtime (minutes)</span>
              <input
                v-model.number="fields.episodeRuntimeMinutes"
                type="number"
                min="0"
              />
            </label>
            <label v-if="kind === 'tv'" class="mf-field full">
              <span>Creators (comma separated)</span>
              <input v-model="fields.creatorsInput" type="text" />
            </label>
            <label v-if="kind === 'anime'" class="mf-field">
              <span>Format</span>
              <input
                v-model="fields.format"
                type="text"
                placeholder="TV, Movie, OVA"
              />
            </label>
            <label class="mf-field">
              <span>Days between episodes</span>
              <input
                v-model.number="fields.airingIntervalDays"
                type="number"
                min="1"
                placeholder="Weekly"
              />
            </label>
          </template>
        </div>

        <p class="mf-section">Credits and tags</p>
        <div class="mf-grid">
          <label class="mf-field full">
            <span>Studios (comma separated)</span>
            <input v-model="fields.studiosInput" type="text" />
          </label>
          <label class="mf-field full">
            <span>Genres (comma separated)</span>
            <input v-model="fields.genresInput" type="text" />
          </label>
          <label class="mf-field full">
            <span>Tags (comma separated)</span>
            <input v-model="fields.tagsInput" type="text" />
          </label>
          <label class="mf-field full">
            <span>Features (comma separated)</span>
            <input v-model="fields.featuresInput" type="text" />
          </label>
        </div>

        <p class="mf-section">Release details</p>
        <div class="mf-grid">
          <label class="mf-field">
            <span>Age rating</span>
            <input
              v-model="fields.ageRating"
              type="text"
              placeholder="PG-13, TV-MA"
            />
          </label>
          <label class="mf-field">
            <span>Source</span>
            <input
              v-model="fields.source"
              type="text"
              placeholder="Blu-ray, Netflix"
            />
          </label>
          <label class="mf-field">
            <span>Countries (comma separated)</span>
            <input v-model="fields.countriesInput" type="text" />
          </label>
          <label class="mf-field">
            <span>Languages (comma separated)</span>
            <input v-model="fields.languagesInput" type="text" />
          </label>
        </div>
      </div>

      <div v-else-if="tab === 'Ratings'">
        <p class="mf-section">Your ratings (0 to 10)</p>
        <div class="mf-grid four">
          <label class="mf-field">
            <span>Overall</span>
            <input
              v-model.number="fields.ratingOverall"
              type="number"
              min="0"
              max="10"
              step="0.1"
            />
          </label>
          <label class="mf-field">
            <span>Story</span>
            <input
              v-model.number="fields.ratingStory"
              type="number"
              min="0"
              max="10"
              step="0.1"
            />
          </label>
          <label class="mf-field">
            <span>Performance</span>
            <input
              v-model.number="fields.ratingPerformance"
              type="number"
              min="0"
              max="10"
              step="0.1"
            />
          </label>
          <label class="mf-field">
            <span>Soundtrack</span>
            <input
              v-model.number="fields.ratingSoundtrack"
              type="number"
              min="0"
              max="10"
              step="0.1"
            />
          </label>
        </div>

        <p class="mf-section">Ranking and scores</p>
        <div class="mf-grid">
          <label class="mf-field">
            <span>Personal rank</span>
            <input v-model.number="fields.personalRank" type="number" min="1" />
          </label>
          <label v-if="kind !== 'anime'" class="mf-field">
            <span>TMDB or IMDb score (0 to 10)</span>
            <input
              v-model.number="fields.tmdbScore"
              type="number"
              min="0"
              max="10"
              step="0.1"
            />
          </label>
          <template v-else>
            <label class="mf-field">
              <span>AniList score</span>
              <input
                v-model.number="fields.anilistScore"
                type="number"
                min="0"
                max="100"
                step="0.1"
              />
            </label>
            <label class="mf-field">
              <span>MAL score (0 to 10)</span>
              <input
                v-model.number="fields.malScore"
                type="number"
                min="0"
                max="10"
                step="0.01"
              />
            </label>
          </template>
        </div>
      </div>

      <div v-else-if="tab === 'Artwork'">
        <div class="mf-art">
          <div class="mf-art-slot">
            <p class="mf-section">Poster</p>
            <div class="mf-art-row">
              <div
                class="mf-art-preview tall"
                :style="
                  fields.posterUrl
                    ? { backgroundImage: `url(${fields.posterUrl})` }
                    : {}
                "
              ></div>
              <div class="mf-art-actions">
                <label class="mf-field">
                  <span>Image link</span>
                  <input
                    v-model="fields.posterUrl"
                    type="url"
                    placeholder="https://"
                  />
                </label>
                <button
                  v-if="fields.posterUrl"
                  type="button"
                  class="mf-link"
                  @click="fields.posterUrl = ''"
                >
                  Remove poster
                </button>
              </div>
            </div>
          </div>
          <div class="mf-art-slot">
            <p class="mf-section">Backdrop</p>
            <div class="mf-art-row">
              <div
                class="mf-art-preview wide"
                :style="
                  fields.backdropUrl
                    ? { backgroundImage: `url(${fields.backdropUrl})` }
                    : {}
                "
              ></div>
              <div class="mf-art-actions">
                <label class="mf-field">
                  <span>Image link</span>
                  <input
                    v-model="fields.backdropUrl"
                    type="url"
                    placeholder="https://"
                  />
                </label>
                <button
                  v-if="fields.backdropUrl"
                  type="button"
                  class="mf-link"
                  @click="fields.backdropUrl = ''"
                >
                  Remove backdrop
                </button>
              </div>
            </div>
          </div>
        </div>
        <p class="mf-hint">
          Use Look up metadata to pick the provider's poster and backdrop. A new
          image is saved with the {{ noun.toLowerCase() }} and shown as soon as
          you save.
        </p>
      </div>

      <div v-else-if="tab === 'Notes'">
        <p class="mf-section">Notes</p>
        <label class="mf-field">
          <span>Your notes</span>
          <textarea v-model="fields.note" rows="10"></textarea>
        </label>
      </div>

      <div v-else-if="tab === 'Advanced'">
        <p class="mf-section">Provider links</p>
        <p class="mf-hint">
          The ids episode sync and the airing check use. Look up metadata fills
          them in; change them only to point at a different entry.
        </p>
        <div class="mf-grid">
          <label class="mf-field">
            <span>{{ kind === "tv" ? "TVmaze id" : "MyAnimeList id" }}</span>
            <input v-model="fields.externalId" type="text" />
          </label>
          <label v-if="kind === 'anime'" class="mf-field">
            <span>AniList id</span>
            <input v-model="fields.anilistId" type="text" />
          </label>
        </div>
      </div>
    </template>

    <template #lookup="{ close }">
      <MediaLookupPanel
        :noun="noun.toLowerCase()"
        :run="runSearch"
        :resolve="search.resolve"
        :results="search.results.value"
        :searching="search.searching.value"
        :message="search.message.value"
        :warnings="search.warnings.value"
        :describe="describe"
        :build="buildChanges"
        :poster-of="(r) => r.posterUrl"
        :adding="!item"
        :initial-query="fields.title"
        @close="close"
        @apply="(changes, provider) => applyChanges(changes, provider, close)"
      />
    </template>
  </MediaFormShell>
</template>

<style scoped>
.mf-section {
  margin: 18px 0 8px;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-faint, #666);
}
.mf-section:first-child {
  margin-top: 0;
}
.mf-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
.mf-grid.four {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}
.mf-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
.mf-field.full {
  grid-column: 1 / -1;
}
.mf-field > span {
  font-size: 0.74rem;
  font-weight: 600;
  color: var(--text-dim, var(--ui-dim));
}
.mf-field input,
.mf-field select,
.mf-field textarea {
  width: 100%;
  background: var(--surface-2, #222);
  border: 1px solid var(--border, var(--ui-border));
  color: var(--text, var(--ui-text));
  border-radius: 8px;
  padding: 9px 11px;
  font: inherit;
  font-size: 0.86rem;
}
.mf-field textarea {
  resize: vertical;
  min-height: 70px;
}
.mf-field input:focus,
.mf-field select:focus,
.mf-field textarea:focus {
  outline: none;
  border-color: var(--accent-line, var(--ui-accent-line));
}
.mf-check {
  display: flex;
  gap: 10px;
  align-items: center;
  align-self: end;
  font-size: 0.86rem;
  padding: 8px 0;
}
.mf-check input {
  accent-color: var(--accent, var(--ui-accent));
}
.mf-hint {
  margin: 4px 0 10px;
  font-size: 0.78rem;
  color: var(--text-faint, #666);
  line-height: 1.5;
}
.mf-note {
  margin: 0 0 14px;
  padding: 8px 12px;
  border: 1px solid var(--accent-line, var(--ui-accent-line));
  border-radius: 8px;
  background: var(--accent-soft, var(--ui-accent-soft));
  font-size: 0.8rem;
}
.mf-art {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px 20px;
}
.mf-art-slot .mf-section {
  margin-top: 0;
}
.mf-art-row {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}
.mf-art-preview {
  flex: none;
  border: 1px solid var(--border, var(--ui-border));
  border-radius: 8px;
  background-color: var(--surface-2, #222);
  background-size: cover;
  background-position: center;
}
.mf-art-preview.tall {
  width: 90px;
  height: 130px;
}
.mf-art-preview.wide {
  width: 160px;
  height: 90px;
}
.mf-art-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
  flex: 1;
}
.mf-link {
  align-self: flex-start;
  padding: 0;
  border: 0;
  background: none;
  color: var(--text-faint, #666);
  font: inherit;
  font-size: 0.78rem;
  cursor: pointer;
}
.mf-link:hover {
  color: var(--accent, var(--ui-accent));
}
@media (max-width: 720px) {
  .mf-grid,
  .mf-grid.four,
  .mf-art {
    grid-template-columns: 1fr;
  }
}
</style>
