<script setup lang="ts">
import { ref, onMounted } from "vue";
import {
  fetchLibraryExport,
  importLibrary,
  fetchBackupStatus,
} from "../../services/exportImport";
import type { ImportResult, BackupStatus } from "../../services/exportImport";

const backupStatus = ref<BackupStatus | null>(null);
onMounted(async () => {
  try {
    backupStatus.value = await fetchBackupStatus();
  } catch {
    // status tile just doesn't show, not worth failing the whole page over
  }
});
function formatBackupDate(epochSeconds: number): string {
  return new Date(epochSeconds * 1000).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

const exporting = ref(false);
const exportError = ref<string | null>(null);

async function exportLibrary() {
  exporting.value = true;
  exportError.value = null;
  try {
    const data = await fetchLibraryExport();
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const date = new Date().toISOString().slice(0, 10);
    const link = document.createElement("a");
    link.href = url;
    link.download = `library-export-${date}.json`;
    link.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    exportError.value =
      err instanceof Error ? err.message : "Failed to export library";
  } finally {
    exporting.value = false;
  }
}

const importing = ref(false);
const importError = ref<string | null>(null);
const importResult = ref<ImportResult | null>(null);

async function onFileSelected(e: Event) {
  const input = e.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;

  importing.value = true;
  importError.value = null;
  importResult.value = null;

  try {
    const text = await file.text();
    const parsed = JSON.parse(text);
    const games = Array.isArray(parsed) ? parsed : parsed.games;
    if (!Array.isArray(games)) {
      throw new Error(
        'This file doesn\'t look like a library export, expected a "games" list.',
      );
    }
    importResult.value = await importLibrary(games);
  } catch (err) {
    importError.value =
      err instanceof Error ? err.message : "Failed to import library";
  } finally {
    importing.value = false;
    // otherwise re-picking the same file for a second attempt fires no
    // 'change' event at all
    input.value = "";
  }
}
</script>

<template>
  <section class="settings-section">
    <h2>Export / Import</h2>
    <p class="section-hint">
      A portable JSON snapshot of your games, for backups, or moving to a new
      server. This covers game data and metadata only, not attached files
      (screenshots, saves, docs) or bounties.
    </p>

    <div v-if="backupStatus" class="tile backup-status-tile">
      <h3>Automatic backups</h3>
      <p class="tile-desc">
        A snapshot like the one above is written automatically every
        {{ backupStatus.interval_hours }} hours, keeping the last
        {{ backupStatus.backups_kept }} on this server, a safety net, not a
        replacement for the manual export below (nothing here can be downloaded
        directly; it's the same file shape, stored server-side).
      </p>
      <p class="backup-status-line">
        <span v-if="backupStatus.last_backup_at">
          Last backup {{ formatBackupDate(backupStatus.last_backup_at) }} ·
          {{ backupStatus.backup_count }} kept
        </span>
        <span v-else
          >No backup yet, the first one is written within
          {{ backupStatus.interval_hours }} hours of the server starting.</span
        >
      </p>
    </div>

    <div class="tile">
      <h3>Export</h3>
      <p class="tile-desc">
        Downloads every game in your library as a single JSON file.
      </p>
      <div v-if="exportError" class="form-error">{{ exportError }}</div>
      <button
        type="button"
        class="primary-button"
        :disabled="exporting"
        @click="exportLibrary"
      >
        {{ exporting ? "Exporting…" : "Export library" }}
      </button>
    </div>

    <div class="tile">
      <h3>Import</h3>
      <p class="tile-desc">
        Add games from a previously exported file. Existing games are never
        overwritten, a folder name collision gets a numbered suffix instead of
        failing the whole import.
      </p>
      <div v-if="importError" class="form-error">{{ importError }}</div>
      <div v-if="importResult" class="form-success">
        Imported {{ importResult.created }} game{{
          importResult.created === 1 ? "" : "s"
        }}.
        <template v-if="importResult.skipped"
          >{{ importResult.skipped }} skipped.</template
        >
        <ul v-if="importResult.errors.length" class="import-errors">
          <li v-for="(err, i) in importResult.errors" :key="i">{{ err }}</li>
        </ul>
      </div>
      <label class="secondary-button upload-label">
        {{ importing ? "Importing…" : "Choose file…" }}
        <input
          type="file"
          accept="application/json"
          class="hidden-input"
          :disabled="importing"
          @change="onFileSelected"
        />
      </label>
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
  margin: 0 0 20px;
}
.tile {
  background: #111;
  border: 1px solid #2a2a2a;
  border-radius: 10px;
  padding: 18px 20px;
  margin-bottom: 16px;
}
.tile h3 {
  margin: 0 0 6px;
  font-size: 0.9rem;
  color: #fff;
}
.tile-desc {
  color: #999;
  font-size: 0.8rem;
  line-height: 1.5;
  margin: 0 0 14px;
}
.backup-status-tile {
  border-color: rgba(214, 138, 52, 0.3);
  background: rgba(214, 138, 52, 0.04);
}
.backup-status-line {
  margin: 0;
  color: #d68a34;
  font-size: 0.78rem;
  font-weight: 600;
}
.primary-button {
  background: #d68a34;
  color: #111;
  border: none;
  border-radius: 8px;
  padding: 11px 20px;
  font-weight: 600;
  cursor: pointer;
}
.primary-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.secondary-button {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 10px 16px;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
}
.upload-label {
  display: inline-block;
  cursor: pointer;
}
.hidden-input {
  display: none;
}
.form-error {
  color: #fca5a5;
  font-size: 13px;
  background: rgba(220, 38, 38, 0.1);
  border: 1px solid rgba(220, 38, 38, 0.3);
  border-radius: 8px;
  padding: 8px 10px;
  margin-bottom: 12px;
}
.form-success {
  color: #86efac;
  font-size: 13px;
  background: rgba(34, 197, 94, 0.1);
  border: 1px solid rgba(34, 197, 94, 0.3);
  border-radius: 8px;
  padding: 8px 10px;
  margin-bottom: 12px;
}
.import-errors {
  margin: 8px 0 0;
  padding-left: 18px;
  color: #fca5a5;
  font-size: 12px;
}
</style>
