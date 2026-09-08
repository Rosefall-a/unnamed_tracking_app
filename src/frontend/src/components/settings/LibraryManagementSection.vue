<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { fetchGames, refreshGameMetadata, previewGameMetadataRefresh, fetchGameTrash, restoreGame } from '../../services/games'
import type {
  RefreshMetadataOptions,
  RefreshMetadataOutcome,
  RefreshMetadataResult,
  RefreshMetadataPreview,
  TrashedGame,
} from '../../services/games'
import type { Game } from '../../types/game'
import ToggleButton from './ToggleButton.vue'
import { startTask, updateTask, completeTask, errorTask, addFeedItem } from '../../state/taskProgress'

// how many games are refreshed in parallel at once, high enough to be a
// real speedup, low enough not to hammer external metadata APIs or exceed
// the browser's ~6 connections-per-origin cap (each in-flight game can hold
// a search + patch + 2 asset-check requests briefly, so this stays well
// under 6 even with other page activity sharing the same origin)
const REFRESH_CONCURRENCY = 4

async function runInBatches<T, R>(items: T[], concurrency: number, worker: (item: T) => Promise<R>): Promise<R[]> {
  const results: R[] = new Array(items.length)
  let cursor = 0
  async function runNext(): Promise<void> {
    const index = cursor++
    if (index >= items.length) return
    results[index] = await worker(items[index])
    await runNext()
  }
  await Promise.all(Array.from({ length: Math.min(concurrency, items.length) }, runNext))
  return results
}

interface RefreshLogEntry {
  title: string
  result: RefreshMetadataResult
}

const refreshing = ref(false)
const refreshProgress = ref({ done: 0, total: 0 })
const refreshResults = ref<RefreshLogEntry[]>([])
const imagesAddedCount = ref(0)
const refreshError = ref<string | null>(null)

const refreshUpdateText = ref(true)
const refreshFillMissingArt = ref(true)
const refreshOverwriteArt = ref(false)
const lastRunOverwrote = ref(false)

const updatedCount = computed(() => refreshResults.value.filter((r) => r.result === 'updated').length)
const noMatchCount = computed(() => refreshResults.value.filter((r) => r.result === 'no-match').length)
const errorCount = computed(() => refreshResults.value.filter((r) => r.result === 'error').length)
const unresolvedResults = computed(() => refreshResults.value.filter((r) => r.result !== 'updated'))

function currentOptions(): RefreshMetadataOptions {
  return {
    updateText: refreshUpdateText.value,
    fillMissingArt: refreshFillMissingArt.value,
    overwriteExistingArt: refreshOverwriteArt.value,
  }
}

function describeOptions(options: RefreshMetadataOptions): string[] {
  const parts: string[] = []
  if (options.updateText) {
    parts.push('description, developer, publisher, release date, age rating, and tags/features')
  }
  if (options.overwriteExistingArt) {
    parts.push('cover/banner art: INCLUDING replacing art you already have')
  } else if (options.fillMissingArt) {
    parts.push('cover/banner art, only for games that currently have none')
  }
  return parts
}

// --- Dry run: shows exactly which games would actually change before any
// real write happens, the old flow committed on a single generic
// window.confirm with no visibility into whether a refresh would even do
// anything different from what's already there. ------------------------
interface PreviewEntry {
  game: Game
  preview: RefreshMetadataPreview
}
const previewing = ref(false)
const previewResults = ref<PreviewEntry[]>([])
const showPreviewDialog = ref(false)
const previewError = ref<string | null>(null)

const previewWithChanges = computed(() =>
  previewResults.value.filter(
    (e) => e.preview.status === 'updated' && (e.preview.changedFields.length || e.preview.wouldAddKeyArt || e.preview.wouldAddBanner),
  ),
)
const previewUnchanged = computed(
  () => previewResults.value.filter((e) => e.preview.status === 'updated' && !previewWithChanges.value.includes(e)).length,
)
const previewNoMatch = computed(() => previewResults.value.filter((e) => e.preview.status === 'no-match').length)
const previewErrors = computed(() => previewResults.value.filter((e) => e.preview.status === 'error').length)

