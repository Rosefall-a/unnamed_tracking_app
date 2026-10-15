<script setup lang="ts">
import { ref, onMounted } from "vue";
import { fetchUploadLimits, updateUploadLimit } from "../../services/settings";

const loading = ref(true);
const loadError = ref<string | null>(null);
const effectiveMb = ref<number | null>(null);
// what the admin's typing — separate from effectiveMb so a bad value being
// edited doesn't flash the wrong number elsewhere while it's mid-edit
const draftMb = ref("");

const saving = ref(false);
const saveError = ref<string | null>(null);
const saveSuccess = ref(false);

async function load() {
  loading.value = true;
  loadError.value = null;
  try {
    const r = await fetchUploadLimits();
    effectiveMb.value = r.max_upload_size_mb;
    draftMb.value = String(r.max_upload_size_mb);
  } catch (e) {
    loadError.value =
      e instanceof Error ? e.message : "Could not load the upload limit.";
  } finally {
    loading.value = false;
  }
}
onMounted(load);

async function save() {
  const n = Number(draftMb.value);
  saveError.value = null;
  saveSuccess.value = false;
  if (!Number.isFinite(n) || n < 1) {
    saveError.value = "Enter a whole number of at least 1 MB.";
    return;
  }
  saving.value = true;
  try {
    const r = await updateUploadLimit(Math.round(n));
    effectiveMb.value = r.max_upload_size_mb;
    saveSuccess.value = true;
  } catch (e) {
    saveError.value =
      e instanceof Error ? e.message : "Could not save the upload limit.";
  } finally {
    saving.value = false;
  }
}

async function resetToDefault() {
  saving.value = true;
  saveError.value = null;
  saveSuccess.value = false;
  try {
    const r = await updateUploadLimit(null);
    effectiveMb.value = r.max_upload_size_mb;
    draftMb.value = String(r.max_upload_size_mb);
    saveSuccess.value = true;
  } catch (e) {
    saveError.value =
      e instanceof Error ? e.message : "Could not reset the upload limit.";
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <section class="settings-section">
    <h2>Upload limits</h2>
    <p class="hint">
      Server-wide limits for administrators. Only the image and media upload
      size can be changed here. Video clips and world saves have separate,
      larger limits.
    </p>

    <p v-if="loading" class="hint">Loading…</p>
    <template v-else>
      <p v-if="loadError" class="form-error">{{ loadError }}</p>
      <template v-else>
        <label class="field">
          <span>Max upload size (MB)</span>
          <div class="row">
            <input
              v-model="draftMb"
              type="number"
              min="1"
              step="1"
              inputmode="numeric"
            />
            <button
              type="button"
              class="primary-button"
              :disabled="saving"
              @click="save"
            >
              {{ saving ? "Saving…" : "Save" }}
            </button>
          </div>
          <span class="field-hint">
            Applies to cover art, banners, screenshots and documents.
          </span>
        </label>

        <button
          type="button"
          class="text-button"
          :disabled="saving"
          @click="resetToDefault"
        >
          Reset to default
        </button>

        <div v-if="saveError" class="form-error">{{ saveError }}</div>
        <div v-if="saveSuccess" class="form-success">Saved</div>
      </template>
    </template>
  </section>
</template>

<style scoped>
.settings-section {
  max-width: 480px;
}
.settings-section h2 {
  margin: 0 0 8px;
  padding-left: 12px;
  border-left: 3px solid var(--ui-accent);
  font-size: 1rem;
  color: var(--ui-heading);
}
.hint {
  color: var(--ui-dim-2);
  font-size: 0.85rem;
  line-height: 1.5;
  margin: 0 0 18px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 0.85rem;
  color: var(--ui-text-soft);
  margin-bottom: 12px;
}
.row {
  display: flex;
  gap: 10px;
}
.field input {
  flex: 1;
  min-width: 0;
  background: var(--ui-bg-2);
  border: 1px solid var(--ui-border-strong);
  border-radius: 8px;
  color: var(--ui-heading);
  padding: 10px 12px;
  font: inherit;
}
.field input:focus {
  outline: none;
  border-color: var(--ui-accent);
}
.field-hint {
  color: var(--ui-faint-2);
  font-size: 0.78rem;
}
.primary-button {
  background: var(--ui-accent);
  color: #111;
  border: none;
  border-radius: 8px;
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
  color: var(--ui-accent);
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
  color: var(--ui-error-text);
  font-size: 13px;
  background: color-mix(in srgb, var(--ui-danger) 10%, transparent);
  border: 1px solid color-mix(in srgb, var(--ui-danger) 30%, transparent);
  border-radius: 8px;
  padding: 8px 10px;
}
.form-success {
  margin-top: 12px;
  color: var(--ui-good-text);
  font-size: 13px;
  background: color-mix(in srgb, var(--ui-success) 10%, transparent);
  border: 1px solid color-mix(in srgb, var(--ui-success) 30%, transparent);
  border-radius: 8px;
  padding: 8px 10px;
}
</style>
