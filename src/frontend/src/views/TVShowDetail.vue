<script setup lang="ts">
import { usePageTitle } from "../state/pageTitle";
import MyNote from "../components/MyNote.vue";
import MediaDetailHero from "../components/MediaDetailHero.vue";
import MediaDetailTabs from "../components/MediaDetailTabs.vue";
import ExpandableDescription from "../components/ExpandableDescription.vue";
import { ref, computed, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  getTVShow,
  peekTVShow,
  updateTVShow,
  tvShowToInput,
  fetchEpisodes,
  updateEpisode,
  refreshTVShowAiring,
  bulkSetEpisodesWatched,
  fetchTVShowRelations,
  fetchTVShowRecommended,
  fetchTVShows,
  createTVShow,
  searchTVShowMetadata,
} from "../services/tvShows";
import type { RelatedShow } from "../services/tvShows";
import type { TVShow, TVShowStatus } from "../types/tv_show";
import TVShowFormModal from "../components/TVShowFormModal.vue";
import EpisodeList from "../components/EpisodeList.vue";
import RelationsGraph from "../components/RelationsGraph.vue";
import type { ChainNode, BranchNode } from "../components/RelationsGraph.vue";
import MediaPreviewModal from "../components/MediaPreviewModal.vue";
import { useConfirm } from "../state/dialog";
import MediaTopBar from "../components/MediaTopBar.vue";
import BackButton from "../components/BackButton.vue";
import { formatAiringCountdown } from "../utils/countdown";
import { statusBucket, bucketToReal } from "../utils/mediaStatus";

const route = useRoute();
const router = useRouter();
const showId = computed(() => route.params.id as string);

const show = ref<TVShow | null>(null);
usePageTitle(() => show.value?.title);
const loading = ref(true);
const error = ref<string | null>(null);
const showEditModal = ref(false);
const activeTab = ref<"overview" | "episodes" | "related" | "recommended">(
  "overview",
);
const statusBucketModel = computed({
  get: () => statusBucket(show.value?.status ?? "wishlist"),
  set: (bucket: string) => {
    if (!show.value) return;
    show.value.status = bucketToReal(bucket) as TVShowStatus;
  },
});

function goBack() {
  if (window.history.length > 1) {
    router.back();
  } else {
    router.push("/tv");
  }
}

async function load() {
  const cached = peekTVShow(showId.value);
  if (cached) {
    show.value = cached;
    loading.value = false;
  } else {
    loading.value = true;
  }
  try {
    show.value = await getTVShow(showId.value);
  } catch (e) {
    if (!cached)
      error.value = e instanceof Error ? e.message : "Failed to load show.";
  } finally {
    loading.value = false;
  }
}

async function toggleFavorite() {
  if (!show.value) return;
  const next = !show.value.favorite;
  show.value.favorite = next;
  try {
    await updateTVShow(show.value.id, {
      ...tvShowToInput(show.value),
      favorite: next,
    });
  } catch {
    show.value.favorite = !next;
  }
}

async function saveNote(note: string | null) {
  if (!show.value) return;
  const previous = show.value.note;
  show.value.note = note;
  try {
    show.value = await updateTVShow(show.value.id, {
      ...tvShowToInput(show.value),
      note,
    });
  } catch {
    show.value.note = previous;
  }
}

async function onStatusChange() {
  if (!show.value) return;
  const previous = show.value.status;
  try {
    show.value = await updateTVShow(show.value.id, {
      ...tvShowToInput(show.value),
      status: show.value.status,
    });
  } catch {
    show.value.status = previous;
  }
}

function onSaved(saved: TVShow) {
  show.value = saved;
  showEditModal.value = false;
}

function onDeleted() {
  router.push("/tv");
}

const firstAirYear = computed(() =>
  show.value?.firstAirDate ? show.value.firstAirDate.slice(0, 4) : null,
);
const episodeRuntimeLabel = computed(() => {
  const minutes = show.value?.episodeRuntimeMinutes;
  return minutes ? `${minutes}m episodes` : null;
});
const nativeTitleLine = computed(() => {
  if (!show.value) return "";
  const studios = show.value.studios.length
    ? show.value.studios.join(", ")
    : show.value.creators.join(", ");
  return studios ? `Series · ${studios}` : "Series";
});
const heroBackdropUrl = computed(
  () => show.value?.backdropUrl ?? show.value?.posterUrl ?? null,
);

