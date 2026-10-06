<script setup lang="ts">
import { localMediaImage } from "../utils/mediaImages";
import { usePageTitle } from "../state/pageTitle";
import MyNote from "../components/MyNote.vue";
import MediaDetailHero from "../components/MediaDetailHero.vue";
import MediaDetailTabs from "../components/MediaDetailTabs.vue";
import ExpandableDescription from "../components/ExpandableDescription.vue";
import { ref, computed, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  getMovie,
  peekMovie,
  updateMovie,
  movieToInput,
  fetchMovieRelations,
  fetchMovieRecommended,
  fetchMovies,
  createMovie,
  searchMovieMetadata,
} from "../services/movies";
import type { RelatedMovie } from "../services/movies";
import type { Movie, MovieStatus } from "../types/movie";
import MovieFormModal from "../components/MovieFormModal.vue";
import RelationsGraph from "../components/RelationsGraph.vue";
import type { ChainNode, BranchNode } from "../components/RelationsGraph.vue";
import MediaPreviewModal from "../components/MediaPreviewModal.vue";
import MediaProviderPanel from "../components/MediaProviderPanel.vue";
import MediaTopBar from "../components/MediaTopBar.vue";
import BackButton from "../components/BackButton.vue";
import PluginExtensionSlot from "../components/plugins/PluginExtensionSlot.vue";
import PluginContextualActions from "../components/plugins/PluginContextualActions.vue";
import { statusBucket, bucketToReal } from "../utils/mediaStatus";
import {
  formatProgressMinutes,
  parseProgressMinutes,
  progressPercent,
} from "../utils/watchProgress";

const route = useRoute();
const router = useRouter();
const movieId = computed(() => route.params.id as string);

const movie = ref<Movie | null>(null);
usePageTitle(() => movie.value?.title);
const loading = ref(true);
const error = ref<string | null>(null);
const showEditModal = ref(false);
const activeTab = ref<"overview" | "related" | "recommended">("overview");
const statusBucketModel = computed({
  get: () => statusBucket(movie.value?.status ?? "wishlist"),
  set: (bucket: string) => {
    if (!movie.value) return;
    movie.value.status = bucketToReal(bucket) as MovieStatus;
  },
});

function goBack() {
  if (window.history.length > 1) {
    router.back();
  } else {
    router.push("/movies");
  }
}

async function load() {
  const cached = peekMovie(movieId.value);
  if (cached) {
    movie.value = cached;
    loading.value = false;
  } else {
    loading.value = true;
  }
  try {
    movie.value = await getMovie(movieId.value);
  } catch (e) {
    if (!cached)
      error.value = e instanceof Error ? e.message : "Failed to load movie.";
  } finally {
    loading.value = false;
  }
}

async function toggleFavorite() {
  if (!movie.value) return;
  const next = !movie.value.favorite;
  movie.value.favorite = next;
  try {
    await updateMovie(movie.value.id, {
      ...movieToInput(movie.value),
      favorite: next,
    });
  } catch {
    movie.value.favorite = !next;
  }
}

async function saveNote(note: string | null) {
  if (!movie.value) return;
  const previous = movie.value.note;
  movie.value.note = note;
  try {
    movie.value = await updateMovie(movie.value.id, {
      ...movieToInput(movie.value),
      note,
    });
  } catch {
    movie.value.note = previous;
  }
}

async function onStatusChange() {
  if (!movie.value) return;
  const previous = movie.value.status;
  try {
    movie.value = await updateMovie(movie.value.id, {
      ...movieToInput(movie.value),
      status: movie.value.status,
    });
  } catch {
    movie.value.status = previous;
  }
}

// "Left off at" (#191): where you stopped in a movie you haven't finished
const progressInput = ref("");
const savingProgress = ref(false);
const progressError = ref<string | null>(null);
watch(
  () => movie.value?.progressMinutes,
  (minutes) => {
    progressInput.value =
      minutes === null || minutes === undefined
        ? ""
        : formatProgressMinutes(minutes);
    progressError.value = null;
  },
  { immediate: true },
);
const showResumeRow = computed(
  () =>
    !!movie.value &&
    (statusBucket(movie.value.status) !== "completed" ||
      movie.value.progressMinutes !== null),
);
const progressPct = computed(() =>
  movie.value
    ? progressPercent(movie.value.progressMinutes, movie.value.runtimeMinutes)
    : null,
);

