<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import { useConfirm } from "../../state/dialog";
import {
  fetchBackups,
  updateBackupSettings,
  runBackupsNow,
  deleteBackup,
  backupDownloadUrl,
  fetchLeftovers,
  deleteLeftover,
} from "../../services/settings";
import type {
  BackupOverview,
  BackupFile,
  Leftover,
} from "../../services/settings";

type Unit = "hours" | "days";
const UNIT_MINUTES: Record<Unit, number> = { hours: 60, days: 24 * 60 };

const overview = ref<BackupOverview | null>(null);
// null until the scan of the data folder answers, which can take seconds
const leftovers = ref<Leftover[] | null>(null);
const leftoversError = ref<string | null>(null);
const error = ref<string | null>(null);
const busy = ref<string | null>(null);
const draft = ref<{ amount: number; unit: Unit; keep: number }>({
  amount: 1,
  unit: "days",
  keep: 7,
});
let poll: number | undefined;

function resetDraft() {
  const o = overview.value;
  if (!o) return;
  draft.value =
    o.intervalMinutes % UNIT_MINUTES.days === 0
      ? {
          amount: o.intervalMinutes / UNIT_MINUTES.days,
          unit: "days",
          keep: o.keep,
        }
      : {
          amount: Math.round(o.intervalMinutes / 60),
          unit: "hours",
          keep: o.keep,
        };
}

async function loadOverview() {
  try {
    const first = !overview.value;
    overview.value = await fetchBackups();
    // only the first time: a refresh during a run must not undo typing
    if (first) resetDraft();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Could not load backups";
  }
  // keeps the page current while a run started here is still going
  window.clearTimeout(poll);
  if (overview.value?.running) poll = window.setTimeout(loadOverview, 3000);
}

async function loadLeftovers() {
  try {
    leftovers.value = await fetchLeftovers();
    leftoversError.value = null;
  } catch (e) {
    leftoversError.value =
      e instanceof Error ? e.message : "Could not check for leftover files";
  }
}

onMounted(() => {
  void loadOverview();
  void loadLeftovers();
});
onBeforeUnmount(() => window.clearTimeout(poll));

async function save(changes: {
  enabled?: boolean;
  intervalMinutes?: number;
  keep?: number;
}) {
  error.value = null;
  try {
    const saved = await updateBackupSettings(changes);
    if (overview.value)
      overview.value = { ...saved, backups: overview.value.backups };
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Could not save";
  }
  resetDraft();
}

function saveInterval() {
  const o = overview.value;
  if (!o) return;
  error.value = null;
  const minutes = Math.round(
    draft.value.amount * UNIT_MINUTES[draft.value.unit],
  );
  if (
    !Number.isFinite(minutes) ||
    minutes < o.minIntervalMinutes ||
    minutes > o.maxIntervalMinutes
  ) {
    error.value = "Backups can run from every hour to every 30 days.";
    resetDraft();
    return;
  }
  if (minutes !== o.intervalMinutes) void save({ intervalMinutes: minutes });
}

// Going either way keeps the schedule or slows it: picking hours on "1 day"
// must not start hourly backups before a number has been typed.
function changeUnit(unit: Unit) {
  const d = draft.value;
  if (unit === d.unit) return;
  d.amount =
    unit === "hours" ? d.amount * 24 : Math.max(1, Math.round(d.amount / 24));
  d.unit = unit;
  saveInterval();
}

const confirm = useConfirm();

