<script setup lang="ts">
// A single list. Manual lists can be hand-ordered (drag or arrows), have
// titles added from a picker, and use any title as their cover. Smart
// lists show what their saved filter currently matches, so they have no
// add/remove/reorder, only an editable rule. Item tiles use the
// poster+status-pill look already established across Movies/TV/Anime.
import { localMediaImage } from "../utils/mediaImages";
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
import CollectionDetailHeader from "../components/CollectionDetailHeader.vue";
import CollectionItemTile from "../components/CollectionItemTile.vue";
import CollectionAddDialog from "../components/CollectionAddDialog.vue";
import { useReorderGrid } from "../utils/useReorderGrid";
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
    router.push("/media/collections");
  }
}

// ---- reordering ----
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
const {
  reorderMode,
  dragIndex,
  toggleReorder,
  onDragStart,
  onDragOver,
  onDragEnd,
  nudge,
} = useReorderGrid<MediaListItemVM>({
  getItems: () => list.value?.items ?? [],
  setItems: (next) => {
    if (list.value) list.value.items = next;
  },
  persist: persistOrder,
  onEnter: () => {
    sortMode.value = "manual";
  },
});

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
    router.push("/media/collections");
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
      <CollectionDetailHeader
        v-model:sort-mode="sortMode"
        :title="list.name"
        :count-text="`${list.itemCount} title${list.itemCount === 1 ? '' : 's'}`"
        :is-smart="isSmart"
        :reorder-mode="reorderMode"
        :can-reorder="!isSmart && list.items.length > 1"
        :can-add="!isSmart"
        add-label="+ Add Titles"
        :can-edit="!isSystem"
        :can-delete="!isSystem"
        :deleting="deletingList"
        @reorder="toggleReorder"
        @add="openAdd"
        @edit="showEdit = true"
        @delete="deleteList"
      />
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
        <CollectionItemTile
          v-for="(item, index) in shownItems"
          :key="item.id"
          :title="item.title"
          :poster-url="
            localMediaImage(
              item.mediaType,
              item.mediaId,
              'poster',
              item.posterUrl,
            )
          "
          :status-label="statusBucketLabel(item.status)"
          :status-class="statusBucket(item.status)"
          :index="index"
          :count="shownItems.length"
          :reorder-mode="reorderMode"
          :dragging="dragIndex === index"
          :cover-mark="list.coverMediaId === item.mediaId"
          cover-mark-title="List cover"
          star-title="Use as the list cover"
          remove-title="Remove from list"
          :can-remove="!isSmart"
          @open="openItem(item)"
          @nudge="nudge(index, $event)"
          @cover="setCover(item)"
          @remove="removeItem(item.id)"
          @dragstart="onDragStart(index, $event)"
          @dragover="onDragOver(index)"
          @dragend="onDragEnd"
        />
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

    <CollectionAddDialog
      v-if="showAdd"
      v-model:search="addSearch"
      heading="Add titles"
      :loaded="libraryLoaded"
      :results="
        addResults.map((m) => ({
          key: `${m.mediaType}-${m.mediaId}`,
          title: m.title,
          thumbUrl: m.posterUrl,
          kind: m.mediaType,
        }))
      "
      :error="addError"
      @add="
        (key) =>
          addTitle(
            addResults.find((m) => `${m.mediaType}-${m.mediaId}` === key)!,
          )
      "
      @close="showAdd = false"
    />
  </main>
</template>

<style scoped src="../styles/shared/listDetail.css"></style>

<style scoped>
.type-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 8px 0 0;
}
</style>
