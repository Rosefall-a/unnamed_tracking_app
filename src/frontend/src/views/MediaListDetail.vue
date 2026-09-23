<script setup lang="ts">
// A single list. Manual lists can be hand-ordered (drag or arrows), have
// titles added from a picker, and use any title as their cover. Smart
// lists show what their saved filter currently matches, so they have no
// add/remove/reorder, only an editable rule. Item tiles use the
// poster+status-pill look already established across Movies/TV/Anime.
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  fetchMediaListDetail,
  addToMediaList,
  removeFromMediaList,
  reorderMediaList,
  updateMediaList,
  deleteMediaList,
} from "../services/mediaExtras";
import type {
  MediaListDetail,
  MediaListItemVM,
  MediaType,
  SmartRule,
} from "../services/mediaExtras";
import ListFormModal from "../components/ListFormModal.vue";
import BackButton from "../components/BackButton.vue";
import MediaTopBar from "../components/MediaTopBar.vue";
import {
  STATUS_BUCKETS,
  statusBucket,
  statusBucketLabel,
} from "../utils/mediaStatus";
import { useConfirm } from "../state/dialog";
import { fetchMovies } from "../services/movies";
import { fetchTVShows } from "../services/tvShows";
import { fetchAnime } from "../services/anime";
import { displayTitle } from "../utils/displayTitle";

const route = useRoute();
const router = useRouter();
const listId = computed(() => route.params.id as string);

const list = ref<MediaListDetail | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);

async function load() {
  loading.value = true;
  error.value = null;
  try {
    list.value = await fetchMediaListDetail(listId.value);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to load list.";
  } finally {
    loading.value = false;
  }
}
watch(listId, load, { immediate: true });

const isSmart = computed(() => list.value?.isSmart ?? false);
const isSystem = computed(() => list.value?.isSystem ?? false);

// ---- filter by type ----
const typeFilter = ref<"all" | MediaType>("all");
const typeCounts = computed(() => list.value?.typeCounts ?? {});
const presentTypes = computed(() =>
  (["movie", "tv", "anime"] as MediaType[]).filter(
    (t) => (typeCounts.value[t] ?? 0) > 0,
  ),
);
const TYPE_LABEL: Record<MediaType, string> = {
  movie: "Movies",
  tv: "TV Shows",
  anime: "Anime",
};

// ---- sorting (view only; "manual" is the stored order) ----
type SortMode = "manual" | "title" | "status";
const sortMode = ref<SortMode>("manual");
watch(isSmart, (smart) => {
  // a smart list has no stored order, so "manual" would just be its
  // built-in title sort
  if (smart && sortMode.value === "manual") sortMode.value = "title";
});
const STATUS_ORDER = STATUS_BUCKETS.map((s) => s.key as string);
const shownItems = computed<MediaListItemVM[]>(() => {
  const all = list.value?.items ?? [];
  const items =
    typeFilter.value === "all"
      ? all
      : all.filter((i) => i.mediaType === typeFilter.value);
  if (sortMode.value === "manual") return items;
  const copy = [...items];
  if (sortMode.value === "title")
    copy.sort((a, b) => a.title.localeCompare(b.title));
  else
    copy.sort(
      (a, b) =>
        STATUS_ORDER.indexOf(statusBucket(a.status)) -
        STATUS_ORDER.indexOf(statusBucket(b.status)),
    );
  return copy;
});

// ---- removing ----
async function removeItem(itemId: string) {
  if (!list.value) return;
  try {
    await removeFromMediaList(list.value.id, itemId);
    list.value.items = list.value.items.filter((i) => i.id !== itemId);
    list.value.itemCount -= 1;
  } catch (e) {
    error.value =
      e instanceof Error ? e.message : "Failed to remove from list.";
  }
}

function openItem(item: { mediaType: string; mediaId: string }) {
  if (reorderMode.value) return;
  const base =
    item.mediaType === "movie"
      ? "/movies"
      : item.mediaType === "tv"
        ? "/tv"
        : "/anime";
  router.push(`${base}/${item.mediaId}`);
}

function goBack() {
  if (window.history.length > 1) {
    router.back();
  } else {
    router.push("/lists");
  }
}

