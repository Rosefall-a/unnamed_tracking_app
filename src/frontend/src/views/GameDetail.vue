<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  deleteGameNote,
  fetchGame,
  fetchGameNote,
  listGameNotes,
  saveGameNote,
} from '../services/games'
import type { Achievement, Game } from '../types/game'
import GameFormModal from '../components/GameFormModal.vue'

const route = useRoute()

const game = ref<Game | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const showEditModal = ref(false)
const descriptionParagraphs = computed(() => {
  if (!game.value?.description) return []
  return game.value.description
    .split('•')
    .map((s) => s.trim())
    .filter(Boolean)
})
const noteNames = ref<string[]>([])
const noteMode = ref<'list' | 'editor'>('list')
const editingNoteName = ref<string | null>(null)
const draftName = ref('')
const draftContent = ref('')
const noteLoading = ref(false)
const noteSaving = ref(false)
const noteError = ref<string | null>(null)

const hasDraft = computed(
  () => editingNoteName.value === null && (draftName.value.trim() !== '' || draftContent.value.trim() !== '')
)

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

function startNewNote() {
  // resumes whatever was already typed if there's an unsaved draft,
  // otherwise starts blank
  if (!hasDraft.value) {
    draftName.value = ''
    draftContent.value = ''
  }
  editingNoteName.value = null
  noteMode.value = 'editor'
}

async function editNote(noteName: string) {
  if (!game.value) return
  editingNoteName.value = noteName
  draftName.value = noteName
  noteLoading.value = true
  noteError.value = null
  try {
    draftContent.value = await fetchGameNote(game.value.id, noteName)
    noteMode.value = 'editor'
  } catch (err) {
    noteError.value = err instanceof Error ? err.message : 'Failed to load note'
  } finally {
    noteLoading.value = false
  }
}

function backToList() {
  noteMode.value = 'list'
}

async function saveDraft() {
  if (!game.value) return
  const name = draftName.value.trim()
  if (!name) {
    noteError.value = 'Enter a note name first.'
    return
  }

  noteSaving.value = true
  noteError.value = null

  try {
    await saveGameNote(game.value.id, name, draftContent.value)
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
    if (editingNoteName.value === noteName) {
      editingNoteName.value = null
      draftName.value = ''
      draftContent.value = ''
      noteMode.value = 'list'
    }
    await loadNotes()
  } catch (err) {
    noteError.value = err instanceof Error ? err.message : 'Failed to delete note'
  } finally {
    noteSaving.value = false
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

const tally = computed(() => {
  if (!game.value) return null
  const values = [
    game.value.ratingOverall,
    game.value.ratingStory,
    game.value.ratingGameplay,
    game.value.ratingSound,
  ].filter((v): v is number => v !== null)
  if (values.length === 0) return null
  return { sum: values.reduce((a, b) => a + b, 0), max: values.length * 10 }
})

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

<GameFormModal v-if="showEditModal" :game="game" @close="showEditModal = false" @saved="onGameSaved" />

<section class="hero" :style="{ backgroundImage: `url(${game.bannerImageUrl})` }">
  <div class="hero-overlay"></div>
  <button class="edit-button" type="button" @click="showEditModal = true">Edit</button>
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
<div v-if="descriptionParagraphs.length" class="description-wrap">
  <p v-for="(section, i) in descriptionParagraphs" :key="i" class="description">
    {{ section }}
  </p>
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
      <span class="rating-label">Tally</span>
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
      <span v-if="game.ownership.price !== null">${{ game.ownership.price.toFixed(2) }}</span>
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
      <ul class="achievement-list">
        <li
          v-for="achievement in sortedAchievements(game.achievements)"
          :key="achievement.id"
          :class="{ unlocked: achievement.unlockedAt !== null }"
        >
          {{ achievement.unlockedAt !== null ? '✓' : '○' }} {{ achievement.name }}
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
<li v-for="note in noteNames" :key="note" class="notes-list-row" @click="void editNote(note)">
  <span class="note-name">{{ note }}</span>
  <div class="notes-list-actions">
    <button type="button" class="small-button" @click.stop="void editNote(note)">Edit</button>
    <button type="button" class="danger-button" :disabled="noteSaving" @click.stop="void deleteNote(note)">
      Delete
    </button>
  </div>
</li>
        </ul>
      </div>

      <div v-else class="notes-editor">
  <div class="notes-editor-card">
    <div class="notes-toolbar">
          <button type="button" class="small-button" @click="backToList">← Back</button>
          <span class="selected-note">{{ editingNoteName ?? 'New note' }}</span>
        </div>

        <label class="field">
          <span>Note name</span>
          <input
            v-model="draftName"
            type="text"
            placeholder="meeting-notes"
            pattern="[A-Za-z0-9_-]+"
            :disabled="editingNoteName !== null"
          />
        </label>

        <textarea
          v-model="draftContent"
          placeholder="Write markdown here…"
          spellcheck="true"
        ></textarea>

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
  position: absolute;
  inset: 0;
  background-size: cover;
  background-position: center;
  filter: blur(80px);
  opacity: 0.25;
  transform: scale(1.2);
  z-index: 0;
}
.overview {
  width: 100%;
  max-width: 1600px;
  margin: 0 auto;
  padding: 24px;
  box-sizing: border-box;
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 28px;
  align-items: start;
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
.edit-button {
  position: absolute;
  top: 20px;
  right: 24px;
  z-index: 2;
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.25);
  color: #fff;
  border-radius: 999px;
  padding: 8px 20px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s ease, background 0.15s ease;
}
.hero:hover .edit-button {
  opacity: 1;
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
.description {
  margin: 0;
  color: #ddd;
  font-size: 16px;
  line-height: 1.7;
}
.description.clamped {
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.description-toggle {
  align-self: flex-start;
  background: none;
  border: none;
  color: #d68a34;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  padding-left: 19px;
}
.description-toggle:hover {
  text-decoration: underline;
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
.achievements {
  width: 100%;
  max-width: 1600px;
  margin: 0 auto;
  padding: 24px;
  box-sizing: border-box;
}
.achievements-header {
  display: flex;
  align-items: center;
  gap: 12px;
}
.percent {
  color: #d68a34;
}
.achievement-list {
  list-style: none;
  padding: 0;
  margin-top: 16px;
}
.achievement-list li {
  padding: 6px 0;
  color: #777;
}
.achievement-list li.unlocked {
  color: #fff;
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
</style>