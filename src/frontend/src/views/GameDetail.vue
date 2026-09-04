<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  deleteGame,
  deleteGameNote,
  fetchGame,
  fetchGameNote,
  listGameNotes,
  saveGameNote,
  setFavorite,
} from '../services/games'
import type { Achievement, AchievementTier, Game } from '../types/game'
import GameFormModal from '../components/GameFormModal.vue'
import CollectionPickerModal from '../components/CollectionPickerModal.vue'
import { computeScore } from '../utils/scoring'
import { currentUser } from '../state/auth'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const route = useRoute()
const router = useRouter()

function goBackToLibrary() {
  if (window.history.length > 1) {
    router.back()
  } else {
    router.push('/games')
  }
}

const game = ref<Game | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const showEditModal = ref(false)

const deleting = ref(false)
const deleteError = ref<string | null>(null)
const showDeleteConfirm = ref(false)

const noteNames = ref<string[]>([])
const noteMode = ref<'list' | 'view' | 'editor'>('list')
const viewingNoteName = ref<string | null>(null)
const viewingNoteContent = ref('')
const editingNoteName = ref<string | null>(null)
const draftName = ref('')
const draftContent = ref('')
const noteLoading = ref(false)
const noteSaving = ref(false)
const noteError = ref<string | null>(null)

const hasDraft = computed(
  () => editingNoteName.value === null && (draftName.value.trim() !== '' || draftContent.value.trim() !== ''),
)

const renderedNoteHtml = computed(() => marked.parse(viewingNoteContent.value || '') as string)

function startNewNote() {
  if (!hasDraft.value) {
    draftName.value = ''
    draftContent.value = ''
  }
  editingNoteName.value = null
  noteMode.value = 'editor'
}

async function viewNote(noteName: string) {
  if (!game.value) return
  viewingNoteName.value = noteName
  noteLoading.value = true
  noteError.value = null
  try {
    viewingNoteContent.value = await fetchGameNote(game.value.id, noteName)
    noteMode.value = 'view'
  } catch (err) {
    noteError.value = err instanceof Error ? err.message : 'Failed to load note'
  } finally {
    noteLoading.value = false
  }
}

function editFromView() {
  if (!viewingNoteName.value) return
  editingNoteName.value = viewingNoteName.value
  draftName.value = viewingNoteName.value
  draftContent.value = viewingNoteContent.value
  noteMode.value = 'editor'
}

function backToList() {
  noteMode.value = 'list'
  viewingNoteName.value = null
}

async function saveDraft() {
  if (!game.value) return
  const newName = draftName.value.trim()
  if (!newName) {
    noteError.value = 'Enter a note name first.'
    return
  }

  noteSaving.value = true
  noteError.value = null

  try {
    await saveGameNote(game.value.id, newName, draftContent.value)
    // renaming an existing note — the backend has no rename endpoint,
    // so simulate it by creating the new name and deleting the old one
    if (editingNoteName.value && editingNoteName.value !== newName) {
      await deleteGameNote(game.value.id, editingNoteName.value)
    }
    editingNoteName.value = null
    draftName.value = ''
    draftContent.value = ''
    noteMode.value = 'list'
    await loadNotes()
  } catch (err) {
    noteError.value = err instanceof Error ? err.message : 'Failed to save note'
  } finally {
    noteSaving.value = false
  }
}

async function deleteNote(noteName: string) {
  if (!game.value) return

  noteSaving.value = true
  noteError.value = null

  try {
    await deleteGameNote(game.value.id, noteName)
    if (viewingNoteName.value === noteName || editingNoteName.value === noteName) {
      noteMode.value = 'list'
      viewingNoteName.value = null
      editingNoteName.value = null
    }
    await loadNotes()
  } catch (err) {
    noteError.value = err instanceof Error ? err.message : 'Failed to delete note'
  } finally {
    noteSaving.value = false
  }
}

// Steam's "About This Game" section is rich HTML (headers, screenshots,
// gifs) — sanitize it instead of stripping it down to plain text so that
// content survives
const descriptionHtml = computed(() => {
  if (!game.value?.description) return ''
  return DOMPurify.sanitize(game.value.description)
})

async function loadGame(id: string) {
  loading.value = true
  error.value = null
  try {
    game.value = await fetchGame(id)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load game'
  } finally {
    loading.value = false
  }
}

