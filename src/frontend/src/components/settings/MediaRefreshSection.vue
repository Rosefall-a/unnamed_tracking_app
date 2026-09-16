<script setup lang="ts">
import { ref } from "vue";
import { refreshMediaMetadata } from "../../services/settings";
import type { MediaMetadataRefreshResult } from "../../services/settings";

const refreshing = ref(false);
const error = ref<string | null>(null);
const result = ref<MediaMetadataRefreshResult | null>(null);
const lastRunAt = ref<Date | null>(null);

async function runRefresh() {
  refreshing.value = true;
  error.value = null;
  try {
    result.value = await refreshMediaMetadata();
    lastRunAt.value = new Date();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Refresh failed";
  } finally {
    refreshing.value = false;
  }
}

function formatTime(d: Date): string {
  return d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}
</script>

<template>
  <section class="settings-section">
    <h2>Refresh Media</h2>
    <p class="section-hint">
      This full refresh already runs automatically every 24 hours, same as
      backups. Run it manually here to check for newly-aired episodes, or to
      fill in titles/images on episodes that were only ever synced as bare
      placeholders, right away instead of waiting for the next automatic
      pass (e.g. right after adding a TMDB key).
    </p>

    <div class="tile">
      <h3>Show &amp; anime episodes</h3>
      <p class="tile-desc">
        Checks every show and anime you're already tracking episode-by-episode
        against Jikan, AniList, and TMDB (whichever are configured). Appends
        any newly-aired episode numbers, and fills in title/description/image
        on existing rows that were still blank placeholders. Never touches
        which episodes you've already marked watched, or your ratings.
      </p>
      <div v-if="error" class="form-error">{{ error }}</div>
      <div v-if="result" class="refresh-result">
        <div class="refresh-result-row">
          <span class="refresh-result-label">Anime</span>
          <span
            >+{{ result.animeEpisodesAdded }} new, {{
              result.animeEpisodesUpdated
            }}
            updated</span
          >
        </div>
        <div class="refresh-result-row">
          <span class="refresh-result-label">TV</span>
          <span
            >+{{ result.tvEpisodesAdded }} new, {{
              result.tvEpisodesUpdated
            }}
            updated</span
          >
        </div>
      </div>
      <div class="tile-footer">
        <button
          type="button"
          class="primary-button"
          :disabled="refreshing"
          @click="runRefresh"
        >
          {{ refreshing ? "Refreshing…" : "Refresh now" }}
        </button>
        <span v-if="lastRunAt" class="last-run"
          >Last run {{ formatTime(lastRunAt) }}</span
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
  font-size: 0.82rem;
  color: #e5e5e5;
}
.refresh-result-label {
  font-weight: 700;
  color: #d68a34;
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
.primary-button:disabled {
  opacity: 0.6;
  cursor: default;
}
.last-run {
  color: #777;
  font-size: 0.78rem;
}
</style>