async function saveKeep() {
  const o = overview.value;
  if (!o) return;
  error.value = null;
  // a cleared field arrives as "", which Math.round would turn into keep 0
  const raw: unknown = draft.value.keep;
  const keep = typeof raw === "number" ? Math.round(raw) : NaN;
  if (!Number.isFinite(keep) || keep < 0 || keep > o.maxKeep) {
    error.value = `Keep between 0 (every backup) and ${o.maxKeep}.`;
    resetDraft();
    return;
  }
  draft.value.keep = keep;
  if (keep === o.keep) return;
  const lowering = keep > 0 && (o.keep === 0 || keep < o.keep);
  const willGo = o.backups.length + 1 - keep;
  if (lowering && willGo > 0) {
    const ok = await confirm({
      message: `Keep only the newest ${keep} ${backupWord(keep)}? The next backup will permanently delete ${willGo} older ${backupWord(willGo)}. This cannot be undone.`,
      confirmLabel: "Change",
      danger: true,
    });
    if (!ok) {
      resetDraft();
      return;
    }
  }
  void save({ keep });
}

async function runNow() {
  error.value = null;
  if (overview.value) overview.value.running = true;
  try {
    await runBackupsNow();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Could not start a backup";
  }
  await loadOverview();
}

async function removeBackup(b: BackupFile) {
  const ok = await confirm({
    message: `Delete the backup from ${formatTime(b.createdAt)}? This cannot be undone.`,
    confirmLabel: "Delete",
    danger: true,
  });
  if (!ok) return;
  busy.value = `database/${b.name}`;
  error.value = null;
  try {
    await deleteBackup(b.name);
    await loadOverview();
  } catch (e) {
    error.value =
      e instanceof Error ? e.message : "Could not delete the backup";
  } finally {
    busy.value = null;
  }
}
async function removeLeftover(item: Leftover) {
  const ok = await confirm({
    message: `Delete these files (${formatBytes(item.bytes)}) permanently? This cannot be undone.`,
    confirmLabel: "Delete",
    danger: true,
  });
  if (!ok) return;
  busy.value = `${item.kind}/${item.name}`;
  error.value = null;
  try {
    await deleteLeftover(item);
    await loadLeftovers();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Could not delete the files";
  } finally {
    busy.value = null;
  }
}

const lastResult = computed(() => overview.value?.lastResult ?? {});
const lastSummary = computed(() => {
  const r = lastResult.value;
  if (!overview.value?.lastRunAt || r.status !== "written") return "";
  const parts = [`saved (${formatBytes(Number(r.size ?? 0))})`];
  if (r.removed) parts.push(`${r.removed} old removed`);
  return parts.join(", ");
});
const failedReason = computed(() =>
  overview.value?.lastRunAt && lastResult.value.status === "failed"
    ? String(lastResult.value.error ?? "unknown error").replace(/[.\s]+$/, "")
    : "",
);
const held = computed(() =>
  lastResult.value.held ? String(lastResult.value.held) : "",
);

function backupWord(count: number): string {
  return count === 1 ? "backup" : "backups";
}
function formatTime(epochSeconds: number | null): string {
  if (!epochSeconds) return "Never";
  return new Date(epochSeconds * 1000).toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}
function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
  return `${(bytes / 1024 ** 3).toFixed(2)} GB`;
}
</script>

