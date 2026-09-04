<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import GameCard from '../components/GameCard.vue'
import GameFormModal from '../components/GameFormModal.vue'
import CollectionPickerModal from '../components/CollectionPickerModal.vue'
import { fetchGames, deleteGame, removeGameFromCollection } from '../services/games'
import type { Game } from '../types/game'
import { currentUser } from '../state/auth'

const route = useRoute()
const router = useRouter()

const games = ref<Game[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

const showFormModal = ref(false)
const editingGame = ref<Game | null>(null)

const deletingGame = ref<Game | null>(null)
const deleting = ref(false)
const deleteError = ref<string | null>(null)

const collectionName = computed(() => decodeURIComponent(route.params.name as string))
const collectionGames = computed(() => games.value.filter((g) => g.collections.includes(collectionName.value)))

async function loadGames() {
  loading.value = true
  try {
    games.value = await fetchGames()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load games'
  } finally {
    loading.value = false
  }
}

onMounted(loadGames)

function openEditModal(game: Game) {
  editingGame.value = game
  showFormModal.value = true
}

async function onGameSaved() {
  showFormModal.value = false
  editingGame.value = null
  await loadGames()
}

function onDeleteFromModal(gameId: string) {
  const game = games.value.find((g) => g.id === gameId)
  showFormModal.value = false
  editingGame.value = null
  if (game) requestDelete(game)
}

function requestDelete(game: Game) {
  deletingGame.value = game
  deleteError.value = null
}

async function confirmDelete() {
  if (!deletingGame.value) return
  deleting.value = true
  deleteError.value = null
  try {
    await deleteGame(deletingGame.value.id)
    deletingGame.value = null
    await loadGames()
  } catch (err) {
    deleteError.value = err instanceof Error ? err.message : 'Failed to delete game'
  } finally {
    deleting.value = false
  }
}

const collectionPickerGame = ref<Game | null>(null)

function handleAddToCollection(game: Game) {
  collectionPickerGame.value = game
}

async function onCollectionAdded() {
  await loadGames()
}

function goBack() {
  if (window.history.length > 1) {
    router.back()
  } else {
    router.push('/collections')
  }
}

const deletingCollection = ref(false)
const deleteCollectionError = ref<string | null>(null)

async function deleteCollection() {
  if (!window.confirm(`Delete "${collectionName.value}"? This removes it from every game.`)) return
  deletingCollection.value = true
  deleteCollectionError.value = null
  try {
    for (const game of collectionGames.value) {
      await removeGameFromCollection(game.id, collectionName.value)
    }
    try {
      const raw = localStorage.getItem('manualCollections')
      const names: string[] = raw ? JSON.parse(raw) : []
      localStorage.setItem(
        'manualCollections',
        JSON.stringify(names.filter((n) => n !== collectionName.value)),
      )
    } catch {
      // non-critical — manual-collections cleanup is best-effort
    }
    router.push('/collections')
  } catch (err) {
    deleteCollectionError.value = err instanceof Error ? err.message : 'Failed to delete collection'
  } finally {
    deletingCollection.value = false
  }
}
</script>

<template>
  <main class="collection-detail">
    <button type="button" class="back-arrow-button" title="Back" @click="goBack">
      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M19 12H5" />
        <path d="M12 19l-7-7 7-7" />
      </svg>
    </button>

    <div v-if="currentUser" class="profile-chip">
      <span class="profile-name">{{ currentUser.username }}</span>
      <div class="profile-avatar">{{ currentUser.username.slice(0, 2).toUpperCase() }}</div>
    </div>

    <div class="content">
      <div class="header-row">
        <h1>{{ collectionName }}</h1>
        <span class="count-badge">{{ collectionGames.length }} game{{ collectionGames.length === 1 ? '' : 's' }}</span>
        <div class="header-spacer"></div>
        <button type="button" class="danger-button" :disabled="deletingCollection" @click="deleteCollection">
          {{ deletingCollection ? 'Deleting…' : 'Delete Collection' }}
        </button>
      </div>
      <p v-if="deleteCollectionError" class="error">{{ deleteCollectionError }}</p>

      <p v-if="loading">Loading…</p>
      <p v-else-if="error" class="error">{{ error }}</p>

      <template v-else>
        <div v-if="collectionGames.length" class="grid">
          <GameCard
            v-for="game in collectionGames"
            :key="game.id"
            :game="game"
            @edit="openEditModal"
            @add-to-collection="handleAddToCollection"
          />
        </div>
        <p v-else class="empty-row">No games in this collection.</p>
      </template>

      <CollectionPickerModal
        v-if="collectionPickerGame"
        :game="collectionPickerGame"
        @close="collectionPickerGame = null"
        @added="onCollectionAdded"
      />

      <GameFormModal
        v-if="showFormModal"
        :game="editingGame"
        @close="showFormModal = false"
        @saved="onGameSaved"
        @delete="onDeleteFromModal"
      />

      <div v-if="deletingGame" class="confirm-backdrop" @click.self="deletingGame = null">
        <div class="confirm-dialog">
          <h3>Delete {{ deletingGame.title }}?</h3>
          <p>This can't be undone.</p>
          <div v-if="deleteError" class="confirm-error">{{ deleteError }}</div>
          <div class="confirm-actions">
            <button type="button" class="secondary-button" @click="deletingGame = null">Cancel</button>
            <button type="button" class="danger-button" :disabled="deleting" @click="confirmDelete">
              {{ deleting ? 'Deleting…' : 'Delete' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </main>
</template>

<style scoped>
.collection-detail {
  position: relative;
  padding: 84px 24px 24px;
  font-family: system-ui, sans-serif;
  background: #121212;
  min-height: 100vh;
  color: #fff;
}
.back-arrow-button {
  position: fixed;
  top: 16px;
  left: 62px;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(20, 20, 20, 0.55);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 100;
  transition: background 0.15s ease;
}
.back-arrow-button:hover {
  background: rgba(40, 40, 40, 0.85);
}
.profile-chip {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 100;
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(20, 20, 20, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.14);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  border-radius: 999px;
  padding: 6px 6px 6px 16px;
}
.profile-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #d68a34;
  color: #111;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
}
.profile-name {
  color: #fff;
  font-size: 13px;
  font-weight: 600;
}
.header-row {
  display: flex;
  align-items: baseline;
  gap: 14px;
  margin-bottom: 24px;
}
.header-spacer {
  flex: 1;
}
.header-row h1 {
  margin: 0;
  font-size: 1.6rem;
  font-weight: 700;
}
.count-badge {
  color: #999;
  font-size: 13px;
  background: rgba(255, 255, 255, 0.06);
  padding: 4px 12px;
  border-radius: 999px;
}
/* fixed 10-per-row grid — column width only depends on the container, never
   on how many games there are, so adding one more game just starts filling
   the next row instead of resizing every existing card */
.grid {
  display: grid;
  grid-template-columns: repeat(10, 1fr);
  gap: 16px;
}
.grid :deep(.game-card-wrap) {
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
.confirm-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.65);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 60;
}
.confirm-dialog {
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  border-radius: 12px;
  padding: 22px;
  width: 100%;
  max-width: 360px;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.6);
}
.confirm-dialog h3 {
  margin: 0 0 8px;
}
.confirm-dialog p {
  margin: 0 0 16px;
  color: #aaa;
  font-size: 14px;
}
.confirm-error {
  color: #fca5a5;
  font-size: 13px;
  margin-bottom: 12px;
}
.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
.secondary-button,
.danger-button {
  border: none;
  border-radius: 8px;
  padding: 10px 18px;
  font-weight: 600;
  cursor: pointer;
}
.secondary-button {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}
.danger-button {
  background: #dc2626;
  color: #fff;
}
.danger-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
