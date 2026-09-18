<script setup lang="ts">
// Create or edit a list. A list is either Manual (you add and order the
// titles) or Smart (a saved filter that fills itself from the whole
// library, like the Games side's Smart Collections). The kind is chosen at
// creation and can't be flipped afterwards: a manual list's hand-picked
// items and a rule's live results are different things, and silently
// dropping one for the other would lose work.
import { ref, computed } from "vue";
import { STATUS_BUCKETS } from "../utils/mediaStatus";
import type { MediaListSummary, MediaType, SmartRule } from "../services/mediaExtras";

const props = defineProps<{
  // set = editing that list; null = creating
  list: MediaListSummary | null;
  existingNames: string[];
}>();

const emit = defineEmits<{
  save: [payload: { name: string; description: string | null; smartRule: SmartRule | null }];
  close: [];
}>();

const editing = computed(() => props.list !== null);
const name = ref(props.list?.name ?? "");
const description = ref(props.list?.description ?? "");
const smart = ref(props.list?.isSmart ?? false);

const MEDIA_OPTIONS: { key: MediaType; label: string }[] = [
  { key: "movie", label: "Movies" },
  { key: "tv", label: "TV Shows" },
  { key: "anime", label: "Anime" },
];

const rule = props.list?.smartRule ?? {};
const mediaTypes = ref<MediaType[]>(rule.mediaTypes ? [...rule.mediaTypes] : []);
const statusBuckets = ref<string[]>(rule.statusBuckets ? [...rule.statusBuckets] : []);
const genre = ref(rule.genre ?? "");
const minScore = ref<number | null>(rule.minScore ?? null);
const favoriteOnly = ref(rule.favorite === true);

function toggle<T>(list: T[], value: T) {
  const i = list.indexOf(value);
  if (i === -1) list.push(value);
  else list.splice(i, 1);
}

const error = ref<string | null>(null);

function buildRule(): SmartRule {
  const r: SmartRule = {};
  if (mediaTypes.value.length) r.mediaTypes = [...mediaTypes.value];
  if (statusBuckets.value.length) r.statusBuckets = [...statusBuckets.value];
  if (genre.value.trim()) r.genre = genre.value.trim();
  if (minScore.value !== null && !Number.isNaN(minScore.value)) r.minScore = minScore.value;
  if (favoriteOnly.value) r.favorite = true;
  return r;
}

function submit() {
  const trimmed = name.value.trim();
  if (!trimmed) {
    error.value = "Give the list a name.";
    return;
  }
  const clash = props.existingNames.some(
    (n) => n.toLowerCase() === trimmed.toLowerCase() && n !== props.list?.name,
  );
  if (clash) {
    error.value = `"${trimmed}" already exists.`;
    return;
  }
  const smartRule = smart.value ? buildRule() : null;
  if (smartRule && !Object.keys(smartRule).length) {
    error.value = "Pick at least one filter, or the list would just be your whole library.";
    return;
  }
  emit("save", {
    name: trimmed,
    description: description.value.trim() || null,
    smartRule,
  });
}
</script>

