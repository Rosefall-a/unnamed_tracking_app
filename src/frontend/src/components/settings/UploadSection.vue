<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { fetchUploadLimits } from '../../services/settings'
import { fetchGames } from '../../services/games'
import type { Game } from '../../types/game'
import { uploadToInbox, listInbox, deleteInboxMedia, assignInboxMedia } from '../../services/media'
import type { MediaItem } from '../../services/media'
import { startTask, completeTask, errorTask } from '../../state/taskProgress'

const maxUploadSizeMb = ref<number | null>(null)

onMounted(async () => {
  try {
    const limits = await fetchUploadLimits()
    maxUploadSizeMb.value = limits.max_upload_size_mb
  } catch {
    // non-critical — the upload flow below still works without this number
  }
})

const games = ref<Game[]>([])
onMounted(async () => {
  try {
    games.value = await fetchGames()
  } catch {
    // game picker just stays empty; assign still shows an error if attempted
  }
})

const inboxMedia = ref<MediaItem[]>([])
const loadingInbox = ref(true)
const inboxError = ref<string | null>(null)

async function loadInbox() {
  loadingInbox.value = true
  inboxError.value = null
  try {
    inboxMedia.value = await listInbox()
  } catch (err) {
    inboxError.value = err instanceof Error ? err.message : 'Failed to load inbox'
  } finally {
    loadingInbox.value = false
  }
}
onMounted(loadInbox)

const screenshots = computed(() => inboxMedia.value.filter((m) => m.kind === 'screenshot'))
const clips = computed(() => inboxMedia.value.filter((m) => m.kind === 'clip'))

const uploading = ref(false)
const uploadSummary = ref<string | null>(null)
const uploadError = ref<string | null>(null)

async function onFilesSelected(e: Event) {
  const input = e.target as HTMLInputElement
  const files = Array.from(input.files ?? [])
  if (!files.length) return

  uploading.value = true
  uploadSummary.value = null
  uploadError.value = null
  const taskId = startTask(`Uploading ${files.length} file${files.length === 1 ? '' : 's'}`, files.length)
  try {
    const results = await uploadToInbox(files)
    const saved = results.filter((r) => r.status === 'saved').length
    const rejected = results.filter((r) => r.status === 'rejected')
    uploadSummary.value = `${saved} uploaded${rejected.length ? `, ${rejected.length} skipped (unsupported file type or too large)` : ''}.`
    completeTask(taskId, uploadSummary.value)
    await loadInbox()
  } catch (err) {
    uploadError.value = err instanceof Error ? err.message : 'Upload failed'
    errorTask(taskId, uploadError.value)
  } finally {
    uploading.value = false
    input.value = ''
  }
}

const selected = ref<Set<string>>(new Set())
function itemKey(item: MediaItem) {
  return `${item.kind}:${item.filename}`
}
function toggleSelected(item: MediaItem) {
  const key = itemKey(item)
  if (selected.value.has(key)) selected.value.delete(key)
  else selected.value.add(key)
  selected.value = new Set(selected.value)
}
const selectedCount = computed(() => selected.value.size)

const assignTargetGameId = ref('')
const assigning = ref(false)
const assignError = ref<string | null>(null)

async function assignSelected() {
  if (!assignTargetGameId.value || !selected.value.size) return
  assigning.value = true
  assignError.value = null
  try {
    const items = inboxMedia.value.filter((m) => selected.value.has(itemKey(m)))
    for (const item of items) {
      await assignInboxMedia(item.kind, item.filename, assignTargetGameId.value)
    }
    selected.value = new Set()
    assignTargetGameId.value = ''
    await loadInbox()
  } catch (err) {
    assignError.value = err instanceof Error ? err.message : 'Failed to assign media'
  } finally {
    assigning.value = false
  }
}

async function removeItem(item: MediaItem) {
  try {
    await deleteInboxMedia(item.kind, item.filename)
    await loadInbox()
  } catch (err) {
    inboxError.value = err instanceof Error ? err.message : 'Failed to delete media'
  }
}
</script>

