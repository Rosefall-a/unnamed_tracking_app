<script setup lang="ts">
import { ref, onMounted } from "vue";
import {
  fetchMediaRefreshStatus,
  checkAiringEpisodes,
} from "../../services/settings";
import type { MediaRefreshStatus } from "../../services/settings";

const status = ref<MediaRefreshStatus | null>(null);
const loadError = ref<string | null>(null);
const checking = ref(false);
const checkError = ref<string | null>(null);

async function loadStatus() {
  loadError.value = null;
  try {
    status.value = await fetchMediaRefreshStatus();
  } catch (err) {
    loadError.value = err instanceof Error ? err.message : "Failed to load task status";
  }
}
onMounted(loadStatus);

async function runAiringCheckNow() {
  checking.value = true;
  checkError.value = null;
  try {
    await checkAiringEpisodes();
    await loadStatus();
  } catch (err) {
    checkError.value = err instanceof Error ? err.message : "Check failed";
  } finally {
    checking.value = false;
  }
}

function formatTime(epochSeconds: number | null): string {
  if (!epochSeconds) return "Never run yet";
  return new Date(epochSeconds * 1000).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function formatInterval(seconds: number): string {
  if (seconds % 3600 === 0) return `every ${seconds / 3600}h`;
  return `every ${Math.round(seconds / 60)}m`;
}
</script>

<template>
  <section class="settings-section">
    <h2>Tasks</h2>
    <p class="section-hint">
      Recurring jobs run by the app's own in-process scheduler, with no separate
      worker or server needed.
    </p>

    <div v-if="loadError" class="form-error">{{ loadError }}</div>

    <div v-if="status" class="tile">
      <div class="tile-head">
        <h3>Airing episode check</h3>
        <span class="status-badge" :class="{ on: status.airingCheck.enabled }">
          {{ status.airingCheck.enabled ? "Running automatically" : "Off" }}
        </span>
      </div>
      <p class="tile-desc">
        A cheap check ({{ formatInterval(status.airingCheck.intervalSeconds) }})
        for whether a tracked show or anime has a newly-aired episode number.
        Adds a bare placeholder row right away so you can check it off. The
        real title and image come later from a full refresh.
      </p>
      <p class="last-run">
        Last run: {{ formatTime(status.airingCheck.lastRunAt) }}
        <template
          v-if="
            status.airingCheck.lastRunAt &&
            (status.airingCheck.lastResult.anime_episodes_added ||
              status.airingCheck.lastResult.tv_episodes_added)
          "
        >
          · +{{ status.airingCheck.lastResult.anime_episodes_added || 0 }} anime,
          +{{ status.airingCheck.lastResult.tv_episodes_added || 0 }} TV
        </template>
      </p>
      <div v-if="checkError" class="form-error">{{ checkError }}</div>
      <button
        type="button"
        class="secondary-button"
        :disabled="checking"
        @click="runAiringCheckNow"
      >
        {{ checking ? "Checking…" : "Check now" }}
      </button>
    </div>

    <div v-if="status" class="tile">
      <div class="tile-head">
        <h3>Full metadata refresh</h3>
        <span class="status-badge" :class="{ on: status.fullRefresh.enabled }">
          {{ status.fullRefresh.enabled ? "Running automatically" : "Off" }}
        </span>
      </div>
      <p class="tile-desc">
        Backfills real titles, descriptions, and images (including a TMDB
        lookup for anime), on top of whatever the airing check already added.
        Runs on its own
        {{ formatInterval(status.fullRefresh.intervalSeconds) }}. Run it
        early from Metadata &gt; Refresh Media if you don't want to wait.
      </p>
      <p class="last-run">
        Last run: {{ formatTime(status.fullRefresh.lastRunAt) }}
        <template
          v-if="
            status.fullRefresh.lastRunAt &&
            (status.fullRefresh.lastResult.anime_episodes_added ||
              status.fullRefresh.lastResult.tv_episodes_added ||
              status.fullRefresh.lastResult.anime_episodes_updated ||
              status.fullRefresh.lastResult.tv_episodes_updated)
          "
        >
          · +{{ status.fullRefresh.lastResult.anime_episodes_added || 0 }}/upd
          {{ status.fullRefresh.lastResult.anime_episodes_updated || 0 }} anime,
          +{{ status.fullRefresh.lastResult.tv_episodes_added || 0 }}/upd
          {{ status.fullRefresh.lastResult.tv_episodes_updated || 0 }} TV
        </template>
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
</style>
