<script setup lang="ts">
// The first thing an admin sees under Server: anything that needs a look,
// then backups, tasks and the system at a glance. Each card links to the tab
// that changes it. Reads only; nothing here changes a setting.
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { currentUser } from "../../state/auth";
import {
  fetchBackups,
  fetchJobs,
  fetchSystemInfo,
  type BackupOverview,
  type CleanupJob,
  type SystemInfo,
} from "../../services/settings";
import SettingsCard from "./SettingsCard.vue";
import SettingsRow from "./SettingsRow.vue";

const router = useRouter();
const isAdmin = computed(() => !!currentUser.value?.is_admin);
const backups = ref<BackupOverview | null>(null);
const jobs = ref<CleanupJob[]>([]);
const system = ref<SystemInfo | null>(null);
const error = ref<string | null>(null);

onMounted(async () => {
  if (!isAdmin.value) return;
  const [b, j, s] = await Promise.allSettled([
    fetchBackups(),
    fetchJobs(),
    fetchSystemInfo(),
  ]);
  if (b.status === "fulfilled") backups.value = b.value;
  if (j.status === "fulfilled") jobs.value = j.value;
  if (s.status === "fulfilled") system.value = s.value;
  const failed = [b, j, s].find((r) => r.status === "rejected");
  if (failed && failed.status === "rejected")
    error.value =
      failed.reason instanceof Error
        ? failed.reason.message
        : "Some details could not be loaded.";
});

function open(tab: string) {
  void router.replace({ query: { section: "server", tab } });
}

interface Issue {
  title: string;
  hint: string;
  tab: string;
  action: string;
}
const issues = computed<Issue[]>(() => {
  const out: Issue[] = [];
  const b = backups.value;
  if (!b) return out;
  if (!b.enabled)
    out.push({
      title: "Automatic backups are off",
      hint: "Nothing is saved if the database is lost.",
      tab: "tasks",
      action: "Open backups",
    });
  if (b.storage.sameDrive)
    out.push({
      title: `Backups are on ${b.storage.backups?.label ?? "the same drive"}, the same drive as your data`,
      hint: "A failed drive would lose both. Set BACKUP_FOLDER in .env to another drive.",
      tab: "tasks",
      action: "Open backups",
    });
  if (b.storage.backups && !b.storage.backups.mounted)
    out.push({
      title: "Backups are only inside the container",
      hint: "Removing the container loses them. Mount a folder at /data/backups.",
      tab: "tasks",
      action: "Open backups",
    });
  return out;
});

function when(unix: number | null): string {
  if (!unix) return "Never";
  return new Date(unix * 1000).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}
function size(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let v = bytes / 1024;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i++;
  }
  return `${v.toFixed(v < 10 ? 1 : 0)} ${units[i]}`;
}
function uptime(seconds: number): string {
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return d ? `${d}d ${h}h` : `${h}h ${m}m`;
}
const newest = computed(() => backups.value?.backups[0] ?? null);
function jobMode(j: CleanupJob): { label: string; cls: string } {
  if (!j.enabled) return { label: "Off", cls: "" };
  return j.together
    ? { label: "Together", cls: "acc" }
    : { label: "Own timer", cls: "acc" };
}
</script>

<template>
  <template v-if="isAdmin">
    <p v-if="error" class="st-error">{{ error }}</p>
    <SettingsCard v-if="issues.length" title="Needs a look" warn>
      <template #actions>
        <span class="st-chip bad">{{ issues.length }}</span>
      </template>
      <div v-for="issue in issues" :key="issue.title" class="st-list-row">
        <div class="st-lbl">
          <strong>{{ issue.title }}</strong>
          <span>{{ issue.hint }}</span>
        </div>
        <button type="button" class="st-btn" @click="open(issue.tab)">
          {{ issue.action }}
        </button>
      </div>
    </SettingsCard>

    <div class="pair">
      <SettingsCard v-if="backups" title="Backups">
        <div class="st-stats">
          <div class="st-stat">
            <span class="st-muted">Last backup</span>
            <b class="small">{{ when(backups.lastRunAt) }}</b>
          </div>
          <div class="st-stat">
            <span class="st-muted">Size</span>
            <b class="small">{{ newest ? size(newest.size) : "None yet" }}</b>
          </div>
          <div class="st-stat">
            <span class="st-muted">Kept</span>
            <b class="small">{{ backups.backups.length }}</b>
          </div>
        </div>
      </SettingsCard>

      <SettingsCard v-if="system" title="System">
        <SettingsRow label="Uptime">
          <span class="st-muted">{{ uptime(system.uptime_seconds) }}</span>
        </SettingsRow>
        <SettingsRow label="Python">
          <span class="st-muted">{{ system.python_version }}</span>
        </SettingsRow>
        <SettingsRow label="Debug mode">
          <span class="st-muted">{{ system.debug ? "On" : "Off" }}</span>
        </SettingsRow>
      </SettingsCard>
    </div>

    <SettingsCard v-if="jobs.length" title="Tasks">
      <template #actions>
        <button type="button" class="st-btn" @click="open('tasks')">
          Open tasks
        </button>
      </template>
      <SettingsRow
        v-for="j in jobs"
        :key="j.id"
        :label="j.name"
        :hint="`${when(j.lastRunAt)}${j.lastSummary ? ' · ' + j.lastSummary : ''}`"
      >
        <span class="st-chip" :class="jobMode(j).cls">{{
          jobMode(j).label
        }}</span>
      </SettingsRow>
    </SettingsCard>
  </template>
</template>

<style scoped>
.pair {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
}
.small {
  font-size: 15px;
}
</style>
