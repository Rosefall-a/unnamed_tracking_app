<script setup lang="ts">
import { ref } from "vue";
import {
  importYamtrack,
  previewYamtrack,
} from "../../services/yamtrack";
import type {
  YamtrackImportResult,
  YamtrackPreview,
} from "../../services/yamtrack";

const busy = ref(false);
const error = ref<string | null>(null);
const file = ref<File | null>(null);
const preview = ref<YamtrackPreview | null>(null);
const result = ref<YamtrackImportResult | null>(null);
const useYamtrack = ref<Set<string>>(new Set());
const fetchDetails = ref(true);

async function selected(event: Event) {
  const input = event.target as HTMLInputElement;
  const picked = input.files?.[0];
  input.value = "";
  if (!picked) return;
  busy.value = true;
  error.value = null;
  result.value = null;
  preview.value = null;
  useYamtrack.value = new Set();
  try {
    preview.value = await previewYamtrack(picked);
    file.value = picked;
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to read the YamTrack CSV";
  } finally {
    busy.value = false;
  }
}

function toggle(id: string) {
  const next = new Set(useYamtrack.value);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  useYamtrack.value = next;
}

function chooseAll(value: boolean) {
  useYamtrack.value = new Set(
    value ? (preview.value?.existing.map((item) => item.yamtrack_id) ?? []) : [],
  );
}

function cancel() {
  preview.value = null;
  file.value = null;
  useYamtrack.value = new Set();
}

async function runImport() {
  if (!file.value) return;
  busy.value = true;
  error.value = null;
  try {
    result.value = await importYamtrack(
      file.value,
      [...useYamtrack.value],
      fetchDetails.value,
    );
    cancel();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to import the YamTrack CSV";
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div class="tile yamtrack-tile">
    <h3>Import from YamTrack</h3>
    <p class="tile-desc">
      Upload the native CSV export from YamTrack. Movies and TV shows are imported with
      status, ratings, dates, and TV episode progress. Unsupported media such as games,
      books, manga, comics, and anime are skipped rather than stopping the import.
      You can review existing titles before anything is changed.
    </p>

    <div v-if="error" class="form-error">{{ error }}</div>
    <div v-if="result" class="form-success">
      Added {{ result.created }}, updated {{ result.updated }}, kept {{ result.kept }}.
      <template v-if="result.episodes_imported">
        Imported {{ result.episodes_imported }} watched TV episodes.
      </template>
      <template v-if="result.details_filled">
        Filled in missing details for {{ result.details_filled }} titles from
        {{ result.details_source }}.
      </template>
      <template v-if="result.details_not_found">
        {{ result.details_not_found }} titles had no metadata match.
      </template>
      <template v-if="result.details_unavailable">
        No TMDB or OMDb key is configured, so metadata was not fetched.
      </template>
      <template v-if="result.skipped_other">
        {{ result.skipped_other }} unsupported rows were skipped.
      </template>
    </div>

    <div v-if="preview" class="yamtrack-review">
      <p class="tile-desc">
        {{ preview.total }} supported titles:
        <strong>{{ preview.new_count }} new</strong>,
        {{ preview.existing.length }} already here with differences,
        {{ preview.identical }} already here and identical.
      </p>
      <template v-if="preview.existing.length">
        <div class="yamtrack-bulk">
          <button type="button" class="secondary-button" @click="chooseAll(true)">
            Use YamTrack for all
          </button>
          <button type="button" class="secondary-button" @click="chooseAll(false)">
            Keep all as they are
          </button>
        </div>
        <ul class="yamtrack-list">
          <li v-for="item in preview.existing" :key="item.yamtrack_id + item.title">
            <label class="yamtrack-row">
              <input
                type="checkbox"
                :checked="useYamtrack.has(item.yamtrack_id)"
                @change="toggle(item.yamtrack_id)"
              />
              <span class="yamtrack-title">{{ item.site_title }}</span>
              <span class="yamtrack-choice">
                {{ useYamtrack.has(item.yamtrack_id) ? "Use YamTrack's" : "Keep as is" }}
              </span>
            </label>
            <ul class="yamtrack-diffs">
              <li v-for="difference in item.differences" :key="difference.field">
                {{ difference.field }}: {{ difference.site ?? "empty" }} on the site,
                {{ difference.mal }} in YamTrack
              </li>
            </ul>
          </li>
        </ul>
      </template>

      <label class="yamtrack-details">
        <input v-model="fetchDetails" type="checkbox" />
        Fill missing posters, genres, and details from TMDB or OMDb. This only fills
        blank fields.
      </label>
      <div class="yamtrack-actions">
        <button type="button" class="primary-button" :disabled="busy" @click="runImport">
          {{ busy ? "Importing…" : "Import" }}
        </button>
        <button type="button" class="secondary-button" :disabled="busy" @click="cancel">
          Cancel
        </button>
      </div>
    </div>

    <label v-else class="secondary-button upload-label">
      {{ busy ? "Reading…" : "Choose YamTrack CSV…" }}
      <input
        type="file"
        accept=".csv,text/csv"
        class="hidden-input"
        :disabled="busy"
        @change="selected"
      />
    </label>
  </div>
</template>

<style scoped>
.yamtrack-tile {
  margin-top: 16px;
}
.yamtrack-review {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.yamtrack-bulk,
.yamtrack-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.yamtrack-list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 360px;
  overflow-y: auto;
  border: 1px solid #2a2a2a;
  border-radius: 8px;
}
.yamtrack-list > li {
  padding: 10px 12px;
  border-bottom: 1px solid #1f1f1f;
}
.yamtrack-list > li:last-child {
  border-bottom: none;
}
.yamtrack-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.yamtrack-title {
  color: #fff;
  font-size: 0.82rem;
  flex: 1;
}
.yamtrack-choice {
  color: #999;
  font-size: 0.75rem;
}
.yamtrack-diffs {
  margin: 6px 0 0 26px;
  padding-left: 16px;
  color: #999;
  font-size: 0.72rem;
}
.yamtrack-details {
  color: #aaa;
  font-size: 0.78rem;
}
.hidden-input {
  display: none;
}
.upload-label {
  display: inline-block;
  cursor: pointer;
}
.primary-button,
.secondary-button {
  border-radius: 8px;
  border: none;
  padding: 10px 16px;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
}
.primary-button {
  background: #d68a34;
  color: #111;
}
.secondary-button {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}
.primary-button:disabled,
.secondary-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.form-error,
.form-success {
  font-size: 13px;
  border-radius: 8px;
  padding: 8px 10px;
  margin-bottom: 12px;
}
.form-error {
  color: #fca5a5;
  background: rgba(220, 38, 38, 0.1);
  border: 1px solid rgba(220, 38, 38, 0.3);
}
.form-success {
  color: #86efac;
  background: rgba(34, 197, 94, 0.1);
  border: 1px solid rgba(34, 197, 94, 0.3);
}
</style>