// ---- reordering ----
const reorderMode = ref(false);
const dragIndex = ref<number | null>(null);

function toggleReorder() {
  reorderMode.value = !reorderMode.value;
  if (reorderMode.value) sortMode.value = "manual";
}
async function persistOrder() {
  if (!list.value) return;
  try {
    await reorderMediaList(
      list.value.id,
      list.value.items.map((i) => i.id),
    );
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to save the order.";
    await load();
  }
}
function moveItem(from: number, to: number) {
  if (!list.value || to < 0 || to >= list.value.items.length || from === to)
    return;
  const items = [...list.value.items];
  const [moved] = items.splice(from, 1);
  items.splice(to, 0, moved);
  list.value.items = items;
}
function onDragStart(index: number, event: DragEvent) {
  dragIndex.value = index;
  if (event.dataTransfer) event.dataTransfer.effectAllowed = "move";
}
function onDragOver(index: number) {
  if (dragIndex.value === null || dragIndex.value === index) return;
  moveItem(dragIndex.value, index);
  dragIndex.value = index;
}
function onDragEnd() {
  if (dragIndex.value !== null) persistOrder();
  dragIndex.value = null;
}
async function nudge(index: number, delta: number) {
  moveItem(index, index + delta);
  await persistOrder();
}

// ---- cover ----
async function setCover(item: MediaListItemVM) {
  if (!list.value) return;
  try {
    const updated = await updateMediaList(list.value.id, {
      coverMediaId: item.mediaId,
    });
    list.value.coverMediaId = updated.coverMediaId;
    list.value.previewPosters = updated.previewPosters;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to set the cover.";
  }
}

// ---- edit / delete ----
const showEdit = ref(false);
async function onEdit(payload: {
  name: string;
  description: string | null;
  smartRule: SmartRule | null;
}) {
  if (!list.value) return;
  try {
    await updateMediaList(list.value.id, {
      name: payload.name,
      description: payload.description,
      ...(list.value.isSmart ? { smartRule: payload.smartRule } : {}),
    });
    showEdit.value = false;
    await load();
  } catch (e) {
    showEdit.value = false;
    error.value = e instanceof Error ? e.message : "Failed to save the list.";
  }
}

const deletingList = ref(false);
const confirm = useConfirm();
async function deleteList() {
  if (!list.value) return;
  const ok = await confirm({
    message: `Delete "${list.value.name}"? This doesn't delete the titles in it, just the list.`,
    confirmLabel: "Delete list",
    danger: true,
  });
  if (!ok) return;
  deletingList.value = true;
  try {
    await deleteMediaList(list.value.id);
    router.push("/lists");
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to delete list.";
    deletingList.value = false;
  }
}

// ---- describing a smart rule in words ----
const ruleSummary = computed(() => {
  const r = list.value?.smartRule;
  if (!r) return "";
  const parts: string[] = [];
  if (r.mediaTypes?.length) {
    const names: Record<MediaType, string> = {
      movie: "movies",
      tv: "TV shows",
      anime: "anime",
    };
    parts.push(r.mediaTypes.map((t) => names[t]).join(", "));
  }
  if (r.statusBuckets?.length) {
    parts.push(
      r.statusBuckets
        .map((k) => STATUS_BUCKETS.find((s) => s.key === k)?.label ?? k)
        .join(" or "),
    );
  }
  if (r.genre) parts.push(`genre ${r.genre}`);
  if (r.minScore != null) parts.push(`score ${r.minScore}+`);
  if (r.favorite) parts.push("favorites");
  return parts.join(" · ");
});

// ---- adding titles (manual lists) ----
interface PickItem {
  mediaType: MediaType;
  mediaId: string;
  title: string;
  posterUrl: string | null;
}
const showAdd = ref(false);
const library = ref<PickItem[]>([]);
const libraryLoaded = ref(false);
const addSearch = ref("");
const addError = ref<string | null>(null);

