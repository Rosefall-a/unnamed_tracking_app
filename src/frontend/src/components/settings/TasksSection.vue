<script setup lang="ts">
// Each task runs one of three ways: off, on its own timer, or together with
// the other tasks set that way, once a day at one time (the backup goes last).
import { computed, ref, onMounted } from "vue";
import {
  browserTimeZone,
  fetchJobs,
  fetchTaskSchedule,
  runDailyTasksNow,
  runJobNow,
  updateJob,
  updateTaskSchedule,
} from "../../services/settings";
import type { CleanupJob, TaskSchedule } from "../../services/settings";

type Unit = "minutes" | "hours" | "days";
type Mode = "off" | "timer" | "together";
const UNIT_MINUTES: Record<Unit, number> = {
  minutes: 1,
  hours: 60,
  days: 24 * 60,
};

const jobs = ref<CleanupJob[]>([]);
const jobError = ref<string | null>(null);
// a problem with one job shows on that job
const jobErrors = ref<Record<string, string>>({});
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
    jobError.value = err instanceof Error ? err.message : "Could not load jobs";
  }
}

function modeOf(job: CleanupJob): Mode {
  if (!job.enabled) return "off";
  return job.together ? "together" : "timer";
}
async function changeJob(
  job: CleanupJob,
  changes: { enabled?: boolean; intervalMinutes?: number; together?: boolean },
) {
  jobErrors.value = { ...jobErrors.value, [job.id]: "" };
  try {
    const saved = await updateJob(job.id, changes);
    jobs.value = jobs.value.map((j) => (j.id === saved.id ? saved : j));
    drafts.value = {
      ...drafts.value,
      [saved.id]: split(saved.intervalMinutes),
    };
    // which tasks run together, and when, may have changed
    await loadSchedule();
  } catch (err) {
    jobErrors.value = {
      ...jobErrors.value,
      [job.id]: err instanceof Error ? err.message : "Could not save",
    };
  }
}
function setMode(job: CleanupJob, mode: Mode) {
  if (mode === "off") void changeJob(job, { enabled: false });
  else void changeJob(job, { enabled: true, together: mode === "together" });
}
function draftMinutes(job: CleanupJob): number {
  const draft = drafts.value[job.id];
  return Math.round(draft.amount * UNIT_MINUTES[draft.unit]);
}
function draftChanged(job: CleanupJob): boolean {
  return draftMinutes(job) !== job.intervalMinutes;
}
function saveInterval(job: CleanupJob) {
  const minutes = draftMinutes(job);
  if (
    !Number.isFinite(minutes) ||
    minutes < job.minIntervalMinutes ||
    minutes > job.maxIntervalMinutes
  ) {
    // what was typed stays, so it can be corrected
    jobErrors.value = {
      ...jobErrors.value,
      [job.id]: `Choose between ${describe(job.minIntervalMinutes)} and ${describe(job.maxIntervalMinutes)}.`,
    };
    return;
  }
  void changeJob(job, { intervalMinutes: minutes });
}
function describe(minutes: number): string {
  const { amount, unit } = split(minutes);
  return `${amount} ${amount === 1 ? unit.slice(0, -1) : unit}`;
}
async function runNow(job: CleanupJob) {
  jobErrors.value = { ...jobErrors.value, [job.id]: "" };
  try {
    await runJobNow(job.id);
    jobs.value = await fetchJobs();
  } catch (err) {
    jobErrors.value = {
      ...jobErrors.value,
      [job.id]: err instanceof Error ? err.message : "Could not start",
    };
  }
}
onMounted(loadJobs);

// ---- the time the tasks set to run together start ----
const schedule = ref<TaskSchedule | null>(null);
const scheduleTime = ref("03:00");
const scheduleError = ref<string | null>(null);
async function loadSchedule() {
  try {
    schedule.value = await fetchTaskSchedule();
    scheduleTime.value = schedule.value.time;
  } catch (err) {
    scheduleError.value =
      err instanceof Error ? err.message : "Could not load the task time";
  }
}
async function saveTime() {
  scheduleError.value = null;
  try {
    schedule.value = await updateTaskSchedule({ time: scheduleTime.value });
    scheduleTime.value = schedule.value.time;
  } catch (err) {
    scheduleError.value =
      err instanceof Error ? err.message : "Could not save the time";
  }
}
async function runTogetherNow() {
  scheduleError.value = null;
  try {
    await runDailyTasksNow();
    await loadSchedule();
    jobs.value = await fetchJobs();
  } catch (err) {
    scheduleError.value =
      err instanceof Error ? err.message : "Could not start the tasks";
  }
}
// the tasks that run together, by name, in the order they run
const memberNames = computed(() =>
  (schedule.value?.members ?? []).map((id) =>
    id === "auto_backup"
      ? "the backup"
      : (jobs.value.find((j) => j.id === id)?.name ?? id),
  ),
);
const memberList = computed(() => {
  const names = memberNames.value;
  if (names.length <= 1) return names.join("");
  return `${names.slice(0, -1).join(", ")}, then ${names[names.length - 1]}`;
});
// saved in another time zone than this browser's: say which, so 03:00 is clear
const otherZone = computed(() =>
  schedule.value && schedule.value.timezone !== browserTimeZone()
    ? schedule.value.timezone
    : null,
);
onMounted(loadSchedule);