<template>
  <section class="settings-section">
    <h2>Upload</h2>
    <p class="section-hint">
      Bulk-upload screenshots and clips without picking a game first — drop in everything at
      once, then group and assign them below. Images become screenshots, videos become clips
      automatically.
      <template v-if="maxUploadSizeMb">Each file must be under {{ maxUploadSizeMb }} MB.</template>
    </p>

    <label class="upload-dropzone">
      <input type="file" multiple accept="image/*,video/*" hidden @change="onFilesSelected" :disabled="uploading" />
      <span v-if="uploading">Uploading…</span>
      <span v-else>Click to choose files (images and videos, any number at once)</span>
    </label>

    <div v-if="uploadSummary" class="form-success">{{ uploadSummary }}</div>
    <div v-if="uploadError" class="form-error">{{ uploadError }}</div>

    <div class="settings-divider"></div>

    <div class="inbox-header">
      <h3>Unassigned ({{ inboxMedia.length }})</h3>
      <div v-if="selectedCount" class="assign-bar">
        <select v-model="assignTargetGameId">
          <option value="" disabled>Assign {{ selectedCount }} selected to…</option>
          <option v-for="game in games" :key="game.id" :value="game.id">{{ game.title }}</option>
        </select>
        <button type="button" class="primary-button" :disabled="!assignTargetGameId || assigning" @click="assignSelected">
          {{ assigning ? 'Assigning…' : 'Assign' }}
        </button>
      </div>
    </div>
    <div v-if="assignError" class="form-error">{{ assignError }}</div>

    <p v-if="loadingInbox">Loading…</p>
    <p v-else-if="inboxError" class="form-error">{{ inboxError }}</p>
    <template v-else>
      <p v-if="!inboxMedia.length" class="empty-hint">Nothing waiting to be sorted.</p>

      <div v-if="screenshots.length" class="media-group">
        <span class="media-group-label">Screenshots</span>
        <div class="media-grid">
          <div
            v-for="item in screenshots"
            :key="itemKey(item)"
            class="media-thumb"
            :class="{ selected: selected.has(itemKey(item)) }"
            @click="toggleSelected(item)"
          >
            <img :src="item.url" alt="" />
            <button type="button" class="remove-button" title="Delete" @click.stop="removeItem(item)">✕</button>
          </div>
        </div>
      </div>

      <div v-if="clips.length" class="media-group">
        <span class="media-group-label">Clips</span>
        <div class="media-grid">
          <div
            v-for="item in clips"
            :key="itemKey(item)"
            class="media-thumb clip"
            :class="{ selected: selected.has(itemKey(item)) }"
            @click="toggleSelected(item)"
          >
            <video :src="item.url" muted></video>
            <span class="clip-badge">▶</span>
            <button type="button" class="remove-button" title="Delete" @click.stop="removeItem(item)">✕</button>
          </div>
        </div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.settings-section h2 {
  margin: 0 0 8px;
  padding-left: 12px;
  border-left: 3px solid #d68a34;
  font-size: 1rem;
  color: #fff;
}
.settings-section h3 {
  margin: 0;
  font-size: 0.9rem;
  color: #fff;
}
.section-hint {
  color: #999;
  font-size: 0.82rem;
  line-height: 1.6;
  margin: 0 0 16px;
}
.settings-divider {
  height: 1px;
  background: #2a2a2a;
  margin: 20px 0;
}
.upload-dropzone {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 90px;
  border: 1px dashed #3a3a3a;
  border-radius: 10px;
  color: #999;
  font-size: 0.85rem;
  cursor: pointer;
  transition: border-color 0.15s ease, color 0.15s ease;
}
.upload-dropzone:hover {
  border-color: #d68a34;
  color: #d68a34;
}
.form-error {
  color: #fca5a5;
  font-size: 13px;
  background: rgba(220, 38, 38, 0.1);
  border: 1px solid rgba(220, 38, 38, 0.3);
  border-radius: 8px;
  padding: 8px 10px;
  margin-top: 10px;
}
.form-success {
  color: #86efac;
  font-size: 13px;
  background: rgba(34, 197, 94, 0.1);
  border: 1px solid rgba(34, 197, 94, 0.3);
  border-radius: 8px;
  padding: 8px 10px;
  margin-top: 10px;
}
.inbox-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.assign-bar {
  display: flex;
  gap: 8px;
}
.assign-bar select {
  background: #111;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  color: #fff;
  padding: 8px 10px;
  font-size: 0.82rem;
}
.primary-button {
  background: #d68a34;
  color: #111;
  border: none;
  border-radius: 8px;
  padding: 8px 16px;
  font-weight: 600;
  font-size: 0.82rem;
  cursor: pointer;
}
.primary-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.empty-hint {
  color: #777;
  font-size: 0.85rem;
}
.media-group {
  margin-bottom: 18px;
}
.media-group-label {
  display: block;
  color: #999;
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  margin-bottom: 8px;
}
.media-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 8px;
}
.media-thumb {
  position: relative;
  aspect-ratio: 16 / 9;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  border: 2px solid transparent;
  background: #111;
}
.media-thumb img,
.media-thumb video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.media-thumb.selected {
  border-color: #d68a34;
}
.clip-badge {
  position: absolute;
  bottom: 4px;
  left: 4px;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  font-size: 10px;
  padding: 2px 5px;
  border-radius: 4px;
}
.remove-button {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: none;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  font-size: 11px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
