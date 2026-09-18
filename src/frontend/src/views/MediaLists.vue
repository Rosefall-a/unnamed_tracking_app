<script setup lang="ts">
// The Lists overview grid — deliberately built to match Collections.vue
// (games) field for field: same profile chip, same header-row layout,
// same search/sort controls, same card-collage grid — so a list reads
// as "the same kind of thing" as a game collection, not a separate,
// differently-styled feature.
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import ListCard from "../components/ListCard.vue";
import ListFormModal from "../components/ListFormModal.vue";
import MediaTopBar from "../components/MediaTopBar.vue";
import {
  fetchMediaLists,
  createMediaList,
  deleteMediaList,
} from "../services/mediaExtras";
import type { MediaListSummary, SmartRule } from "../services/mediaExtras";

type SortBy = "name" | "count" | "recent";

const router = useRouter();

const lists = ref<MediaListSummary[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);
const searchQuery = ref("");
const sortBy = ref<SortBy>("name");
const showCreate = ref(false);

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
    const created = await createMediaList(payload.name, payload.description, payload.smartRule);
    lists.value.push(created);
    showCreate.value = false;
    router.push(`/lists/${created.id}`);
  } catch (e) {
    showCreate.value = false;
    createError.value = e instanceof Error ? e.message : "Failed to create list.";
  }
}

const filteredLists = computed(() => {
  const q = searchQuery.value.trim().toLowerCase();
  let result = lists.value;
  if (q) result = result.filter((l) => l.name.toLowerCase().includes(q));
  return [...result].sort((a, b) => {
    if (sortBy.value === "count") return b.itemCount - a.itemCount;
    if (sortBy.value === "recent") return b.updatedAt - a.updatedAt;
    return a.name.localeCompare(b.name);
  });
});

function openList(id: string) {
  router.push(`/lists/${id}`);
}

async function deleteList(id: string) {
  const list = lists.value.find((l) => l.id === id);
  if (!list) return;
  if (!window.confirm(`Delete "${list.name}"? This doesn't delete the titles in it, just the list.`)) return;
  try {
    await deleteMediaList(id);
    lists.value = lists.value.filter((l) => l.id !== id);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to delete list.";
  }
}
</script>

<template>
  <main class="collections-page">
    <MediaTopBar active="lists" />

    <div class="content">
      <div class="header-row">
        <h1>Lists</h1>
        <div class="header-actions">
          <input
            v-model="searchQuery"
            type="text"
            class="search-input"
            placeholder="Search lists…"
          />
          <select v-model="sortBy" class="filter-select">
            <option value="name">Name</option>
            <option value="count">Most Titles</option>
            <option value="recent">Recently Updated</option>
          </select>
          <button type="button" class="add-button" @click="showCreate = true">
            + Create List
          </button>
        </div>
      </div>

      <p v-if="createError" class="error create-error">{{ createError }}</p>

      <p v-if="loading">Loading…</p>
      <p v-else-if="error" class="error">{{ error }}</p>

      <template v-else>
        <div v-if="filteredLists.length" class="grid">
          <ListCard
            v-for="list in filteredLists"
            :key="list.id"
            :list="list"
            @open="openList"
            @delete="deleteList"
          />
        </div>
        <p v-else class="empty-row">
          No lists yet: create one above, or use a movie/TV/anime page's list
          button to start one. A smart list fills itself from a filter, like
          every anime you rated 9 or higher.
        </p>
      </template>
    </div>

    <ListFormModal
      v-if="showCreate"
      :list="null"
      :existing-names="lists.map((l) => l.name)"
      @save="onCreate"
      @close="showCreate = false"
    />
  </main>
</template>

<style scoped>
.collections-page {
  position: relative;
  font-family: system-ui, sans-serif;
  background: #121212;
  min-height: 100vh;
  color: #fff;
}
.content {
  padding: 24px 24px 24px;
}
.header-row {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}
.header-row h1 {
  margin: 0;
  font-size: 1.6rem;
  font-weight: 700;
}
.header-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}
.search-input,
.filter-select {
  height: 40px;
  box-sizing: border-box;
  background: #111;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  color: #fff;
  padding: 0 14px;
  font: inherit;
  font-size: 13px;
  transition: border-color 0.15s ease;
}
.search-input {
  width: 220px;
}
.search-input:focus,
.filter-select:focus {
  outline: none;
  border-color: #d68a34;
}
.filter-select:hover {
  border-color: #4a4a4a;
}
.filter-select {
  appearance: none;
  -webkit-appearance: none;
  padding-right: 34px;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'><path d='M1 1l4 4 4-4' stroke='%23999' stroke-width='1.5' fill='none' stroke-linecap='round' stroke-linejoin='round'/></svg>");
  background-repeat: no-repeat;
  background-position: right 16px center;
}
.add-button {
  height: 40px;
  box-sizing: border-box;
  background: #d68a34;
  color: #111;
  border: none;
  border-radius: 8px;
  padding: 0 18px;
  font-weight: 600;
  cursor: pointer;
}
/* fixed 10-per-row grid, column width only depends on the container, never
   on how many lists there are, matching Collections.vue's own grid */
.grid {
  display: grid;
  grid-template-columns: repeat(10, 1fr);
  gap: 16px;
}
.grid :deep(.collection-card-wrap) {
  width: auto;
  min-width: 0;
}
.empty-row {
  color: #777;
  font-size: 14px;
}
.error {
  color: #f87171;
}
.create-error {
  font-size: 13px;
  background: rgba(220, 38, 38, 0.1);
  border: 1px solid rgba(220, 38, 38, 0.3);
  border-radius: 8px;
  padding: 8px 12px;
  margin-bottom: 16px;
}
</style>
