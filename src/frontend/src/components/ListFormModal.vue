<script setup lang="ts">
// Create or edit a list. A list is either Manual (you add and order the
// titles) or Smart (a saved filter that fills itself from the whole
// library, like the Games side's Smart Collections). The kind is chosen at
// creation and can't be flipped afterwards: a manual list's hand-picked
// items and a rule's live results are different things, and silently
// dropping one for the other would lose work.
import { ref, computed } from "vue";
import { STATUS_BUCKETS } from "../utils/mediaStatus";
import type {
  MediaListSummary,
  MediaType,
  SmartRule,
} from "../services/mediaExtras";

const props = defineProps<{
  // set = editing that list; null = creating
  list: MediaListSummary | null;
  existingNames: string[];
}>();

const emit = defineEmits<{
  save: [
    payload: {
      name: string;
      description: string | null;
      smartRule: SmartRule | null;
    },
  ];
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
const mediaTypes = ref<MediaType[]>(
  rule.mediaTypes ? [...rule.mediaTypes] : [],
);
const statusBuckets = ref<string[]>(
  rule.statusBuckets ? [...rule.statusBuckets] : [],
);
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
  if (minScore.value !== null && !Number.isNaN(minScore.value))
    r.minScore = minScore.value;
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
    error.value =
      "Pick at least one filter, or the list would just be your whole library.";
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
  <div class="ui-backdrop" @click.self="emit('close')">
    <form
      class="ui-modal"
      role="dialog"
      aria-modal="true"
      @submit.prevent="submit"
    >
      <h3>{{ editing ? "Edit list" : "Create a list" }}</h3>

      <div v-if="!editing" class="kind-pick">
        <button
          type="button"
          :class="{ active: !smart }"
          @click="smart = false"
        >
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
        <input
          v-model="name"
          type="text"
          class="ui-field"
          maxlength="200"
          autofocus
        />
      </label>
      <label class="field">
        <span>Description (optional)</span>
        <input v-model="description" type="text" class="ui-field" />
      </label>

      <template v-if="smart">
        <div class="field">
          <span>Type</span>
          <div class="chips">
            <button
              v-for="m in MEDIA_OPTIONS"
              :key="m.key"
              type="button"
              class="ui-chip"
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
              class="ui-chip"
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
            <input
              v-model="genre"
              type="text"
              class="ui-field"
              placeholder="e.g. Comedy"
            />
          </label>
          <label class="field score-field">
            <span>Min. score</span>
            <input
              v-model.number="minScore"
              type="number"
              min="0"
              max="10"
              step="0.5"
              class="ui-field"
              placeholder="0-10"
            />
          </label>
        </div>
        <label class="check">
          <input v-model="favoriteOnly" type="checkbox" />
          Favorites only
        </label>
      </template>

      <p v-if="error" class="ui-error-box">{{ error }}</p>

      <div class="ui-modal-actions">
        <button
          type="button"
          class="ui-btn ui-btn-secondary"
          @click="emit('close')"
        >
          Cancel
        </button>
        <button type="submit" class="ui-btn ui-btn-primary">
          {{ editing ? "Save" : "Create" }}
        </button>
      </div>
    </form>
  </div>
</template>

<style scoped>
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
  color: #9c9c9c;
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
  color: #666;
  font-size: 0.72rem;
}
.row {
  display: flex;
  gap: 12px;
}
.score-field {
  flex: 0 0 110px;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.check {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.82rem;
  color: #ccc;
  margin-bottom: 14px;
}
</style>