async function saveProgress() {
  // Enter then blur would otherwise send the same save twice
  if (!movie.value || savingProgress.value) return;
  const parsed = parseProgressMinutes(progressInput.value);
  if (parsed !== null && Number.isNaN(parsed)) {
    progressError.value = "Enter minutes (72) or hours:minutes (1:12).";
    return;
  }
  const runtime = movie.value.runtimeMinutes;
  const minutes =
    parsed !== null && runtime ? Math.min(parsed, runtime) : parsed;
  if (minutes === movie.value.progressMinutes) return;
  // saving a position in a movie you hadn't started means you're watching it
  const status =
    minutes && statusBucket(movie.value.status) === "plan"
      ? ("in progress" as MovieStatus)
      : movie.value.status;
  savingProgress.value = true;
  progressError.value = null;
  try {
    movie.value = await updateMovie(movie.value.id, {
      ...movieToInput(movie.value),
      status,
      progressMinutes: minutes || null,
    });
  } catch (e) {
    progressError.value =
      e instanceof Error ? e.message : "Couldn't save where you left off.";
  } finally {
    savingProgress.value = false;
  }
}

function onSaved(saved: Movie) {
  movie.value = saved;
  showEditModal.value = false;
}

function onDeleted() {
  router.push("/movies");
}

const releaseYear = computed(() =>
  movie.value?.releaseDate ? movie.value.releaseDate.slice(0, 4) : null,
);
const runtimeLabel = computed(() => {
  const minutes = movie.value?.runtimeMinutes;
  if (!minutes) return null;
  const hrs = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return hrs > 0 ? `${hrs}h ${mins}m` : `${mins}m`;
});
const nativeTitleLine = computed(() => {
  if (!movie.value) return "";
  const credit = movie.value.director || movie.value.studios[0];
  return credit ? `Movie · ${credit}` : "Movie";
});
const heroBackdropUrl = computed(() =>
  movie.value
    ? localMediaImage(
        "movie",
        movie.value.id,
        "hero",
        movie.value.backdropUrl ?? movie.value.posterUrl,
      )
    : null,
);

// ---- related (real TMDB collection data) ----
const relatedLoading = ref(false);
const relatedLoaded = ref(false);
const relatedError = ref<string | null>(null);
const relatedList = ref<RelatedMovie[]>([]);
const relatedCollectionName = ref<string | null>(null);
const relatedConfigured = ref(true);

async function loadRelated() {
  if (!movie.value || relatedLoaded.value) return;
  relatedLoading.value = true;
  relatedError.value = null;
  try {
    const res = await fetchMovieRelations(movie.value.id);
    relatedList.value = res.related;
    relatedCollectionName.value = res.collectionName;
    relatedConfigured.value = res.configured;
    relatedLoaded.value = true;
  } catch (e) {
    relatedError.value =
      e instanceof Error ? e.message : "Failed to load related movies.";
  } finally {
    relatedLoading.value = false;
  }
}

const relatedChainNodes = computed<ChainNode[]>(() =>
  movie.value
    ? [
        {
          id: "current",
          title: movie.value.title,
          type: "This movie",
          sub: "",
          current: true,
        },
      ]
    : [],
);
const relatedBranchNodes = computed<BranchNode[]>(() =>
  relatedList.value.map((r) => ({
    id: String(r.id),
    title: r.title,
    type: "Movie",
    sub: r.year ?? "",
    label: relatedCollectionName.value ?? "Related",
    anchorIndex: 0,
  })),
);
function onRelatedBranchClick() {
  // Related titles are TMDB entries, not necessarily in this library —
  // nothing to navigate to yet.
}

// ---- recommended (TMDB) ----
const recommendedLoading = ref(false);
const recommendedLoaded = ref(false);
const recommendedError = ref<string | null>(null);
const recommendedList = ref<RelatedMovie[]>([]);
const recommendedConfigured = ref(true);

async function loadRecommended() {
  if (!movie.value || recommendedLoaded.value) return;
  recommendedLoading.value = true;
  recommendedError.value = null;
  try {
    const res = await fetchMovieRecommended(movie.value.id);
    recommendedList.value = res.recommended;
    recommendedConfigured.value = res.configured;
    recommendedLoaded.value = true;
  } catch (e) {
    recommendedError.value =
      e instanceof Error ? e.message : "Failed to load recommendations.";
  } finally {
    recommendedLoading.value = false;
  }
}