// ---- episodes (every season's real episode list, no season picker) ----
const episodesLoading = ref(false);
const episodesLoaded = ref(false);
const episodesError = ref<string | null>(null);

const totalEpisodeCount = computed(
  () => show.value?.seasons.reduce((sum, s) => sum + s.episodes.length, 0) ?? 0,
);
const watchedEpisodeCount = computed(
  () =>
    show.value?.seasons.reduce(
      (sum, s) => sum + s.episodes.filter((e) => e.watched).length,
      0,
    ) ?? 0,
);

async function loadAllEpisodes() {
  if (!show.value || episodesLoaded.value) return;
  episodesLoading.value = true;
  episodesError.value = null;
  try {
    for (const season of show.value.seasons) {
      if (season.episodes.length > 0) continue;
      show.value = await fetchEpisodes(show.value.id, season.id);
    }
    episodesLoaded.value = true;
  } catch (e) {
    episodesError.value =
      e instanceof Error ? e.message : "Failed to load episodes.";
  } finally {
    episodesLoading.value = false;
  }
}

// Checking off an episode on a show that's still Plan to Watch or On
// Hold almost always means "I'm starting/resuming this" — asked once
// per visit rather than nagging on every single episode, and only when
// moving *toward* watched (unwatching one back never prompts).
const confirm = useConfirm();
const moveToWatchingPromptShown = ref(false);
function maybePromptMoveToWatching() {
  if (!show.value || moveToWatchingPromptShown.value) return;
  const bucket = statusBucket(show.value.status);
  if (bucket !== "plan" && bucket !== "hold") return;
  moveToWatchingPromptShown.value = true;
  void confirm({
    message: "Move this to Watching?",
    confirmLabel: "Move to Watching",
    cancelLabel: "Leave as is",
  }).then(confirmMoveToWatching);
}
async function confirmMoveToWatching(move: boolean) {
  if (!move || !show.value) return;
  const previous = show.value.status;
  show.value.status = "in progress";
  try {
    show.value = await updateTVShow(show.value.id, {
      ...tvShowToInput(show.value),
      status: "in progress",
    });
  } catch {
    if (show.value) show.value.status = previous;
  }
}

// Finishing the last episode of something that isn't still airing almost
// always means "I'm done with this" — offered once per visit, and never
// for a show with more episodes coming (all-watched-so-far isn't finished)
// or one that's already Completed/Dropped.
const moveToCompletedPromptShown = ref(false);
function maybePromptMoveToCompleted(): boolean {
  if (!show.value || moveToCompletedPromptShown.value) return false;
  const bucket = statusBucket(show.value.status);
  if (bucket === "completed" || bucket === "dropped") return false;
  if (show.value.nextEpisodeAirAt || show.value.isAiring) return false;
  const seasons = show.value.seasons;
  if (!seasons.length) return false;
  const allDone = seasons.every(
    (s) =>
      s.episodes.length > 0 &&
      s.episodes.every((e) => e.watched) &&
      (s.episodeCount == null || s.episodes.length >= s.episodeCount),
  );
  if (!allDone) return false;
  moveToCompletedPromptShown.value = true;
  void confirm({
    message: "You've watched every episode. Move this to Completed?",
    confirmLabel: "Move to Completed",
    cancelLabel: "Leave as is",
  }).then(confirmMoveToCompleted);
  return true;
}
async function confirmMoveToCompleted(move: boolean) {
  if (!move || !show.value) return;
  const previous = show.value.status;
  show.value.status = "watched";
  try {
    show.value = await updateTVShow(show.value.id, {
      ...tvShowToInput(show.value),
      status: "watched",
    });
  } catch {
    if (show.value) show.value.status = previous;
  }
}
// The one call every "just marked something watched" path makes: the
// finished-it prompt outranks the started-it prompt when both apply.
function afterMarkedWatched() {
  if (!maybePromptMoveToCompleted()) maybePromptMoveToWatching();
}

