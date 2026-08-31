<script setup lang="ts">
import { ref } from 'vue'
import { createGame, uploadGameAsset } from '../services/games'
import type { GameLink, GameOwnership } from '../services/games'
import type { GameStatus } from '../types/game'

const emit = defineEmits<{
  close: []
  created: [gameId: string]
}>()

const statuses: GameStatus[] = [
  'wishlist',
  'backlog',
  'playing',
  'on hold',
  'beaten',
  'played',
  'dropped',
  'mastered',
]

const tabs = ['General', 'Ratings & Tags', 'Media', 'Links', 'Ownership'] as const
const activeTab = ref<(typeof tabs)[number]>('General')

const title = ref('')
const sortTitle = ref('')
const folderLocation = ref('')
const status = ref<GameStatus>('backlog')
const developer = ref('')
const publisher = ref('')
const series = ref('')
const source = ref('')
const ageRating = ref('')
const releaseDate = ref('')
const dateAdded = ref(new Date().toISOString().slice(0, 10))
const description = ref('')

const ratingOverall = ref<number | null>(null)
const ratingStory = ref<number | null>(null)
const ratingGameplay = ref<number | null>(null)
const ratingSound = ref<number | null>(null)
const tagsInput = ref('')
const featuresInput = ref('')

const coverFile = ref<File | null>(null)
const bannerFile = ref<File | null>(null)

const links = ref<GameLink[]>([])
function addLink() {
  links.value.push({ label: '', url: '' })
}
function removeLink(index: number) {
  links.value.splice(index, 1)
}

const ownershipFormat = ref<GameOwnership['format']>(null)
const purchaseDate = ref('')
const price = ref<number | null>(null)
const condition = ref('')

const saving = ref(false)
const error = ref<string | null>(null)

const folderTouched = ref(false)
function suggestFolderFromTitle() {
  if (folderTouched.value) return
  folderLocation.value = title.value
    .trim()
    .replace(/[^A-Za-z0-9_-]+/g, '-')
    .replace(/^-+|-+$/g, '')
}

function onCoverFileChange(e: Event) {
  coverFile.value = (e.target as HTMLInputElement).files?.[0] ?? null
}
function onBannerFileChange(e: Event) {
  bannerFile.value = (e.target as HTMLInputElement).files?.[0] ?? null
}