<template>
  <div class="modal-backdrop" @click.self="emit('close')">
    <form class="modal-card" @submit.prevent="submit">
      <h3>{{ editing ? "Edit list" : "Create a list" }}</h3>

      <div v-if="!editing" class="kind-pick">
        <button type="button" :class="{ active: !smart }" @click="smart = false">
          <strong>Manual</strong>
          <span>You add and order the titles</span>
        </button>
        <button type="button" :class="{ active: smart }" @click="smart = true">
          <strong>Smart</strong>
          <span>Fills itself from a filter</span>
        </button>
      </div>

      <label class="field">
        <span>Name</span>
        <input v-model="name" type="text" class="input" maxlength="200" autofocus />
      </label>
      <label class="field">
        <span>Description (optional)</span>
        <input v-model="description" type="text" class="input" />
      </label>

      <template v-if="smart">
        <div class="field">
          <span>Type</span>
          <div class="chips">
            <button
              v-for="m in MEDIA_OPTIONS"
              :key="m.key"
              type="button"
              class="chip"
              :class="{ on: mediaTypes.includes(m.key) }"
              @click="toggle(mediaTypes, m.key)"
            >
              {{ m.label }}
            </button>
          </div>
          <small>None selected means all three.</small>
        </div>
        <div class="field">
          <span>Status</span>
          <div class="chips">
            <button
              v-for="s in STATUS_BUCKETS"
              :key="s.key"
              type="button"
              class="chip"
              :class="{ on: statusBuckets.includes(s.key) }"
              @click="toggle(statusBuckets, s.key)"
            >
              {{ s.label }}
            </button>
          </div>
        </div>
        <div class="row">
          <label class="field">
            <span>Genre</span>
            <input v-model="genre" type="text" class="input" placeholder="e.g. Comedy" />
          </label>
          <label class="field score-field">
            <span>Min. score</span>
            <input v-model.number="minScore" type="number" min="0" max="10" step="0.5" class="input" placeholder="0-10" />
          </label>
        </div>
        <label class="check">
          <input v-model="favoriteOnly" type="checkbox" />
          Favorites only
        </label>
      </template>

      <p v-if="error" class="error">{{ error }}</p>

      <div class="actions">
        <button type="button" class="secondary-button" @click="emit('close')">Cancel</button>
        <button type="submit" class="add-button">{{ editing ? "Save" : "Create" }}</button>
      </div>
    </form>
  </div>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.65);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
  padding: 24px;
}
.modal-card {
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  border-radius: 12px;
  padding: 22px;
  width: 100%;
  max-width: 440px;
  max-height: 88vh;
  overflow-y: auto;
  box-sizing: border-box;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.6);
  color: #fff;
}
.modal-card h3 {
  margin: 0 0 14px;
}
.kind-pick {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-bottom: 16px;
}
.kind-pick button {
  display: flex;
  flex-direction: column;
  gap: 3px;
  text-align: left;
  background: #111;
  border: 1px solid #333;
  border-radius: 10px;
  padding: 10px 12px;
  color: #ccc;
  font-family: inherit;
  cursor: pointer;
}
.kind-pick button strong {
  font-size: 0.86rem;
  color: #fff;
}
.kind-pick button span {
  font-size: 0.72rem;
  color: #888;
}
.kind-pick button.active {
  border-color: #d68a34;
  background: rgba(214, 138, 52, 0.1);
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 0.82rem;
  color: #ccc;
  margin-bottom: 14px;
  flex: 1;
}
.field small {
  color: #777;
  font-size: 0.72rem;
}
.row {
  display: flex;
  gap: 12px;
}
.score-field {
  flex: 0 0 110px;
}
.input {
  background: #111;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  color: #fff;
  padding: 9px 12px;
  font: inherit;
  font-size: 13px;
  box-sizing: border-box;
  width: 100%;
}
.input:focus {
  outline: none;
  border-color: #d68a34;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.chip {
  height: 28px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid #333;
  background: transparent;
  color: #888;
  font-family: inherit;
  font-size: 0.76rem;
  font-weight: 700;
  cursor: pointer;
}
.chip.on {
  color: #14100a;
  background: #d68a34;
  border-color: #d68a34;
}
.check {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.82rem;
  color: #ccc;
  margin-bottom: 14px;
}
.error {
  color: #fca5a5;
  font-size: 13px;
  background: rgba(220, 38, 38, 0.1);
  border: 1px solid rgba(220, 38, 38, 0.3);
  border-radius: 8px;
  padding: 8px 10px;
  margin: 0 0 12px;
}
.actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
.secondary-button {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 10px 18px;
  font-weight: 600;
  font-size: 0.84rem;
  cursor: pointer;
  font-family: inherit;
}
.add-button {
  background: #d68a34;
  color: #111;
  border: none;
  border-radius: 8px;
  padding: 10px 18px;
  font-weight: 600;
  font-size: 0.84rem;
  cursor: pointer;
  font-family: inherit;
}
</style>