function previewChangeSummary(preview: RefreshMetadataPreview): string {
  const parts = [...preview.changedFields]
  if (preview.wouldAddKeyArt) parts.push('cover art')
  if (preview.wouldAddBanner) parts.push('banner art')
  return parts.join(', ')
}

async function previewRefresh() {
  const options = currentOptions()
  previewing.value = true
  previewError.value = null
  if (!describeOptions(options).length) {
    previewError.value = 'Nothing is selected to refresh: check at least one option below.'
    previewing.value = false
    return
  }
  previewResults.value = []
  let taskId: string | null = null
  try {
    const games = await fetchGames()
    taskId = startTask('Checking what would change', games.length, { indeterminate: false })
    let done = 0
    previewResults.value = await runInBatches(games, REFRESH_CONCURRENCY, async (game: Game) => {
      const preview = await previewGameMetadataRefresh(game, options)
      done++
      if (taskId) updateTask(taskId, done)
      return { game, preview }
    })
    if (taskId) completeTask(taskId, `${previewWithChanges.value.length} would change`)
    showPreviewDialog.value = true
  } catch (err) {
    previewError.value = err instanceof Error ? err.message : 'Failed to check for changes'
    if (taskId) errorTask(taskId, previewError.value)
  } finally {
    previewing.value = false
  }
}

async function applyPreviewedRefresh() {
  showPreviewDialog.value = false
  const options = currentOptions()
  // only the games the preview actually flagged as changing, the button
  // itself is labeled "Apply to N games" using this same count, so applying
  // to every previewed game (including no-match/already-up-to-date/error
  // ones) would silently do more than what was shown and confirmed
  const games = previewWithChanges.value.map((e) => e.game)

  refreshing.value = true
  refreshResults.value = []
  imagesAddedCount.value = 0
  lastRunOverwrote.value = options.overwriteExistingArt
  refreshError.value = null

  let taskId: string | null = null
  try {
    refreshProgress.value = { done: 0, total: games.length }
    taskId = startTask('Refreshing metadata', games.length)
    let doneCount = 0

    await runInBatches(games, REFRESH_CONCURRENCY, async (game: Game) => {
      const outcome: RefreshMetadataOutcome = await refreshGameMetadata(game, options)
      refreshResults.value.push({ title: game.title, result: outcome.status })
      if (outcome.keyArtAdded) imagesAddedCount.value++
      if (outcome.bannerAdded) imagesAddedCount.value++
      doneCount++
      refreshProgress.value.done = doneCount
      if (taskId) {
        updateTask(taskId, doneCount)
        addFeedItem(taskId, outcome.status === 'updated' ? `${game.title} updated` : `${game.title}: no match`)
      }
    })

    if (taskId) completeTask(taskId, `${updatedCount.value} updated, ${errorCount.value} failed`)
  } catch (err) {
    refreshError.value = err instanceof Error ? err.message : 'Failed to refresh metadata'
    if (taskId) errorTask(taskId, refreshError.value)
  } finally {
    refreshing.value = false
  }
}

// duplicate folder_location scan, entirely client-side against the already
// fetched game list, no new backend endpoint needed
const scanningDuplicates = ref(false)
const duplicateGroups = ref<{ folderLocation: string; titles: string[] }[]>([])
const duplicateScanRan = ref(false)
const duplicateScanError = ref<string | null>(null)

async function scanForDuplicateFolders() {
  scanningDuplicates.value = true
  duplicateScanRan.value = false
  duplicateScanError.value = null
  try {
    const games = await fetchGames()
    const byFolder = new Map<string, string[]>()
    for (const game of games) {
      if (!game.folderLocation) continue
      const list = byFolder.get(game.folderLocation) ?? []
      list.push(game.title)
      byFolder.set(game.folderLocation, list)
    }
    duplicateGroups.value = Array.from(byFolder.entries())
      .filter(([, titles]) => titles.length > 1)
      .map(([folderLocation, titles]) => ({ folderLocation, titles }))
    duplicateScanRan.value = true
  } catch (err) {
    duplicateScanError.value = err instanceof Error ? err.message : 'Failed to scan for duplicates'
  } finally {
    scanningDuplicates.value = false
  }
}

// --- Deleted games: soft-deleted, recoverable for 7 days before the
// background sweep purges them for good (features/trash/sweep.py) --------
const gameTrash = ref<TrashedGame[]>([])
const loadingGameTrash = ref(false)
const gameTrashError = ref<string | null>(null)
const restoringGameId = ref<string | null>(null)

