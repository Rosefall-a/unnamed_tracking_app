<script setup lang="ts">
// The Lists overview grid — deliberately built to match Collections.vue
// (games) field for field: same profile chip, same header-row layout,
// same search/sort controls, same card-collage grid — so a list reads
// as "the same kind of thing" as a game collection, not a separate,
// differently-styled feature.
import { ref, computed, onMounted, watch } from "vue";
import { useRouter } from "vue-router";
import CollectionTile from "../components/CollectionTile.vue";
import SegmentedTabs from "../components/SegmentedTabs.vue";
import type { SegmentOption } from "../components/SegmentedTabs.vue";
import { useConfirm } from "../state/dialog";
import { useCardOrder, kindOptions as kindCounts } from "../utils/useCardOrder";
import { preferences } from "../state/preferences";
import ListFormModal from "../components/ListFormModal.vue";
import MediaTopBar from "../components/MediaTopBar.vue";
import {
  fetchMediaLists,
  createMediaList,
  deleteMediaList,
  updateMediaList,
  saveListOrder,
} from "../services/mediaExtras";
import type { MediaListSummary, SmartRule } from "../services/mediaExtras";

type SortBy = "custom" | "name" | "count" | "recent";
type KindFilter = "all" | "manual" | "smart";

const router = useRouter();

const lists = ref<MediaListSummary[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);
const searchQuery = ref("");
const sortBy = ref<SortBy>(preferences.value.lists_default_sort);
watch(
  () => preferences.value.lists_default_sort,
  (v) => {
    sortBy.value = v;
  },
);
const showCreate = ref(false);
const kindFilter = ref<KindFilter>("all");
const editingList = ref<MediaListSummary | null>(null);
const typeFilter = ref<"all" | "movie" | "tv" | "anime">("all");

async function load() {
  loading.value = true;
  error.value = null;
  try {
    lists.value = await fetchMediaLists();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to load lists.";
  } finally {
    loading.value = false;
  }
}
onMounted(load);

const createError = ref<string | null>(null);
async function onCreate(payload: {
  name: string;
  description: string | null;
  smartRule: SmartRule | null;
}) {
  createError.value = null;
  try {
    const created = await createMediaList(
      payload.name,
      payload.description,
      payload.smartRule,
    );
    lists.value.push(created);
    showCreate.value = false;
    router.push(`/media/collections/${created.id}`);
  } catch (e) {
    showCreate.value = false;
    createError.value =
      e instanceof Error ? e.message : "Failed to create collection.";
  }
}

// pinned lists always come first, then the chosen sort within each group
function inMyOrder(a: MediaListSummary, b: MediaListSummary): number {
  return (
    a.position - b.position ||
    Number(b.isSystem) - Number(a.isSystem) ||
    a.name.localeCompare(b.name)
  );
}
const filtering = computed(
  () =>
    searchQuery.value.trim() !== "" ||
    kindFilter.value !== "all" ||
    typeFilter.value !== "all",
);
// moving lists only makes sense when every list is in view, in your own order
const reorderable = computed(
  () => sortBy.value === "custom" && !filtering.value,
);

const filteredLists = computed(() => {
  const q = searchQuery.value.trim().toLowerCase();
  let result = lists.value;
  if (kindFilter.value === "smart") result = result.filter((l) => l.isSmart);
  if (typeFilter.value !== "all") {
    const t = typeFilter.value;
    result = result.filter((l) => (l.typeCounts[t] ?? 0) > 0);
  }
  if (kindFilter.value === "manual") result = result.filter((l) => !l.isSmart);
  if (q) result = result.filter((l) => l.name.toLowerCase().includes(q));
  return [...result].sort((a, b) => {
    const pin = Number(b.pinned) - Number(a.pinned);
    if (pin) return pin;
    if (sortBy.value === "count") return b.itemCount - a.itemCount;
    if (sortBy.value === "recent") return b.updatedAt - a.updatedAt;
    if (sortBy.value === "custom") return inMyOrder(a, b);
    return a.name.localeCompare(b.name);
  });
});

async function togglePin(id: string) {
  const list = lists.value.find((l) => l.id === id);
  if (!list) return;
  try {
    const updated = await updateMediaList(id, { pinned: !list.pinned });
    lists.value = lists.value.map((l) => (l.id === updated.id ? updated : l));
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to pin the list.";
  }
}

// The new order is applied at once and saved behind it; if saving fails the
// page reloads the real order instead of showing one that is not stored.
async function applyOrder(ordered: MediaListSummary[]) {
  const position = new Map(ordered.map((l, i) => [l.id, i]));
  lists.value = lists.value.map((l) => ({
    ...l,
    position: position.get(l.id) ?? l.position,
  }));
  try {
    await saveListOrder(ordered.map((l) => l.id));
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to save the order.";
    await load();
  }
}
const order = useCardOrder({
  items: lists,
  keyOf: (l) => l.id,
  inMyOrder,
  apply: applyOrder,
});

