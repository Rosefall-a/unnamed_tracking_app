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

const route = useRoute()

const game = ref<Game | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

const noteNames = ref<string[]>([])
const selectedNoteName = ref<string>('')
const noteContent = ref('')
const noteDraftName = ref('')
const noteLoading = ref(false)
const noteSaving = ref(false)
const noteError = ref<string | null>(null)

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

async function loadNotes() {
  if (!game.value) {
    noteNames.value = []
    selectedNoteName.value = ''
    noteContent.value = ''
    return
  }

  noteLoading.value = true
  noteError.value = null

  try {
    const notes = await listGameNotes(game.value.id)
    noteNames.value = notes
    if (!selectedNoteName.value && notes.length > 0) {
      await openNote(notes[0])
    }
    if (selectedNoteName.value && !notes.includes(selectedNoteName.value)) {
      selectedNoteName.value = ''
      noteContent.value = ''
    }
  } catch (err) {
    noteError.value = err instanceof Error ? err.message : 'Failed to load notes'
  } finally {
    noteLoading.value = false
  }
}

async function openNote(noteName: string) {
  if (!game.value) return

  selectedNoteName.value = noteName
  noteDraftName.value = noteName
  noteLoading.value = true
  noteError.value = null

  try {
    noteContent.value = await fetchGameNote(game.value.id, noteName)
  } catch (err) {
    noteError.value = err instanceof Error ? err.message : 'Failed to load note'
    noteContent.value = ''
  } finally {
    noteLoading.value = false
  }
}

async function saveCurrentNote() {
  if (!game.value) return

  const noteName = selectedNoteName.value || noteDraftName.value.trim()
  if (!noteName) {
    noteError.value = 'Enter a note name first.'
    return
  }

  noteSaving.value = true
  noteError.value = null

  try {
    await saveGameNote(game.value.id, noteName, noteContent.value)
    selectedNoteName.value = noteName
    noteDraftName.value = noteName
    await loadNotes()
  } catch (err) {
    noteError.value = err instanceof Error ? err.message : 'Failed to save note'
  } finally {
    noteSaving.value = false
  }
}