// ---- click-through on a Related/Recommended title: go straight to it
// if it's already in the library, otherwise preview it with an Add
// button (reusing the same search-then-create flow the library page's
// quick-add uses) ----
const myMovies = ref<Movie[] | null>(null);
async function ensureMyMovies(): Promise<Movie[]> {
  if (!myMovies.value) myMovies.value = await fetchMovies();
  return myMovies.value;
}

const previewOpen = ref(false);
const previewLoading = ref(false);
const previewAdding = ref(false);
const previewError = ref<string | null>(null);
const previewTitle = ref("");
const previewPosterUrl = ref<string | null>(null);
const previewDescription = ref<string | null>(null);
const previewMeta = ref<string[]>([]);

function closePreview() {
  previewOpen.value = false;
}

async function onRelatedTitleClick(r: {
  title: string;
  posterUrl: string | null;
}) {
  const mine = await ensureMyMovies();
  const existing = mine.find(
    (m) => m.title.trim().toLowerCase() === r.title.trim().toLowerCase(),
  );
  if (existing) {
    router.push(`/movies/${existing.id}`);
    return;
  }
  previewOpen.value = true;
  previewLoading.value = true;
  previewError.value = null;
  previewTitle.value = r.title;
  previewPosterUrl.value = r.posterUrl;
  previewDescription.value = null;
  previewMeta.value = [];
  try {
    const { results } = await searchMovieMetadata(r.title, 1);
    const match = results.find((m) => m.title === r.title) ?? results[0];
    previewDescription.value = match?.description ?? null;
    previewMeta.value = [
      match?.releaseDate?.slice(0, 4),
      match?.director,
    ].filter((v): v is string => !!v);
  } catch (e) {
    previewError.value =
      e instanceof Error ? e.message : "Failed to load a preview.";
  } finally {
    previewLoading.value = false;
  }
}

async function addPreviewToLibrary() {
  previewAdding.value = true;
  previewError.value = null;
  try {
    const { results } = await searchMovieMetadata(previewTitle.value, 1);
    const match =
      results.find((m) => m.title === previewTitle.value) ?? results[0];
    const created = await createMovie({
      title: previewTitle.value,
      description: match?.description ?? null,
      releaseDate: match?.releaseDate ?? null,
      runtimeMinutes: match?.runtimeMinutes ?? null,
      director: match?.director ?? null,
      writer: match?.writer ?? null,
      studios: match?.studios ?? [],
      countries: match?.countries ?? [],
      genres: match?.genres ?? [],
      posterUrl: previewPosterUrl.value,
      backdropUrl: match?.backdropUrl ?? null,
      tmdbScore: match?.tmdbScore ?? null,
      status: "wishlist",
    });
    if (myMovies.value) myMovies.value.push(created);
    router.push(`/movies/${created.id}`);
  } catch (e) {
    previewError.value =
      e instanceof Error ? e.message : "Failed to add to library.";
  } finally {
    previewAdding.value = false;
  }
}

const TABS: { key: "overview" | "related" | "recommended"; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "related", label: "Related" },
  { key: "recommended", label: "Recommended" },
];

function setTab(tab: "overview" | "related" | "recommended") {
  activeTab.value = tab;
  if (tab === "related") loadRelated();
  if (tab === "recommended") loadRecommended();
}

// Vue Router reuses this component instance across /movies/:id → /movies/:id2
// navigations (same matched route), so onMounted alone would never refire —
// watch the param instead, resetting every tab's lazy-loaded state so a
// click-through from Related/Recommended actually shows the new title.
watch(
  movieId,
  () => {
    activeTab.value = "overview";
    relatedLoaded.value = false;
    recommendedLoaded.value = false;
    previewOpen.value = false;
    load();
  },
  { immediate: true },
);
async function onRatingChange(value: number | null) {
  if (!movie.value) return;
  const previous = movie.value.ratingOverall;
  movie.value.ratingOverall = value;
  try {
    movie.value = await updateMovie(movie.value.id, {
      ...movieToInput(movie.value),
      ratingOverall: value,
    });
  } catch {
    if (movie.value) movie.value.ratingOverall = previous;
  }
}
</script>