async function onSetEpisodeNote(
  seasonId: string,
  episodeId: string,
  note: string | null,
) {
  if (!show.value) return;
  try {
    show.value = await updateEpisode(show.value.id, seasonId, episodeId, {
      note,
    });
  } catch (e) {
    episodesError.value =
      e instanceof Error ? e.message : "Failed to save note.";
  }
}

// ---- airing controls: check now, and a per-show release cadence ----
const refreshingAiring = ref(false);
async function onRefreshAiring() {
  if (!show.value) return;
  refreshingAiring.value = true;
  episodesError.value = null;
  try {
    show.value = await refreshTVShowAiring(show.value.id);
  } catch (e) {
    episodesError.value =
      e instanceof Error ? e.message : "Failed to check the airing schedule.";
  } finally {
    refreshingAiring.value = false;
  }
}
const CADENCE_PRESETS = [
  { days: 1, label: "Daily" },
  { days: 7, label: "Weekly" },
  { days: 14, label: "Every 2 weeks" },
  { days: 30, label: "Monthly" },
];
const cadenceOptions = computed(() => {
  const current = show.value?.airingIntervalDays;
  if (current && !CADENCE_PRESETS.some((p) => p.days === current)) {
    return [
      ...CADENCE_PRESETS,
      { days: current, label: `Every ${current} days` },
    ].sort((a, b) => a.days - b.days);
  }
  return CADENCE_PRESETS;
});
async function onCadenceChange(event: Event) {
  if (!show.value) return;
  const days = Number((event.target as HTMLSelectElement).value);
  try {
    show.value = await updateTVShow(show.value.id, {
      ...tvShowToInput(show.value),
      airingIntervalDays: days === 7 ? null : days,
    });
  } catch (e) {
    episodesError.value =
      e instanceof Error ? e.message : "Failed to save the schedule.";
  }
}

async function onToggleEpisodeWatched(seasonId: string, episodeId: string) {
  if (!show.value) return;
  const season = show.value.seasons.find((s) => s.id === seasonId);
  const episode = season?.episodes.find((e) => e.id === episodeId);
  if (!episode) return;
  const markingWatched = !episode.watched;
  try {
    show.value = await updateEpisode(show.value.id, seasonId, episodeId, {
      watched: markingWatched,
    });
    if (markingWatched) afterMarkedWatched();
  } catch (e) {
    episodesError.value =
      e instanceof Error ? e.message : "Failed to update episode.";
  }
}

async function onBulkSetEpisodesWatched(
  seasonId: string,
  episodeIds: string[],
  watched: boolean,
) {
  if (!show.value) return;
  try {
    show.value = await bulkSetEpisodesWatched(
      show.value.id,
      seasonId,
      episodeIds,
      watched,
    );
    if (watched) afterMarkedWatched();
  } catch (e) {
    episodesError.value =
      e instanceof Error ? e.message : "Failed to update episodes.";
  }
}

async function onSetEpisodeRating(
  seasonId: string,
  episodeId: string,
  rating: number | null,
) {
  if (!show.value) return;
  try {
    show.value = await updateEpisode(show.value.id, seasonId, episodeId, {
      rating,
    });
  } catch (e) {
    episodesError.value =
      e instanceof Error ? e.message : "Failed to update episode.";
  }
}

// ---- related (real TheTVDB franchise data) ----
const relatedLoading = ref(false);
const relatedLoaded = ref(false);
const relatedError = ref<string | null>(null);
const relatedList = ref<RelatedShow[]>([]);
const relatedListName = ref<string | null>(null);
const relatedConfigured = ref(true);

async function loadRelated() {
  if (!show.value || relatedLoaded.value) return;
  relatedLoading.value = true;
  relatedError.value = null;
  try {
    const res = await fetchTVShowRelations(show.value.id);
    relatedList.value = res.related;
    relatedListName.value = res.listName;
    relatedConfigured.value = res.configured;
    relatedLoaded.value = true;
  } catch (e) {
    relatedError.value =
      e instanceof Error ? e.message : "Failed to load related shows.";
  } finally {
    relatedLoading.value = false;
  }
}

