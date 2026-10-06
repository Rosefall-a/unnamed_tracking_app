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
  getAnime,
  peekAnime,
  peekAllAnimes,
  peekAnimeRelations,
  updateAnime,
  animeToInput,
  fetchEpisodes,
  updateEpisode,
  refreshAnimeAiring,
  bulkSetEpisodesWatched,
  fetchAnimeRelations,
  fetchAnimeRecommended,
  fetchAnime,
  createAnime,
  searchAnimeMetadata,
  fetchAnimeMetadataByAnilistId,
} from "../services/anime";
import type {
  RelatedAnime,
  AnimeChainNode,
  AnimeRelationBranch,
  AnimeMetadataResult,
} from "../services/anime";
import type { Anime, AnimeStatus } from "../types/anime";
import AnimeFormModal from "../components/AnimeFormModal.vue";
import EpisodeList from "../components/EpisodeList.vue";
import RelationsGraph from "../components/RelationsGraph.vue";
import type { ChainNode, BranchNode } from "../components/RelationsGraph.vue";
import MediaPreviewModal from "../components/MediaPreviewModal.vue";
import { useConfirm } from "../state/dialog";
import { displayTitle } from "../utils/displayTitle";
import MediaTopBar from "../components/MediaTopBar.vue";
import BackButton from "../components/BackButton.vue";
import {
  STATUS_BUCKETS,
  statusBucket,
  bucketToReal,
} from "../utils/mediaStatus";
import { formatAiringCountdown } from "../utils/countdown";

const route = useRoute();
const router = useRouter();
const showId = computed(() => route.params.id as string);

const show = ref<Anime | null>(null);
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
    show.value.status = bucketToReal(bucket) as AnimeStatus;
  },
});

function goBack() {
  if (window.history.length > 1) {
    router.back();
  } else {
    router.push("/anime");
  }
}

// Runs after the first paint, so secondary requests and the re-renders they
// cause never compete with the page appearing.
function afterFirstPaint(fn: () => void) {
  requestAnimationFrame(() => setTimeout(fn, 0));
}

async function load() {
  // Draw at once from what the library or the last visit already fetched;
  // the fresh copy replaces it a moment later.
  const cached = peekAnime(showId.value);
  if (cached) {
    show.value = cached;
    loading.value = false;
  } else {
    loading.value = true;
  }
  try {
    show.value = await getAnime(showId.value);
    // Needed for the Overview tab's Seasons grid, not just the Related tab
    afterFirstPaint(() => {
      loadRelated();
      loadLibrarySeasons();
    });
  } catch (e) {
    if (!cached)
      error.value = e instanceof Error ? e.message : "Failed to load anime.";
  } finally {
    loading.value = false;
  }
}

