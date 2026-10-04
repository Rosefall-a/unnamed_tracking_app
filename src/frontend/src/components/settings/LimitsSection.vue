<script setup lang="ts">
import { ref, onMounted, useId } from "vue";
import {
  fetchUploadLimits,
  updateUploadLimits,
  type UploadLimits,
} from "../../services/settings";
const fieldId = useId();
const limits: { key: keyof UploadLimits; label: string; hint: string }[] = [
  {
    key: "max_upload_size_mb",
    label: "Images & general files",
    hint: "Cover art, banners, screenshots, documents and other general uploads.",
  },
  {
    key: "max_save_archive_size_mb",
    label: "Save archives",
    hint: "Each version of a named game save archive.",
  },
  {
    key: "max_clip_size_mb",
    label: "Video clips",
    hint: "Clips and soundtracks uploaded to a game or the media inbox.",
  },
  {
    key: "max_world_save_size_mb",
    label: "World saves & modpacks",
    hint: "Each uploaded world save archive or modpack.",
  },
];
const loading = ref(true),
  saving = ref(false);
const error = ref("");
const success = ref("");
const effective = ref<UploadLimits | null>(null);
const drafts = ref<Partial<Record<keyof UploadLimits, string | number>>>({});
function apply(values: UploadLimits) {
  effective.value = values;
  for (const { key } of limits) drafts.value[key] = String(values[key]);
}
onMounted(async () => {
  try {
    apply(await fetchUploadLimits());
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Unable to load limits.";
  } finally {
    loading.value = false;
  }
});
async function save(reset = false) {
  error.value = "";
  success.value = "";
  const values: Partial<Record<keyof UploadLimits, number | null>> = {};
  for (const { key, label } of limits) {
    const raw = String(drafts.value[key] ?? "").trim();
    const value = Number(raw);
    if (
      !reset &&
      (!raw || !Number.isInteger(value) || value < 1 || value > 2147483647)
    ) {
      error.value = `${label}: enter a whole number from 1 to 2147483647 MB.`;
      return;
    }
    values[key] = reset ? null : value;
  }
  saving.value = true;
  try {
    apply(await updateUploadLimits(values));
    success.value = reset
      ? "All limits reset to the server environment defaults."
      : "Limits saved. New uploads use them immediately.";
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Unable to save limits.";
  } finally {
    saving.value = false;
  }
}
</script>
<template>
  <section class="settings-section">
    <h2>Upload limits</h2>
    <p class="hint">
      Server-wide limits in megabytes. Each value overrides its environment
      default; resetting uses the current server configuration.
    </p>
    <p v-if="loading" class="hint">Loading…</p>
    <form v-else-if="effective" @submit.prevent="save()">
      <div v-for="limit in limits" :key="limit.key" class="field">
        <label :for="`${fieldId}-${limit.key}`">{{ limit.label }} (MB)</label>
        <input
          :id="`${fieldId}-${limit.key}`"
          :aria-describedby="`${fieldId}-${limit.key}-hint`"
          v-model="drafts[limit.key]"
          type="number"
          min="1"
          max="2147483647"
          step="1"
          inputmode="numeric"
          required
          :disabled="saving"
        />
        <span :id="`${fieldId}-${limit.key}-hint`" class="field-hint"
          >{{ limit.hint }} <code>{{ limit.key.toUpperCase() }}</code></span
        >
      </div>
      <div class="row">
        <button type="submit" class="primary-button" :disabled="saving">
          {{ saving ? "Saving…" : "Save limits" }}
        </button>
        <button
          type="button"
          class="text-button"
          :disabled="saving"
          @click="save(true)"
        >
          Reset all to server defaults
        </button>
      </div>
    </form>
    <p v-if="error" class="form-error" role="alert">{{ error }}</p>
    <p v-if="success" class="form-success" role="status">{{ success }}</p>
  </section>
</template>
<style scoped>
.settings-section {
  max-width: 760px;
}
.settings-section h2 {
  margin: 0 0 12px;
  font: var(--ui-weight-heading) var(--ui-font-heading)/1.4
    var(--ui-font-family);
  color: var(--ui-text);
}
.hint {
  color: var(--ui-faint);
  font-size: 0.85rem;
  line-height: 1.5;
  margin: 0 0 18px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 0.85rem;
  color: var(--ui-text);
  margin-bottom: 12px;
}
.row {
  display: flex;
  gap: 10px;
}
.field input {
  flex: 1;
  min-width: 0;
  background: var(--ui-bg);
  border: 1px solid var(--ui-border-strong);
  border-radius: var(--ui-radius-control);
  color: var(--ui-text);
  padding: 10px 12px;
  font: inherit;
}
.field input:focus {
  border-color: var(--ui-accent);
}
.field-hint {
  color: var(--ui-faint);
  font-size: 0.78rem;
}
.primary-button {
  background: var(--ui-accent);
  color: var(--ui-on-accent);
  border: none;
  border-radius: var(--ui-radius-control);
  padding: 0 18px;
  font-weight: 600;
  cursor: pointer;
}
.primary-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.text-button {
  background: none;
  border: none;
  padding: 0;
  color: var(--ui-accent-text);
  font-size: 0.82rem;
  cursor: pointer;
}
.text-button:hover {
  text-decoration: underline;
}
.text-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  text-decoration: none;
}
.form-error {
  margin-top: 12px;
  color: var(--ui-error);
  font-size: 13px;
  background: rgba(220, 38, 38, 0.1);
  border: 1px solid rgba(220, 38, 38, 0.3);
  border-radius: var(--ui-radius-control);
  padding: 8px 10px;
}
.form-success {
  margin-top: 12px;
  color: var(--ui-good);
  font-size: 13px;
  background: rgba(34, 197, 94, 0.1);
  border: 1px solid rgba(34, 197, 94, 0.3);
  border-radius: var(--ui-radius-control);
  padding: 8px 10px;
}
.row {
  flex-wrap: wrap;
}
button,
input {
  min-height: var(--ui-control-height);
}
code {
  display: block;
  margin-top: 4px;
  overflow-wrap: anywhere;
}
</style>