<template>
  <section class="settings-section">
    <h2>Backups</h2>
    <p class="section-hint">
      The whole database is saved to one file: every account, library, note,
      achievement, setting and link. Covers, screenshots and saves stay in the
      data folder and are not inside it. A backup is opened and checked after it
      is written before anything older is removed, and only an admin can delete
      backups, here.
    </p>

    <div v-if="error" class="form-error">{{ error }}</div>

    <div v-if="overview" class="tile">
      <div class="tile-head">
        <h3>Schedule</h3>
        <span class="status-badge" :class="{ on: overview.enabled }">
          {{
            overview.running ? "Running now" : overview.enabled ? "On" : "Off"
          }}
        </span>
      </div>
      <div class="controls">
        <label class="inline">
          <input
            type="checkbox"
            :checked="overview.enabled"
            @change="
              save({ enabled: ($event.target as HTMLInputElement).checked })
            "
          />
          Back up automatically
        </label>
        <label class="inline">
          Every
          <input
            v-model.number="draft.amount"
            type="number"
            min="1"
            class="num"
            :disabled="!overview.enabled"
            aria-label="How often backups run"
            @change="saveInterval"
          />
          <select
            :value="draft.unit"
            class="unit"
            :disabled="!overview.enabled"
            aria-label="Unit of time"
            @change="
              changeUnit(($event.target as HTMLSelectElement).value as Unit)
            "
          >
            <option value="hours">
              {{ draft.amount === 1 ? "hour" : "hours" }}
            </option>
            <option value="days">
              {{ draft.amount === 1 ? "day" : "days" }}
            </option>
          </select>
        </label>
        <label class="inline">
          Keep
          <input
            v-model.number="draft.keep"
            type="number"
            min="0"
            :max="overview.maxKeep"
            class="num"
            aria-label="Backups kept"
            @change="saveKeep"
          />
          {{ backupWord(draft.keep) }}
        </label>
        <button
          type="button"
          class="secondary-button"
          :disabled="overview.running"
          @click="runNow"
        >
          {{ overview.running ? "Backing up…" : "Back up now" }}
        </button>
      </div>
      <p class="tile-desc">
        <template v-if="overview.keep > 0">
          After a new backup passes its check, anything past the newest
          {{ overview.keep }} is removed.
        </template>
        <template v-else
          >Keep 0: every backup is kept until deleted here.</template
        >
        Saved in {{ overview.folder }} on the server.
      </p>
      <p class="last-run">
        Last run: {{ formatTime(overview.lastRunAt) }}
        <template v-if="lastSummary"> · {{ lastSummary }}</template>
      </p>
      <p v-if="failedReason" class="form-error">
        The last backup failed: {{ failedReason }}. Nothing older was removed.
        <template v-if="overview.enabled">
          Automatic backups try again an hour after a failure.
        </template>
      </p>
      <p v-if="held" class="warning">
        Old backups were kept: {{ held }}. Check the libraries before deleting
        anything.
      </p>
    </div>

    <div v-if="overview" class="tile">
      <h3>Saved backups</h3>
      <p v-if="!overview.backups.length" class="tile-desc">No backups yet.</p>
      <ul v-else class="backup-list">
        <li v-for="b in overview.backups" :key="b.name" class="backup-row">
          <span class="backup-when">{{ formatTime(b.createdAt) }}</span>
          <span class="backup-meta">
            {{ formatBytes(b.size) }}
            <template v-if="b.items !== null"> · {{ b.items }} titles</template>
            <template v-if="b.tables !== null">
              · {{ b.tables }} tables</template
            >
          </span>
          <a
            class="secondary-button small"
            :href="backupDownloadUrl(b.name)"
            download
          >
            Download
          </a>
          <button
            type="button"
            class="danger-button small"
            :disabled="busy === `database/${b.name}`"
            @click="removeBackup(b)"
          >
            Delete
          </button>
        </li>
      </ul>
      <p class="tile-desc restore">
        To restore one, stop the backend and run
        <code
          >docker exec -i &lt;db container&gt; pg_restore --clean --if-exists -U
          &lt;user&gt; -d &lt;database&gt; &lt; backup.dump</code
        >
      </p>
    </div>

    <div class="tile">
      <h3>Leftover files</h3>
      <p class="tile-desc">
        Files nothing in the app points at any more: games that were emptied
        from the trash before the cleanup knew where to look, files of deleted
        accounts, and the older per-account backups made before whole-database
        backups. They are only removed from here.
      </p>
      <p v-if="leftoversError" class="form-error">{{ leftoversError }}</p>
      <p v-else-if="leftovers === null" class="tile-desc">
        Checking for leftover files…
      </p>
      <p v-else-if="!leftovers.length" class="tile-desc">Nothing left over.</p>
      <ul v-else class="backup-list">
        <li
          v-for="item in leftovers"
          :key="item.kind + item.name"
          class="backup-row"
        >
          <span class="backup-when">{{ item.label }}</span>
          <span class="backup-meta">
            {{ item.name }} · {{ formatBytes(item.bytes) }} · last changed
            {{ formatTime(item.modifiedAt) }}
          </span>
          <button
            type="button"
            class="danger-button small"
            :disabled="busy === `${item.kind}/${item.name}`"
            @click="removeLeftover(item)"
          >
            Delete
          </button>
        </li>
      </ul>
    </div>
  </section>
