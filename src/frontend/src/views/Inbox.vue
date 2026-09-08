<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { fetchUploadLimits } from '../services/settings'
import { fetchGames } from '../services/games'
import type { Game } from '../types/game'
import { uploadToInbox, listInbox, deleteInboxMedia, assignInboxMedia, fetchInboxTrash, restoreInboxMedia } from '../services/media'
import type { InboxMediaItem, TrashedInboxItem } from '../services/media'
import { startTask, updateTask, completeTask, errorTask, addFeedItem, setTaskRetry } from '../state/taskProgress'
import { refreshInboxCount } from '../state/inbox'

const maxUploadSizeMb = ref<number | null>(null)

onMounted(async () => {
  try {
    const limits = await fetchUploadLimits()
    maxUploadSizeMb.value = limits.max_upload_size_mb
  } catch {
    // non-critical, the upload flow below still works without this number
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

const inboxMedia = ref<InboxMediaItem[]>([])
const loadingInbox = ref(true)
const inboxError = ref<string | null>(null)

function pruneSelectionToCurrentItems() {
  const currentKeys = new Set(inboxMedia.value.map(itemKey))
  const pruned = new Set([...selected.value].filter((key) => currentKeys.has(key)))
  if (pruned.size !== selected.value.size) selected.value = pruned
}

async function loadInbox() {
  loadingInbox.value = true
  inboxError.value = null
  try {
    inboxMedia.value = await listInbox()
    // a partially-failed bulk action can leave `selected` pointing at items
    // that got assigned/deleted and are gone from this fresh list, drop
    // those rather than let the selection count lie
    pruneSelectionToCurrentItems()
  } catch (err) {
    inboxError.value = err instanceof Error ? err.message : 'Failed to load inbox'
  } finally {
    loadingInbox.value = false
  }
  void refreshInboxCount()
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
  input.value = ''
  // real byte-level progress against the actual upload (not a fake jump to
  // 100%), see uploadToInbox/uploadFiles in services/media.ts
  const taskId = startTask(`Uploading ${files.length} file${files.length === 1 ? '' : 's'}`, 100)

  const attempt = async () => {
    try {
      const results = await uploadToInbox(files, (fraction, speedLabel) => updateTask(taskId, Math.round(fraction * 100), undefined, speedLabel))
      const saved = results.filter((r) => r.status === 'saved')
      const rejected = results.filter((r) => r.status === 'rejected')
      uploadSummary.value = `${saved.length} uploaded${rejected.length ? `, ${rejected.length} rejected` : ''}.`
      for (const r of results) {
        addFeedItem(taskId, r.status === 'saved' ? `${r.filename} uploaded` : `${r.filename}: ${r.reason ?? 'rejected'}`)
      }
      if (saved.length === 0 && rejected.length > 0) {
        errorTask(taskId, uploadSummary.value)
      } else {
        completeTask(taskId, uploadSummary.value)
      }
      await loadInbox()
    } catch (err) {
      uploadError.value = err instanceof Error ? err.message : 'Upload failed'
      errorTask(taskId, uploadError.value)
      setTaskRetry(taskId, () => void attempt())
    } finally {
      uploading.value = false
    }
  }
  await attempt()
}

const selected = ref<Set<string>>(new Set())
function itemKey(item: { kind: string; filename: string }) {
  return `${item.kind}:${item.filename}`
}
function toggleSelected(item: InboxMediaItem) {
  const key = itemKey(item)
  if (selected.value.has(key)) selected.value.delete(key)
  else selected.value.add(key)
  selected.value = new Set(selected.value)
}
const selectedCount = computed(() => selected.value.size)
const allSelected = computed(() => inboxMedia.value.length > 0 && selectedCount.value === inboxMedia.value.length)

function toggleSelectAll() {
  selected.value = allSelected.value ? new Set() : new Set(inboxMedia.value.map(itemKey))
}

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
  } catch (err) {
    assignError.value = err instanceof Error ? err.message : 'Failed to assign media'
  } finally {
    // always reload, not just on the success path, a failure partway
    // through the loop still assigned some items, so the list needs to
    // reflect that rather than keep showing them as still unassigned
    await loadInbox()
    assigning.value = false
  }
}

const deleting = ref(false)
const deleteError = ref<string | null>(null)
const confirmingBulkDelete = ref(false)

async function removeItem(item: InboxMediaItem) {
  deleteError.value = null
  try {
    await deleteInboxMedia(item.kind, item.filename)
    selected.value.delete(itemKey(item))
    await loadInbox()
    await refreshTrash()
  } catch (err) {
    deleteError.value = err instanceof Error ? err.message : 'Failed to delete media'
  }
}

async function deleteSelected() {
  confirmingBulkDelete.value = false
  if (!selected.value.size) return
  deleting.value = true
  deleteError.value = null
  try {
    const items = inboxMedia.value.filter((m) => selected.value.has(itemKey(m)))
    for (const item of items) {
      await deleteInboxMedia(item.kind, item.filename)
    }
  } catch (err) {
    deleteError.value = err instanceof Error ? err.message : 'Failed to delete media'
  } finally {
    // always reload, not just on the success path, see assignSelected
    await loadInbox()
    await refreshTrash()
    deleting.value = false
  }
}

function formatItemDate(unixSeconds: number): string {
  return new Date(unixSeconds * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

// --- Trash: soft-deleted inbox items stay recoverable for 7 days before
// the background sweep purges them for good (features/trash/sweep.py) ----
const inboxTrash = ref<TrashedInboxItem[]>([])
const showTrash = ref(false)

async function refreshTrash() {
  try {
    inboxTrash.value = await fetchInboxTrash()
  } catch {
    // trash listing failing silently isn't worth blocking the main view
  }
}
onMounted(refreshTrash)

function daysUntil(unixSeconds: number): number {
  return Math.max(0, Math.ceil((unixSeconds - Date.now() / 1000) / 86400))
}

async function restoreItem(item: TrashedInboxItem) {
  try {
    await restoreInboxMedia(item.kind, item.filename)
    await loadInbox()
    await refreshTrash()
  } catch (err) {
    deleteError.value = err instanceof Error ? err.message : 'Failed to restore media'
  }
}
</script>

<template>
  <main class="inbox">
    <div class="inbox-top">
      <div>
        <h1>Inbox</h1>
        <p class="section-hint">
          Drop in screenshots and clips without picking a game first: sort them into games
          whenever you get to it. Images become screenshots, videos become clips automatically.
          <template v-if="maxUploadSizeMb">Each file must be under {{ maxUploadSizeMb }} MB.</template>
        </p>
      </div>
      <span class="unassigned-count">{{ inboxMedia.length }} item{{ inboxMedia.length === 1 ? '' : 's' }} unassigned</span>
    </div>

    <label class="upload-dropzone">
      <input type="file" multiple accept="image/*,video/*" hidden @change="onFilesSelected" :disabled="uploading" />
      <span v-if="uploading">Uploading…</span>
      <span v-else>Click to choose files (images and videos, any number at once)</span>
    </label>

    <div v-if="uploadSummary" class="form-success">{{ uploadSummary }}</div>
    <div v-if="uploadError" class="form-error">{{ uploadError }}</div>

    <div class="inbox-divider"></div>

    <div class="inbox-toolbar">
      <button type="button" class="secondary-button" :disabled="!inboxMedia.length" @click="toggleSelectAll">
        {{ allSelected ? 'Deselect all' : 'Select all' }}
      </button>
      <div v-if="selectedCount" class="assign-bar">
        <select v-model="assignTargetGameId">
          <option value="" disabled>Assign {{ selectedCount }} selected to…</option>
          <option v-for="game in games" :key="game.id" :value="game.id">{{ game.title }}</option>
        </select>
        <button type="button" class="secondary-button" :disabled="!assignTargetGameId || assigning" @click="assignSelected">
          {{ assigning ? 'Assigning…' : 'Assign' }}
        </button>
        <button type="button" class="danger-button" :disabled="deleting" @click="confirmingBulkDelete = true">
          {{ deleting ? 'Deleting…' : `Delete (${selectedCount})` }}
        </button>
      </div>
    </div>
    <div v-if="assignError" class="form-error">{{ assignError }}</div>
    <div v-if="deleteError" class="form-error">{{ deleteError }}</div>

    <p v-if="loadingInbox">Loading…</p>
    <p v-else-if="inboxError" class="form-error">{{ inboxError }}</p>
    <template v-else>
      <p v-if="!inboxMedia.length" class="empty-hint">Nothing waiting to be sorted: dropped files with no game picked land here.</p>

      <div v-if="screenshots.length" class="media-group">
        <span class="media-group-label">Screenshots</span>
        <div class="media-grid">
          <div v-for="item in screenshots" :key="itemKey(item)" class="media-item">
            <div
              class="media-thumb"
              :class="{ selected: selected.has(itemKey(item)) }"
              @click="toggleSelected(item)"
            >
              <div class="select-check" :class="{ checked: selected.has(itemKey(item)) }">
                <svg v-if="selected.has(itemKey(item))" viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M20 6L9 17l-5-5" />
                </svg>
              </div>
              <img :src="item.url" alt="" />
              <button type="button" class="remove-button" title="Delete" @click.stop="removeItem(item)">✕</button>
            </div>
            <span class="media-date">{{ formatItemDate(item.created_at) }}</span>
          </div>
        </div>
      </div>

      <div v-if="clips.length" class="media-group">
        <span class="media-group-label">Clips</span>
        <div class="media-grid">
          <div v-for="item in clips" :key="itemKey(item)" class="media-item">
            <div
              class="media-thumb clip"
              :class="{ selected: selected.has(itemKey(item)) }"
              @click="toggleSelected(item)"
            >
              <div class="select-check" :class="{ checked: selected.has(itemKey(item)) }">
                <svg v-if="selected.has(itemKey(item))" viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M20 6L9 17l-5-5" />
                </svg>
              </div>
              <video :src="item.url" muted></video>
              <span class="clip-badge">▶</span>
              <button type="button" class="remove-button" title="Delete" @click.stop="removeItem(item)">✕</button>
            </div>
            <span class="media-date">{{ formatItemDate(item.created_at) }}</span>
          </div>
        </div>
      </div>

      <div v-if="inboxTrash.length" class="trash-section">
        <button type="button" class="trash-toggle" @click="showTrash = !showTrash">
          {{ showTrash ? '▾' : '▸' }} Recently deleted ({{ inboxTrash.length }})
        </button>
        <ul v-if="showTrash" class="trash-list">
          <li v-for="item in inboxTrash" :key="itemKey(item)" class="trash-row">
            <span class="trash-name">{{ item.filename.split('_').slice(1).join('_') }}</span>
            <span class="trash-meta">purges in {{ daysUntil(item.purge_at) }}d</span>
            <button type="button" class="secondary-button" @click="restoreItem(item)">Restore</button>
          </li>
        </ul>
      </div>
    </template>

    <div v-if="confirmingBulkDelete" class="confirm-backdrop" @click.self="confirmingBulkDelete = false">
      <div class="confirm-dialog">
        <h3>Delete {{ selectedCount }} item{{ selectedCount === 1 ? '' : 's' }}?</h3>
        <p>Moved to trash: recoverable for 7 days, then purged for good.</p>
        <div class="confirm-actions">
          <button type="button" class="secondary-button" @click="confirmingBulkDelete = false">Cancel</button>
          <button type="button" class="danger-button" @click="deleteSelected">Delete</button>
        </div>
      </div>
    </div>
  </main>
</template>

<style scoped>
.inbox {
  padding: 84px 32px 40px;
  max-width: 1100px;
  margin: 0 auto;
  font-family: system-ui, sans-serif;
  color: #fff;
}
.inbox-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  flex-wrap: wrap;
}
.inbox h1 {
  margin: 0 0 8px;
  font-size: 1.6rem;
}
.section-hint {
  color: #999;
  font-size: 0.85rem;
  line-height: 1.6;
  margin: 0;
  max-width: 560px;
}
.unassigned-count {
  color: #999;
  font-size: 0.85rem;
  white-space: nowrap;
  padding-top: 6px;
}
.upload-dropzone {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100px;
  margin-top: 20px;
  border: 1px dashed #3a3a3a;
  border-radius: 10px;
  color: #999;
  font-size: 0.9rem;
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
.inbox-divider {
  height: 1px;
  background: #2a2a2a;
  margin: 24px 0 20px;
}
.inbox-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.assign-bar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.assign-bar select {
  background: #111;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  color: #fff;
  padding: 8px 10px;
  font-size: 0.82rem;
}
.secondary-button,
.danger-button {
  border: none;
  border-radius: 8px;
  padding: 8px 16px;
  font-weight: 600;
  font-size: 0.82rem;
  cursor: pointer;
}
.secondary-button {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}
.secondary-button:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.14);
}
.secondary-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.danger-button {
  background: rgba(220, 38, 38, 0.18);
  color: #fca5a5;
}
.danger-button:hover:not(:disabled) {
  background: rgba(220, 38, 38, 0.28);
}
.danger-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.empty-hint {
  color: #777;
  font-size: 0.9rem;
}
.media-group {
  margin-bottom: 22px;
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
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: 10px;
}
.media-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.media-date {
  color: #777;
  font-size: 0.72rem;
  text-align: center;
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
.select-check {
  position: absolute;
  top: 4px;
  left: 4px;
  width: 20px;
  height: 20px;
  border-radius: 6px;
  border: 2px solid rgba(255, 255, 255, 0.5);
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #111;
  z-index: 1;
}
.select-check.checked {
  background: #d68a34;
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
.trash-section {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #2a2a2a;
}
.trash-toggle {
  background: none;
  border: none;
  color: #999;
  font-size: 0.85rem;
  cursor: pointer;
  padding: 0;
}
.trash-toggle:hover {
  color: #ccc;
}
.trash-list {
  list-style: none;
  margin: 12px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.trash-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid #232323;
  border-radius: 8px;
  font-size: 0.82rem;
}
.trash-name {
  flex: 1;
  color: #ccc;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.trash-meta {
  color: #777;
  font-size: 0.76rem;
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
.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

@media (max-width: 760px) {
  .inbox {
    padding: 84px 16px 32px;
  }
}
</style>
