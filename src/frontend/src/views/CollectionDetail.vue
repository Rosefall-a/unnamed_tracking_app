<script setup lang="ts">
// A single collection, laid out like Media's list detail (MediaListDetail):
// header with count and sort, in-grid reorder, a star on a tile to use it as
// the collection's cover, remove, and an Add Games dialog. Smart collections
// show what their rule currently matches, so they have no add, remove or
// reorder, only the rule.
import { computed, ref, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import BackButton from "../components/BackButton.vue";
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
// same "Parent/Child" naming convention as CollectionCard.vue
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
const reorderMode = ref(false);
const dragIndex = ref<number | null>(null);

function toggleReorder() {
  reorderMode.value = !reorderMode.value;
  if (reorderMode.value) sortMode.value = "manual";
}
function moveItem(from: number, to: number) {
  const ids = collectionGames.value.map((g) => g.id);
  if (to < 0 || to >= ids.length || from === to) return;
  const [moved] = ids.splice(from, 1);
  ids.splice(to, 0, moved);
  gameOrder.value = ids;
}
function persistOrder() {
  if (gameOrder.value) saveOrder(gameOrder.value);
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
function nudge(index: number, delta: number) {
  moveItem(index, index + delta);
  persistOrder();
}

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
      await router.replace(`/collections/${encodeURIComponent(payload.name)}`);
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
    router.push("/collections");
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
  router.push("/collections");
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
    router.push("/collections");
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
      <div class="header-row">
        <h1>
          <router-link
            v-if="nestedParent"
            :to="`/collections/${encodeURIComponent(nestedParent)}`"
            class="parent-crumb"
            >{{ nestedParent }} ›</router-link
          >
          {{ collectionDisplayName }}
        </h1>
        <span class="count-badge"
          >{{ collectionGames.length }} game{{
            collectionGames.length === 1 ? "" : "s"
          }}</span
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
          v-if="!isSmart && collectionGames.length > 1"
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
          + Add Games
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
          v-if="!isSmart"
          type="button"
          class="ui-btn ui-btn-danger"
          :disabled="deletingCollection"
          @click="deleteCollection"
        >
          {{ deletingCollection ? "Deleting…" : "Delete" }}
        </button>
        <button
          v-else-if="!isSystem"
          type="button"
          class="ui-btn ui-btn-danger"
          @click="deleteSmartRule"
        >
          Delete
        </button>
      </div>
      <p v-if="description" class="subtitle">{{ description }}</p>
      <p v-if="smartRule" class="subtitle rule-line">
        Matches: {{ describeSmartCollection(smartRule) }}
      </p>
      <p v-if="error" class="ui-state error">{{ error }}</p>
      <p v-if="reorderMode" class="hint">
        Drag games, or use the arrows, to set the order. It saves as you go.
      </p>

      <div v-if="shownGames.length" class="grid">
        <div
          v-for="(game, index) in shownGames"
          :key="game.id"
          class="item-card"
          :class="{ reordering: reorderMode, dragging: dragIndex === index }"
          :draggable="reorderMode"
          @click="openGame(game)"
          @dragstart="onDragStart(index, $event)"
          @dragover.prevent="onDragOver(index)"
          @dragend="onDragEnd"
        >
          <div class="item-cover">
            <div
              class="item-poster"
              :style="
                game.coverImageUrl
                  ? { backgroundImage: `url(${game.coverImageUrl})` }
                  : {}
              "
            ></div>
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
                :disabled="index === shownGames.length - 1"
                title="Move later"
                @click.stop="nudge(index, 1)"
              >
                ›
              </button>
            </div>
            <div v-else class="tile-actions">
              <button
                type="button"
                class="tile-btn star"
                :class="{ on: coverGameId === game.id }"
                :title="
                  coverGameId === game.id
                    ? 'Collection cover'
                    : 'Use as the collection cover'
                "
                @click.stop="setCoverPick(game.id)"
              >
                ★
              </button>
              <button
                v-if="!isSmart"
                type="button"
                class="tile-btn"
                title="Remove from collection"
                @click.stop="removeItem(game)"
              >
                ✕
              </button>
            </div>
          </div>
          <div class="card-info">
            <h3 class="title">{{ game.title }}</h3>
            <span class="pill" :class="statusTone(game.status)">{{
              game.status
            }}</span>
          </div>
        </div>
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

    <div v-if="showAdd" class="ui-backdrop" @click.self="showAdd = false">
      <div class="ui-modal add-modal">
        <h3>Add games</h3>
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
            v-for="g in addResults"
            :key="g.id"
            type="button"
            class="add-row"
            @click="addGame(g)"
          >
            <span
              class="add-thumb"
              :style="
                g.coverImageUrl
                  ? { backgroundImage: `url(${g.coverImageUrl})` }
                  : {}
              "
            ></span>
            <span class="add-title">{{ g.title }}</span>
            <span class="add-kind">{{ g.status }}</span>
            <span class="add-plus">+</span>
          </button>
          <p v-if="!addResults.length" class="ui-state">
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
.parent-crumb {
  color: #666;
  font-size: 1.1rem;
  font-weight: 600;
  text-decoration: none;
  margin-right: 4px;
}
.parent-crumb:hover {
  color: #d68a34;
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
.hint {
  margin: 0 0 4px;
  color: #d68a34;
  font-size: 0.8rem;
}
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
.tile-actions {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 2;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
/* the buttons appear on hover, except the star that is currently the cover,
   which stays lit so the cover is always visible */
.tile-btn {
  opacity: 0;
  transition: opacity 0.15s ease;
}
.item-card:hover .tile-btn,
.tile-btn.on {
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
.tile-btn.star:hover,
.tile-btn.on {
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

/* add-games dialog */
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