<template>
  <main v-if="loading" class="detail loading-state">
    <MediaTopBar active="movie" />
    <p class="loading-text">Loading…</p>
  </main>

  <main v-else-if="error" class="detail error-state">
    <MediaTopBar active="movie" />
    <p class="loading-text">{{ error }}</p>
  </main>

  <main v-else-if="movie" class="detail">
    <MediaTopBar active="movie" />
    <PluginExtensionSlot
      slot-id="media.detail.after-header"
      :context="{
        host_page: 'media.detail',
        media_id: movie.id,
        media_type: 'movie',
      }"
    />
    <PluginContextualActions
      :context="{
        kind: 'media',
        resource_id: String(movie.id),
        resource_type: 'movie',
      }"
    />

    <BackButton class="back-spot" @click="goBack" />

    <MovieFormModal
      v-if="showEditModal"
      :movie="movie"
      @saved="onSaved"
      @deleted="onDeleted"
      @closed="showEditModal = false"
    />

    <MediaDetailHero
      v-model:status="statusBucketModel"
      :title="movie.title"
      :native-title="nativeTitleLine"
      :poster-url="
        localMediaImage('movie', movie.id, 'poster', movie.posterUrl)
      "
      :hero-backdrop-url="heroBackdropUrl"
      :has-backdrop="!!movie.backdropUrl"
      :rating-overall="movie.ratingOverall"
      :favorite="movie.favorite"
      media-type="movie"
      :media-id="movie.id"
      :badges="[
        ...(releaseYear ? [{ text: releaseYear }] : []),
        ...(runtimeLabel ? [{ text: runtimeLabel }] : []),
      ]"
      @status-change="onStatusChange"
      @rating-change="onRatingChange"
      @edit="showEditModal = true"
      @toggle-favorite="toggleFavorite"
    >
      <template #below-badges>
        <div v-if="showResumeRow" class="resume-row">
          <label class="resume-label" for="movie-left-off">Left off at</label>
          <input
            id="movie-left-off"
            v-model="progressInput"
            class="resume-input"
            inputmode="numeric"
            placeholder="h:mm"
            aria-describedby="movie-left-off-hint"
            @keydown.enter.prevent="saveProgress"
            @blur="saveProgress"
          />
          <span v-if="movie.runtimeMinutes" class="resume-of"
            >of {{ formatProgressMinutes(movie.runtimeMinutes) }}</span
          >
          <span
            v-if="progressPct !== null"
            class="resume-bar"
            role="progressbar"
            :aria-valuenow="progressPct"
            aria-valuemin="0"
            aria-valuemax="100"
            aria-label="Watched so far"
            ><span :style="{ width: `${progressPct}%` }"></span
          ></span>
          <span id="movie-left-off-hint" class="resume-hint">{{
            savingProgress
              ? "Saving…"
              : (progressError ?? "Minutes or h:mm; blank clears it.")
          }}</span>
        </div>
      </template>
    </MediaDetailHero>

    <MediaDetailTabs :tabs="TABS" :active="activeTab" @select="setTab" />

    <div class="body">
      <div v-if="activeTab === 'overview'" class="tab-panel">
        <div class="meta-grid">
          <div v-if="movie.director" class="meta-item">
            <span class="meta-label">Director</span>
            <span class="meta-value">{{ movie.director }}</span>
          </div>
          <div v-if="movie.writer" class="meta-item">
            <span class="meta-label">Writer</span>
            <span class="meta-value">{{ movie.writer }}</span>
          </div>
          <div v-if="movie.studios.length" class="meta-item">
            <span class="meta-label">Studios</span>
            <span class="meta-value">{{ movie.studios.join(", ") }}</span>
          </div>
          <div v-if="movie.tmdbScore !== null" class="meta-item">
            <span class="meta-label">TMDB score</span>
            <span class="meta-value accent">{{
              movie.tmdbScore.toFixed(1)
            }}</span>
          </div>
          <div v-if="movie.ratingOverall !== null" class="meta-item">
            <span class="meta-label">Your score</span>
            <span class="meta-value accent">{{
              movie.ratingOverall.toFixed(1)
            }}</span>
          </div>
          <div v-if="movie.personalRank !== null" class="meta-item">
            <span class="meta-label">Personal rank</span>
            <span class="meta-value">#{{ movie.personalRank }}</span>
          </div>
          <div v-if="movie.rewatches > 0" class="meta-item">
            <span class="meta-label">Rewatches</span>
            <span class="meta-value">{{ movie.rewatches }}</span>
          </div>
        </div>

        <div v-if="movie.genres.length" class="chip-row">
          <router-link
            v-for="g in movie.genres"
            :key="g"
            class="chip primary chip-link"
            :to="{ path: '/movies', query: { genre: g } }"
            :title="`All movies tagged ${g}`"
            >{{ g }}</router-link
          >
        </div>
        <div v-if="movie.tags.length" class="chip-row">
          <span v-for="t in movie.tags" :key="t" class="chip">{{ t }}</span>
        </div>
        <ExpandableDescription
          v-if="movie.description"
          :text="movie.description"
        />
        <MyNote :note="movie.note" @save="saveNote" />
        <MediaProviderPanel media-type="movie" :media-id="movie.id" />
      </div>

      <div v-else-if="activeTab === 'related'" class="tab-panel">
        <div class="section-heading">
          <h2>Related</h2>
        </div>
        <p v-if="relatedLoading" class="empty-state">Loading…</p>
        <p v-else-if="relatedError" class="empty-state error-text">
          {{ relatedError }}
        </p>
        <p v-else-if="!relatedConfigured" class="empty-state">
          TMDB isn't configured yet. A server admin can add an API key under
          Settings &gt; Metadata Sources to enable this.
        </p>
        <p v-else-if="!relatedList.length" class="empty-state">
          Not part of any known collection on TMDB.
        </p>
        <template v-else>
          <RelationsGraph
            :chain-nodes="relatedChainNodes"
            :branch-nodes="relatedBranchNodes"
            @branch-click="onRelatedBranchClick"
          />
          <div class="poster-grid">
            <div
              v-for="r in relatedList"
              :key="r.id"
              class="poster-card-sm"
              @click="onRelatedTitleClick(r)"
            >
              <div
                class="poster-card-sm-art"
                :style="
                  r.posterUrl ? { backgroundImage: `url(${r.posterUrl})` } : {}
                "
              ></div>
              <div class="poster-card-sm-title">{{ r.title }}</div>
              <div v-if="r.year" class="poster-card-sm-meta">{{ r.year }}</div>
            </div>
          </div>
        </template>
      </div>

      <div v-else class="tab-panel">
        <div class="section-heading">
          <h2>Recommended</h2>
        </div>
        <p v-if="recommendedLoading" class="empty-state">Loading…</p>
        <p v-else-if="recommendedError" class="empty-state error-text">
          {{ recommendedError }}
        </p>
        <p v-else-if="!recommendedConfigured" class="empty-state">
          TMDB isn't configured yet. A server admin can add an API key under
          Settings &gt; Metadata Sources to enable this.
        </p>
        <p v-else-if="!recommendedList.length" class="empty-state">
          No recommendations found.
        </p>
        <div v-else class="poster-grid">
          <div
            v-for="r in recommendedList"
            :key="r.id"
            class="poster-card-sm"
            @click="onRelatedTitleClick(r)"
          >
            <div
              class="poster-card-sm-art"
              :style="
                r.posterUrl ? { backgroundImage: `url(${r.posterUrl})` } : {}
              "
            ></div>
            <div class="poster-card-sm-title">{{ r.title }}</div>
            <div v-if="r.year" class="poster-card-sm-meta">{{ r.year }}</div>
          </div>
        </div>
      </div>
    </div>

    <MediaPreviewModal
      v-if="previewOpen"
      :title="previewTitle"
      :poster-url="previewPosterUrl"
      :description="previewDescription"
      :meta="previewMeta"
      :loading="previewLoading"
      :adding="previewAdding"
      :error="previewError"
      @add="addPreviewToLibrary"
      @close="closePreview"
    />
  </main>
