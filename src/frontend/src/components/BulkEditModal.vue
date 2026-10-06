<script setup lang="ts">
import { reactive, ref } from "vue";
import { bulkUpdateGames } from "../services/games";
import type { BulkEditFields } from "../services/games";
import type { GameStatus } from "../types/game";
import { PRIORITY_OPTIONS } from "../utils/priority";

const props = defineProps<{
  gameIds: string[];
}>();

const emit = defineEmits<{
  close: [];
  saved: [count: number];
}>();

const statuses: GameStatus[] = [
  "playing",
  "beaten",
  "mastered",
  "played",
  "on hold",
  "dropped",
  "backlog",
  "wishlist",
];

// each field is opt-in via its own checkbox, leaving one unchecked means
// "don't touch this field on any selected game", never "clear it"
const apply = reactive({
  status: false,
  favorite: false,
  developer: false,
  publisher: false,
  series: false,
  ageRating: false,
  platform: false,
  priority: false,
  tags: false,
  features: false,
});

const statusValue = ref<GameStatus>("backlog");
const favoriteValue = ref(true);
const developerValue = ref("");
const publisherValue = ref("");
const seriesValue = ref("");
const ageRatingValue = ref("");
const platformValue = ref("");
const priorityValue = ref("");
const tagsValue = ref("");
const featuresValue = ref("");

const saving = ref(false);
const error = ref<string | null>(null);

const anyFieldChecked = () => Object.values(apply).some(Boolean);

async function submit() {
  if (!anyFieldChecked()) {
    error.value = "Check at least one field to apply.";
    return;
  }
  saving.value = true;
  error.value = null;
  try {
    const fields: BulkEditFields = {};
    if (apply.status) fields.status = statusValue.value;
    if (apply.favorite) fields.favorite = favoriteValue.value;
    if (apply.developer) fields.developer = developerValue.value.trim() || null;
    if (apply.publisher) fields.publisher = publisherValue.value.trim() || null;
    if (apply.series) fields.series = seriesValue.value.trim() || null;
    if (apply.ageRating) fields.ageRating = ageRatingValue.value.trim() || null;
    if (apply.platform) fields.platform = platformValue.value.trim() || null;
    if (apply.priority) fields.priority = priorityValue.value || null;
    if (apply.tags)
      fields.tags = tagsValue.value
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
    if (apply.features)
      fields.features = featuresValue.value
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);

    const count = await bulkUpdateGames(props.gameIds, fields);
    emit("saved", count);
  } catch (err) {
    error.value =
      err instanceof Error ? err.message : "Failed to bulk-update games";
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <div class="modal-backdrop" @click.self="emit('close')">
    <div class="modal">
      <div class="modal-header">
        <h2>
          Bulk Edit: {{ gameIds.length }} game{{
            gameIds.length === 1 ? "" : "s"
          }}
        </h2>
        <button type="button" class="close-button" @click="emit('close')">
          ✕
        </button>
      </div>

      <form class="modal-form" @submit.prevent="submit">
        <div class="modal-body">
          <p class="hint">
            Check a field to apply it to every selected game: an unchecked field
            is left exactly as-is on all of them.
          </p>

          <div class="field-row">
            <label class="field-check">
              <input v-model="apply.status" type="checkbox" />
              <span>Status</span>
            </label>
            <select
              v-model="statusValue"
              class="field-input"
              :disabled="!apply.status"
              aria-label="New status"
            >
              <option v-for="s in statuses" :key="s" :value="s">{{ s }}</option>
            </select>
          </div>

          <div class="field-row">
            <label class="field-check">
              <input v-model="apply.favorite" type="checkbox" />
              <span>Favorite</span>
            </label>
            <select
              v-model="favoriteValue"
              class="field-input"
              :disabled="!apply.favorite"
              aria-label="Favorite"
            >
              <option :value="true">Mark as favorite</option>
              <option :value="false">Remove from favorites</option>
            </select>
          </div>

          <div class="field-row">
            <label class="field-check">
              <input v-model="apply.developer" type="checkbox" />
              <span>Developer</span>
            </label>
            <input
              v-model="developerValue"
              type="text"
              class="field-input"
              :disabled="!apply.developer"
              aria-label="New developer"
              placeholder="Developer name"
            />
          </div>

          <div class="field-row">
            <label class="field-check">
              <input v-model="apply.publisher" type="checkbox" />
              <span>Publisher</span>
            </label>
            <input
              v-model="publisherValue"
              type="text"
              class="field-input"
              :disabled="!apply.publisher"
              aria-label="New publisher"
              placeholder="Publisher name"
            />
          </div>

          <div class="field-row">
            <label class="field-check">
              <input v-model="apply.series" type="checkbox" />
              <span>Series</span>
            </label>
            <input
              v-model="seriesValue"
              type="text"
              class="field-input"
              :disabled="!apply.series"
              aria-label="New series"
              placeholder="Franchise name"
            />
          </div>

          <div class="field-row">
            <label class="field-check">
              <input v-model="apply.ageRating" type="checkbox" />
              <span>Age Rating</span>
            </label>
            <input
              v-model="ageRatingValue"
              type="text"
              class="field-input"
              :disabled="!apply.ageRating"
              aria-label="New age rating"
              placeholder="e.g. 17+"
            />
          </div>

          <div class="field-row">
            <label class="field-check">
              <input v-model="apply.platform" type="checkbox" />
              <span>Platform</span>
            </label>
            <input
              v-model="platformValue"
              type="text"
              class="field-input"
              :disabled="!apply.platform"
              aria-label="New platform"
              placeholder="e.g. PC, Nintendo Switch (blank clears)"
            />
          </div>

          <div class="field-row">
            <label class="field-check">
              <input v-model="apply.priority" type="checkbox" />
              <span>Priority</span>
            </label>
            <select
              v-model="priorityValue"
              class="field-input"
              :disabled="!apply.priority"
              aria-label="New priority"
            >
              <option value="">None (clear)</option>
              <option
                v-for="option in PRIORITY_OPTIONS"
                :key="option.value"
                :value="option.value"
              >
                {{ option.label }}
              </option>
            </select>
          </div>

          <div class="field-row">
            <label class="field-check">
              <input v-model="apply.tags" type="checkbox" />
              <span>Tags</span>
            </label>
            <input
              v-model="tagsValue"
              type="text"
              class="field-input"
              :disabled="!apply.tags"
              aria-label="New tags"
              placeholder="Comma-separated: replaces existing tags"
            />
          </div>

          <div class="field-row">
            <label class="field-check">
              <input v-model="apply.features" type="checkbox" />
              <span>Features</span>
            </label>
            <input
              v-model="featuresValue"
              type="text"
              class="field-input"
              :disabled="!apply.features"
              aria-label="New features"
              placeholder="Comma-separated: replaces existing features"
            />
          </div>

          <div v-if="error" class="form-error">{{ error }}</div>
        </div>

        <div class="modal-footer">
          <button type="button" class="secondary-button" @click="emit('close')">
            Cancel
          </button>
          <button type="submit" class="primary-button" :disabled="saving">
            {{
              saving
                ? "Applying…"
                : `Apply to ${gameIds.length} game${gameIds.length === 1 ? "" : "s"}`
            }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: var(--ui-overlay);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: var(--ui-z-modal);
}
.modal {
  background: var(--ui-surface);
  border: 1px solid var(--ui-border);
  border-radius: 14px;
  width: 100%;
  max-width: 520px;
  max-height: 88vh;
  display: flex;
  flex-direction: column;
  color: var(--ui-text);
  font-family: var(--ui-font-family);
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.6);
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 22px;
  border-bottom: 1px solid var(--ui-border);
  flex-shrink: 0;
}
.modal-header h2 {
  margin: 0;
  font-size: 1.1rem;
}
.close-button {
  background: none;
  border: none;
  color: var(--ui-dim);
  font-size: 15px;
  cursor: pointer;
  width: var(--ui-control-height);
  height: var(--ui-control-height);
  border-radius: 50%;
  transition:
    background 0.15s ease,
    color 0.15s ease;
}
.close-button:hover {
  background: color-mix(in srgb, var(--ui-text) 10%, transparent);
  color: var(--ui-text);
}
.modal-form {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}
.modal-body {
  padding: 18px 22px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}
