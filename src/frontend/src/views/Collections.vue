<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import CollectionCard from "../components/CollectionCard.vue";
import GameTopBar from "../components/GameTopBar.vue";
import SegmentedTabs from "../components/SegmentedTabs.vue";
import type { SegmentOption } from "../components/SegmentedTabs.vue";
import { fetchGames } from "../services/games";
import type { Game } from "../types/game";
import {
  smartCollections,
  addSmartCollection,
  matchesSmartCollection,
  FAVORITES_NAME,
} from "../state/smartCollections";
import CollectionFormModal from "../components/CollectionFormModal.vue";
import type { CollectionFormPayload } from "../components/CollectionFormModal.vue";
import {
  collectionMeta,
  setCollectionOrder,
  updateMeta,
} from "../state/collectionMeta";
import {
  saveCollectionEdit,
  deleteCollectionFully,
} from "../utils/collectionEdit";
import { useConfirm } from "../state/dialog";

const confirm = useConfirm();

type SortBy = "custom" | "name" | "count";
type KindFilter = "all" | "manual" | "smart";

const router = useRouter();

const games = ref<Game[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);
const searchQuery = ref("");
const sortBy = ref<SortBy>("custom");
const kindFilter = ref<KindFilter>("all");

// Empty collections (no games assigned yet) have nowhere to live on the
// backend, so they're tracked locally until a game is actually added to them.
const MANUAL_COLLECTIONS_KEY = "manualCollections";
const manualCollectionNames = ref<string[]>(loadManualCollections());

function loadManualCollections(): string[] {
  try {
    const raw = localStorage.getItem(MANUAL_COLLECTIONS_KEY);
    return raw ? (JSON.parse(raw) as string[]) : [];
  } catch {
    return [];
  }
}

function saveManualCollections() {
  localStorage.setItem(
    MANUAL_COLLECTIONS_KEY,
    JSON.stringify(manualCollectionNames.value),
  );
}

const createError = ref<string | null>(null);

function addCollectionName(trimmed: string): boolean {
  const alreadyExists = collectionSummaries.value.some(
    (c) => c.name.toLowerCase() === trimmed.toLowerCase(),
  );
  if (alreadyExists) {
    createError.value = `"${trimmed}" already exists.`;
    return false;
  }
  createError.value = null;
  manualCollectionNames.value.push(trimmed);
  saveManualCollections();
  return true;
}

const showCreate = ref(false);
function onCreate(payload: CollectionFormPayload) {
  createError.value = null;
  if (payload.smart) {
    addSmartCollection({
      name: payload.name,
      field: payload.smart.field,
      value: payload.smart.value,
    });
  } else if (!addCollectionName(payload.name)) {
    showCreate.value = false;
    return;
  }
  updateMeta(payload.name, {
    description: payload.description ?? undefined,
  });
  showCreate.value = false;
  router.push(`/collections/${encodeURIComponent(payload.name)}`);
}

async function loadGames() {
  loading.value = true;
  try {
    games.value = await fetchGames();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to load games";
  } finally {
    loading.value = false;
  }
}

onMounted(loadGames);

interface CollectionSummary {
  name: string;
  games: Game[];
  isSmart?: boolean;
  // kept by the app (Favorites): can't be edited or deleted
  isSystem?: boolean;
  description: string | null;
  pinned: boolean;
  position: number;
}