</template>

<style scoped src="../styles/shared/mediaDetail.css"></style>

<style scoped>
.resume-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin: -6px 0 16px;
  font-size: 0.8rem;
  color: var(--ui-dim);
}

.resume-label {
  font-weight: 600;
}

.resume-input {
  width: 70px;
  height: 30px;
  box-sizing: border-box;
  padding: 0 8px;
  background: color-mix(in srgb, var(--ui-text) 6%, transparent);
  border: 1px solid color-mix(in srgb, var(--ui-text) 10%, transparent);
  border-radius: var(--ui-radius-control);
  color: var(--ui-text);
  font: inherit;
}

.resume-input:focus {
  outline: none;
  border-color: var(--ui-accent-line);
}

.resume-bar {
  position: relative;
  width: 120px;
  height: 6px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--ui-text) 10%, transparent);
  overflow: hidden;
}

.resume-bar > span {
  position: absolute;
  inset: 0 auto 0 0;
  background: var(--ui-accent);
}

.resume-hint {
  color: var(--ui-faint);
  font-size: 0.74rem;
}

.error-text {
  color: var(--ui-error);
}

.poster-card-sm:hover .poster-card-sm-art {
  border-color: color-mix(in srgb, var(--ui-accent) 50%, transparent);
}
</style>