.hint {
  color: var(--ui-dim);
  font-size: 12.5px;
  line-height: 1.5;
  margin: 0 0 4px;
}
.field-row {
  display: grid;
  grid-template-columns: 130px 1fr;
  align-items: center;
  gap: 12px;
}
.field-check {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--ui-text);
  font-size: 13px;
  cursor: pointer;
}
.field-check input {
  accent-color: var(--ui-accent-text);
  width: 15px;
  height: 15px;
  cursor: pointer;
}
.field-input {
  height: 36px;
  box-sizing: border-box;
  background: var(--ui-surface);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-control);
  color: var(--ui-text);
  padding: 0 12px;
  font: inherit;
  font-size: 13px;
}
.field-input:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.field-input:focus:not(:disabled) {
  outline: none;
  border-color: var(--ui-accent-line);
}
.form-error {
  color: var(--ui-error);
  font-size: 13px;
  background: rgba(220, 38, 38, 0.1);
  border: 1px solid rgba(220, 38, 38, 0.3);
  border-radius: var(--ui-radius-control);
  padding: 8px 10px;
}
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 22px;
  border-top: 1px solid var(--ui-border);
  flex-shrink: 0;
}
.primary-button,
.secondary-button {
  border: none;
  border-radius: var(--ui-radius-control);
  padding: 10px 18px;
  font-weight: 600;
  cursor: pointer;
  font-size: 13px;
}
.primary-button {
  background: var(--ui-accent);
  color: var(--ui-on-accent);
}
.primary-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.secondary-button {
  background: color-mix(in srgb, var(--ui-text) 8%, transparent);
  color: var(--ui-text);
}
</style>
