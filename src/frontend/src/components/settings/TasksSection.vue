<script setup lang="ts">
import { ref, onMounted } from "vue";
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
async function loadJobs() {
  try {
    jobs.value = await fetchJobs();
    resetDrafts();
  } catch (err) {
    jobError.value = err instanceof Error ? err.message : "Failed to load jobs";
  }
}
async function changeJob(
  job: CleanupJob,
  changes: { enabled?: boolean; intervalMinutes?: number },
) {
  jobError.value = null;
  try {
    const saved = await updateJob(job.id, changes);
    jobs.value = jobs.value.map((j) => (j.id === saved.id ? saved : j));
  } catch (err) {
    jobError.value = err instanceof Error ? err.message : "Failed to save";
  }
  resetDrafts();
}
function saveInterval(job: CleanupJob) {
  const draft = drafts.value[job.id];
  const minutes = Math.round(draft.amount * UNIT_MINUTES[draft.unit]);
  if (
    !Number.isFinite(minutes) ||
    minutes < job.minIntervalMinutes ||
    minutes > job.maxIntervalMinutes
  ) {
    jobError.value = `Choose between ${describe(job.minIntervalMinutes)} and ${describe(job.maxIntervalMinutes)}.`;
    resetDrafts();
    return;
  }
  if (minutes !== job.intervalMinutes)
    void changeJob(job, { intervalMinutes: minutes });
}
function describe(minutes: number): string {
  const { amount, unit } = split(minutes);
  return `${amount} ${amount === 1 ? unit.slice(0, -1) : unit}`;
}
async function runNow(job: CleanupJob) {
  jobError.value = null;
  try {
    await runJobNow(job.id);
    await loadJobs();
  } catch (err) {
    jobError.value = err instanceof Error ? err.message : "Failed to start";
  }
}
onMounted(loadJobs);

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
      Recurring jobs run by the app's own scheduler, with no separate worker or
      server needed. Each one can be switched off and given its own schedule.
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
      <div class="job-controls">
        <label class="job-toggle">
          <input
            type="checkbox"
            :checked="job.enabled"
            @change="
              changeJob(job, {
                enabled: ($event.target as HTMLInputElement).checked,
              })
            "
          />
          Run by itself
        </label>
        <label v-if="drafts[job.id]" class="job-every">
          Every
          <input
            v-model.number="drafts[job.id].amount"
            type="number"
            min="1"
            class="job-amount"
            :disabled="!job.enabled"
            :aria-label="`How often ${job.name} runs`"
            @change="saveInterval(job)"
          />
          <select
            v-model="drafts[job.id].unit"
            class="job-interval"
            :disabled="!job.enabled"
            aria-label="Unit of time"
            @change="saveInterval(job)"
          >
            <option value="minutes">minutes</option>
            <option value="hours">hours</option>
            <option value="days">days</option>
          </select>
        </label>
        <button
          type="button"
          class="secondary-button"
          :disabled="job.running"
          @click="runNow(job)"
        >
          {{ job.running ? "Running…" : "Run now" }}
        </button>
      </div>
      <p class="last-run">
        Last run: {{ formatTime(job.lastRunAt) }}
        <template v-if="job.lastSummary"> · {{ job.lastSummary }}</template>
      </p>
      <p class="tile-desc job-note">
        Allowed: every {{ describe(job.minIntervalMinutes) }} to
        {{ describe(job.maxIntervalMinutes) }}. "Run now" works whether or not
        it runs by itself.
      </p>
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
  color: #fff;
}
.status-badge {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #999;
  background: rgba(255, 255, 255, 0.06);
  padding: 3px 10px;
  border-radius: 999px;
  white-space: nowrap;
}
.status-badge.on {
  color: #6fbf73;
  background: rgba(111, 191, 115, 0.14);
}
.tile-desc {
  color: #999;
  font-size: 0.8rem;
  line-height: 1.5;
  margin: 0 0 12px;
}
.last-run {
  color: #777;
  font-size: 0.76rem;
  margin: 0 0 14px;
}
.form-error {
  color: #f87171;
  font-size: 0.8rem;
  margin: 0 0 12px;
}
.secondary-button {
  background: #1a1a1a;
  border: 1px solid #2b2b2b;
  color: #ccc;
  border-radius: 8px;
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
  color: #e5e5e5;
}
.job-every {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.85rem;
  color: #e5e5e5;
}
.job-amount {
  width: 72px;
  background: #1a1a1a;
  color: #e5e5e5;
  border: 1px solid #2a2a2a;
  border-radius: 8px;
  padding: 7px 10px;
  font-size: 0.82rem;
}
.job-amount:disabled {
  opacity: 0.5;
}
.job-interval {
  background: #1a1a1a;
  color: #e5e5e5;
  border: 1px solid #2a2a2a;
  border-radius: 8px;
  padding: 7px 10px;
  font-size: 0.82rem;
}
.job-interval:disabled {
  opacity: 0.5;
}
.job-note {
  margin: 8px 0 0;
}
</style>
