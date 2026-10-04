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
  removeSmartCollection,
  matchesSmartCollection,
} from "../state/smartCollections";
import CollectionFormModal from "../components/CollectionFormModal.vue";
import type { CollectionFormPayload } from "../components/CollectionFormModal.vue";
import { updateMeta } from "../state/collectionMeta";
import { useConfirm } from "../state/dialog";

const confirm = useConfirm();

type SortBy = "name" | "count";
type KindFilter = "all" | "manual" | "smart";

const router = useRouter();

const games = ref<Game[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);
const searchQuery = ref("");
const sortBy = ref<SortBy>("name");
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
    return { name, games: orderedGames };
  });
  const smart = smartCollections.value.map((rule) => ({
    name: rule.name,
    games: games.value.filter((g) => matchesSmartCollection(g, rule)),
    isSmart: true,
  }));
  return [...manual, ...smart];
});

const filteredCollections = computed(() => {
  const q = searchQuery.value.trim().toLowerCase();
  let result = collectionSummaries.value;
  if (kindFilter.value === "smart") result = result.filter((c) => c.isSmart);
  if (kindFilter.value === "manual") result = result.filter((c) => !c.isSmart);
  if (q) {
    result = result.filter((c) => c.name.toLowerCase().includes(q));
  }
  return [...result].sort((a, b) => {
    if (sortBy.value === "count") return b.games.length - a.games.length;
    return a.name.localeCompare(b.name);
  });
});

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

async function deleteSmartCollection(id: string) {
  const ok = await confirm({
    title: "Delete smart collection",
    message:
      "Delete this smart collection? This only removes the rule, no games are affected.",
    confirmLabel: "Delete",
    danger: true,
  });
  if (ok) removeSmartCollection(id);
}
function smartIdForName(name: string): string | undefined {
  return smartCollections.value.find((c) => c.name === name)?.id;
}
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
            placeholder="Search collections…"
            aria-label="Search collections"
          />
          <select v-model="sortBy" class="ui-field" aria-label="Sort by">
            <option value="name">Name</option>
            <option value="count">Most games</option>
          </select>
          <button
            type="button"
            class="ui-btn ui-btn-primary"
            @click="showCreate = true"
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
            @open="openCollection"
            @delete="deleteSmartCollection(smartIdForName(col.name)!)"
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