async function onGameSaved() {
  showEditModal.value = false
  await loadGame(route.params.id as string)
}

async function toggleFavorite() {
  if (!game.value) return
  const next = !game.value.favorite
  game.value.favorite = next
  try {
    await setFavorite(game.value.id, next)
  } catch {
    game.value.favorite = !next
  }
}

const showCollectionPicker = ref(false)

async function onCollectionAdded() {
  await loadGame(route.params.id as string)
}

function onDeleteFromModal() {
  showEditModal.value = false
  deleteError.value = null
  showDeleteConfirm.value = true
}

async function confirmDelete() {
  if (!game.value) return
  deleting.value = true
  deleteError.value = null
  try {
    await deleteGame(game.value.id)
    router.push('/games')
  } catch (err) {
    deleteError.value = err instanceof Error ? err.message : 'Failed to delete game'
  } finally {
    deleting.value = false
  }
}

async function loadNotes() {
  if (!game.value) {
    noteNames.value = []
    return
  }
  noteLoading.value = true
  noteError.value = null
  try {
    noteNames.value = await listGameNotes(game.value.id)
  } catch (err) {
    noteError.value = err instanceof Error ? err.message : 'Failed to load notes'
  } finally {
    noteLoading.value = false
  }
}

// re-fetches automatically if you ever navigate from one game's page
// straight to another, not just on the first load
watch(() => route.params.id as string, loadGame, { immediate: true })
watch(() => game.value?.id, () => {
  if (game.value) {
    void loadNotes()
  }
})

const recentActivity = computed(() => {
  if (!game.value) return null
  const dates = game.value.platforms
    .map((p) => p.lastPlayedAt)
    .filter((d): d is string => d !== null)
  return dates.length > 0 ? dates.reduce((latest, d) => (d > latest ? d : latest)) : null
})

const tally = computed(() => (game.value ? computeScore(game.value) : null))

const tabs = ['Overview', 'Achievements', 'Screenshots', 'Clips', 'Saves', 'Docs', 'Notes', 'Stats'] as const
const activeTab = ref<(typeof tabs)[number]>('Overview')

function sortedAchievements(achievements: Achievement[]) {
  return [...achievements].sort((a, b) => {
    if (a.unlockedAt === null && b.unlockedAt === null) return 0
    if (a.unlockedAt === null) return 1
    if (b.unlockedAt === null) return -1
    return b.unlockedAt.localeCompare(a.unlockedAt)
  })
}

function deriveTier(achievement: Achievement): AchievementTier {
  if (achievement.tierOverride) return achievement.tierOverride
  const rarity = achievement.rarityPercent
  if (rarity === null || rarity === undefined) return 'bronze'
  if (rarity <= 20) return 'gold'
  if (rarity <= 50) return 'silver'
  return 'bronze'
}

const isPlatinumEarned = computed(
  () =>
    !!game.value &&
    game.value.achievements.length > 0 &&
    game.value.achievements.every((a) => a.unlockedAt !== null),
)

const trophyCounts = computed(() => {
  const counts = { bronze: 0, silver: 0, gold: 0 }
  if (!game.value) return counts
  for (const a of game.value.achievements) {
    if (a.unlockedAt !== null) counts[deriveTier(a)]++
  }
  return counts
})

function formatUnlockedAt(dateStr: string) {
  const d = new Date(dateStr)
  return `${d.toLocaleDateString()} ${d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}`
}

