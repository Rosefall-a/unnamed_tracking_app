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
  SMART_FIELD_LABELS,
} from "../state/smartCollections";
import type { SmartField } from "../state/smartCollections";
import type { GameStatus } from "../types/game";
import { useConfirm, usePrompt } from "../state/dialog";

const confirm = useConfirm();
const prompt = usePrompt();

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

async function createCollection() {
  createError.value = null;
  const name = await prompt({
    title: "New collection",
    message:
      'Name your new collection (use "Parent/Child" to nest it under another).',
    confirmLabel: "Create",
  });
  if (!name || !name.trim()) return;
  addCollectionName(name.trim());
}

// one-click starter suggestions, a blank "Create Collection" prompt gives
// no sense of what a collection is even for, until you've made a few
const STARTER_TEMPLATES = [
  "Currently Playing",
  "Backlog Priority",
  "Co-op Games",
];
const showTemplates = ref(false);
function useTemplate(name: string) {
  if (addCollectionName(name)) showTemplates.value = false;
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

// --- smart collections -----------------------------------------------
const STATUS_OPTIONS: GameStatus[] = [
  "playing",
  "beaten",
  "mastered",
  "played",
  "on hold",
  "dropped",
  "backlog",
  "wishlist",
];
const showSmartForm = ref(false);
const smartName = ref("");
const smartField = ref<SmartField>("status");
const smartValue = ref("");
const smartError = ref<string | null>(null);

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

function openSmartForm() {
  smartName.value = "";
  smartField.value = "status";
  smartValue.value = "";
  smartError.value = null;
  showSmartForm.value = true;
}

function createSmartCollection() {
  const name = smartName.value.trim();
  if (!name) {
    smartError.value = "Give it a name.";
    return;
  }
  if (
    collectionSummaries.value.some(
      (c) => c.name.toLowerCase() === name.toLowerCase(),
    )
  ) {
    smartError.value = `"${name}" already exists.`;
    return;
  }
  if (smartField.value !== "favorite" && !smartValue.value.trim()) {
    smartError.value = "Pick a value for the rule.";
    return;
  }
  addSmartCollection({
    name,
    field: smartField.value,
    value: smartValue.value.trim(),
  });
  showSmartForm.value = false;
}

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
          <div class="templates-wrap">
            <button
              type="button"
              class="ui-btn ui-btn-secondary"
              @click="showTemplates = !showTemplates"
            >
              Starter templates
            </button>
            <div v-if="showTemplates" class="templates-dropdown">
              <button
                v-for="t in STARTER_TEMPLATES"
                :key="t"
                type="button"
                class="template-item"
                :disabled="
                  collectionSummaries.some(
                    (c) => c.name.toLowerCase() === t.toLowerCase(),
                  )
                "
                @click="useTemplate(t)"
              >
                {{ t }}
              </button>
            </div>
          </div>
          <button
            type="button"
            class="ui-btn ui-btn-secondary"
            @click="openSmartForm"
          >
            + Smart Collection
          </button>
          <button
            type="button"
            class="ui-btn ui-btn-primary"
            @click="createCollection"
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

    <div
      v-if="showSmartForm"
      class="ui-backdrop"
      @click.self="showSmartForm = false"
    >
      <div class="ui-modal">
        <h3>New smart collection</h3>
        <p class="dialog-hint">
          Membership updates automatically as your library changes.
        </p>
        <label class="field-label">
          Name
          <input
            v-model="smartName"
            type="text"
            class="ui-field"
            placeholder="e.g. Mastered Games"
          />
        </label>
        <label class="field-label">
          Rule
          <select v-model="smartField" class="ui-field">
            <option
              v-for="(label, key) in SMART_FIELD_LABELS"
              :key="key"
              :value="key"
            >
              {{ label }}
            </option>
          </select>
        </label>
        <label v-if="smartField === 'status'" class="field-label">
          Value
          <select v-model="smartValue" class="ui-field">
            <option value="">Select…</option>
            <option v-for="s in STATUS_OPTIONS" :key="s" :value="s">
              {{ s }}
            </option>
          </select>
        </label>
        <label v-else-if="smartField === 'playtime_hours'" class="field-label">
          Hours
          <input
            v-model="smartValue"
            type="number"
            min="0"
            class="ui-field"
            placeholder="e.g. 20"
          />
        </label>
        <label v-else-if="smartField === 'tag'" class="field-label">
          Tag
          <input
            v-model="smartValue"
            type="text"
            list="smart-tag-options"
            class="ui-field"
            placeholder="e.g. RPG"
          />
          <datalist id="smart-tag-options">
            <option v-for="t in tagOptions" :key="t" :value="t" />
          </datalist>
        </label>
        <label v-else-if="smartField === 'source'" class="field-label">
          Source
          <input
            v-model="smartValue"
            type="text"
            list="smart-source-options"
            class="ui-field"
            placeholder="e.g. Steam"
          />
          <datalist id="smart-source-options">
            <option v-for="s in sourceOptions" :key="s" :value="s" />
          </datalist>
        </label>
        <p v-if="smartError" class="ui-error-box">{{ smartError }}</p>
        <div class="ui-modal-actions">
          <button
            type="button"
            class="ui-btn ui-btn-secondary"
            @click="showSmartForm = false"
          >
            Cancel
          </button>
          <button
            type="button"
            class="ui-btn ui-btn-primary"
            @click="createSmartCollection"
          >
            Create
          </button>
        </div>
      </div>
    </div>
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
.templates-wrap {
  position: relative;
}
.templates-dropdown {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  width: 200px;
  background: var(--ui-popover);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-control);
  padding: 6px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.45);
  z-index: 20;
}
.template-item {
  display: block;
  width: 100%;
  background: none;
  border: none;
  color: var(--ui-text);
  font-family: inherit;
  font-size: 0.85rem;
  text-align: left;
  padding: 8px;
  border-radius: 6px;
  cursor: pointer;
}
.template-item:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.06);
}
.template-item:disabled {
  color: var(--ui-faint);
  cursor: not-allowed;
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
.dialog-hint {
  color: var(--ui-dim);
  font-size: 0.78rem;
  margin: 0 0 16px;
}
.field-label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 0.82rem;
  color: #ccc;
  margin-bottom: 14px;
}
</style>