async function refreshGameTrash() {
  loadingGameTrash.value = true
  gameTrashError.value = null
  try {
    gameTrash.value = await fetchGameTrash()
  } catch (err) {
    gameTrashError.value = err instanceof Error ? err.message : 'Failed to load deleted games'
  } finally {
    loadingGameTrash.value = false
  }
}
onMounted(refreshGameTrash)

function daysUntil(unixSeconds: number): number {
  return Math.max(0, Math.ceil((unixSeconds - Date.now() / 1000) / 86400))
}

async function restoreGameById(game: TrashedGame) {
  restoringGameId.value = game.id
  gameTrashError.value = null
  try {
    await restoreGame(game.id)
    await refreshGameTrash()
  } catch (err) {
    gameTrashError.value = err instanceof Error ? err.message : 'Failed to restore game'
  } finally {
    restoringGameId.value = null
  }
}
</script>

<template>
  <section class="settings-section">
    <h2>Refresh Metadata</h2>
    <p class="section-hint">
      Re-fetches from Steam / SteamGridDB for every game: only applied when a search
      result's title matches exactly, so nothing gets guessed. Notes and achievements are
      never touched by this, no matter which options below are on.
    </p>

    <div class="refresh-options">
      <ToggleButton v-model="refreshUpdateText" label="Update text fields">
        Update text fields (description, developer, publisher, release date, age rating,
        tags/features): always a full refresh, replacing whatever's already there
      </ToggleButton>
      <ToggleButton v-model="refreshFillMissingArt" label="Fill missing art" :disabled="refreshOverwriteArt">
        Fill in cover/banner art for games that currently have none
      </ToggleButton>
      <ToggleButton v-model="refreshOverwriteArt" label="Overwrite art">
        <span class="warning-text">Also replace art on games that already have it (overwrites anything you've set)</span>
      </ToggleButton>
    </div>

    <button type="button" class="secondary-button" :disabled="refreshing || previewing" @click="previewRefresh">
      {{ previewing ? 'Checking what would change…' : refreshing ? `Refreshing… (${refreshProgress.done}/${refreshProgress.total})` : 'Preview Refresh' }}
    </button>
    <p class="section-hint" style="margin: 8px 0 0">
      Shows exactly which games would actually change before anything is written: nothing is
      applied until you confirm.
    </p>

    <div v-if="previewError" class="form-error">{{ previewError }}</div>
    <div v-if="refreshError" class="form-error">{{ refreshError }}</div>

    <div v-if="!refreshing && refreshResults.length" class="refresh-summary">
      <p>
        {{ updatedCount }} updated, {{ noMatchCount }} skipped (no exact title match), {{ errorCount }} failed.
        <template v-if="imagesAddedCount">
          {{ imagesAddedCount }} image{{ imagesAddedCount === 1 ? '' : 's' }}
          {{ lastRunOverwrote ? 'set (including replacing existing art).' : 'added for previously blank games.' }}
        </template>
      </p>
      <ul v-if="unresolvedResults.length" class="refresh-list">
        <li v-for="entry in unresolvedResults" :key="entry.title">
          {{ entry.title }}: {{ entry.result === 'no-match' ? 'no exact match' : 'failed' }}
        </li>
      </ul>
    </div>
  </section>

  <div v-if="showPreviewDialog" class="confirm-backdrop" @click.self="showPreviewDialog = false">
    <div class="confirm-dialog preview-dialog">
      <h3>Refresh preview</h3>
      <p>
        <strong>{{ previewWithChanges.length }}</strong> game{{ previewWithChanges.length === 1 ? '' : 's' }} would
        actually change, {{ previewUnchanged }} matched but are already up to date,
        {{ previewNoMatch }} have no exact title match, {{ previewErrors }} failed to check.
      </p>
      <ul v-if="previewWithChanges.length" class="preview-change-list">
        <li v-for="entry in previewWithChanges" :key="entry.game.id">
          <span class="preview-change-title">{{ entry.game.title }}</span>
          <span class="preview-change-fields">{{ previewChangeSummary(entry.preview) }}</span>
        </li>
      </ul>
      <p v-else class="section-hint" style="margin-top: 10px">
        Nothing would actually change: every matched game already has this data.
      </p>
      <div class="confirm-actions">
        <button type="button" class="secondary-button" @click="showPreviewDialog = false">Cancel</button>
        <button
          type="button"
          class="primary-button"
          :disabled="!previewWithChanges.length"
          @click="applyPreviewedRefresh"
        >
          Apply to {{ previewWithChanges.length }} game{{ previewWithChanges.length === 1 ? '' : 's' }}
        </button>
      </div>
    </div>
  </div>

  <div class="settings-divider"></div>

  <section class="settings-section">
    <h2>Duplicate Folders</h2>
    <p class="section-hint">
      Checks whether more than one game is pointing at the same storage folder: a sign
      something got mis-imported or renamed incorrectly.
    </p>

    <button type="button" class="secondary-button" :disabled="scanningDuplicates" @click="scanForDuplicateFolders">
      {{ scanningDuplicates ? 'Scanning…' : 'Scan for Duplicates' }}
    </button>

    <div v-if="duplicateScanError" class="form-error">{{ duplicateScanError }}</div>
    <div v-if="duplicateScanRan" class="refresh-summary">
      <p v-if="!duplicateGroups.length">No duplicate folders found.</p>
      <ul v-else class="refresh-list">
        <li v-for="group in duplicateGroups" :key="group.folderLocation">
          <strong>{{ group.folderLocation }}</strong>: {{ group.titles.join(', ') }}
        </li>
      </ul>
    </div>
  </section>

  <div class="settings-divider"></div>

  <section class="settings-section">
    <h2>Deleted Games</h2>
    <p class="section-hint">
      A deleted game moves here first: recoverable for 7 days before it's purged for good,
      along with its screenshots, clips, saves, notes, and everything else.
    </p>

    <p v-if="loadingGameTrash">Loading…</p>
    <div v-if="gameTrashError" class="form-error">{{ gameTrashError }}</div>
    <p v-if="!loadingGameTrash && !gameTrash.length" class="empty-hint">Nothing in trash.</p>
    <ul v-else class="trash-list">
      <li v-for="game in gameTrash" :key="game.id" class="trash-row">
        <span class="trash-name">{{ game.title }}</span>
        <span class="trash-meta">purges in {{ daysUntil(game.purge_at) }}d</span>
        <button
          type="button"
          class="secondary-button"
          :disabled="restoringGameId === game.id"
          @click="restoreGameById(game)"
        >
          {{ restoringGameId === game.id ? 'Restoring…' : 'Restore' }}
        </button>
      </li>
    </ul>
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
.section-hint {
  color: #999;
  font-size: 0.82rem;
  line-height: 1.6;
  margin: 0 0 16px;
}
.settings-divider {
  height: 1px;
  background: #2a2a2a;
  margin: 24px 0;
}
.refresh-options {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 16px;
}
.warning-text {
  color: #f0b458;
}
.secondary-button {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 10px 18px;
  font-weight: 600;
  cursor: pointer;
}
.secondary-button:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.14);
}
.secondary-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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
.refresh-summary {
  margin-top: 14px;
  font-size: 0.82rem;
  color: #ccc;
}
.refresh-summary p {
  margin: 0 0 8px;
}
.refresh-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 160px;
  overflow-y: auto;
  color: #999;
  font-size: 0.78rem;
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
  color: #fff;
}
.confirm-dialog p {
  margin: 0 0 16px;
  color: #aaa;
  font-size: 13.5px;
}
.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
.preview-dialog {
  max-width: 480px;
}
.preview-change-list {
  list-style: none;
  margin: 0 0 16px;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 260px;
  overflow-y: auto;
}
.preview-change-list li {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid #232323;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 12.5px;
}
.preview-change-title {
  color: #fff;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.preview-change-fields {
  color: #d68a34;
  text-align: right;
  flex-shrink: 0;
}
.primary-button {
  background: #d68a34;
  color: #111;
  border: none;
  border-radius: 8px;
  padding: 9px 16px;
  font-weight: 600;
  cursor: pointer;
}
.primary-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.empty-hint {
  color: #777;
  font-size: 0.82rem;
}
.trash-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.trash-row {
  display: flex;
  align-items: center;
  gap: 12px;
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
</style>