function formatPlaytime(minutes: number) {
  if (minutes === 0) return 'Not played yet'
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`
}
</script>

<template>
<main v-if="loading" class="detail loading-state">
  <p>Loading…</p>
</main>

<main v-else-if="error" class="detail error-state">
  <p>{{ error }}</p>
</main>

<main v-else-if="game" class="detail">
    <!-- heavily blurred, dimmed copy of the cover image behind the whole page —
         separate from the sharp version used in .hero itself -->
<div class="ambient-bg" :style="{ backgroundImage: `url(${game.bannerImageUrl})` }"></div>

<button type="button" class="back-arrow-button" title="Back" @click="goBackToLibrary">
  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M19 12H5" />
    <path d="M12 19l-7-7 7-7" />
  </svg>
</button>

<div v-if="currentUser" class="profile-chip">
  <span class="profile-name">{{ currentUser.username }}</span>
  <div class="profile-avatar">{{ currentUser.username.slice(0, 2).toUpperCase() }}</div>
</div>

<GameFormModal
  v-if="showEditModal"
  :game="game"
  @close="showEditModal = false"
  @saved="onGameSaved"
  @delete="onDeleteFromModal"
/>

<CollectionPickerModal
  v-if="showCollectionPicker"
  :game="game"
  @close="showCollectionPicker = false"
  @added="onCollectionAdded"
/>

<div v-if="showDeleteConfirm" class="confirm-backdrop" @click.self="showDeleteConfirm = false">
  <div class="confirm-dialog">
    <h3>Delete {{ game.title }}?</h3>
    <p>This can't be undone.</p>
    <div v-if="deleteError" class="confirm-error">{{ deleteError }}</div>
    <div class="confirm-actions">
      <button type="button" class="secondary-button" @click="showDeleteConfirm = false">Cancel</button>
      <button type="button" class="danger-button" :disabled="deleting" @click="confirmDelete">
        {{ deleting ? 'Deleting…' : 'Delete' }}
      </button>
    </div>
  </div>
</div>

<section class="hero" :style="{ backgroundImage: `url(${game.bannerImageUrl})` }">
  <div class="hero-overlay"></div>
  <div class="hero-actions">
    <button
      class="hero-icon-button"
      type="button"
      title="Add to collection"
      @click="showCollectionPicker = true"
    >
      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
      </svg>
    </button>
    <button
      class="hero-icon-button"
      :class="{ active: game.favorite }"
      type="button"
      :title="game.favorite ? 'Remove from favorites' : 'Add to favorites'"
      @click="toggleFavorite"
    >
      <svg viewBox="0 0 24 24" width="16" height="16" :fill="game.favorite ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.6l-1-1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 21l7.8-7.8 1-1a5.5 5.5 0 0 0 0-7.6z" />
      </svg>
    </button>
    <button class="edit-button" type="button" @click="showEditModal = true">Edit</button>
  </div>
  <div class="hero-inner">
    <h1>{{ game.title }}</h1>
    <div class="badges">
      <span class="badge status-badge">{{ game.status }}</span>
      <span v-if="tally" class="badge rating-badge">
        ★ {{ tally.sum.toFixed(1) }}
      </span>
      <span v-if="game.dateAdded" class="badge">
        {{ new Date(game.dateAdded).toLocaleDateString() }}
      </span>
      <span v-if="game.platforms.length" class="badge">{{ game.platforms[0].platform }}</span>
    </div>
  </div>
</section>

    <nav class="tabs">
      <button
        v-for="tab in tabs"
        :key="tab"
        type="button"
        class="tab"
        :class="{ active: activeTab === tab }"
        @click="activeTab = tab"
      >
        {{ tab }}
      </button>
    </nav>

    <section v-if="activeTab === 'Overview'" class="overview">
<div class="overview-main">
<div v-if="descriptionHtml" class="description-wrap">
  <div class="description-html" v-html="descriptionHtml"></div>
</div>

  <div class="rating-breakdown" v-if="game.ratingOverall !== null || game.ratingStory !== null || game.ratingGameplay !== null || game.ratingSound !== null">
    <div v-if="game.ratingOverall !== null" class="rating-item">
      <span class="rating-label">Atmosphere</span>
      <span class="rating-score">★ {{ game.ratingOverall.toFixed(1) }}</span>
    </div>
    <div v-if="game.ratingStory !== null" class="rating-item">
      <span class="rating-label">Story</span>
      <span class="rating-score">★ {{ game.ratingStory.toFixed(1) }}</span>
    </div>
    <div v-if="game.ratingGameplay !== null" class="rating-item">
      <span class="rating-label">Gameplay</span>
      <span class="rating-score">★ {{ game.ratingGameplay.toFixed(1) }}</span>
    </div>
    <div v-if="game.ratingSound !== null" class="rating-item">
      <span class="rating-label">Sound</span>
      <span class="rating-score">★ {{ game.ratingSound.toFixed(1) }}</span>
    </div>
    <div v-if="tally" class="rating-item">
      <span class="rating-label">Score</span>
      <span class="rating-score">{{ tally.sum.toFixed(1) }}</span>
    </div>
  </div>
</div>

<aside class="details-panel">
  <h3 class="panel-title">Details</h3>
  <div class="detail-row">
    <span class="detail-label">Developer</span>
    <span class="detail-value">{{ game.developer ?? '—' }}</span>
  </div>
  <div class="detail-row">
    <span class="detail-label">Publisher</span>
    <span class="detail-value">{{ game.publisher ?? '—' }}</span>
  </div>
  <div class="detail-row">
    <span class="detail-label">Series</span>
    <span class="detail-value">{{ game.series ?? '—' }}</span>
  </div>
  <div v-if="game.releaseDate" class="detail-row">
    <span class="detail-label">Release Date</span>
    <span class="detail-value">{{ new Date(game.releaseDate).toLocaleDateString() }}</span>
  </div>
  <div class="detail-row">
    <span class="detail-label">Date Added</span>
    <span class="detail-value">
      {{ game.dateAdded ? new Date(game.dateAdded).toLocaleDateString() : '—' }}
    </span>
  </div>
  <div class="detail-row">
    <span class="detail-label">Recent Activity</span>
    <span class="detail-value">
      {{ recentActivity ? new Date(recentActivity).toLocaleDateString() : '—' }}
    </span>
  </div>
  <div class="detail-row">
    <span class="detail-label">Platforms</span>
    <ul class="platforms">
      <li v-for="p in game.platforms" :key="p.platform" class="platform-row">
        <div class="platform-line">
          <span class="platform-name">{{ p.platform }}</span>
          <span class="platform-meta">
            {{ formatPlaytime(p.playtimeMinutes) }}<span v-if="p.completionPercent !== null"> · {{ p.completionPercent }}%</span>
          </span>
        </div>
        <div v-if="p.lastPlayedAt" class="platform-last-played">
          last played {{ new Date(p.lastPlayedAt).toLocaleDateString() }}
        </div>
      </li>
    </ul>
  </div>
  <div v-if="game.tags.length" class="detail-row">
    <span class="detail-label">Tags</span>
    <span class="feature-pills">
      <span v-for="tag in game.tags" :key="tag" class="feature-pill">{{ tag }}</span>
    </span>
  </div>
  <div v-if="game.features.length" class="detail-row">
    <span class="detail-label">Features</span>
    <span class="feature-pills">
      <span v-for="f in game.features" :key="f" class="feature-pill">{{ f }}</span>
    </span>
  </div>
  <div v-if="game.source" class="detail-row">
    <span class="detail-label">Source</span>
    <span class="detail-value">{{ game.source }}</span>
  </div>
  <div v-if="game.ageRating" class="detail-row">
    <span class="detail-label">Age Rating</span>
    <span class="detail-value">{{ game.ageRating }}</span>
  </div>
  <div v-if="game.timeToBeatHours" class="detail-row">
    <span class="detail-label">Time to Beat</span>
    <span class="detail-value">{{ game.timeToBeatHours }}h</span>
  </div>
  <div v-if="game.region" class="detail-row">
    <span class="detail-label">Region</span>
    <span class="detail-value">{{ game.region }}</span>
  </div>
  <div v-if="game.language" class="detail-row">
    <span class="detail-label">Language</span>
    <span class="detail-value">{{ game.language }}</span>
  </div>
  <div v-if="game.achievementsProvider" class="detail-row">
    <span class="detail-label">Achievement Tracking</span>
    <span class="detail-value">{{ game.achievementsProvider === 'retroachievements' ? 'RetroAchievements' : 'Native' }}</span>
  </div>
  <div v-if="game.links.length" class="detail-row">
    <span class="detail-label">Links</span>
    <ul class="links-list">
      <li v-for="link in game.links" :key="link.url">
        <a :href="link.url" target="_blank" rel="noopener noreferrer">{{ link.label }}</a>
      </li>
    </ul>
  </div>
  <div
    v-if="game.ownership.format || game.ownership.purchaseDate || game.ownership.price !== null"
    class="detail-row"
  >
    <span class="detail-label">Ownership</span>
    <div class="ownership-info">
      <span v-if="game.ownership.format" class="ownership-format">{{ game.ownership.format }}</span>
      <span v-if="game.ownership.purchaseDate">
        Purchased {{ new Date(game.ownership.purchaseDate).toLocaleDateString() }}
      </span>
      <span v-if="game.ownership.price !== null">
        {{ game.ownership.priceCurrency ?? 'USD' }} {{ game.ownership.price.toFixed(2) }}
      </span>
      <span v-if="game.ownership.condition">{{ game.ownership.condition }}</span>
    </div>
  </div>
  <div v-if="game.folderLocation" class="detail-row">
    <span class="detail-label">Folder</span>
    <span class="detail-value">{{ game.folderLocation }}</span>
  </div>
</aside>
    </section>

<section v-else-if="activeTab === 'Achievements'" class="achievements">
  <div class="achievements-header">
    <h2>Achievements</h2>
    <span class="percent">{{ game.achievementPercent }}%</span>
  </div>

  <div class="trophy-summary">
    <div class="trophy-count">
      <span class="trophy-badge trophy-badge-platinum" :class="{ dim: !isPlatinumEarned }"></span>
      <span>{{ isPlatinumEarned ? 1 : 0 }}</span>
    </div>
    <div class="trophy-count">
      <span class="trophy-badge trophy-badge-gold"></span>
      <span>{{ trophyCounts.gold }}</span>
    </div>
    <div class="trophy-count">
      <span class="trophy-badge trophy-badge-silver"></span>
      <span>{{ trophyCounts.silver }}</span>
    </div>
    <div class="trophy-count">
      <span class="trophy-badge trophy-badge-bronze"></span>
      <span>{{ trophyCounts.bronze }}</span>
    </div>
  </div>

  <ul class="achievement-list">
    <li v-for="achievement in sortedAchievements(game.achievements)" :key="achievement.id">
      <router-link
        :to="{ name: 'achievement-detail', params: { gameId: game.id, achievementId: achievement.id } }"
        class="achievement-row"
        :class="{ unlocked: achievement.unlockedAt !== null }"
      >
        <div
          class="achievement-icon"
          :style="achievement.hidden && achievement.unlockedAt === null ? {} : { backgroundImage: `url(${game.coverImageUrl})` }"
        >
          <span
            class="achievement-badge"
            :class="achievement.unlockedAt !== null ? `badge-${deriveTier(achievement)}` : 'badge-locked'"
          >
            <template v-if="achievement.hidden && achievement.unlockedAt === null">?</template>
          </span>
        </div>

        <div class="achievement-info">
          <template v-if="achievement.hidden && achievement.unlockedAt === null">
            <span class="achievement-name">Hidden Trophy</span>
            <span class="achievement-description">Unlock this achievement to reveal it.</span>
          </template>
          <template v-else>
            <span class="achievement-name">{{ achievement.name }}</span>
            <span v-if="achievement.description" class="achievement-description">{{ achievement.description }}</span>
          </template>

          <div v-if="achievement.unlockedAt !== null" class="achievement-unlocked-at">
            Unlocked {{ formatUnlockedAt(achievement.unlockedAt) }}
          </div>
          <div
            v-else-if="achievement.progressCurrent != null && achievement.progressTarget"
            class="achievement-progress"
          >
            <div class="progress-bar">
              <div
                class="progress-fill"
                :style="{ width: `${Math.min(100, (achievement.progressCurrent / achievement.progressTarget) * 100)}%` }"
              ></div>
            </div>
            <span class="progress-label">{{ achievement.progressCurrent }} / {{ achievement.progressTarget }}</span>
          </div>
        </div>
      </router-link>
    </li>
  </ul>
</section>

<section v-else-if="activeTab === 'Notes'" class="notes-panel">
  <div v-if="noteMode === 'list'" class="notes-list-view">
    <div class="notes-header-row">
      <h2>Notes</h2>
      <button type="button" class="primary-button" @click="startNewNote">
        {{ hasDraft ? 'Continue Draft' : 'New Note' }}
      </button>
    </div>

    <div v-if="noteError" class="note-error">{{ noteError }}</div>

    <p v-if="noteLoading" class="empty-state">Loading…</p>
    <p v-else-if="!noteNames.length" class="empty-state">No notes yet.</p>
    <ul v-else class="notes-list">
      <li v-for="note in noteNames" :key="note" class="notes-list-row" @click="void viewNote(note)">
        <span class="note-name">{{ note }}</span>
        <div class="notes-list-actions">
          <button type="button" class="danger-button" :disabled="noteSaving" @click.stop="void deleteNote(note)">
            Delete
          </button>
        </div>
      </li>
    </ul>
  </div>

  <div v-else-if="noteMode === 'view'" class="notes-editor">
    <div class="notes-editor-card">
      <div class="notes-toolbar">
        <button type="button" class="small-button" @click="backToList">← Back</button>
        <span class="selected-note">{{ viewingNoteName }}</span>
        <button type="button" class="small-button" @click="editFromView">Edit</button>
      </div>

      <div v-if="noteLoading" class="empty-state">Loading…</div>
      <div v-else class="note-rendered" v-html="renderedNoteHtml"></div>

      <div v-if="noteError" class="note-error">{{ noteError }}</div>
    </div>
  </div>

  <div v-else class="notes-editor">
    <div class="notes-editor-card">
      <div class="notes-toolbar">
        <button type="button" class="small-button" @click="backToList">← Back</button>
      </div>

      <label class="field">
        <span>Note name</span>
        <input v-model="draftName" type="text" placeholder="meeting-notes" pattern="[A-Za-z0-9_-]+" />
      </label>

      <textarea v-model="draftContent" placeholder="Write markdown here…" spellcheck="true"></textarea>

      <div v-if="noteError" class="note-error">{{ noteError }}</div>

      <div class="notes-editor-actions">
        <button type="button" class="small-button" @click="backToList">Cancel</button>
        <button
          type="button"
          class="primary-button"
          :disabled="noteSaving || !draftName.trim()"
          @click="void saveDraft()"
        >
          {{ noteSaving ? 'Saving…' : 'Save' }}
        </button>
      </div>
    </div>
  </div>
</section>

    <section v-else class="coming-soon">
      <p>{{ activeTab }} coming soon.</p>
    </section>
  </main>

  <main v-else class="not-found">
    <p>Game not found.</p>
  </main>
</template>

<style scoped>
.detail {
  position: relative;
  font-family: system-ui, sans-serif;
  color: #fff;
  min-height: 100vh;
  background: #121212;
  overflow: hidden;
}
.ambient-bg {
  position: fixed;
  inset: 0;
  background-size: cover;
  background-position: center;
  filter: blur(80px);
  opacity: 0.25;
  transform: scale(1.2);
  z-index: 0;
}
.hero,
.tabs,
.overview,
.achievements,
.notes-panel,
.coming-soon {
  position: relative;
  z-index: 1;
}
.hero {
  position: relative;
  background-size: cover;
  background-position: center;
  min-height: 360px;
  display: flex;
  align-items: flex-end;
}
.hero-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(18, 18, 18, 0) 40%, rgba(18, 18, 18, 0.85) 85%, #121212 100%);
}
.hero-inner {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 1600px;
  margin: 0 auto;
  padding: 0 24px 28px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 18px;
}
.hero-inner h1 {
  margin: 0;
  font-size: 2.4rem;
  text-shadow: 0 2px 12px rgba(0, 0, 0, 0.6);
}
.badges {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.badge {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 999px;
  padding: 4px 14px;
  font-size: 13px;
  text-transform: capitalize;
  color: #ddd;
}
.rating-badge {
  color: #d68a34;
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
.hero-actions {
  position: absolute;
  bottom: 20px;
  right: 24px;
  z-index: 2;
  display: flex;
  align-items: center;
  gap: 8px;
  opacity: 0;
  transition: opacity 0.2s ease;
}
.hero:hover .hero-actions {
  opacity: 1;
}
.hero-icon-button {
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.25);
  color: #fff;
  border-radius: 50%;
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}
.hero-icon-button:hover {
  background: rgba(0, 0, 0, 0.7);
}
.hero-icon-button.active {
  color: #d68a34;
  border-color: rgba(214, 138, 52, 0.5);
}
.edit-button {
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.25);
  color: #fff;
  border-radius: 999px;
  padding: 8px 20px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s ease;
}
.edit-button:hover {
  background: rgba(0, 0, 0, 0.7);
}
.meta {
  text-transform: capitalize;
  color: #ddd;
}
.tabs {
  display: flex;
  gap: 4px;
  width: 100%;
  max-width: 1600px;
  margin: 16px auto 0;
  padding: 8px 16px;
  box-sizing: border-box;
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid #2a2a2a;
  border-radius: 8px;
  overflow-x: auto;
}
.tab {
  background: rgba(255, 255, 255, 0.06);
  border: none;
  color: #ccc;
  padding: 8px 18px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border-radius: 999px;
  white-space: nowrap;
  transition: background 0.15s ease, color 0.15s ease;
}
.tab:hover {
  background: #3a3a3a;
  color: #fff;
}
.tab.active {
  background: #d68a34;
  color: #121212;
}
.overview {
  width: 100%;
  max-width: 1600px;
  margin: 0 auto;
  padding: 24px;
  box-sizing: border-box;
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 24px;
  align-items: start;
}
.description-wrap {
  display: flex;
  flex-direction: column;
  gap: 14px;
  max-width: 720px;
  padding-left: 16px;
  border-left: 3px solid #d68a34;
}
.description-html {
  color: #ddd;
  font-size: 16px;
  line-height: 1.7;
}
.description-html :deep(img),
.description-html :deep(video) {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  margin: 10px 0;
  display: block;
}
.description-html :deep(h1),
.description-html :deep(h2),
.description-html :deep(h3) {
  margin: 18px 0 6px;
  font-size: 15px;
  font-weight: 700;
  color: #fff;
}
.description-html :deep(p) {
  margin: 0 0 12px;
}
.description-html :deep(a) {
  color: #d68a34;
}
.description-html :deep(ul) {
  padding-left: 20px;
  margin: 0 0 12px;
}
.rating-breakdown {
  display: flex;
  gap: 12px;
  margin-top: 24px;
  flex-wrap: wrap;
}
.rating-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid #232323;
  border-radius: 10px;
  padding: 12px 18px;
  min-width: 90px;
}
.rating-label {
  color: #999;
  font-size: 13px;
}
.rating-score {
  color: #d68a34;
  font-size: 18px;
  font-weight: 600;
}
.details-panel {
  border: 1px solid #2a2a2a;
  border-radius: 12px;
  padding: 6px 18px 16px;
  background: rgba(0, 0, 0, 0.3);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
  margin-right: -24px;
}
.panel-title {
  margin: 14px 0 6px;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #777;
  font-weight: 700;
}
.detail-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px 0;
  font-size: 14px;
  border-bottom: 1px solid #202020;
}
.detail-row:last-child {
  border-bottom: none;
}
.detail-label {
  color: #999;
}
.detail-value {
  color: #fff;
}
.feature-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.feature-pill {
  background: #2a2a2a;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 11px;
  color: #ccc;
}
.platforms {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.platform-row {
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.platform-line {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 8px;
  font-size: 14px;
}
.platform-name {
  color: #fff;
  font-weight: 600;
}
.platform-meta {
  color: #999;
  white-space: nowrap;
}
.platform-last-played {
  color: #666;
  font-size: 12px;
}
.links-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.links-list a {
  color: #d68a34;
  font-size: 14px;
  text-decoration: none;
}
.links-list a:hover {
  text-decoration: underline;
}
.ownership-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  color: #ddd;
  font-size: 14px;
}
.ownership-format {
  text-transform: capitalize;
  color: #fff;
  font-weight: 600;
}
.trophy-summary {
  display: flex;
  gap: 20px;
  margin: 16px 0 24px;
}
.trophy-count {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #ccc;
  font-size: 14px;
  font-weight: 600;
}
.trophy-badge {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: inline-block;
}
.trophy-badge-bronze {
  background: #b06a35;
  border: 2px solid #7a4a25;
}
.trophy-badge-silver {
  background: #b8b8b8;
  border: 2px solid #7a7a7a;
}
.trophy-badge-gold {
  background: #d4af37;
  border: 2px solid #9a7a1a;
}
.trophy-badge-platinum {
  background: #a8b8c8;
  border: 2px solid #6a7a8a;
}
.trophy-badge.dim {
  background: #2a2a2a;
  border-color: #3a3a3a;
}
.achievement-list {
  list-style: none;
  padding: 0;
  margin-top: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.achievement-row {
  display: flex;
  gap: 14px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid #232323;
  border-radius: 10px;
  align-items: center;
  text-decoration: none;
  color: inherit;
}
.achievement-icon {
  position: relative;
  width: 56px;
  height: 56px;
  border-radius: 10px;
  background-size: cover;
  background-position: center;
  background-color: #1a1a1a;
  flex-shrink: 0;
}
.achievement-row:not(.unlocked) .achievement-icon {
  filter: grayscale(100%) brightness(0.5);
}
.achievement-badge {
  position: absolute;
  bottom: -6px;
  right: -6px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  color: #1a1a1a;
  border: 2px solid #121212;
}
.badge-bronze {
  background: #b06a35;
}
.badge-silver {
  background: #b8b8b8;
}
.badge-gold {
  background: #d4af37;
}
.badge-locked {
  background: #3a3a3a;
  color: #888;
}
.achievement-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.achievement-name {
  color: #fff;
  font-weight: 600;
  font-size: 15px;
}
.achievement-row:not(.unlocked) .achievement-name {
  color: #999;
}
.achievement-description {
  color: #999;
  font-size: 13px;
}
.achievement-unlocked-at {
  color: #d68a34;
  font-size: 12px;
  margin-top: 4px;
}
.achievement-progress {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
}
.progress-bar {
  flex: 1;
  max-width: 160px;
  height: 6px;
  background: #2a2a2a;
  border-radius: 3px;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: #d68a34;
}
.progress-label {
  color: #999;
  font-size: 12px;
  white-space: nowrap;
}
.achievements-header {
  display: flex;
  align-items: center;
  gap: 12px;
}
.percent {
  color: #d68a34;
}
.notes-panel {
  width: 100%;
  max-width: 1600px;
  margin: 0 auto;
  padding: 24px;
  box-sizing: border-box;
}
.notes-list-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.notes-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.notes-header-row h2 {
  margin: 0;
  font-size: 1.1rem;
}
.notes-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.notes-list-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid #2a2a2a;
  border-radius: 8px;
  padding: 12px 16px;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease;
}
.notes-list-row:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: #3a3a3a;
}
.note-name {
  color: #fff;
  font-weight: 600;
}
.notes-list-actions {
  display: flex;
  gap: 8px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: #ddd;
  font-size: 0.85rem;
}
.field input {
  background: #111;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  color: #fff;
  padding: 10px 12px;
}
.field input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.primary-button,
.small-button,
.danger-button {
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: opacity 0.15s ease;
}
.primary-button {
  background: #d68a34;
  color: #111;
  padding: 10px 12px;
}
.small-button {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
  padding: 7px 10px;
  font-size: 0.8rem;
}
.danger-button {
  background: rgba(220, 38, 38, 0.18);
  color: #fca5a5;
  padding: 8px 10px;
}
.primary-button:disabled,
.danger-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.notes-editor {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 100%;
}
.notes-editor-card {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid #2a2a2a;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.notes-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  padding-bottom: 12px;
  border-bottom: 1px solid #2a2a2a;
}
.selected-note {
  color: #fff;
  font-weight: 600;
  font-size: 1.05rem;
}
.field input:focus,
.notes-editor textarea:focus {
  outline: none;
  border-color: #d68a34;
}
.notes-editor textarea {
  width: 100%;
  min-height: 420px;
  box-sizing: border-box;
  border: 1px solid #3a3a3a;
  border-radius: 10px;
  background: #111;
  color: #f5f5f5;
  resize: vertical;
  padding: 14px;
  font: inherit;
}
.notes-editor-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
.note-error {
  color: #fca5a5;
}
.empty-state {
  color: #777;
  margin: 0;
}
.coming-soon {
  width: 100%;
  max-width: 1600px;
  margin: 0 auto;
  padding: 48px 24px;
  color: #777;
  text-align: center;
}
.not-found {
  padding: 24px;
  color: #fff;
}
.note-rendered {
  color: #ddd;
  line-height: 1.6;
  font-size: 14px;
}
.note-rendered :deep(h1),
.note-rendered :deep(h2),
.note-rendered :deep(h3) {
  color: #fff;
  margin: 16px 0 8px;
}
.note-rendered :deep(p) {
  margin: 0 0 10px;
}
.note-rendered :deep(a) {
  color: #d68a34;
}
.note-rendered :deep(code) {
  background: #111;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
}
.note-rendered :deep(pre) {
  background: #111;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
}
.note-rendered :deep(ul),
.note-rendered :deep(ol) {
  padding-left: 20px;
  margin: 0 0 10px;
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
.confirm-actions .secondary-button,
.confirm-actions .danger-button {
  padding: 10px 18px;
}
.secondary-button {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}
</style>