async function toggleFavorite() {
  if (!show.value) return;
  const next = !show.value.favorite;
  show.value.favorite = next;
  try {
    await updateAnime(show.value.id, {
      ...animeToInput(show.value),
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
    show.value = await updateAnime(show.value.id, {
      ...animeToInput(show.value),
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
    show.value = await updateAnime(show.value.id, {
      ...animeToInput(show.value),
      status: show.value.status,
    });
  } catch {
    show.value.status = previous;
  }
}

function onSaved(saved: Anime) {
  show.value = saved;
  showEditModal.value = false;
}

function onDeleted() {
  router.push("/anime");
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
  const kind = show.value.format || "Anime";
  const studios = show.value.studios.length
    ? show.value.studios.join(", ")
    : "";
  return studios ? `${kind} · ${studios}` : kind;
});
// the spellings that are not the main name, so ERASED shows
// "Boku dake ga Inai Machi" under it, and the other way round
const otherTitles = computed(() => {
  const s = show.value;
  if (!s) return [];
  const main = displayTitle(s).toLowerCase();
  const seen = new Set<string>([main]);
  const out: string[] = [];
  for (const name of [s.titleEnglish, s.titleRomaji, s.titleNative, s.title]) {
    const key = name?.trim().toLowerCase();
    if (!name || !key || seen.has(key)) continue;
    seen.add(key);
    out.push(name.trim());
  }
  return out;
});
const heroBackdropUrl = computed(() =>
  show.value
    ? localMediaImage(
        "anime",
        show.value.id,
        "hero",
        show.value.backdropUrl ?? show.value.posterUrl,
      )
    : null,
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
    show.value = await updateAnime(show.value.id, {
      ...animeToInput(show.value),
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
    show.value = await updateAnime(show.value.id, {
      ...animeToInput(show.value),
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
    show.value = await refreshAnimeAiring(show.value.id);
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
    show.value = await updateAnime(show.value.id, {
      ...animeToInput(show.value),
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

// ---- related (real AniList relations graph) ----
const relatedLoading = ref(false);
const relatedLoaded = ref(false);
const relatedError = ref<string | null>(null);
const relatedChain = ref<AnimeChainNode[]>([]);
const relatedBranches = ref<AnimeRelationBranch[]>([]);

async function loadRelated() {
  if (!show.value || relatedLoaded.value) return;
  const remembered = peekAnimeRelations(show.value.id);
  if (remembered) {
    relatedChain.value = remembered.chain;
    relatedBranches.value = remembered.branches;
  } else {
    relatedLoading.value = true;
  }
  relatedError.value = null;
  try {
    const res = await fetchAnimeRelations(show.value.id);
    relatedChain.value = res.chain;
    relatedBranches.value = res.branches;
    relatedLoaded.value = true;
  } catch (e) {
    relatedError.value =
      e instanceof Error ? e.message : "Failed to load related anime.";
  } finally {
    relatedLoading.value = false;
  }
}

// ---- every season of this anime, in order ----
// Anime seasons are separate top-level library entries (AniList has no
// "seasons of a show" grouping the way TMDB does for TV), so a franchise
// reads as unrelated titles unless the chain is stitched back together.
// This lists every anime entry in the franchise (never the manga/novel
// side of the graph): seasons in chain order first, then OVAs/specials,
// movies last. Ones already in the library link straight to their page;
// the rest are dimmed and open the same add-preview as the Related tab.
const librarySeasons = ref<Anime[]>([]);
async function loadLibrarySeasons() {
  const known = peekAllAnimes();
  if (known) librarySeasons.value = known;
  try {
    librarySeasons.value = await fetchAnime();
  } catch {
    // non-critical — cards just all show as not-in-library if this fails
  }
}

interface SeasonCard {
  key: string;
  anilistId: number;
  title: string;
  posterUrl: string | null;
  format: string | null;
  year: number | null;
  episodeCount: number | null;
  isCurrent: boolean;
  inLibrary: Anime | null;
}

// 0 = seasons/series, 2 = movies (always last). OVAs, specials, music
// and everything else stay on the Related tab, not here.
function seasonRank(format: string | null): number {
  const t = (format ?? "").toLowerCase();
  if (t.includes("movie")) return 2;
  if (t === "tv" || t === "tv short" || t === "ona") return 0;
  return -1;
}

const allSeasons = computed<SeasonCard[]>(() => {
  if (!show.value) return [];
  const cards: (SeasonCard & { rank: number; order: number })[] = [];
  const matchLibrary = (id: number, title: string): Anime | null =>
    librarySeasons.value.find(
      (a) => a.anilistId && Number(a.anilistId) === id,
    ) ??
    librarySeasons.value.find(
      (a) => a.title.trim().toLowerCase() === title.trim().toLowerCase(),
    ) ??
    null;

  relatedChain.value.forEach((n, i) => {
    cards.push({
      key: `chain-${n.id}`,
      anilistId: n.id,
      title: n.title,
      posterUrl: n.posterUrl,
      format: n.format,
      year: n.year,
      episodeCount: n.episodeCount,
      isCurrent: n.isCurrent,
      inLibrary: n.isCurrent ? null : matchLibrary(n.id, n.title),
      rank: seasonRank(n.format),
      order: i,
    });
  });
  // side entries that are still anime (a spin-off series, a film, an OVA)
  // sort after the main chain within their own rank, oldest first
  const branchAnime = relatedBranches.value
    .filter(
      (b) =>
        !isPrintFormat(b.format) &&
        !(b.format ?? "").toLowerCase().includes("music"),
    )
    .sort((x, y) => (x.year ?? 9999) - (y.year ?? 9999));
  branchAnime.forEach((b, i) => {
    cards.push({
      key: `branch-${b.id}`,
      anilistId: b.id,
      title: b.title,
      posterUrl: b.posterUrl,
      format: b.format,
      year: b.year,
      episodeCount: b.episodeCount,
      isCurrent: b.isCurrent,
      inLibrary: b.isCurrent ? null : matchLibrary(b.id, b.title),
      rank: seasonRank(b.format),
      order: 1000 + i,
    });
  });
  return cards
    .filter((c) => c.rank >= 0 || c.isCurrent)
    .sort((x, y) => x.rank - y.rank || x.order - y.order);
});

function seasonCardMeta(c: SeasonCard): string {
  const parts = [c.format, c.year ? String(c.year) : null];
  if (c.episodeCount) parts.push(`${c.episodeCount} ep`);
  return parts.filter(Boolean).join(" · ");
}
async function onSeasonCardClick(c: SeasonCard) {
  if (c.isCurrent) return;
  if (c.inLibrary) {
    router.push(`/anime/${c.inLibrary.id}`);
    return;
  }
  await onRelatedTitleClick({
    id: c.anilistId,
    title: c.title,
    posterUrl: c.posterUrl,
    format: c.format,
  });
}

// Which branch formats to leave out of the graph/poster-grid — e.g. a
// user who doesn't read manga can hide those branches entirely. Built
// from whatever formats actually appear so the filter row only ever
// shows options that exist for this entry.
const hiddenBranchFormats = ref<Set<string>>(new Set());
const availableBranchFormats = computed(() => {
  const set = new Set<string>();
  for (const b of relatedBranches.value) set.add(b.format ?? "Other");
  return [...set].sort();
});
function toggleBranchFormat(format: string) {
  const next = new Set(hiddenBranchFormats.value);
  if (next.has(format)) next.delete(format);
  else next.add(format);
  hiddenBranchFormats.value = next;
}
// A branch whose own format is hidden is excluded, and so is anything
// chained onto it (its anchor is that now-excluded branch) — otherwise
// hiding a middle link would leave its descendants floating with
// nowhere to anchor.
const visibleBranches = computed(() => {
  const excluded = new Set<number>();
  for (const b of relatedBranches.value) {
    if (hiddenBranchFormats.value.has(b.format ?? "Other")) excluded.add(b.id);
  }
  let changed = true;
  while (changed) {
    changed = false;
    for (const b of relatedBranches.value) {
      if (excluded.has(b.id)) continue;
      if (b.anchorKind === "branch" && excluded.has(b.anchorId)) {
        excluded.add(b.id);
        changed = true;
      }
    }
  }
  return relatedBranches.value.filter((b) => !excluded.has(b.id));
});

// Flat list for the poster grid below the graph — every chain entry
// except the current one, plus every visible branch (adaptation, side
// story, source manga/novel, etc.), each labeled by how it relates.
const relatedList = computed(() => {
  const currentIndex = relatedChain.value.findIndex((n) => n.isCurrent);
  const chainItems = relatedChain.value
    .map((n, i) => ({
      ...n,
      // a movie/OVA opened from the library isn't in the chain at all
      // (currentIndex -1): its chain entries are the main series
      relationLabel:
        currentIndex === -1
          ? "Main series"
          : i < currentIndex
            ? "Prequel"
            : "Sequel",
    }))
    .filter((n) => !n.isCurrent);
  return [...chainItems, ...visibleBranches.value.filter((b) => !b.isCurrent)];
});

const relatedChainNodes = computed<ChainNode[]>(() =>
  relatedChain.value.map((n) => ({
    id: String(n.id),
    title: n.title,
    type: n.format ?? "Anime",
    sub: n.episodeCount ? `${n.episodeCount} Episodes` : "",
    current: n.isCurrent,
    year: n.year,
  })),
);
const relatedBranchNodes = computed<BranchNode[]>(() => {
  const indexById = new Map(relatedChain.value.map((n, i) => [n.id, i]));
  const nodes: BranchNode[] = [];
  for (const b of visibleBranches.value) {
    if (b.anchorKind === "show" && indexById.get(b.anchorId) === undefined)
      continue;
    nodes.push({
      id: String(b.id),
      title: b.title,
      type: b.format ?? "Anime",
      sub: b.episodeCount ? `${b.episodeCount} Episodes` : "",
      label: b.relationLabel,
      anchorIndex: b.anchorKind === "show" ? indexById.get(b.anchorId)! : 0,
      parentBranchId:
        b.anchorKind === "branch" ? String(b.anchorId) : undefined,
      year: b.year,
      current: b.isCurrent,
    });
  }
  return nodes;
});

function findRelatedNode(id: string): RelatedAnime | undefined {
  return (
    relatedChain.value.find((n) => String(n.id) === id) ??
    relatedBranches.value.find((b) => String(b.id) === id)
  );
}
async function onRelatedGraphNodeClick(id: string) {
  const node = findRelatedNode(id);
  if (node) await onRelatedTitleClick(node);
}

// ---- recommended (AniList) ----
const recommendedLoading = ref(false);
const recommendedLoaded = ref(false);
const recommendedError = ref<string | null>(null);
const recommendedList = ref<RelatedAnime[]>([]);

async function loadRecommended() {
  if (!show.value || recommendedLoaded.value) return;
  recommendedLoading.value = true;
  recommendedError.value = null;
  try {
    const res = await fetchAnimeRecommended(show.value.id);
    recommendedList.value = res.recommended;
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
const myAnime = ref<Anime[] | null>(null);
async function ensureMyAnime(): Promise<Anime[]> {
  if (!myAnime.value) myAnime.value = await fetchAnime();
  return myAnime.value;
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

// Manga/novel/one-shot/doujinshi relation branches (the source material a
// TV/movie adaptation is based on) aren't anime and have no AniList "type:
// ANIME" entry to search for — letting them through "+ Add to Library"
// either silently creates a bogus anime row (null format/episode data) or
// matches an unrelated anime that happens to share the title. Blocked at
// the point of adding rather than filtered out of the graph/list entirely,
// since they're still useful to see as a relation.
function isPrintFormat(format: string | null): boolean {
  const t = (format ?? "").toLowerCase();
  return (
    t.includes("manga") ||
    t.includes("novel") ||
    t.includes("doujin") ||
    t.includes("one shot")
  );
}

function posterMeta(r: RelatedAnime): string {
  const parts = [r.format, r.year ? String(r.year) : null];
  if (r.episodeCount) parts.push(`${r.episodeCount} ep`);
  return parts.filter(Boolean).join(" · ");
}

const previewFormat = ref<string | null>(null);
const previewAnilistId = ref<number | null>(null);

// Preferred over a fresh title search whenever the clicked item already
// carries a real AniList id (every Related/Recommended item does) — a
// text search can miss or mismatch an unusual/long title (e.g. "STEEL
// BALL RUN JoJo's Bizarre Adventure 2nd - 3rd STAGE"), silently creating
// a library entry with null format/episode data. Falls back to a title
// search only if the id lookup itself comes back empty.
async function lookupMetadata(
  anilistId: number | null,
  title: string,
): Promise<AnimeMetadataResult | null> {
  if (anilistId) {
    const byId = await fetchAnimeMetadataByAnilistId(anilistId);
    if (byId) return byId;
  }
  const { results } = await searchAnimeMetadata(title, 1);
  return results.find((m) => m.title === title) ?? results[0] ?? null;
}

async function onRelatedTitleClick(r: {
  id: number;
  title: string;
  posterUrl: string | null;
  format?: string | null;
}) {
  const mine = await ensureMyAnime();
  const existing = mine.find(
    (a) => a.title.trim().toLowerCase() === r.title.trim().toLowerCase(),
  );
  if (existing) {
    router.push(`/anime/${existing.id}`);
    return;
  }
  previewOpen.value = true;
  previewLoading.value = false;
  previewError.value = null;
  previewTitle.value = r.title;
  previewPosterUrl.value = r.posterUrl;
  previewDescription.value = null;
  previewMeta.value = [];
  previewFormat.value = r.format ?? null;
  previewAnilistId.value = r.id;
  if (isPrintFormat(r.format ?? null)) {
    previewMeta.value = [r.format ?? "Print"].filter((v): v is string => !!v);
    previewError.value = `"${r.title}" is ${r.format?.toLowerCase() ?? "print media"}, not an anime, so it can't be added to your anime list.`;
    return;
  }
  previewLoading.value = true;
  try {
    const match = await lookupMetadata(r.id, r.title);
    previewDescription.value = match?.description ?? null;
    previewMeta.value = [
      match?.firstAirDate?.slice(0, 4),
      match?.format,
    ].filter((v): v is string => !!v);
  } catch (e) {
    previewError.value =
      e instanceof Error ? e.message : "Failed to load a preview.";
  } finally {
    previewLoading.value = false;
  }
}

async function addPreviewToLibrary() {
  if (isPrintFormat(previewFormat.value)) return;
  previewAdding.value = true;
  previewError.value = null;
  try {
    const match = await lookupMetadata(
      previewAnilistId.value,
      previewTitle.value,
    );
    const created = await createAnime({
      title: previewTitle.value,
      description: match?.description ?? null,
      firstAirDate: match?.firstAirDate ?? null,
      episodeRuntimeMinutes: match?.episodeRuntimeMinutes ?? null,
      studios: match?.studios ?? [],
      genres: match?.genres ?? [],
      posterUrl: previewPosterUrl.value,
      backdropUrl: match?.backdropUrl ?? null,
      format: match?.format ?? null,
      anilistScore: match?.anilistScore ?? null,
      malScore: match?.malScore ?? null,
      externalId: match?.malId ?? null,
      anilistId: match?.provider === "AniList" ? match.providerId : null,
      status: "wishlist",
      ratingOverall: null,
      startDate: null,
      endDate: null,
      seasons: [{ seasonNumber: 1, episodeCount: match?.episodeCount ?? null }],
    });
    if (myAnime.value) myAnime.value.push(created);
    router.push(`/anime/${created.id}`);
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

// Vue Router reuses this component instance across /anime/:id → /anime/:id2
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
    show.value = await updateAnime(show.value.id, {
      ...animeToInput(show.value),
      ratingOverall: value,
    });
  } catch {
    if (show.value) show.value.ratingOverall = previous;
  }
}
</script>

<template>
  <main v-if="loading" class="detail loading-state">
    <MediaTopBar active="anime" />
    <p class="loading-text">Loading…</p>
  </main>

  <main v-else-if="error" class="detail error-state">
    <MediaTopBar active="anime" />
    <p class="loading-text">{{ error }}</p>
  </main>

  <main v-else-if="show" class="detail">
    <MediaTopBar active="anime" />

    <BackButton class="back-spot" @click="goBack" />

    <AnimeFormModal
      v-if="showEditModal"
      :show="show"
      @saved="onSaved"
      @deleted="onDeleted"
      @closed="showEditModal = false"
    />

    <MediaDetailHero
      v-model:status="statusBucketModel"
      :title="displayTitle(show)"
      :native-title="nativeTitleLine"
      :poster-url="localMediaImage('anime', show.id, 'poster', show.posterUrl)"
      :hero-backdrop-url="heroBackdropUrl"
      :has-backdrop="!!show.backdropUrl"
      :rating-overall="show.ratingOverall"
      :favorite="show.favorite"
      media-type="anime"
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
      bright-native-title
      @status-change="onStatusChange"
      @rating-change="onRatingChange"
      @edit="showEditModal = true"
      @toggle-favorite="toggleFavorite"
    >
      <template #subtitle>
        <div v-if="otherTitles.length" class="other-titles">
          {{ otherTitles.join(" · ") }}
        </div>
      </template>
    </MediaDetailHero>

    <MediaDetailTabs :tabs="TABS" :active="activeTab" @select="setTab" />

    <div class="body">
      <div v-if="activeTab === 'overview'" class="tab-panel">
        <div class="meta-grid">
          <div v-if="show.studios.length" class="meta-item">
            <span class="meta-label">Studios</span>
            <span class="meta-value">{{ show.studios.join(", ") }}</span>
          </div>
          <div v-if="show.anilistScore !== null" class="meta-item">
            <span class="meta-label">AniList score</span>
            <span class="meta-value accent">{{
              show.anilistScore.toFixed(1)
            }}</span>
          </div>
          <div v-if="show.malScore !== null" class="meta-item">
            <span class="meta-label">MAL score</span>
            <span class="meta-value">{{ show.malScore.toFixed(1) }}</span>
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
          <router-link
            v-for="g in show.genres"
            :key="g"
            class="chip primary chip-link"
            :to="{ path: '/anime', query: { genre: g } }"
            :title="`All anime tagged ${g}`"
            >{{ g }}</router-link
          >
        </div>
        <div v-if="show.tags.length" class="chip-row">
          <span v-for="t in show.tags" :key="t" class="chip">{{ t }}</span>
        </div>
        <ExpandableDescription
          v-if="show.description"
          :text="show.description"
        />
        <MyNote :note="show.note" @save="saveNote" />

        <div v-if="allSeasons.length > 1" class="seasons-section">
          <h3 class="seasons-heading">
            Seasons
            <span class="seasons-count">{{ allSeasons.length }}</span>
          </h3>
          <div class="seasons-grid">
            <button
              v-for="c in allSeasons"
              :key="c.key"
              type="button"
              class="season-card"
              :class="{
                current: c.isCurrent,
                missing: !c.isCurrent && !c.inLibrary,
              }"
              :disabled="c.isCurrent"
              :title="c.title"
              @click="onSeasonCardClick(c)"
            >
              <span
                class="season-poster"
                :style="
                  c.posterUrl ? { backgroundImage: `url(${c.posterUrl})` } : {}
                "
              >
                <span v-if="c.isCurrent" class="season-flag now">Viewing</span>
                <span v-else-if="!c.inLibrary" class="season-flag add"
                  >+ Add</span
                >
              </span>
              <span class="season-title">{{ c.title }}</span>
              <span class="season-meta">{{ seasonCardMeta(c) }}</span>
              <span
                v-if="c.inLibrary"
                class="pill"
                :class="statusBucket(c.inLibrary.status)"
                >{{
                  STATUS_BUCKETS.find(
                    (s) => s.key === statusBucket(c.inLibrary!.status),
                  )?.label
                }}</span
              >
            </button>
          </div>
        </div>
      </div>

      <div v-else-if="activeTab === 'episodes'" class="tab-panel">
        <div class="section-heading">
          <h2>Episodes</h2>
          <div class="section-heading-right">
            <button
              v-if="show.anilistId"
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
        <p v-else-if="!relatedList.length" class="empty-state">
          No known relations on AniList.
        </p>
        <template v-else>
          <div v-if="availableBranchFormats.length" class="format-filter">
            <span class="format-filter-label">Show:</span>
            <button
              v-for="format in availableBranchFormats"
              :key="format"
              type="button"
              class="format-chip"
              :class="{ off: hiddenBranchFormats.has(format) }"
              @click="toggleBranchFormat(format)"
            >
              {{ format }}
            </button>
          </div>
          <RelationsGraph
            :chain-nodes="relatedChainNodes"
            :branch-nodes="relatedBranchNodes"
            @chain-click="onRelatedGraphNodeClick"
            @branch-click="onRelatedGraphNodeClick"
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
              <div class="poster-card-sm-meta">{{ posterMeta(r) }}</div>
              <div v-if="r.relationLabel" class="poster-card-sm-tag">
                {{ r.relationLabel }}
              </div>
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
            <div class="poster-card-sm-meta">{{ posterMeta(r) }}</div>
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
.other-titles {
  margin: -8px 0 14px;
  font-size: 0.9rem;
  color: #b0b0b0;
  text-shadow: 0 2px 12px rgba(0, 0, 0, 0.6);
}

.seasons-section {
  margin-top: 28px;
  padding-top: 20px;
  border-top: 1px solid #202020;
}

.seasons-heading {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 14px;
  font-size: 0.9rem;
  font-weight: 800;
  color: #f2f2f2;
}

.seasons-count {
  font-size: 0.72rem;
  font-weight: 700;
  color: #999;
  background: rgba(255, 255, 255, 0.06);
  padding: 2px 9px;
  border-radius: 999px;
}

.seasons-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(118px, 1fr));
  gap: 16px 14px;
}

.season-card {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
  padding: 0;
  background: none;
  border: none;
  text-align: left;
  color: inherit;
  font-family: inherit;
  cursor: pointer;
}

.season-card:disabled {
  cursor: default;
}

.season-poster {
  position: relative;
  display: block;
  width: 100%;
  aspect-ratio: 2 / 3;
  border-radius: 8px;
  background-color: #1c1c1c;
  background-size: cover;
  background-repeat: no-repeat;
  background-origin: border-box;
  background-clip: border-box;
  background-position: center;
  border: 1px solid transparent;
  overflow: hidden;
  transition:
    transform 0.25s cubic-bezier(0.22, 1, 0.36, 1),
    border-color 0.15s ease;
}

.season-card:not(:disabled):hover .season-poster {
  transform: translateY(-3px);
  border-color: rgba(214, 138, 52, 0.5);
}

.season-card.current .season-poster {
  border: 2px solid #d68a34;
}

.season-card.missing .season-poster {
  opacity: 0.5;
  filter: saturate(0.6);
}

.season-card.missing:hover .season-poster {
  opacity: 0.85;
}

.season-flag {
  position: absolute;
  left: 6px;
  bottom: 6px;
  font-size: 0.62rem;
  font-weight: 800;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 3px 8px;
  border-radius: 999px;
}

.season-flag.now {
  background: #d68a34;
  color: #14100a;
}

.season-flag.add {
  background: rgba(20, 20, 20, 0.85);
  color: #ddd;
}

.season-title {
  font-size: 0.78rem;
  font-weight: 700;
  color: #f2f2f2;
  line-height: 1.25;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.season-meta {
  font-size: 0.68rem;
  color: #8a8a8a;
}

.pill {
  align-self: flex-start;
  display: inline-flex;
  align-items: center;
  font-size: 0.66rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  padding: 3px 9px;
  border-radius: 999px;
}

.pill.watching {
  background: rgba(214, 138, 52, 0.16);
  color: #d68a34;
}

.pill.completed {
  background: rgba(111, 191, 115, 0.16);
  color: #6fbf73;
}

.pill.hold {
  background: rgba(123, 167, 217, 0.16);
  color: #7ba7d9;
}

.pill.dropped {
  background: rgba(217, 111, 111, 0.16);
  color: #d96f6f;
}

.pill.plan {
  background: rgba(157, 140, 217, 0.16);
  color: #9d8cd9;
}

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

.poster-card-sm-tag {
  margin-top: 2px;
  font-size: 0.66rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: #d68a34;
}

.format-filter {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.format-filter-label {
  font-size: 0.76rem;
  color: #777;
}

.format-chip {
  font-size: 0.72rem;
  font-weight: 600;
  color: #d68a34;
  background: rgba(214, 138, 52, 0.14);
  border: 1px solid rgba(214, 138, 52, 0.35);
  border-radius: 999px;
  padding: 4px 12px;
  cursor: pointer;
}

.format-chip:hover {
  background: rgba(214, 138, 52, 0.22);
}

.format-chip.off {
  color: #666;
  background: transparent;
  border-color: #2a2a2a;
  text-decoration: line-through;
}
</style>