const relatedChainNodes = computed<ChainNode[]>(() =>
  show.value
    ? [
        {
          id: "current",
          title: show.value.title,
          type: "This show",
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
    type: "TV",
    sub: r.year ?? "",
    label: relatedListName.value ?? "Related",
    anchorIndex: 0,
  })),
);
function onRelatedBranchClick() {
  // Related titles are TheTVDB entries, not necessarily in this
  // library — nothing to navigate to yet.
}

// ---- recommended (TMDB) ----
const recommendedLoading = ref(false);
const recommendedLoaded = ref(false);
const recommendedError = ref<string | null>(null);
const recommendedList = ref<RelatedShow[]>([]);
const recommendedConfigured = ref(true);

async function loadRecommended() {
  if (!show.value || recommendedLoaded.value) return;
  recommendedLoading.value = true;
  recommendedError.value = null;
  try {
    const res = await fetchTVShowRecommended(show.value.id);
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
const myShows = ref<TVShow[] | null>(null);
async function ensureMyShows(): Promise<TVShow[]> {
  if (!myShows.value) myShows.value = await fetchTVShows();
  return myShows.value;
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
  const mine = await ensureMyShows();
  const existing = mine.find(
    (s) => s.title.trim().toLowerCase() === r.title.trim().toLowerCase(),
  );
  if (existing) {
    router.push(`/tv/${existing.id}`);
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
    const { results } = await searchTVShowMetadata(r.title, 1);
    const match = results.find((m) => m.title === r.title) ?? results[0];
    previewDescription.value = match?.description ?? null;
    previewMeta.value = [
      match?.firstAirDate?.slice(0, 4),
      match?.studios?.[0],
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
    const { results } = await searchTVShowMetadata(previewTitle.value, 1);
    const match =
      results.find((m) => m.title === previewTitle.value) ?? results[0];
    const seasons =
      match?.seasons && match.seasons.length > 0
        ? match.seasons
        : [{ seasonNumber: 1, episodeCount: undefined }];
    const created = await createTVShow({
      title: previewTitle.value,
      description: match?.description ?? null,
      firstAirDate: match?.firstAirDate ?? null,
      episodeRuntimeMinutes: match?.episodeRuntimeMinutes ?? null,
      creators: match?.creators ?? [],
      studios: match?.studios ?? [],
      genres: match?.genres ?? [],
      posterUrl: previewPosterUrl.value,
      backdropUrl: match?.backdropUrl ?? null,
      tmdbScore: match?.tmdbScore ?? null,
      externalId: match?.provider === "TVmaze" ? match.providerId : null,
      status: "wishlist",
      ratingOverall: null,
      startDate: null,
      endDate: null,
      seasons,
    });
    if (myShows.value) myShows.value.push(created);
    router.push(`/tv/${created.id}`);
  } catch (e) {
    previewError.value =
      e instanceof Error ? e.message : "Failed to add to library.";
  } finally {
    previewAdding.value = false;
  }
}

const TABS: {
  key: "overview" | "episodes" | "related" | "recommended";
  label: string;
}[] = [
  { key: "overview", label: "Overview" },
  { key: "episodes", label: "Episodes" },
  { key: "related", label: "Related" },
  { key: "recommended", label: "Recommended" },
];

function setTab(tab: "overview" | "episodes" | "related" | "recommended") {
  activeTab.value = tab;
  if (tab === "episodes") loadAllEpisodes();
  if (tab === "related") loadRelated();
  if (tab === "recommended") loadRecommended();
}

// Vue Router reuses this component instance across /tv/:id → /tv/:id2
// navigations (same matched route), so onMounted alone would never refire —
// watch the param instead, resetting every tab's lazy-loaded state so a
// click-through from Related/Recommended actually shows the new title.
watch(
  showId,
  () => {
    activeTab.value = "overview";
    episodesLoaded.value = false;
    relatedLoaded.value = false;
    recommendedLoaded.value = false;
    previewOpen.value = false;
    moveToWatchingPromptShown.value = false;
    moveToCompletedPromptShown.value = false;
    load();
  },
  { immediate: true },
);
async function onRatingChange(value: number | null) {
  if (!show.value) return;
  const previous = show.value.ratingOverall;
  show.value.ratingOverall = value;
  try {
    show.value = await updateTVShow(show.value.id, {
      ...tvShowToInput(show.value),
      ratingOverall: value,
    });
  } catch {
    if (show.value) show.value.ratingOverall = previous;
  }
}
</script>

<template>
  <main v-if="loading" class="detail loading-state">
    <MediaTopBar active="tv" />
    <p class="loading-text">Loading…</p>
  </main>

  <main v-else-if="error" class="detail error-state">
    <MediaTopBar active="tv" />
    <p class="loading-text">{{ error }}</p>
  </main>

  <main v-else-if="show" class="detail">
    <MediaTopBar active="tv" />

    <BackButton class="back-spot" @click="goBack" />

    <TVShowFormModal
      v-if="showEditModal"
      :show="show"
      @saved="onSaved"
      @deleted="onDeleted"
      @closed="showEditModal = false"
    />

    <MediaDetailHero
      v-model:status="statusBucketModel"
      :title="show.title"
      :native-title="nativeTitleLine"
      :poster-url="show.posterUrl"
      :hero-backdrop-url="heroBackdropUrl"
      :has-backdrop="!!show.backdropUrl"
      :rating-overall="show.ratingOverall"
      :favorite="show.favorite"
      media-type="tv"
      :media-id="show.id"
      :badges="[
        ...(firstAirYear ? [{ text: firstAirYear }] : []),
        ...(episodeRuntimeLabel ? [{ text: episodeRuntimeLabel }] : []),
        ...(show.seasons.length
          ? [
              {
                text: `${show.seasons.length} season${show.seasons.length === 1 ? '' : 's'}`,
                tone: 'good' as const,
              },
            ]
          : []),
      ]"
      @status-change="onStatusChange"
      @rating-change="onRatingChange"
      @edit="showEditModal = true"
      @toggle-favorite="toggleFavorite"
    >
    </MediaDetailHero>

    <MediaDetailTabs :tabs="TABS" :active="activeTab" @select="setTab" />

    <div class="body">
      <div v-if="activeTab === 'overview'" class="tab-panel">
        <div class="meta-grid">
          <div v-if="show.creators.length" class="meta-item">
            <span class="meta-label">Creators</span>
            <span class="meta-value">{{ show.creators.join(", ") }}</span>
          </div>
          <div v-if="show.tmdbScore !== null" class="meta-item">
            <span class="meta-label">Score</span>
            <span class="meta-value accent">{{
              show.tmdbScore.toFixed(1)
            }}</span>
          </div>
          <div v-if="show.ratingOverall !== null" class="meta-item">
            <span class="meta-label">Your score</span>
            <span class="meta-value accent">{{
              show.ratingOverall.toFixed(1)
            }}</span>
          </div>
          <div v-if="show.personalRank !== null" class="meta-item">
            <span class="meta-label">Personal rank</span>
            <span class="meta-value">#{{ show.personalRank }}</span>
          </div>
          <div v-if="show.rewatches > 0" class="meta-item">
            <span class="meta-label">Rewatches</span>
            <span class="meta-value">{{ show.rewatches }}</span>
          </div>
        </div>

        <div v-if="show.genres.length" class="chip-row">
          <span v-for="g in show.genres" :key="g" class="chip primary">{{
            g
          }}</span>
        </div>
        <div v-if="show.tags.length" class="chip-row">
          <span v-for="t in show.tags" :key="t" class="chip">{{ t }}</span>
        </div>
        <ExpandableDescription
          v-if="show.description"
          :text="show.description"
        />
        <MyNote :note="show.note" @save="saveNote" />
      </div>

      <div v-else-if="activeTab === 'episodes'" class="tab-panel">
        <div class="section-heading">
          <h2>Episodes</h2>
          <div class="section-heading-right">
            <button
              v-if="show.externalId"
              type="button"
              class="airing-ctl"
              :disabled="refreshingAiring"
              title="Look up the latest episode and air date now"
              @click="onRefreshAiring"
            >
              {{ refreshingAiring ? "Checking…" : "Check Airing" }}
            </button>
            <select
              v-if="show.nextEpisodeAirAt"
              class="airing-ctl"
              :value="show.airingIntervalDays ?? 7"
              title="How often new episodes air"
              @change="onCadenceChange"
            >
              <option v-for="c in cadenceOptions" :key="c.days" :value="c.days">
                {{ c.label }}
              </option>
            </select>
            <span v-if="show.nextEpisodeAirAt" class="next-episode-banner">
              Episode {{ show.nextEpisodeNumber }} airs in
              {{ formatAiringCountdown(show.nextEpisodeAirAt) }}
            </span>
            <span v-if="totalEpisodeCount" class="episodes-total"
              >{{ watchedEpisodeCount }} / {{ totalEpisodeCount }} watched</span
            >
          </div>
        </div>

        <p v-if="episodesError" class="error-text">{{ episodesError }}</p>
        <p v-if="episodesLoading" class="empty-state">Loading episodes…</p>
        <p v-else-if="!show.seasons.length" class="empty-state">
          No episode data yet.
        </p>

        <template v-else>
          <template v-for="season in show.seasons" :key="season.id">
            <div v-if="show.seasons.length > 1" class="season-divider">
              Season {{ season.seasonNumber
              }}<template v-if="season.name">: {{ season.name }}</template>
            </div>
            <EpisodeList
              class="season-episodes"
              :episodes="season.episodes"
              :loading="false"
              :next-episode-number="show.nextEpisodeNumber"
              :next-episode-air-at="show.nextEpisodeAirAt"
              :episode-count="season.episodeCount"
              :interval-days="show.airingIntervalDays"
              @toggle-watched="
                (epId) => onToggleEpisodeWatched(season.id, epId)
              "
              @set-note="
                (epId, note) => onSetEpisodeNote(season.id, epId, note)
              "
              @set-rating="
                (epId, rating) => onSetEpisodeRating(season.id, epId, rating)
              "
              @bulk-set-watched="
                (epIds, watched) =>
                  onBulkSetEpisodesWatched(season.id, epIds, watched)
              "
            />
          </template>
        </template>
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
          TheTVDB isn't configured yet. A server admin can add an API key under
          Settings &gt; Metadata Sources to enable this.
        </p>
        <p v-else-if="!relatedList.length" class="empty-state">
          Not part of any known franchise on TheTVDB.
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
.error-text {
  color: #e57373;
  font-size: 0.85rem;
  margin: 0 0 12px;
}

.episodes-total {
  font-size: 0.8rem;
  color: #d68a34;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.section-heading-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.airing-ctl {
  height: 30px;
  box-sizing: border-box;
  background: #1a1a1a;
  border: 1px solid #2b2b2b;
  color: #ccc;
  border-radius: 7px;
  padding: 0 12px;
  font-family: inherit;
  font-size: 0.76rem;
  font-weight: 700;
  cursor: pointer;
}

.airing-ctl:hover:not(:disabled) {
  border-color: rgba(214, 138, 52, 0.4);
  color: #d68a34;
}

.airing-ctl:disabled {
  opacity: 0.6;
  cursor: default;
}

.next-episode-banner {
  background: rgba(214, 138, 52, 0.12);
  border: 1px solid rgba(214, 138, 52, 0.35);
  color: #d68a34;
  border-radius: 999px;
  padding: 4px 12px;
  font-size: 0.76rem;
  font-weight: 700;
}

.season-divider {
  margin: 20px 0 10px;
  font-size: 0.78rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #666;
}

.season-divider:first-child {
  margin-top: 0;
}

.season-episodes {
  margin-top: 4px;
}

.poster-card-sm:hover .poster-card-sm-art {
  border-color: rgba(214, 138, 52, 0.5);
}
</style>