// which game's cover represents each collection, set from CollectionDetail.vue's
// "Cover" picker, keyed by collection name since collections have no
// backend row of their own to hang this off
function loadCoverPicks(): Record<string, string> {
  try {
    const raw = localStorage.getItem("collectionCoverPicks");
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

// description, pin and place in "My order" are kept locally per name
function detailsOf(name: string) {
  const meta = collectionMeta.value[name] ?? {};
  return {
    description: meta.description ?? null,
    pinned: meta.pinned === true,
    position: meta.position ?? Number.MAX_SAFE_INTEGER,
  };
}

const collectionSummaries = computed<CollectionSummary[]>(() => {
  const map = new Map<string, Game[]>();
  for (const g of games.value) {
    for (const c of g.collections) {
      if (!map.has(c)) map.set(c, []);
      map.get(c)!.push(g);
    }
  }
  for (const name of manualCollectionNames.value) {
    if (!map.has(name)) map.set(name, []);
  }
  const coverPicks = loadCoverPicks();
  const manual = Array.from(map.entries()).map(([name, list]) => {
    const pickedId = coverPicks[name];
    const pickedIndex = pickedId
      ? list.findIndex((g) => g.id === pickedId)
      : -1;
    const orderedGames =
      pickedIndex > 0
        ? [
            list[pickedIndex],
            ...list.slice(0, pickedIndex),
            ...list.slice(pickedIndex + 1),
          ]
        : list;
    return { name, games: orderedGames, ...detailsOf(name) };
  });
  const smart = smartCollections.value.map((rule) => ({
    name: rule.name,
    games: games.value.filter((g) => matchesSmartCollection(g, rule)),
    isSmart: true,
    ...detailsOf(rule.name),
  }));
  // Favorites is always there, unless the user has a collection by that name
  const userHasFavorites =
    map.has(FAVORITES_NAME) ||
    smartCollections.value.some((c) => c.name === FAVORITES_NAME);
  const system = userHasFavorites
    ? []
    : [
        {
          name: FAVORITES_NAME,
          games: games.value.filter((g) => g.favorite),
          isSmart: true,
          isSystem: true,
          ...detailsOf(FAVORITES_NAME),
        },
      ];
  return [...manual, ...smart, ...system];
});

const filteredCollections = computed(() => {
  const q = searchQuery.value.trim().toLowerCase();
  let result = collectionSummaries.value;
  if (kindFilter.value === "smart") result = result.filter((c) => c.isSmart);
  if (kindFilter.value === "manual") result = result.filter((c) => !c.isSmart);
  if (q) {
    result = result.filter((c) => c.name.toLowerCase().includes(q));
  }
  // pinned collections always come first, then the chosen sort within each
  return [...result].sort((a, b) => {
    const pin = Number(b.pinned) - Number(a.pinned);
    if (pin) return pin;
    if (sortBy.value === "count") return b.games.length - a.games.length;
    if (sortBy.value === "custom") return inMyOrder(a, b);
    return a.name.localeCompare(b.name);
  });
});

function inMyOrder(a: CollectionSummary, b: CollectionSummary): number {
  return (
    a.position - b.position ||
    Number(!!b.isSystem) - Number(!!a.isSystem) ||
    a.name.localeCompare(b.name)
  );
}
const myOrder = computed(() =>
  [...collectionSummaries.value].sort(
    (a, b) => Number(b.pinned) - Number(a.pinned) || inMyOrder(a, b),
  ),
);
// moving cards only makes sense when every collection is in view, in your own order
const reorderable = computed(
  () => sortBy.value === "custom" && !filtering.value,
);

function togglePin(name: string) {
  const current = collectionMeta.value[name]?.pinned === true;
  updateMeta(name, { pinned: !current });
}

// pinned collections and the rest are ordered separately
function groupOf(name: string): CollectionSummary[] {
  const pinned = collectionSummaries.value.find((c) => c.name === name)?.pinned;
  return myOrder.value.filter((c) => c.pinned === !!pinned);
}
function canMove(name: string, direction: -1 | 1): boolean {
  const group = groupOf(name);
  const at = group.findIndex((c) => c.name === name);
  return at + direction >= 0 && at + direction < group.length;
}
function moveCollection(name: string, direction: -1 | 1) {
  const group = groupOf(name);
  const at = group.findIndex((c) => c.name === name);
  const to = at + direction;
  if (at < 0 || to < 0 || to >= group.length) return;
  const swapped = [...group];
  [swapped[at], swapped[to]] = [swapped[to], swapped[at]];
  const pinned = group[0].pinned;
  const pinnedGroup = pinned ? swapped : myOrder.value.filter((c) => c.pinned);
  const rest = pinned ? myOrder.value.filter((c) => !c.pinned) : swapped;
  setCollectionOrder([...pinnedGroup, ...rest].map((c) => c.name));
}

// ---- edit / delete ----
const editingName = ref<string | null>(null);
const editingInfo = computed(() => {
  const c = collectionSummaries.value.find((x) => x.name === editingName.value);
  if (!c) return null;
  const rule = smartCollections.value.find((r) => r.name === c.name);
  return {
    name: c.name,
    description: c.description,
    smart: rule ? { field: rule.field, value: rule.value } : null,
  };
});
function editCollection(name: string) {
  editingName.value = name;
}
async function onEditSave(payload: CollectionFormPayload) {
  const target = collectionSummaries.value.find(
    (c) => c.name === editingName.value,
  );
  editingName.value = null;
  if (!target) return;
  try {
    await saveCollectionEdit({
      oldName: target.name,
      payload,
      smartId: smartCollections.value.find((r) => r.name === target.name)?.id,
      members: target.games,
    });
    manualCollectionNames.value = loadManualCollections();
  } catch (e) {
    error.value =
      e instanceof Error ? e.message : "Failed to save the collection.";
  }
  await loadGames();
}
async function deleteCollection(name: string) {
  const target = collectionSummaries.value.find((c) => c.name === name);
  if (!target) return;
  const rule = smartCollections.value.find((r) => r.name === name);
  const ok = await confirm({
    message: rule
      ? `Delete "${name}"? This only removes the rule, no games are affected.`
      : `Delete "${name}"? This removes it from every game, no games are deleted.`,
    confirmLabel: "Delete collection",
    danger: true,
  });
  if (!ok) return;
  try {
    await deleteCollectionFully({
      name,
      members: target.games,
      smartId: rule?.id,
    });
    manualCollectionNames.value = loadManualCollections();
  } catch (e) {
    error.value =
      e instanceof Error ? e.message : "Failed to delete the collection.";
  }
  await loadGames();
}

// dragging a card onto another one of the same group puts it in that place;
// pinned and other collections stay apart
const dragName = ref<string | null>(null);
const dropOn = ref<string | null>(null);
function onDrop(targetName: string) {
  const from = dragName.value;
  dragName.value = dropOn.value = null;
  if (!from || from === targetName) return;
  const moving = myOrder.value.find((c) => c.name === from);
  if (!moving) return;
  const group = myOrder.value.filter((c) => c.pinned === moving.pinned);
  if (!group.some((c) => c.name === targetName)) return;
  const rest = group.filter((c) => c.name !== from);
  rest.splice(
    group.findIndex((c) => c.name === targetName),
    0,
    moving,
  );
  const pinnedGroup = moving.pinned
    ? rest
    : myOrder.value.filter((c) => c.pinned);
  const others = moving.pinned ? myOrder.value.filter((c) => !c.pinned) : rest;
  setCollectionOrder([...pinnedGroup, ...others].map((c) => c.name));
}

const smartCount = computed(
  () => collectionSummaries.value.filter((c) => c.isSmart).length,
);
const kindOptions = computed<SegmentOption[]>(() => [
  { value: "all", label: "All", count: collectionSummaries.value.length },
  {
    value: "manual",
    label: "Manual",
    count: collectionSummaries.value.length - smartCount.value,
  },
  { value: "smart", label: "Smart", count: smartCount.value },
]);
const filtering = computed(
  () => searchQuery.value.trim() !== "" || kindFilter.value !== "all",
);

function openCollection(name: string) {
  router.push(`/collections/${encodeURIComponent(name)}`);
}

// options offered by the create dialog's rule builder
const sourceOptions = computed(() => {
  const set = new Set<string>();
  for (const g of games.value) if (g.source) set.add(g.source);
  return [...set].sort();
});
const tagOptions = computed(() => {
  const set = new Set<string>();
  for (const g of games.value) for (const t of g.tags) set.add(t);
  return [...set].sort();
});
</script>

<template>
  <main class="ui-page">
    <GameTopBar active="collections" />

    <div class="ui-content">
      <div class="ui-head">
        <h1>Collections</h1>
        <div class="header-actions">
          <input
            v-model="searchQuery"
            type="text"
            class="ui-field search-input"
            data-shortcut="search"
            placeholder="Search collections…"
            aria-label="Search collections"
          />
          <select v-model="sortBy" class="ui-field" aria-label="Sort by">
            <option value="custom">My order</option>
            <option value="name">Name</option>
            <option value="count">Most games</option>
          </select>
          <button
            type="button"
            class="ui-btn ui-btn-primary"
            @click="showCreate = true"
            data-tour="collection-create"
            data-shortcut="create"
            title="Create Collection · N"
            aria-keyshortcuts="N"
          >
            + Create Collection
          </button>
        </div>
      </div>

      <div class="filter-row">
        <SegmentedTabs
          :options="kindOptions"
          :model-value="kindFilter"
          aria-label="Filter by kind of collection"
          @update:model-value="kindFilter = $event as KindFilter"
        />
      </div>

      <p v-if="createError" class="ui-error-box">{{ createError }}</p>

      <p v-if="loading" class="ui-state">Loading…</p>
      <p v-else-if="error" class="ui-state error">{{ error }}</p>

      <template v-else>
        <div v-if="filteredCollections.length" class="grid">
          <CollectionCard
            v-for="col in filteredCollections"
            :key="col.name"
            :name="col.name"
            :games="col.games"
            :is-smart="col.isSmart"
            :is-system="col.isSystem"
            :description="col.description"
            :pinned="col.pinned"
            :reorderable="reorderable"
            :can-move-earlier="canMove(col.name, -1)"
            :can-move-later="canMove(col.name, 1)"
            :drag-over="dropOn === col.name && dragName !== col.name"
            @open="openCollection"
            @edit="editCollection"
            @delete="deleteCollection"
            @pin="togglePin"
            @move="moveCollection"
            @dragstart="dragName = $event"
            @dragover="dropOn = $event"
            @drop="onDrop"
            @dragend="dragName = dropOn = null"
          />
        </div>
        <p v-if="!filteredCollections.length && filtering" class="ui-state">
          No collections match the search and filters.
        </p>
        <p v-else-if="!filteredCollections.length" class="ui-state">
          No collections yet: create one above, or use a game's collection
          button to start one. A smart collection fills itself from a rule, like
          every game you've mastered.
        </p>
      </template>
    </div>

    <CollectionFormModal
      v-if="editingInfo"
      :collection="editingInfo"
      :existing-names="collectionSummaries.map((c) => c.name)"
      :tag-options="tagOptions"
      :source-options="sourceOptions"
      @save="onEditSave"
      @close="editingName = null"
    />
    <CollectionFormModal
      v-if="showCreate"
      :collection="null"
      :existing-names="collectionSummaries.map((c) => c.name)"
      :tag-options="tagOptions"
      :source-options="sourceOptions"
      @save="onCreate"
      @close="showCreate = false"
    />
  </main>
</template>

<style scoped>
.header-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}
.search-input {
  width: 220px;
}
.filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 14px;
  margin-bottom: 20px;
}
/* as many 150px+ columns as fit, so cards stay one size at any window width */
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 20px 16px;
}
.grid :deep(.collection-card-wrap) {
  width: auto;
  min-width: 0;
}
</style>