const smartCount = computed(() => lists.value.filter((l) => l.isSmart).length);
const kindOptions = computed<SegmentOption[]>(() =>
  kindCounts(lists.value.length, smartCount.value),
);
const TYPE_OPTIONS: SegmentOption[] = [
  { value: "all", label: "Any Type" },
  { value: "movie", label: "Movies" },
  { value: "tv", label: "TV Shows" },
  { value: "anime", label: "Anime" },
];
function editList(id: string) {
  editingList.value = lists.value.find((l) => l.id === id) ?? null;
}
async function onEditSave(payload: {
  name: string;
  description: string | null;
  smartRule: SmartRule | null;
}) {
  const target = editingList.value;
  if (!target) return;
  try {
    const updated = await updateMediaList(target.id, {
      name: payload.name,
      description: payload.description,
      ...(target.isSmart ? { smartRule: payload.smartRule } : {}),
    });
    lists.value = lists.value.map((l) => (l.id === updated.id ? updated : l));
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to save the list.";
  } finally {
    editingList.value = null;
  }
}

function openList(id: string) {
  router.push(`/media/collections/${id}`);
}

const confirm = useConfirm();
async function deleteList(id: string) {
  const list = lists.value.find((l) => l.id === id);
  if (!list) return;
  const ok = await confirm({
    message: `Delete "${list.name}"? This doesn't delete the titles in it, just the list.`,
    confirmLabel: "Delete list",
    danger: true,
  });
  if (!ok) return;
  try {
    await deleteMediaList(id);
    lists.value = lists.value.filter((l) => l.id !== id);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to delete list.";
  }
}
</script>

<template>
  <main class="ui-page">
    <MediaTopBar active="lists" />

    <div class="ui-content">
      <div class="ui-head">
        <h1>Collections</h1>
        <div class="header-actions">
          <input
            v-model="searchQuery"
            type="text"
            class="ui-field search-input"
            placeholder="Search collections…"
            aria-label="Search collections"
            data-shortcut="search"
          />
          <select v-model="sortBy" class="ui-field" aria-label="Sort by">
            <option value="custom">My order</option>
            <option value="name">Name</option>
            <option value="count">Most titles</option>
            <option value="recent">Recently updated</option>
          </select>
          <button
            type="button"
            class="ui-btn ui-btn-primary"
            @click="showCreate = true"
            data-shortcut="create"
          >
            + Create Collection
          </button>
        </div>
      </div>

      <div class="filter-row">
        <SegmentedTabs
          :options="kindOptions"
          :model-value="kindFilter"
          aria-label="Filter by kind of list"
          @update:model-value="
            kindFilter = $event as 'all' | 'manual' | 'smart'
          "
        />
        <SegmentedTabs
          :options="TYPE_OPTIONS"
          :model-value="typeFilter"
          aria-label="Filter by type"
          @update:model-value="
            typeFilter = $event as 'all' | 'movie' | 'tv' | 'anime'
          "
        />
      </div>

      <p v-if="createError" class="ui-error-box">{{ createError }}</p>

      <p v-if="loading" class="ui-state">Loading…</p>
      <p v-else-if="error" class="ui-state error">{{ error }}</p>

      <template v-else>
        <div v-if="filteredLists.length" class="grid">
          <CollectionTile
            v-for="list in filteredLists"
            :id="list.id"
            :key="list.id"
            :name="list.name"
            :covers="list.previewPosters"
            :count="list.itemCount"
            count-noun="title"
            noun="list"
            :is-smart="list.isSmart"
            :is-system="list.isSystem"
            :description="list.description"
            :pinned="list.pinned"
            :reorderable="reorderable"
            :can-move-earlier="order.canMove(list.id, -1)"
            :can-move-later="order.canMove(list.id, 1)"
            :drag-over="order.isDropTarget(list.id)"
            @open="openList"
            @edit="editList"
            @delete="deleteList"
            @pin="togglePin"
            @move="order.move"
            @dragstart="order.dragKey.value = $event"
            @dragover="order.dropOn.value = $event"
            @drop="order.drop"
            @dragend="order.endDrag"
          />
        </div>
        <p v-if="!filteredLists.length && filtering" class="ui-state">
          No collections match the search and filters.
        </p>
        <p v-else-if="!filteredLists.length" class="ui-state">
          No collections yet: create one above, or use a movie/TV/anime page's
          collection button to start one. A smart list fills itself from a
          filter, like every anime you rated 9 or higher.
        </p>
        <p v-else-if="sortBy === 'custom' && filtering" class="ui-state">
          Clear the search and filters to move lists around.
        </p>
      </template>
    </div>

    <ListFormModal
      v-if="editingList"
      :list="editingList"
      :existing-names="lists.map((l) => l.name)"
      @save="onEditSave"
      @close="editingList = null"
    />
    <ListFormModal
      v-if="showCreate"
      :list="null"
      :existing-names="lists.map((l) => l.name)"
      @save="onCreate"
      @close="showCreate = false"
    />
  </main>
</template>

<style scoped src="../styles/shared/listIndex.css"></style>

<style scoped></style>
