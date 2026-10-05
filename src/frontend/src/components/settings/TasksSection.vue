<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from "vue";
import { fetchJobs, updateJob, runJobNow } from "../../services/settings";
import type { CleanupJob } from "../../services/settings";

type Unit = "minutes" | "hours" | "days";
const UNIT_MINUTES: Record<Unit, number> = {
  minutes: 1,
  hours: 60,
  days: 24 * 60,
};

const jobs = ref<CleanupJob[]>([]);
const jobError = ref<string | null>(null);
const intervalErrors = ref<Record<string, string>>({});
const actionErrors = ref<Record<string, string>>({});
const saving = ref<Record<string, boolean>>({});
const starting = ref<Record<string, boolean>>({});
let refreshTimer: ReturnType<typeof setInterval> | null = null;
let loading = false;
// what is typed in each job's "every" fields, kept apart from what is saved
const drafts = ref<Record<string, { amount: number; unit: Unit }>>({});

// shows a saved number of minutes in the largest unit that divides it evenly
function split(minutes: number): { amount: number; unit: Unit } {
  if (minutes % UNIT_MINUTES.days === 0)
    return { amount: minutes / UNIT_MINUTES.days, unit: "days" };
  if (minutes % UNIT_MINUTES.hours === 0)
    return { amount: minutes / UNIT_MINUTES.hours, unit: "hours" };
  return { amount: minutes, unit: "minutes" };
}
function resetDrafts() {
  drafts.value = Object.fromEntries(
    jobs.value.map((j) => [j.id, split(j.intervalMinutes)]),
  );
}
async function loadJobs(retainDrafts = false) {
  if (loading) return;
  loading = true;
  try {
    jobError.value = null;
    jobs.value = await fetchJobs();
    if (!retainDrafts) resetDrafts();
    else
      jobs.value.forEach((job) => {
        drafts.value[job.id] ??= split(job.intervalMinutes);
      });
  } catch (err) {
    jobError.value = err instanceof Error ? err.message : "Failed to load jobs";
  } finally {
    loading = false;
  }
}
async function changeJob(
  job: CleanupJob,
  changes: { enabled?: boolean; intervalMinutes?: number },
) {
  if (saving.value[job.id]) return;
  const isInterval = changes.intervalMinutes !== undefined;
  const errors = isInterval ? intervalErrors : actionErrors;
  delete errors.value[job.id];
  saving.value[job.id] = true;
  try {
    const saved = await updateJob(job.id, changes);
    jobs.value = jobs.value.map((j) => (j.id === saved.id ? saved : j));
    if (isInterval) drafts.value[job.id] = split(saved.intervalMinutes);
  } catch (err) {
    errors.value[job.id] =
      err instanceof Error ? err.message : "Failed to save";
  } finally {
    saving.value[job.id] = false;
  }
}
function saveInterval(job: CleanupJob) {
  const draft = drafts.value[job.id];
  const minutes = Math.round(draft.amount * UNIT_MINUTES[draft.unit]);
  if (
    !Number.isFinite(minutes) ||
    minutes < job.minIntervalMinutes ||
    minutes > job.maxIntervalMinutes
  ) {
    intervalErrors.value[job.id] =
      `Choose between ${describe(job.minIntervalMinutes)} and ${describe(job.maxIntervalMinutes)}.`;
    return;
  }
  delete intervalErrors.value[job.id];
  if (minutes !== job.intervalMinutes)
    void changeJob(job, { intervalMinutes: minutes });
}
function describe(minutes: number): string {
  const { amount, unit } = split(minutes);
  return `${amount} ${amount === 1 ? unit.slice(0, -1) : unit}`;
}
async function runNow(job: CleanupJob) {
  delete actionErrors.value[job.id];
  starting.value[job.id] = true;
  try {
    await runJobNow(job.id);
    await loadJobs(true);
  } catch (err) {
    actionErrors.value[job.id] =
      err instanceof Error ? err.message : "Failed to start";
  } finally {
    starting.value[job.id] = false;
  }
}
onMounted(() => {
  void loadJobs();
  refreshTimer = setInterval(() => void loadJobs(true), 5000);
});
onBeforeUnmount(() => {
  if (refreshTimer !== null) clearInterval(refreshTimer);
});

function formatTime(epochSeconds: number | null): string {
  if (!epochSeconds) return "Never run yet";
  return new Date(epochSeconds * 1000).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}
</script>