async function openAdd() {
  showAdd.value = true;
  addSearch.value = "";
  addError.value = null;
  if (libraryLoaded.value) return;
  try {
    const [movies, shows, anime] = await Promise.all([
      fetchMovies(),
      fetchTVShows(),
      fetchAnime(),
    ]);
    library.value = [
      ...movies.map((m) => ({
        mediaType: "movie" as const,
        mediaId: m.id,
        title: m.title,
        posterUrl: m.posterUrl,
      })),
      ...shows.map((s) => ({
        mediaType: "tv" as const,
        mediaId: s.id,
        title: s.title,
        posterUrl: s.posterUrl,
      })),
      ...anime.map((a) => ({
        mediaType: "anime" as const,
        mediaId: a.id,
        title: displayTitle(a),
        posterUrl: a.posterUrl,
      })),
    ];
    libraryLoaded.value = true;
  } catch (e) {
    addError.value =
      e instanceof Error ? e.message : "Failed to load your library.";
  }
}
const inList = computed(
  () =>
    new Set(
      (list.value?.items ?? []).map((i) => `${i.mediaType}-${i.mediaId}`),
    ),
);
const addResults = computed(() => {
  const q = addSearch.value.trim().toLowerCase();
  return library.value
    .filter((m) => !inList.value.has(`${m.mediaType}-${m.mediaId}`))
    .filter((m) => !q || m.title.toLowerCase().includes(q))
    .sort((a, b) => a.title.localeCompare(b.title))
    .slice(0, 60);
});
async function addTitle(m: PickItem) {
  if (!list.value) return;
  addError.value = null;
  try {
    const item = await addToMediaList(list.value.id, m.mediaType, m.mediaId);
    // a fresh add lands at the end, matching the backend's position
    list.value.items = [...list.value.items, item];
    list.value.itemCount += 1;
  } catch (e) {
    addError.value = e instanceof Error ? e.message : "Failed to add title.";
  }
}
</script>