function formatTime(epochSeconds: number | null): string {
  if (!epochSeconds) return "Never run";
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
      Jobs the app runs by itself. Each one can be off, run on its own timer, or
      run together with the others at one time of day. Run now works whatever is
      picked.
    </p>

    <div v-if="schedule" class="tile">
      <div class="tile-head">
        <h3>Run together</h3>
        <span class="status-badge" :class="{ on: schedule.members.length > 0 }">
          {{
            schedule.running
              ? "Running now"
              : schedule.members.length
                ? `${schedule.members.length} selected`
                : "None selected"
          }}
        </span>
      </div>
      <p class="tile-desc">
        Tasks set to "Together with the others" run one after another, once a
        day at this time. The backup can join too, in Backups, and always goes
        last so it holds what the others just did.
      </p>
      <div class="job-controls">
        <label class="job-every">
          Every day at
          <input
            v-model="scheduleTime"
            type="time"
            class="job-amount job-time"
            aria-label="Time the tasks run together"
          />
        </label>
        <button
          v-if="scheduleTime !== schedule.time"
          type="button"
          class="secondary-button"
          @click="saveTime"
        >
          Save
        </button>
        <button
          type="button"
          class="secondary-button"
          :disabled="schedule.running || !schedule.members.length"
          @click="runTogetherNow"
        >
          {{ schedule.running ? "Running…" : "Run them now" }}
        </button>
      </div>
      <div v-if="scheduleError" class="form-error">{{ scheduleError }}</div>
      <p v-if="schedule.members.length" class="tile-desc">
        Runs {{ memberList }}.
      </p>
      <p class="last-run">
        <template v-if="schedule.nextRunAt">
          Next: {{ formatTime(schedule.nextRunAt) }}
          <template v-if="otherZone"> ({{ otherZone }} time)</template> ·
        </template>
        Last: {{ formatTime(schedule.lastRunAt) }}
        <template v-if="schedule.lastStatus === 'failed'">
          · it stopped partway, see the server log</template
        >
      </p>
    </div>

    <div v-if="jobError" class="form-error">{{ jobError }}</div>
    <div v-for="job in jobs" :key="job.id" class="tile">
      <div class="tile-head">
        <h3>{{ job.name }}</h3>
        <span class="status-badge" :class="{ on: job.enabled }">
          {{
            job.running
              ? "Running now"
              : !job.enabled
                ? "Off"
                : job.together
                  ? "Together"
                  : "Own timer"
          }}
        </span>
      </div>
      <p class="tile-desc">{{ job.description }}</p>
      <div class="job-controls">
        <label class="job-every">
          Runs
          <select
            :value="modeOf(job)"
            class="job-interval"
            :aria-label="`How ${job.name} runs`"
            @change="
              setMode(job, ($event.target as HTMLSelectElement).value as Mode)
            "
          >
            <option value="off">Off</option>
            <option value="timer">On its own timer</option>
            <option value="together">
              Together with the others{{
                schedule ? ` (${schedule.time})` : ""
              }}
            </option>
          </select>
        </label>
        <label
          v-if="modeOf(job) === 'timer' && drafts[job.id]"
          class="job-every"
        >
          every
          <input
            v-model.number="drafts[job.id].amount"
            type="number"
            min="1"
            class="job-amount"
            :aria-label="`How often ${job.name} runs`"
          />
          <select
            v-model="drafts[job.id].unit"
            class="job-interval"
            aria-label="Unit of time"
          >
            <option value="minutes">minutes</option>
            <option value="hours">hours</option>
            <option value="days">days</option>
          </select>
        </label>
        <button
          v-if="modeOf(job) === 'timer' && drafts[job.id] && draftChanged(job)"
          type="button"
          class="secondary-button"
          @click="saveInterval(job)"
        >
          Save
        </button>
        <button
          type="button"
          class="secondary-button"
          :disabled="job.running"
          @click="runNow(job)"
        >
          {{ job.running ? "Running…" : "Run now" }}
        </button>
      </div>
      <div v-if="jobErrors[job.id]" class="form-error">
        {{ jobErrors[job.id] }}
      </div>
      <p class="last-run">
        Last run: {{ formatTime(job.lastRunAt) }}
        <template v-if="job.lastSummary"> · {{ job.lastSummary }}</template>
      </p>
      <p v-if="modeOf(job) === 'timer'" class="tile-desc job-note">
        Allowed: every {{ describe(job.minIntervalMinutes) }} to
        {{ describe(job.maxIntervalMinutes) }}.
      </p>
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
  color: var(--ui-heading);
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
  margin: 0 0 14px;
}
.form-error {
  color: var(--ui-danger-bright);
  font-size: 0.8rem;
  margin: 0 0 12px;
}
.secondary-button {
  background: var(--ui-surface);
  border: 1px solid var(--ui-border);
  color: var(--ui-text-soft);
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
  color: var(--ui-text-strong);
}
.job-every {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.85rem;
  color: var(--ui-text-strong);
}
.job-amount {
  width: 72px;
  background: var(--ui-surface);
  color: var(--ui-text-strong);
  border: 1px solid var(--ui-border);
  border-radius: 8px;
  padding: 7px 10px;
  font-size: 0.82rem;
}
.job-amount:disabled {
  opacity: 0.5;
}
.job-interval {
  background: var(--ui-surface);
  color: var(--ui-text-strong);
  border: 1px solid var(--ui-border);
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
.job-time {
  width: auto;
}
</style>
