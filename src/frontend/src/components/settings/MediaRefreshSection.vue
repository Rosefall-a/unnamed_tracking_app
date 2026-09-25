<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import {
  startMediaRefresh,
  fetchMediaRefreshProgress,
} from "../../services/settings";
import type { MediaRefreshProgress } from "../../services/settings";

const progress = ref<MediaRefreshProgress | null>(null);
const error = ref<string | null>(null);
let timer: ReturnType<typeof setInterval> | null = null;

const running = computed(() => progress.value?.running === true);
const percent = computed(() => {
  const p = progress.value;
  return p && p.total ? Math.min(100, Math.round((p.done / p.total) * 100)) : 0;
});
// a finished run to report: something has been checked, or it ran and stopped
const finished = computed(
  () =>
    !!progress.value && !progress.value.running && !!progress.value.finishedAt,
);

async function poll() {
  try {
    progress.value = await fetchMediaRefreshProgress();
    if (!progress.value.running) stopPolling();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Lost the connection";
    stopPolling();
  }
}
function startPolling() {
  if (timer) return;
  timer = setInterval(poll, 1500);
}
function stopPolling() {
  if (timer) clearInterval(timer);
  timer = null;
}

async function run(mode: "needed" | "all") {
  error.value = null;
  try {
    progress.value = await startMediaRefresh(mode);
    startPolling();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Refresh failed";
  }
}

// opening the page while a run is going (or just finished) shows it
onMounted(async () => {
  try {
    const current = await fetchMediaRefreshProgress();
    if (current.running || current.finishedAt) progress.value = current;
    if (current.running) startPolling();
  } catch {
    /* nothing to show yet */
  }
});
onBeforeUnmount(stopPolling);

function formatTime(epochSeconds: number): string {
  return new Date(epochSeconds * 1000).toLocaleTimeString(undefined, {
    hour: "numeric",
    minute: "2-digit",
  });
}
</script>

<template>
  <section class="settings-section">
    <h2>Refresh Media</h2>
    <p class="section-hint">
      It runs only when you start it here or switch on its schedule under Tasks.
      Run it to pick up newly aired episodes, fill in missing episode titles and
      images, and correct a show whose episode count is wrong, right away.
    </p>

    <div class="tile">
      <h3>Show &amp; anime episodes</h3>
      <p class="tile-desc">
        <strong>Refresh what needs it</strong> only looks at titles that are
        still airing, have missing episode titles, or whose episode count
        disagrees with AniList. That is usually a small part of your library, so
        it is quick. <strong>Check every title</strong> looks at all of them.
        Your watched episodes and ratings are never touched, and a title a
        source has wrong is never trusted over what AniList says it has.
      </p>
      <div v-if="error" class="form-error">{{ error }}</div>

      <div v-if="progress && (running || finished)" class="refresh-result">
        <template v-if="running">
          <div class="progress-line">
            <span>{{ progress.phase }}</span>
            <span>{{ progress.done }} of {{ progress.total }}</span>
          </div>
          <div class="progress-track">
            <div class="progress-fill" :style="{ width: percent + '%' }"></div>
          </div>
          <div class="progress-line">
            <span class="progress-current">{{ progress.current }}</span>
            <span
              >{{ progress.checked }} refreshed,
              {{ progress.skippedUpToDate }} already fine</span
            >
          </div>
        </template>
        <template v-else>
          <div class="refresh-result-row">
            <span class="refresh-result-label">Checked</span>
            <span
              >{{ progress.total }} titles: {{ progress.checked }} refreshed,
              {{ progress.skippedUpToDate }} already up to date</span
            >
          </div>
          <div class="refresh-result-row">
            <span class="refresh-result-label">Anime</span>
            <span
              >+{{ progress.animeEpisodesAdded }} new,
              {{ progress.animeEpisodesUpdated }} updated</span
            >
          </div>
          <div class="refresh-result-row">
            <span class="refresh-result-label">TV</span>
            <span
              >+{{ progress.tvEpisodesAdded }} new,
              {{ progress.tvEpisodesUpdated }} updated</span
            >
          </div>
          <div v-if="progress.countsFixed" class="refresh-result-row">
            <span class="refresh-result-label">Corrected</span>
            <span
              >{{ progress.countsFixed }} episode count{{
                progress.countsFixed === 1 ? "" : "s"
              }}</span
            >
          </div>
          <p v-if="!progress.checked && !progress.error" class="refresh-note">
            Nothing needed updating, so nothing changed. Use Check every title
            to look at all of them anyway.
          </p>
          <p v-if="progress.unreachable.length" class="refresh-note">
            Could not refresh {{ progress.unreachable.length }} title{{
              progress.unreachable.length === 1 ? "" : "s"
            }}
            (a source did not answer):
            {{ progress.unreachable.slice(0, 5).join(", ")
            }}{{ progress.unreachable.length > 5 ? "…" : "" }}. Try again later.
          </p>
          <p v-if="progress.error" class="form-error">{{ progress.error }}</p>
        </template>
      </div>

      <div class="tile-footer">
        <button
          type="button"
          class="primary-button"
          :disabled="running"
          @click="run('needed')"
        >
          {{ running ? "Refreshing…" : "Refresh what needs it" }}
        </button>
        <button
          type="button"
          class="refresh-secondary"
          :disabled="running"
          @click="run('all')"
        >
          Check every title
        </button>
        <span v-if="progress?.finishedAt && !running" class="last-run"
          >Last run {{ formatTime(progress.finishedAt) }}</span
        >
      </div>
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
.form-error {
  color: #f87171;
  font-size: 0.8rem;
  margin: 0 0 12px;
}
.refresh-result {
  display: flex;
  flex-direction: column;
  gap: 6px;
  background: rgba(214, 138, 52, 0.06);
  border: 1px solid rgba(214, 138, 52, 0.25);
  border-radius: 8px;
  padding: 12px 14px;
  margin-bottom: 14px;
}
.refresh-result-row {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  font-size: 0.82rem;
  color: #e5e5e5;
}
.refresh-result-row > span:last-child {
  text-align: right;
}
.refresh-result-label {
  flex-shrink: 0;
  font-weight: 700;
  color: #d68a34;
}
.progress-track {
  height: 8px;
  border-radius: 999px;
  background: #1f1f1f;
  overflow: hidden;
  margin: 8px 0 6px;
}
.progress-fill {
  height: 100%;
  background: #d68a34;
  transition: width 0.4s ease;
}
.progress-line {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 0.78rem;
  color: #b5b5b5;
}
.progress-current {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.refresh-note {
  color: #999;
  font-size: 0.76rem;
  line-height: 1.5;
  margin: 8px 0 0;
}
.tile-footer {
  flex-wrap: wrap;
}
.tile-footer {
  display: flex;
  align-items: center;
  gap: 14px;
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
.refresh-secondary {
  background: transparent;
  color: #e5e5e5;
  border: 1px solid #333;
  border-radius: 8px;
  padding: 11px 20px;
  font-weight: 600;
  cursor: pointer;
}
.refresh-secondary:hover:not(:disabled) {
  border-color: rgba(214, 138, 52, 0.5);
}
.refresh-secondary:disabled {
  opacity: 0.6;
  cursor: default;
}
.primary-button:disabled {
  opacity: 0.6;
  cursor: default;
}
.last-run {
  color: #777;
  font-size: 0.78rem;
}
</style>