<template>
  <section class="settings-section">
    <h2>Tasks</h2>
    <p class="section-hint">
      Built-in jobs and approved plugin tasks use the app's scheduler. Each one
      can be switched off and given its own schedule. Plugin schedules start
      off.
    </p>

    <div v-if="jobError" class="form-error">{{ jobError }}</div>
    <div v-for="job in jobs" :key="job.id" class="tile">
      <div class="tile-head">
        <h3>{{ job.name }}</h3>
        <span class="status-badge" :class="{ on: job.enabled }">
          {{ job.running ? "Running now" : job.enabled ? "On" : "Off" }}
        </span>
      </div>
      <p class="tile-desc">{{ job.description }}</p>
      <p v-if="job.pluginId" class="plugin-source">
        From {{ job.pluginName }} · Runs with this plugin's approved background
        access.
      </p>
      <p v-if="!job.available" class="unavailable-note" role="status">
        {{ job.unavailableReason }}
      </p>
      <div class="job-controls">
        <label class="job-toggle">
          <input
            type="checkbox"
            :checked="job.enabled"
            :disabled="saving[job.id] || !job.available"
            @change="
              changeJob(job, {
                enabled: ($event.target as HTMLInputElement).checked,
              })
            "
          />
          Run by itself
        </label>
        <div v-if="drafts[job.id]" class="interval-field">
          <label class="job-every">
            Every
            <input
              v-model.number="drafts[job.id].amount"
              type="number"
              min="1"
              class="job-amount"
              :disabled="saving[job.id] || !job.available"
              :aria-invalid="Boolean(intervalErrors[job.id])"
              :aria-describedby="`interval-help-${job.id}`"
              :aria-label="`How often ${job.name} runs`"
              @change="saveInterval(job)"
            />
            <select
              v-model="drafts[job.id].unit"
              class="job-interval"
              :disabled="saving[job.id] || !job.available"
              :aria-invalid="Boolean(intervalErrors[job.id])"
              :aria-describedby="`interval-help-${job.id}`"
              aria-label="Unit of time"
              @change="saveInterval(job)"
            >
              <option value="minutes">minutes</option>
              <option value="hours">hours</option>
              <option value="days">days</option>
            </select>
          </label>
          <p
            :id="`interval-help-${job.id}`"
            class="interval-help"
            :class="{ invalid: intervalErrors[job.id] }"
            :role="intervalErrors[job.id] ? 'alert' : undefined"
          >
            {{
              intervalErrors[job.id] ||
              `Allowed: ${describe(job.minIntervalMinutes)} to ${describe(job.maxIntervalMinutes)}.`
            }}
          </p>
        </div>
        <button
          type="button"
          class="secondary-button"
          :disabled="job.running || starting[job.id] || !job.available"
          @click="runNow(job)"
        >
          {{ job.running || starting[job.id] ? "Running…" : "Run now" }}
        </button>
      </div>
      <p v-if="actionErrors[job.id]" class="form-error" role="alert">
        {{ actionErrors[job.id] }}
      </p>
      <p class="last-run">
        Last run: {{ formatTime(job.lastRunAt) }}
        <template v-if="job.lastSummary"> · {{ job.lastSummary }}</template>
      </p>
      <p class="tile-desc job-note">
        "Run now" works whether or not it runs by itself.
      </p>
    </div>
  </section>
</template>

<style scoped>
.settings-section h2 {
  margin: 0 0 12px;
  font: var(--ui-weight-heading) var(--ui-font-heading)/1.4
    var(--ui-font-family);
  color: var(--ui-text);
}
.section-hint {
  color: var(--ui-dim);
  font-size: 0.82rem;
  line-height: 1.6;
  margin: 0 0 20px;
}
.tile {
  background: var(--ui-surface);
  border: 1px solid var(--ui-border-strong);
  border-radius: var(--ui-radius-control);
  padding: 18px 20px;
  margin-bottom: 16px;
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
  font-size: 0.9rem;
  color: var(--ui-text);
}
.status-badge {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--ui-dim);
  background: color-mix(in srgb, var(--ui-text) 6%, transparent);
  padding: 3px 10px;
  border-radius: 999px;
  white-space: nowrap;
}
.status-badge.on {
  color: var(--ui-good);
  background: var(--ui-good-soft);
}
.tile-desc {
  color: var(--ui-dim);
  font-size: 0.8rem;
  line-height: 1.5;
  margin: 0 0 12px;
}
.last-run {
  color: var(--ui-dim);
  font-size: 0.76rem;
  margin: 0 0 14px;
}
.form-error {
  color: var(--ui-error);
  font-size: 0.8rem;
  margin: 0 0 12px;
}
.secondary-button {
  background: var(--ui-surface);
  border: 1px solid var(--ui-border);
  color: var(--ui-text);
  border-radius: var(--ui-radius-control);
  padding: 9px 16px;
  font-weight: 600;
  font-size: 0.82rem;
  cursor: pointer;
}
.secondary-button:disabled {
  opacity: 0.6;
  cursor: default;
}
.job-controls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin: 4px 0 10px;
}
.job-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.85rem;
  color: var(--ui-text);
}
.job-toggle input {
  accent-color: var(--ui-accent);
}
.job-every {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  font-size: 0.85rem;
  color: var(--ui-text);
}
.job-amount {
  width: 72px;
  background: var(--ui-surface);
  color: var(--ui-text);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-control);
  padding: 7px 10px;
  font-size: 0.82rem;
}
.job-amount:disabled {
  opacity: 0.5;
}
.job-interval {
  background: var(--ui-surface);
  color: var(--ui-text);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-control);
  padding: 7px 10px;
  font-size: 0.82rem;
}
.job-interval:disabled {
  opacity: 0.5;
}
.job-note {
  margin: 8px 0 0;
}
.interval-field {
  max-width: 100%;
}
.interval-help {
  color: var(--ui-dim);
  font-size: 0.76rem;
  margin: 8px 0 0;
}
.interval-help.invalid {
  color: var(--ui-error);
}
.job-amount[aria-invalid="true"] {
  border-color: var(--ui-error);
}
.plugin-source {
  color: var(--ui-dim);
  font-size: 0.78rem;
  margin: 0 0 12px;
}
.unavailable-note {
  color: var(--ui-warning);
  background: var(--ui-warning-soft);
  padding: 12px;
  border-radius: var(--ui-radius-control);
}
@media (max-width: 760px) {
  .job-amount,
  .job-interval {
    box-sizing: border-box;
    min-height: 44px;
    font-size: 1rem;
  }
  .job-amount {
    width: 64px;
  }
}
</style>