<template>
  <main class="ui-page">
    <MediaTopBar active="lists" />

    <div v-if="loading || (error && !list)" class="ui-content">
      <p v-if="loading" class="ui-state">Loading…</p>
      <p v-else class="ui-state error">{{ error }}</p>
    </div>

    <div v-else-if="list" class="ui-content">
      <BackButton class="back-spot" @click="goBack" />
      <div class="header-row">
        <h1>{{ list.name }}</h1>
        <span class="count-badge"
          >{{ list.itemCount }} title{{ list.itemCount === 1 ? "" : "s" }}</span
        >
        <span
          v-if="isSmart"
          class="smart-pill"
          title="Fills itself from a filter"
          >Smart</span
        >
        <div class="header-spacer"></div>
        <select
          v-model="sortMode"
          class="ui-field"
          :disabled="reorderMode"
          title="Sort"
        >
          <option v-if="!isSmart" value="manual">Manual order</option>
          <option value="title">Title</option>
          <option value="status">Status</option>
        </select>
        <button
          v-if="!isSmart && list.items.length > 1"
          type="button"
          class="ui-btn ui-btn-secondary"
          :class="{ on: reorderMode }"
          @click="toggleReorder"
        >
          {{ reorderMode ? "Done" : "Reorder" }}
        </button>
        <button
          v-if="!isSmart"
          type="button"
          class="ui-btn ui-btn-primary"
          @click="openAdd"
        >
          + Add Titles
        </button>
        <button
          v-if="!isSystem"
          type="button"
          class="ui-btn ui-btn-secondary"
          @click="showEdit = true"
        >
          Edit
        </button>
        <button
          v-if="!isSystem"
          type="button"
          class="ui-btn ui-btn-danger"
          :disabled="deletingList"
          @click="deleteList"
        >
          {{ deletingList ? "Deleting…" : "Delete" }}
        </button>
      </div>
      <p v-if="list.description" class="subtitle">{{ list.description }}</p>
      <p v-if="isSmart && ruleSummary" class="subtitle rule-line">
        Matches: {{ ruleSummary }}
      </p>
      <p v-if="error" class="ui-state error">{{ error }}</p>
      <div v-if="presentTypes.length > 1" class="type-chips">
        <button
          type="button"
          class="ui-chip"
          :class="{ on: typeFilter === 'all' }"
          @click="typeFilter = 'all'"
        >
          All
        </button>
        <button
          v-for="t in presentTypes"
          :key="t"
          type="button"
          class="ui-chip"
          :class="{ on: typeFilter === t }"
          @click="typeFilter = t"
        >
          {{ TYPE_LABEL[t] }} <span class="n">{{ typeCounts[t] }}</span>
        </button>
      </div>
      <p v-if="reorderMode" class="hint">
        Drag titles, or use the arrows, to set the order. It saves as you go.
      </p>

      <div v-if="shownItems.length" class="grid">
        <div
          v-for="(item, index) in shownItems"
          :key="item.id"
          class="item-card"
          :class="{ reordering: reorderMode, dragging: dragIndex === index }"
          :draggable="reorderMode"
          @click="openItem(item)"
          @dragstart="onDragStart(index, $event)"
          @dragover.prevent="onDragOver(index)"
          @dragend="onDragEnd"
        >
          <div class="item-cover">
            <div
              class="item-poster"
              :style="
                item.posterUrl
                  ? { backgroundImage: `url(${item.posterUrl})` }
                  : {}
              "
            ></div>
            <span
              v-if="list.coverMediaId === item.mediaId"
              class="cover-mark"
              title="List cover"
              >★</span
            >
            <div v-if="reorderMode" class="reorder-arrows">
              <button
                type="button"
                :disabled="index === 0"
                title="Move earlier"
                @click.stop="nudge(index, -1)"
              >
                ‹
              </button>
              <span class="reorder-pos">{{ index + 1 }}</span>
              <button
                type="button"
                :disabled="index === shownItems.length - 1"
                title="Move later"
                @click.stop="nudge(index, 1)"
              >
                ›
              </button>
            </div>
            <div v-else class="tile-actions">
              <button
                type="button"
                class="tile-btn"
                title="Use as the list cover"
                @click.stop="setCover(item)"
              >
                ★
              </button>
              <button
                v-if="!isSmart"
                type="button"
                class="tile-btn"
                title="Remove from list"
                @click.stop="removeItem(item.id)"
              >
                ✕
              </button>
            </div>
          </div>
          <div class="card-info">
            <h3 class="title">{{ item.title }}</h3>
            <span class="pill" :class="statusBucket(item.status)">{{
              statusBucketLabel(item.status)
            }}</span>
          </div>
        </div>
      </div>
      <p v-else-if="isSmart" class="ui-state">
        Nothing matches this list's filter right now. Edit the list to loosen
        it.
      </p>
      <p v-else class="ui-state">
        Nothing in this list yet. Use "+ Add Titles", or the list button on any
        movie, TV or anime page.
      </p>
    </div>

    <ListFormModal
      v-if="showEdit && list"
      :list="list"
      :existing-names="[]"
      @save="onEdit"
      @close="showEdit = false"
    />

    <div v-if="showAdd" class="ui-backdrop" @click.self="showAdd = false">
      <div class="ui-modal add-modal">
        <h3>Add titles</h3>
        <input
          v-model="addSearch"
          type="text"
          class="ui-field"
          placeholder="Search your library…"
          autofocus
        />
        <p v-if="addError" class="ui-error-box">{{ addError }}</p>
        <div class="add-results">
          <button
            v-for="m in addResults"
            :key="`${m.mediaType}-${m.mediaId}`"
            type="button"
            class="add-row"
            @click="addTitle(m)"
          >
            <span
              class="add-thumb"
              :style="
                m.posterUrl ? { backgroundImage: `url(${m.posterUrl})` } : {}
              "
            ></span>
            <span class="add-title">{{ m.title }}</span>
            <span class="add-kind">{{ m.mediaType }}</span>
            <span class="add-plus">+</span>
          </button>
          <p v-if="libraryLoaded && !addResults.length" class="ui-state">
            Nothing left to add{{ addSearch ? " for that search" : "" }}.
          </p>
        </div>
        <div class="ui-modal-actions">
          <button
            type="button"
            class="ui-btn ui-btn-primary"
            @click="showAdd = false"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  </main>
</template>