</template>

<style scoped>
.settings-section h2 {
  margin: 0 0 8px;
  padding-left: 12px;
  border-left: 3px solid var(--ui-accent);
  font-size: 1rem;
  color: var(--ui-heading);
}
.section-hint {
  color: var(--ui-dim-3);
  font-size: 0.82rem;
  line-height: 1.6;
  margin: 0 0 20px;
}
.tile {
  background: var(--ui-bg-2);
  border: 1px solid var(--ui-border);
  border-radius: 10px;
  padding: 18px 20px;
  margin-bottom: 16px;
}
.tile h3 {
  margin: 0 0 8px;
  font-size: 0.9rem;
  color: var(--ui-heading);
}
.tile-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 6px;
}
.tile-head h3 {
  margin: 0;
}
.status-badge {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--ui-dim-3);
  background: color-mix(in srgb, var(--ui-wash-base) 6%, transparent);
  padding: 3px 10px;
  border-radius: 999px;
  white-space: nowrap;
}
.status-badge.on {
  color: var(--ui-good);
  background: color-mix(in srgb, var(--ui-good) 14%, transparent);
}
.tile-desc {
  color: var(--ui-dim-3);
  font-size: 0.8rem;
  line-height: 1.5;
  margin: 0 0 12px;
}
.last-run {
  color: var(--ui-faint-2);
  font-size: 0.76rem;
  margin: 0;
}
.form-error {
  color: var(--ui-danger-bright);
  font-size: 0.8rem;
  margin: 10px 0 12px;
}
.warning {
  color: var(--ui-accent);
  font-size: 0.8rem;
  margin: 10px 0 0;
}
.controls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin: 4px 0 12px;
}
.inline {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.85rem;
  color: var(--ui-text-strong);
}
.num,
.unit {
  background: var(--ui-surface);
  color: var(--ui-text-strong);
  border: 1px solid var(--ui-border);
  border-radius: 8px;
  padding: 7px 10px;
  font-size: 0.82rem;
}
.num {
  width: 72px;
}
.num:disabled,
.unit:disabled {
  opacity: 0.5;
}
.secondary-button,
.danger-button {
  border-radius: 8px;
  padding: 9px 16px;
  font-weight: 600;
  font-size: 0.82rem;
  cursor: pointer;
  text-decoration: none;
  white-space: nowrap;
}
.secondary-button {
  background: var(--ui-surface);
  border: 1px solid var(--ui-border);
  color: var(--ui-text-soft);
}
.danger-button {
  background: transparent;
  border: 1px solid color-mix(in srgb, var(--ui-danger-bright) 45%, transparent);
  color: var(--ui-danger-bright);
}
.secondary-button:disabled,
.danger-button:disabled {
  opacity: 0.6;
  cursor: default;
}
.small {
  padding: 5px 12px;
  font-size: 0.76rem;
}
.backup-list {
  list-style: none;
  margin: 10px 0 0;
  padding: 0;
}
.backup-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
  padding: 6px 0;
  font-size: 0.8rem;
}
.backup-when {
  color: var(--ui-text-strong);
  min-width: 170px;
}
.restore {
  margin: 12px 0 0;
}
.restore code {
  font-size: 0.74rem;
  overflow-wrap: anywhere;
}
.backup-meta {
  color: var(--ui-dim-3);
  flex: 1;
  min-width: 0;
  overflow-wrap: anywhere;
}
</style>
