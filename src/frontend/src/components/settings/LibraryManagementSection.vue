<script setup lang="ts">
import { ref, computed } from 'vue'
import { fetchGames, refreshGameMetadata } from '../../services/games'
import type { RefreshMetadataOptions, RefreshMetadataOutcome, RefreshMetadataResult } from '../../services/games'
import type { Game } from '../../types/game'
import ToggleButton from './ToggleButton.vue'
import { startTask, updateTask, completeTask, errorTask } from '../../state/taskProgress'

// how many games are refreshed in parallel at once — high enough to be a
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

async function refreshAllMetadata() {
  const options: RefreshMetadataOptions = {
    updateText: refreshUpdateText.value,
    fillMissingArt: refreshFillMissingArt.value,
    overwriteExistingArt: refreshOverwriteArt.value,
  }

  const parts: string[] = []
  if (options.updateText) {
    parts.push('description, developer, publisher, release date, age rating, and tags/features')
  }
  if (options.overwriteExistingArt) {
    parts.push('cover/banner art — INCLUDING replacing art you already have')
  } else if (options.fillMissingArt) {
    parts.push('cover/banner art, only for games that currently have none')
  }
  if (!parts.length) {
    window.alert('Nothing is selected to refresh — check at least one option below.')
    return
  }

  const confirmed = window.confirm(
    `Refresh from Steam/SteamGridDB for every game?\n\nThis updates: ${parts.join('; ')}.\n\n` +
      'Only applied to games whose title matches a search result exactly. Notes and ' +
      'achievements are never touched by this, regardless of the options below.',
  )
  if (!confirmed) return

  refreshing.value = true
  refreshResults.value = []
  imagesAddedCount.value = 0
  lastRunOverwrote.value = options.overwriteExistingArt
  refreshError.value = null

  let taskId: string | null = null
  try {
    const games = await fetchGames()
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
      if (taskId) updateTask(taskId, doneCount)
    })

    if (taskId) completeTask(taskId, `${updatedCount.value} updated, ${errorCount.value} failed`)
  } catch (err) {
    refreshError.value = err instanceof Error ? err.message : 'Failed to refresh metadata'
    if (taskId) errorTask(taskId, refreshError.value)
  } finally {
    refreshing.value = false
  }
}

// duplicate folder_location scan — entirely client-side against the already
// fetched game list, no new backend endpoint needed
const scanningDuplicates = ref(false)
const duplicateGroups = ref<{ folderLocation: string; titles: string[] }[]>([])
const duplicateScanRan = ref(false)

async function scanForDuplicateFolders() {
  scanningDuplicates.value = true
  duplicateScanRan.value = false
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
  } finally {
    scanningDuplicates.value = false
  }
}
</script>

<template>
  <section class="settings-section">
    <h2>Refresh Metadata</h2>
    <p class="section-hint">
      Re-fetches from Steam / SteamGridDB for every game — only applied when a search
      result's title matches exactly, so nothing gets guessed. Notes and achievements are
      never touched by this, no matter which options below are on.
    </p>

    <div class="refresh-options">
      <ToggleButton v-model="refreshUpdateText" label="Update text fields">
        Update text fields (description, developer, publisher, release date, age rating, tags/features)
      </ToggleButton>
      <ToggleButton v-model="refreshFillMissingArt" label="Fill missing art" :disabled="refreshOverwriteArt">
        Fill in cover/banner art for games that currently have none
      </ToggleButton>
      <ToggleButton v-model="refreshOverwriteArt" label="Overwrite art">
        <span class="warning-text">Also replace art on games that already have it (overwrites anything you've set)</span>
      </ToggleButton>
    </div>

    <button type="button" class="secondary-button" :disabled="refreshing" @click="refreshAllMetadata">
      {{ refreshing ? `Refreshing… (${refreshProgress.done}/${refreshProgress.total})` : 'Refresh All Games' }}
    </button>

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
          {{ entry.title }} — {{ entry.result === 'no-match' ? 'no exact match' : 'failed' }}
        </li>
      </ul>
    </div>
  </section>

  <div class="settings-divider"></div>

  <section class="settings-section">
    <h2>Duplicate Folders</h2>
    <p class="section-hint">
      Checks whether more than one game is pointing at the same storage folder — a sign
      something got mis-imported or renamed incorrectly.
    </p>

    <button type="button" class="secondary-button" :disabled="scanningDuplicates" @click="scanForDuplicateFolders">
      {{ scanningDuplicates ? 'Scanning…' : 'Scan for Duplicates' }}
    </button>

    <div v-if="duplicateScanRan" class="refresh-summary">
      <p v-if="!duplicateGroups.length">No duplicate folders found.</p>
      <ul v-else class="refresh-list">
        <li v-for="group in duplicateGroups" :key="group.folderLocation">
          <strong>{{ group.folderLocation }}</strong> — {{ group.titles.join(', ') }}
        </li>
      </ul>
    </div>
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
</style>