<style scoped>
.header-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 12px;
  margin-bottom: 8px;
}
.header-spacer {
  flex: 1;
}
.header-row h1 {
  margin: 0 4px 0 0;
  font-size: 1.7rem;
  font-weight: 800;
}
.count-badge {
  color: #9c9c9c;
  font-size: 13px;
  background: rgba(255, 255, 255, 0.06);
  padding: 4px 12px;
  border-radius: 999px;
}
.smart-pill {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #d68a34;
  background: rgba(214, 138, 52, 0.14);
  padding: 4px 10px;
  border-radius: 999px;
}
.subtitle {
  margin: 0 0 8px;
  color: #9c9c9c;
  font-size: 0.88rem;
}
.rule-line {
  color: #b9a37f;
}
.type-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 8px 0 0;
}
.hint {
  margin: 0 0 4px;
  color: #d68a34;
  font-size: 0.8rem;
}
/* same fixed 10-per-row grid as Collections/CollectionDetail */
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 16px;
  margin-top: 24px;
}
.item-card {
  cursor: pointer;
}
.item-card.reordering {
  cursor: grab;
}
.item-card.dragging {
  opacity: 0.4;
}
.item-cover {
  position: relative;
  width: 100%;
  aspect-ratio: 2 / 3;
  border-radius: 10px;
  overflow: hidden;
  background: #1a1a1a;
  transition:
    transform 0.32s cubic-bezier(0.22, 1, 0.36, 1),
    box-shadow 0.32s cubic-bezier(0.22, 1, 0.36, 1);
}
.item-card:hover .item-cover {
  transform: scale(1.07) translateY(-4px);
  box-shadow: 0 24px 56px rgba(0, 0, 0, 0.5);
}
.item-card.reordering:hover .item-cover {
  transform: none;
  box-shadow: none;
}
.item-poster {
  width: 100%;
  height: 100%;
  background-size: cover;
  background-position: center;
  background-color: #1c1c1c;
}
.cover-mark {
  position: absolute;
  left: 8px;
  top: 8px;
  z-index: 2;
  color: #d68a34;
  font-size: 14px;
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.8);
}
.tile-actions {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 2;
  display: flex;
  flex-direction: column;
  gap: 6px;
  opacity: 0;
  transition: opacity 0.15s ease;
}
.item-card:hover .tile-actions {
  opacity: 1;
}
.tile-btn {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: none;
  background: rgba(20, 20, 20, 0.75);
  backdrop-filter: blur(4px);
  color: #ccc;
  font-size: 11px;
  cursor: pointer;
}
.tile-btn:hover {
  color: #e57373;
}
.tile-btn[title^="Use"]:hover {
  color: #d68a34;
}
.reorder-arrows {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px;
  background: linear-gradient(transparent, rgba(0, 0, 0, 0.85));
}
.reorder-arrows button {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: none;
  background: rgba(255, 255, 255, 0.14);
  color: #fff;
  font-size: 15px;
  cursor: pointer;
}
.reorder-arrows button:disabled {
  opacity: 0.3;
  cursor: default;
}
.reorder-pos {
  font-size: 12px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}
.card-info {
  padding: 10px 2px 0;
}
.title {
  margin: 0 0 6px;
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.pill {
  display: inline-flex;
  align-items: center;
  font-size: 10.5px;
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

/* add-titles modal */
.add-results {
  overflow-y: auto;
  min-height: 120px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.add-row {
  display: flex;
  align-items: center;
  gap: 10px;
  background: none;
  border: none;
  border-radius: 8px;
  padding: 6px;
  color: #ddd;
  text-align: left;
  font-family: inherit;
  cursor: pointer;
}
.add-row:hover {
  background: rgba(255, 255, 255, 0.06);
}
.add-thumb {
  width: 30px;
  height: 44px;
  border-radius: 4px;
  background: #262626 center / cover;
  flex-shrink: 0;
}
.add-title {
  flex: 1;
  min-width: 0;
  font-size: 0.86rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.add-kind {
  color: #666;
  font-size: 0.7rem;
  text-transform: uppercase;
}
.add-plus {
  color: #d68a34;
  font-weight: 800;
  font-size: 1.1rem;
  width: 20px;
  text-align: center;
}
.back-spot {
  margin-bottom: 14px;
}
.add-modal {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.add-modal h3 {
  margin: 0;
}
</style>
