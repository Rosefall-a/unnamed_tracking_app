<script setup lang="ts">
// A single collection, laid out like Media's list detail (MediaListDetail):
// header with count and sort, in-grid reorder, a star on a tile to use it as
// the collection's cover, remove, and an Add Games dialog. Smart collections
// show what their rule currently matches, so they have no add, remove or
// reorder, only the rule.
import { computed, ref, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import BackButton from "../components/BackButton.vue";
import CollectionDetailHeader from "../components/CollectionDetailHeader.vue";
import CollectionItemTile from "../components/CollectionItemTile.vue";
import CollectionAddDialog from "../components/CollectionAddDialog.vue";
import { useReorderGrid } from "../utils/useReorderGrid";
import GameTopBar from "../components/GameTopBar.vue";
import {
  fetchGames,
  addGameToCollection,
  removeGameFromCollection,
} from "../services/games";
import type { Game, GameStatus } from "../types/game";
import {
  findSmartCollectionByName,
  matchesSmartCollection,
  describeSmartCollection,
  removeSmartCollection,
  smartCollections,
  FAVORITES_NAME,
  FAVORITES_RULE,
} from "../state/smartCollections";
import CollectionFormModal from "../components/CollectionFormModal.vue";
import type { CollectionFormPayload } from "../components/CollectionFormModal.vue";
import { saveCollectionEdit } from "../utils/collectionEdit";
import { collectionMeta, forgetCollectionKeys } from "../state/collectionMeta";
import { useConfirm } from "../state/dialog";

const confirm = useConfirm();

const route = useRoute();
const router = useRouter();

const games = ref<Game[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

const collectionName = computed(() =>
  decodeURIComponent(route.params.name as string),
);
// same "Parent/Child" naming convention as CollectionTile.vue
const nestedParent = computed(() => {
  const idx = collectionName.value.indexOf("/");
  return idx === -1 ? null : collectionName.value.slice(0, idx);
});
const collectionDisplayName = computed(() => {
  const idx = collectionName.value.indexOf("/");
  return idx === -1
    ? collectionName.value
    : collectionName.value.slice(idx + 1);
});

// custom display order, collections have no order of their own on the
// backend (games.collections is just a flat tag), so this lives alongside
// the cover pick below, keyed the same way
const ORDER_KEY = "collectionGameOrder";
function loadOrders(): Record<string, string[]> {
  try {
    const raw = localStorage.getItem(ORDER_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}
function saveOrder(order: string[]) {
  const orders = loadOrders();
  orders[collectionName.value] = order;
  try {
    localStorage.setItem(ORDER_KEY, JSON.stringify(orders));
  } catch {
    // best-effort, falls back to natural order next time
  }
}

const gameOrder = ref<string[] | null>(
  loadOrders()[collectionName.value] ?? null,
);
watch(collectionName, (name) => {
  gameOrder.value = loadOrders()[name] ?? null;
  coverPickedGameId.value = loadCoverPicks()[name] ?? null;
});

const userRule = computed(() =>
  findSmartCollectionByName(collectionName.value),
);
// Favorites is kept by the app, unless the user has a collection by that name
const isSystem = computed(
  () =>
    collectionName.value === FAVORITES_NAME &&
    !userRule.value &&
    !games.value.some((g) => g.collections.includes(collectionName.value)),
);
const smartRule = computed(
  () => userRule.value ?? (isSystem.value ? FAVORITES_RULE : undefined),
);
const isSmart = computed(() => !!smartRule.value);
const description = computed(
  () => collectionMeta.value[collectionName.value]?.description ?? "",
);

const collectionGames = computed(() => {
  const members = smartRule.value
    ? games.value.filter((g) => matchesSmartCollection(g, smartRule.value!))
    : games.value.filter((g) => g.collections.includes(collectionName.value));
  if (smartRule.value || !gameOrder.value) return members;
  const byId = new Map(members.map((g) => [g.id, g]));
  const ordered: Game[] = [];
  for (const id of gameOrder.value) {
    const g = byId.get(id);
    if (g) {
      ordered.push(g);
      byId.delete(id);
    }
  }
  // any member not in the saved order (newly added since) goes at the end
  return [...ordered, ...byId.values()];
});

// ---- sorting (view only; "manual" is the stored order) ----
type SortMode = "manual" | "title" | "status";
const sortMode = ref<SortMode>("manual");
watch(isSmart, (smart) => {
  if (smart && sortMode.value === "manual") sortMode.value = "title";
});
const STATUS_ORDER: GameStatus[] = [
  "playing",
  "beaten",
  "mastered",
  "played",
  "on hold",
  "dropped",
  "backlog",
  "wishlist",
];
const shownGames = computed<Game[]>(() => {
  if (sortMode.value === "manual") return collectionGames.value;
  const copy = [...collectionGames.value];
  if (sortMode.value === "title")
    copy.sort((a, b) => a.title.localeCompare(b.title));
  else
    copy.sort(
      (a, b) => STATUS_ORDER.indexOf(a.status) - STATUS_ORDER.indexOf(b.status),
    );
  return copy;
});

// the status pill uses Media's five colors, so a game's status maps onto them
function statusTone(status: GameStatus): string {
  if (status === "playing") return "watching";
  if (status === "beaten" || status === "mastered" || status === "played")
    return "completed";
  if (status === "on hold") return "hold";
  if (status === "dropped") return "dropped";
  return "plan";
}

function openGame(game: Game) {
  if (reorderMode.value) return;
  router.push(`/games/${game.id}`);
}

// ---- reordering ----
function persistOrder() {
  if (gameOrder.value) saveOrder(gameOrder.value);
}
const {
  reorderMode,
  dragIndex,
  toggleReorder,
  onDragStart,
  onDragOver,
  onDragEnd,
  nudge,
} = useReorderGrid<Game>({
  getItems: () => collectionGames.value,
  setItems: (next) => {
    gameOrder.value = next.map((g) => g.id);
  },
  persist: persistOrder,
  onEnter: () => {
    sortMode.value = "manual";
  },
});

// ---- cover ----
// which game's cover represents this collection on the Collections grid,
// keyed by collection name, alongside manualCollections' own localStorage
// entry, since collections have no backend row of their own to hang this off
const COLLECTION_COVER_KEY = "collectionCoverPicks";
function loadCoverPicks(): Record<string, string> {
  try {
    const raw = localStorage.getItem(COLLECTION_COVER_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}
const coverPickedGameId = ref<string | null>(
  loadCoverPicks()[collectionName.value] ?? null,
);
function setCoverPick(gameId: string) {
  const picks = loadCoverPicks();
  if (gameId) picks[collectionName.value] = gameId;
  else delete picks[collectionName.value];
  try {
    localStorage.setItem(COLLECTION_COVER_KEY, JSON.stringify(picks));
  } catch {
    // best-effort, the collection just falls back to its default cover collage
  }
  coverPickedGameId.value = gameId || null;
}
// with no pick, the first game is the cover
const coverGameId = computed(
  () => coverPickedGameId.value ?? collectionGames.value[0]?.id ?? null,
);

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

function replaceGame(updated: Game) {
  games.value = games.value.map((g) => (g.id === updated.id ? updated : g));
}

// ---- removing ----
async function removeItem(game: Game) {
  error.value = null;
  try {
    replaceGame(await removeGameFromCollection(game.id, collectionName.value));
  } catch (err) {
    error.value =
      err instanceof Error ? err.message : "Failed to remove from collection.";
  }
}

// ---- adding games (manual collections) ----
const showAdd = ref(false);
const addSearch = ref("");
const addError = ref<string | null>(null);

function openAdd() {
  showAdd.value = true;
  addSearch.value = "";
  addError.value = null;
}
const addResults = computed(() => {
  const q = addSearch.value.trim().toLowerCase();
  return games.value
    .filter((g) => !g.collections.includes(collectionName.value))
    .filter((g) => !q || g.title.toLowerCase().includes(q))
    .sort((a, b) => a.title.localeCompare(b.title))
    .slice(0, 60);
});
async function addGame(game: Game) {
  addError.value = null;
  try {
    replaceGame(await addGameToCollection(game.id, collectionName.value));
  } catch (err) {
    addError.value = err instanceof Error ? err.message : "Failed to add game.";
  }
}

// ---- edit ----
const showEdit = ref(false);
const tagOptions = computed(() => {
  const set = new Set<string>();
  for (const g of games.value) for (const t of g.tags) set.add(t);
  return [...set].sort();
});
const sourceOptions = computed(() => {
  const set = new Set<string>();
  for (const g of games.value) if (g.source) set.add(g.source);
  return [...set].sort();
});
const allNames = computed(() => {
  const names = new Set<string>(smartCollections.value.map((c) => c.name));
  for (const g of games.value) for (const c of g.collections) names.add(c);
  return [...names];
});
const editing = computed(() => ({
  name: collectionName.value,
  description: description.value || null,
  smart: smartRule.value
    ? { field: smartRule.value.field, value: smartRule.value.value }
    : null,
}));
async function onEdit(payload: CollectionFormPayload) {
  const oldName = collectionName.value;
  showEdit.value = false;
  error.value = null;
  try {
    await saveCollectionEdit({
      oldName,
      payload,
      smartId: smartRule.value?.id,
      members: collectionGames.value,
    });
    if (payload.name !== oldName) {
      await router.replace(`/games/collections/${encodeURIComponent(payload.name)}`);
    }
  } catch (err) {
    error.value =
      err instanceof Error ? err.message : "Failed to save the collection.";
  }
  await loadGames();
}

function goBack() {
  if (window.history.length > 1) {
    router.back();
  } else {
    router.push("/games/collections");
  }
}

async function deleteSmartRule() {
  if (!smartRule.value) return;
  const ok = await confirm({
    title: "Delete smart collection",
    message: `Delete the smart collection "${collectionName.value}"? This only removes the rule, no games are affected.`,
    confirmLabel: "Delete",
    danger: true,
  });
  if (!ok) return;
  removeSmartCollection(smartRule.value.id);
  forgetCollectionKeys(collectionName.value);
  router.push("/games/collections");
}

const deletingCollection = ref(false);

async function deleteCollection() {
  const ok = await confirm({
    title: "Delete collection",
    message: `Delete "${collectionName.value}"? This removes it from every game.`,
    confirmLabel: "Delete",
    danger: true,
  });
  if (!ok) return;
  deletingCollection.value = true;
  error.value = null;
  try {
    for (const game of collectionGames.value) {
      await removeGameFromCollection(game.id, collectionName.value);
    }
    forgetCollectionKeys(collectionName.value);
    router.push("/games/collections");
  } catch (err) {
    error.value =
      err instanceof Error ? err.message : "Failed to delete collection";
    // some games may have already been removed from the collection before
    // the failure, refresh so the list reflects what actually happened
    // server-side instead of showing the stale pre-delete membership
    await loadGames();
  } finally {
    deletingCollection.value = false;
  }
}
</script>

<template>
  <main class="ui-page">
    <GameTopBar active="collections" />

    <div v-if="loading" class="ui-content">
      <p class="ui-state">Loading…</p>
    </div>

    <div v-else class="ui-content">
      <BackButton class="back-spot" @click="goBack" />
      <CollectionDetailHeader
        v-model:sort-mode="sortMode"
        :title="collectionDisplayName"
        :crumb="
          nestedParent
            ? {
                label: nestedParent,
                to: `/games/collections/${encodeURIComponent(nestedParent)}`,
              }
            : null
        "
        :count-text="`${collectionGames.length} game${collectionGames.length === 1 ? '' : 's'}`"
        :is-smart="isSmart"
        :reorder-mode="reorderMode"
        :can-reorder="!isSmart && collectionGames.length > 1"
        :can-add="!isSmart"
        add-label="+ Add Games"
        :can-edit="!isSystem"
        :can-delete="!isSystem"
        :deleting="!isSmart && deletingCollection"
        @reorder="toggleReorder"
        @add="openAdd"
        @edit="showEdit = true"
        @delete="isSmart ? deleteSmartRule() : deleteCollection()"
      />
      <p v-if="description" class="subtitle">{{ description }}</p>
      <p v-if="smartRule" class="subtitle rule-line">
        Matches: {{ describeSmartCollection(smartRule) }}
      </p>
      <p v-if="error" class="ui-state error">{{ error }}</p>
      <p v-if="reorderMode" class="hint">
        Drag games, or use the arrows, to set the order. It saves as you go.
      </p>

      <div v-if="shownGames.length" class="grid">
        <CollectionItemTile
          v-for="(game, index) in shownGames"
          :key="game.id"
          :title="game.title"
          :poster-url="game.coverImageUrl"
          :status-label="game.status"
          :status-class="statusTone(game.status)"
          :index="index"
          :count="shownGames.length"
          :reorder-mode="reorderMode"
          :dragging="dragIndex === index"
          :star-on="coverGameId === game.id"
          :star-title="
            coverGameId === game.id
              ? 'Collection cover'
              : 'Use as the collection cover'
          "
          remove-title="Remove from collection"
          :can-remove="!isSmart"
          @open="openGame(game)"
          @nudge="nudge(index, $event)"
          @cover="setCoverPick(game.id)"
          @remove="removeItem(game)"
          @dragstart="onDragStart(index, $event)"
          @dragover="onDragOver(index)"
          @dragend="onDragEnd"
        />
      </div>
      <p v-else-if="isSmart" class="ui-state">
        Nothing matches this collection's rule right now. Games appear here as
        your library changes.
      </p>
      <p v-else class="ui-state">
        Nothing in this collection yet. Use "+ Add Games", or the collection
        button on any game.
      </p>
    </div>

    <CollectionFormModal
      v-if="showEdit"
      :collection="editing"
      :existing-names="allNames"
      :tag-options="tagOptions"
      :source-options="sourceOptions"
      @save="onEdit"
      @close="showEdit = false"
    />

    <CollectionAddDialog
      v-if="showAdd"
      v-model:search="addSearch"
      heading="Add games"
      :results="
        addResults.map((g) => ({
          key: g.id,
          title: g.title,
          thumbUrl: g.coverImageUrl,
          kind: g.status,
        }))
      "
      :error="addError"
      @add="(id) => addGame(addResults.find((g) => g.id === id)!)"
      @close="showAdd = false"
    />
  </main>
</template>

<style scoped src="../styles/shared/listDetail.css"></style>