async function submit() {
  if (!title.value.trim() || !folderLocation.value.trim()) {
    error.value = 'Title and folder name are required.'
    activeTab.value = 'General'
    return
  }

  saving.value = true
  error.value = null

  try {
    const newGame = await createGame({
      title: title.value.trim(),
      sortTitle: sortTitle.value.trim() || null,
      folderLocation: folderLocation.value.trim(),
      status: status.value,
      description: description.value.trim() || null,
      developer: developer.value.trim() || null,
      publisher: publisher.value.trim() || null,
      series: series.value.trim() || null,
      releaseDate: releaseDate.value || null,
      dateAdded: dateAdded.value || null,
      source: source.value.trim() || null,
      ageRating: ageRating.value.trim() || null,
      ratingOverall: ratingOverall.value,
      ratingStory: ratingStory.value,
      ratingGameplay: ratingGameplay.value,
      ratingSound: ratingSound.value,
      tags: tagsInput.value.split(',').map((t) => t.trim()).filter(Boolean),
      features: featuresInput.value.split(',').map((f) => f.trim()).filter(Boolean),
      links: links.value.filter((l) => l.label.trim() && l.url.trim()),
      ownership: {
        format: ownershipFormat.value,
        purchaseDate: purchaseDate.value || null,
        price: price.value,
        condition: condition.value.trim() || null,
      },
    })

    if (import.meta.env.VITE_USE_MOCK_DATA !== 'true') {
      if (coverFile.value) {
        await uploadGameAsset(newGame.id, 'key_art', coverFile.value)
      }
      if (bannerFile.value) {
        await uploadGameAsset(newGame.id, 'banner', bannerFile.value)
      }
    }

    emit('created', newGame.id)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to create game'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="modal-backdrop" @click.self="emit('close')">
    <div class="modal">
      <div class="modal-header">
        <h2>Add Game</h2>
        <button type="button" class="close-button" @click="emit('close')">✕</button>
      </div>

      <nav class="modal-tabs">
        <button
          v-for="tab in tabs"
          :key="tab"
          type="button"
          class="modal-tab"
          :class="{ active: activeTab === tab }"
          @click="activeTab = tab"
        >
          {{ tab }}
        </button>
      </nav>

      <form class="modal-body" @submit.prevent="submit">
        <div v-if="activeTab === 'General'" class="tab-panel">
          <div class="field-row">
            <label class="field">
              <span>Title</span>
              <input v-model="title" type="text" required @blur="suggestFolderFromTitle" />
            </label>
            <label class="field">
              <span>Sorting Name</span>
              <input v-model="sortTitle" type="text" placeholder="defaults to Title" />
            </label>
          </div>

          <div class="field-row">
            <label class="field">
              <span>Folder name</span>
              <input
                v-model="folderLocation"
                type="text"
                required
                pattern="[A-Za-z0-9_-]+"
                @input="folderTouched = true"
              />
            </label>
            <label class="field">
              <span>Status</span>
              <select v-model="status">
                <option v-for="s in statuses" :key="s" :value="s">{{ s }}</option>
              </select>
            </label>
          </div>

          <div class="field-row">
            <label class="field">
              <span>Developer</span>
              <input v-model="developer" type="text" />
            </label>
            <label class="field">
              <span>Publisher</span>
              <input v-model="publisher" type="text" />
            </label>
          </div>

          <div class="field-row">
            <label class="field">
              <span>Series</span>
              <input v-model="series" type="text" />
            </label>
            <label class="field">
              <span>Source</span>
              <input v-model="source" type="text" placeholder="Steam, GOG, physical..." />
            </label>
          </div>

          <div class="field-row">
            <label class="field">
              <span>Age Rating</span>
              <input v-model="ageRating" type="text" placeholder="ESRB M, PEGI 18..." />
            </label>
            <label class="field">
              <span>Release Date</span>
              <input v-model="releaseDate" type="date" />
            </label>
          </div>

          <label class="field">
            <span>Date added to library</span>
            <input v-model="dateAdded" type="date" />
          </label>

          <label class="field">
            <span>Description</span>
            <textarea v-model="description" rows="3"></textarea>
          </label>
        </div>

        <div v-else-if="activeTab === 'Ratings & Tags'" class="tab-panel">
          <div class="field-row ratings-row">
            <label class="field">
              <span>Overall</span>
              <input v-model.number="ratingOverall" type="number" min="0" max="10" step="0.1" />
            </label>
            <label class="field">
              <span>Story</span>
              <input v-model.number="ratingStory" type="number" min="0" max="10" step="0.1" />
            </label>
            <label class="field">
              <span>Gameplay</span>
              <input v-model.number="ratingGameplay" type="number" min="0" max="10" step="0.1" />
            </label>
            <label class="field">
              <span>Sound</span>
              <input v-model.number="ratingSound" type="number" min="0" max="10" step="0.1" />
            </label>
          </div>

          <label class="field">
            <span>Tags (comma separated)</span>
            <input v-model="tagsInput" type="text" placeholder="Action RPG, Souls-Like" />
          </label>

          <label class="field">
            <span>Features (comma separated)</span>
            <input v-model="featuresInput" type="text" placeholder="Achievements, Cloud Saves" />
          </label>
        </div>

        <div v-else-if="activeTab === 'Media'" class="tab-panel">
          <label class="field">
            <span>Cover image (portrait)</span>
            <input type="file" accept="image/*" @change="onCoverFileChange" />
          </label>
          <label class="field">
            <span>Banner image (landscape)</span>
            <input type="file" accept="image/*" @change="onBannerFileChange" />
          </label>
          <p class="hint">
            Images upload after the game is created, and only against a real backend — skipped
            automatically while running on mock data.
          </p>
        </div>

        <div v-else-if="activeTab === 'Links'" class="tab-panel">
          <div v-for="(link, index) in links" :key="index" class="field-row link-row">
            <label class="field">
              <span>Label</span>
              <input v-model="link.label" type="text" placeholder="Steam Store Page" />
            </label>
            <label class="field">
              <span>URL</span>
              <input v-model="link.url" type="url" placeholder="https://..." />
            </label>
            <button type="button" class="remove-button" @click="removeLink(index)">✕</button>
          </div>
          <button type="button" class="secondary-button" @click="addLink">+ Add Link</button>
        </div>

        <div v-else-if="activeTab === 'Ownership'" class="tab-panel">
          <label class="field">
            <span>Format</span>
            <select v-model="ownershipFormat">
              <option :value="null">Unspecified</option>
              <option value="digital">Digital</option>
              <option value="physical">Physical</option>
            </select>
          </label>

          <div class="field-row">
            <label class="field">
              <span>Purchase date</span>
              <input v-model="purchaseDate" type="date" />
            </label>
            <label class="field">
              <span>Price</span>
              <input v-model.number="price" type="number" min="0" step="0.01" />
            </label>
          </div>

          <label v-if="ownershipFormat === 'physical'" class="field">
            <span>Condition / notes</span>
            <input v-model="condition" type="text" placeholder="CIB, disc only, box wear..." />
          </label>
        </div>

        <div v-if="error" class="form-error">{{ error }}</div>

        <div class="modal-actions">
          <button type="button" class="secondary-button" @click="emit('close')">Cancel</button>
          <button type="submit" class="primary-button" :disabled="saving">
            {{ saving ? 'Saving…' : 'Add Game' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
}
.modal {
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  border-radius: 12px;
  width: 100%;
  max-width: 760px;
  max-height: 88vh;
  overflow-y: auto;
  color: #fff;
  font-family: system-ui, sans-serif;
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #2a2a2a;
}
.modal-header h2 {
  margin: 0;
  font-size: 1.2rem;
}
.close-button {
  background: none;
  border: none;
  color: #aaa;
  font-size: 16px;
  cursor: pointer;
}
.modal-tabs {
  display: flex;
  gap: 4px;
  padding: 10px 16px 0;
  border-bottom: 1px solid #2a2a2a;
}
.modal-tab {
  background: none;
  border: none;
  color: #999;
  padding: 8px 14px;
  font-size: 13px;
  cursor: pointer;
  border-radius: 999px 999px 0 0;
}
.modal-tab:hover {
  color: #ddd;
}
.modal-tab.active {
  color: #fff;
  background: rgba(245, 197, 24, 0.12);
}
.modal-body {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.tab-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 0.85rem;
  color: #ccc;
  flex: 1;
}
.field input,
.field select,
.field textarea {
  background: #111;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  color: #fff;
  padding: 8px 10px;
  font: inherit;
}
.field-row {
  display: flex;
  gap: 12px;
}
.ratings-row .field {
  min-width: 0;
}
.link-row {
  align-items: flex-end;
}
.remove-button {
  background: rgba(220, 38, 38, 0.18);
  color: #fca5a5;
  border: none;
  border-radius: 8px;
  padding: 8px 10px;
  cursor: pointer;
  height: 38px;
}
.hint {
  color: #888;
  font-size: 0.8rem;
  margin: 0;
}
.form-error {
  color: #fca5a5;
  font-size: 0.85rem;
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 8px;
}
.primary-button,
.secondary-button {
  border: none;
  border-radius: 8px;
  padding: 10px 18px;
  font-weight: 600;
  cursor: pointer;
}
.primary-button {
  background: #f5c518;
  color: #111;
}
.primary-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.secondary-button {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}
</style>