async function deleteCurrentNote() {
  if (!game.value || !selectedNoteName.value) return

  noteSaving.value = true
  noteError.value = null

  try {
    await deleteGameNote(game.value.id, selectedNoteName.value)
    selectedNoteName.value = ''
    noteDraftName.value = ''
    noteContent.value = ''
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
    <div class="ambient-bg" :style="{ backgroundImage: `url(${game.coverImageUrl})` }"></div>

    <section class="hero" :style="{ backgroundImage: `url(${game.coverImageUrl})` }">
      <div class="hero-overlay"></div>
      <div class="hero-inner">
        <div class="hero-top">
          <h1>{{ game.title }}</h1>
          <button class="edit-button" type="button">Edit</button>
        </div>
        <p class="meta">
          <span class="status">{{ game.status }}</span>
          <span v-if="game.ratingOverall !== null"> · ★ {{ game.ratingOverall.toFixed(1) }}</span>
          <span v-if="game.platforms.length > 1">
            · also on {{ game.platforms.slice(1).map((p) => p.platform).join(', ') }}
          </span>
        </p>
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
        <p v-if="game.description" class="description">{{ game.description }}</p>
      </div>

      <aside class="details-panel">
        <div class="detail-row">
          <span class="detail-label">Series</span>
          <span class="detail-value">{{ game.series ?? '—' }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Developer</span>
          <span class="detail-value">{{ game.developer ?? '—' }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Publisher</span>
          <span class="detail-value">{{ game.publisher ?? '—' }}</span>
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
            <li v-for="p in game.platforms" :key="p.platform">
              <span class="platform-name">{{ p.platform }}</span>
              <span>{{ formatPlaytime(p.playtimeMinutes) }}</span>
              <span v-if="p.completionPercent !== null">{{ p.completionPercent }}%</span>
              <span v-if="p.lastPlayedAt">
                last played {{ new Date(p.lastPlayedAt).toLocaleDateString() }}
              </span>
            </li>
          </ul>
        </div>
        <div v-if="game.features.length" class="detail-row">
          <span class="detail-label">Features</span>
          <span class="feature-pills">
            <span v-for="f in game.features" :key="f" class="feature-pill">{{ f }}</span>
          </span>
        </div>
        <div v-if="game.tags.length" class="detail-row">
          <span class="detail-label">Tags</span>
          <span class="feature-pills">
            <span v-for="tag in game.tags" :key="tag" class="feature-pill">{{ tag }}</span>
          </span>
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
      <div class="notes-layout">
        <aside class="notes-sidebar">
          <div class="notes-header-row">
            <h2>Notes</h2>
            <button type="button" class="small-button" @click="selectedNoteName = ''; noteDraftName = ''; noteContent = ''">
              New
            </button>
          </div>

          <label class="field">
            <span>Note name</span>
            <input
              v-model="noteDraftName"
              type="text"
              placeholder="meeting-notes"
              pattern="[A-Za-z0-9_-]+"
            />
          </label>

          <button
            type="button"
            class="primary-button"
            :disabled="noteSaving || !noteDraftName.trim()"
            @click="selectedNoteName = noteDraftName.trim(); void saveCurrentNote()"
          >
            {{ selectedNoteName ? 'Save note' : 'Create note' }}
          </button>

          <ul class="notes-list" v-if="noteNames.length">
            <li v-for="note in noteNames" :key="note">
              <button type="button" class="note-item" :class="{ active: selectedNoteName === note }" @click="void openNote(note)">
                {{ note }}
              </button>
            </li>
          </ul>
          <p v-else class="empty-state">No notes yet.</p>
        </aside>

        <div class="notes-editor">
          <div class="notes-toolbar" v-if="selectedNoteName">
            <span class="selected-note">{{ selectedNoteName }}</span>
            <button type="button" class="danger-button" :disabled="noteSaving" @click="void deleteCurrentNote()">
              Delete
            </button>
          </div>

          <textarea
            v-model="noteContent"
            placeholder="Write markdown here…"
            spellcheck="true"
          ></textarea>

          <div v-if="noteError" class="note-error">{{ noteError }}</div>
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
.hero,
.tabs,
.overview,
.achievements,
.coming-soon {
  position: relative;
  z-index: 1;
}
.hero {
  background-size: cover;
  background-position: center;
  padding: 64px 24px 48px;
}
.hero-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(18, 18, 18, 0.15) 0%, rgba(18, 18, 18, 0.9) 100%);
}
.hero-inner {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 1600px;
  margin: 0 auto;
}
.hero-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}
.hero-top h1 {
  margin: 0;
}
.edit-button {
  background: rgba(255, 255, 255, 0.12);
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
  background: rgba(255, 255, 255, 0.22);
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
  margin: 0 auto;
  padding: 0 24px;
  box-sizing: border-box;
  border-bottom: 1px solid #2a2a2a;
  overflow-x: auto;
}
.tab {
  background: none;
  border: none;
  color: #999;
  padding: 10px 16px;
  font-size: 14px;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  border-radius: 6px 6px 0 0;
  white-space: nowrap;
  transition: color 0.15s ease, background 0.15s ease;
}
.tab:hover {
  color: #ddd;
}
.tab.active {
  color: #fff;
  background: rgba(245, 197, 24, 0.12);
  border-bottom-color: #f5c518;
}
.overview {
  width: 100%;
  max-width: 1600px;
  margin: 0 auto;
  padding: 24px;
  box-sizing: border-box;
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: 24px;
  align-items: start;
}
.description {
  margin: 0;
  color: #ddd;
  font-size: 17px;
  line-height: 1.6;
}
.details-panel {
  border: 1px solid #2a2a2a;
  border-radius: 8px;
  padding: 4px 16px;
  background: rgba(0, 0, 0, 0.25);
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
  gap: 8px;
}
.platforms li {
  display: flex;
  flex-direction: column;
  gap: 2px;
  color: #999;
  font-size: 14px;
}
.platform-name {
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
  color: #f5c518;
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
.notes-layout {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 20px;
  min-height: 520px;
}
.notes-sidebar,
.notes-editor {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid #2a2a2a;
  border-radius: 12px;
  padding: 16px;
}
.notes-sidebar {
  display: flex;
  flex-direction: column;
  gap: 14px;
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
  background: #f5c518;
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
.notes-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.note-item {
  width: 100%;
  text-align: left;
  background: transparent;
  border: 1px solid #2a2a2a;
  border-radius: 8px;
  padding: 8px 10px;
  color: #ddd;
  cursor: pointer;
}
.note-item.active {
  background: rgba(245, 197, 24, 0.12);
  border-color: rgba(245, 197, 24, 0.6);
  color: #fff;
}
.empty-state {
  color: #777;
  margin: 0;
}
.notes-editor {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.notes-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}
.selected-note {
  color: #fff;
  font-weight: 600;
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
.note-error {
  color: #fca5a5;
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