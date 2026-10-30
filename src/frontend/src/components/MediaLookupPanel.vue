<script setup lang="ts" generic="R extends { title: string; provider: string }">
// The "Look up metadata" panel of the movie, TV and anime forms. It searches the
// providers, reads the details of the title that is picked, and lists what would
// change field by field. Only the ticked fields are handed back; the form applies
// them. It is the media version of the game form's panel and looks the same.
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import type { LookupApply, LookupChange } from "../utils/mediaLookup";

const props = defineProps<{
  noun: string;
  // searches the providers for this text; the list below is what it found
  run: (query: string) => Promise<void>;
  resolve: (result: R) => Promise<R>;
  results: R[];
  searching: boolean;
  message: string | null;
  warnings: string[];
  // what the list shows for each result
  describe: (result: R) => {
    key: string;
    title: string;
    provider: string;
    detail?: string;
    image?: string | null;
  };
  // the fields a picked title would fill in
  build: (match: R, poster: string | null) => LookupChange[];
  // the poster a picked title offers
  posterOf: (match: R) => string | null;
  adding: boolean;
  initialQuery: string;
}>();

const emit = defineEmits<{
  close: [];
  apply: [changes: LookupApply[], provider: string];
}>();

const query = ref(props.initialQuery);
const picked = ref<R | null>(null);
const changes = ref<LookupChange[]>([]);
const reading = ref(false);
let timer: ReturnType<typeof setTimeout> | null = null;
let pickId = 0;

const items = computed(() =>
  props.results.map((r) => ({ r, ...props.describe(r) })),
);

function onInput() {
  if (timer) clearTimeout(timer);
  timer = setTimeout(() => void props.run(query.value), 250);
}

async function pick(result: R) {
  const id = ++pickId;
  picked.value = result;
  changes.value = [];
  reading.value = true;
  const match = await props.resolve(result);
  // a later pick, or going back, makes this answer stale
  if (id !== pickId) return;
  reading.value = false;
  changes.value = props.build(match, props.posterOf(match));
  picked.value = match;
}

function back() {
  pickId++;
  picked.value = null;
  changes.value = [];
}

const ticked = computed(() => changes.value.filter((c) => c.checked));
function apply() {
  emit(
    "apply",
    ticked.value.map((c) => ({ key: c.key, value: c.value })),
    picked.value?.provider ?? "the provider",
  );
}

function onKey(e: KeyboardEvent) {
  if (e.key === "Escape") {
    e.stopPropagation();
    emit("close");
  }
}
onMounted(() => {
  window.addEventListener("keydown", onKey, true);
  if (query.value.trim().length >= 2) void props.run(query.value);
});
onBeforeUnmount(() => {
  window.removeEventListener("keydown", onKey, true);
  if (timer) clearTimeout(timer);
});
</script>

<template>
  <aside class="ml" aria-label="Look up metadata">
    <div class="ml-head">
      <div>
        <div class="ml-kicker">Look up metadata</div>
        <p class="ml-hint">
          Pick a {{ noun }}, then choose which fields to fill in.
        </p>
      </div>
      <button
        type="button"
        class="ml-close"
        aria-label="Close lookup"
        @click="emit('close')"
      >
        &#10005;
      </button>
    </div>
    <div class="ml-search">
      <input
        v-model="query"
        type="search"
        :placeholder="`Search for a ${noun}`"
        autofocus
        @input="onInput"
        @keydown.enter.prevent="run(query)"
      />
    </div>

    <div class="ml-body">
      <template v-if="!picked">
        <p v-if="searching" class="ml-hint">Searching…</p>
        <p v-else-if="message" class="ml-hint">{{ message }}</p>
        <p v-for="w in warnings" :key="w" class="ml-hint">
          {{ w }}
        </p>
        <button
          v-for="item in items"
          :key="item.key"
          type="button"
          class="ml-result"
          @click="pick(item.r)"
        >
          <span
            class="ml-result-art"
            :style="item.image ? { backgroundImage: `url(${item.image})` } : {}"
          ></span>
          <span class="ml-result-text">
            <strong>{{ item.title }}</strong>
            <span v-if="item.detail" class="ml-result-meta">{{
              item.detail
            }}</span>
          </span>
          <span class="ml-chip">{{ item.provider }}</span>
        </button>
      </template>

      <template v-else>
        <button type="button" class="ml-back" @click="back">
          &larr; Back to results
        </button>
        <p class="ml-section">
          {{ reading ? "Reading the details…" : picked.title }}
        </p>
        <p v-if="!reading && !changes.length" class="ml-hint">
          Nothing new to fill in from {{ picked.provider }}.
        </p>
        <label v-for="change in changes" :key="change.key" class="ml-change">
          <input v-model="change.checked" type="checkbox" />
          <span class="ml-change-text">
            <strong>{{ change.label }}</strong>
            <span class="ml-change-values">
              <s v-if="change.from">{{ change.from }}</s>
              <span class="ml-change-to">{{ change.to }}</span>
            </span>
          </span>
          <span
            v-if="change.fromImage"
            class="ml-change-img old"
            :style="{ backgroundImage: `url(${change.fromImage})` }"
          ></span>
          <span
            v-if="change.image"
            class="ml-change-img"
            :style="{ backgroundImage: `url(${change.image})` }"
          ></span>
        </label>
      </template>
    </div>

    <div v-if="picked && changes.length" class="ml-foot">
      <button type="button" class="ml-btn" @click="emit('close')">
        Cancel
      </button>
      <button
        type="button"
        class="ml-btn solid"
        :disabled="!ticked.length"
        @click="apply"
      >
        Apply {{ ticked.length }}
        {{ ticked.length === 1 ? "change" : "changes" }}
      </button>
    </div>
  </aside>
</template>

<style scoped>
/* fixed colours, the same as the form it opens over */
.ml {
  --surface: var(--ui-surface);
  --surface-2: var(--ui-surface-2);
  --border: var(--ui-border);
  --border-soft: var(--ui-border-soft);
  --accent: var(--ui-accent);
  --accent-line: var(--ui-accent-line);
  --text: var(--ui-text);
  --text-dim: var(--ui-dim);
  --text-faint: #666;
  position: absolute;
  inset: 0 0 0 auto;
  z-index: 2;
  display: flex;
  flex-direction: column;
  width: min(420px, 100%);
  background: var(--ui-popover, var(--ui-popover));
  border-left: 1px solid var(--border);
  box-shadow: -12px 0 32px
    color-mix(in srgb, var(--ui-scrim-base) 45%, transparent);
  color: var(--text);
}
.ml * {
  box-sizing: border-box;
}
.ml-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  padding: 14px 16px 6px;
}
.ml-kicker {
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--accent);
}
.ml-hint {
  margin: 4px 0 8px;
  font-size: 0.78rem;
  color: var(--text-faint);
  line-height: 1.5;
}
.ml-close {
  flex: none;
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: 8px;
  background: none;
  color: var(--text-dim);
  font-size: 1rem;
  cursor: pointer;
}
.ml-close:hover {
  background: var(--surface-2);
  color: var(--text);
}
.ml-search {
  padding: 4px 16px 12px;
  border-bottom: 1px solid var(--border-soft);
}
.ml-search input {
  width: 100%;
  background: var(--surface-2);
  border: 1px solid var(--border);
  color: var(--text);
  border-radius: 8px;
  padding: 9px 11px;
  font: inherit;
  font-size: 0.86rem;
}
.ml-search input:focus {
  outline: none;
  border-color: var(--accent-line);
}
.ml-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 10px 16px;
}
.ml-foot {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid var(--border-soft);
  background: var(--surface);
}
.ml-btn {
  height: 36px;
  padding: 0 14px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: transparent;
  color: var(--text-dim);
  font: inherit;
  font-size: 0.84rem;
  font-weight: 600;
  cursor: pointer;
}
.ml-btn:hover {
  color: var(--text);
  border-color: var(--accent-line);
}
.ml-btn.solid {
  background: var(--accent);
  border-color: var(--accent);
  color: var(--ui-on-accent);
}
.ml-btn.solid:disabled {
  opacity: 0.6;
  cursor: default;
}
.ml-result {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  margin-bottom: 8px;
  padding: 8px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface-2);
  color: var(--text);
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.ml-result:hover {
  border-color: var(--accent-line);
}
.ml-btn:focus-visible,
.ml-result:focus-visible,
.ml-close:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
.ml-result-art {
  flex: none;
  width: 42px;
  height: 58px;
  border-radius: 6px;
  background-color: var(--surface);
  background-size: cover;
  background-position: center;
}
.ml-result-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.ml-result-text strong {
  font-size: 0.86rem;
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ml-result-meta {
  font-size: 0.74rem;
  color: var(--text-faint);
}
.ml-chip {
  flex: none;
  padding: 1px 8px;
  border: 1px solid var(--border);
  border-radius: 999px;
  font-size: 0.68rem;
  color: var(--text-dim);
}
.ml-back {
  margin-bottom: 4px;
  padding: 0;
  border: 0;
  background: none;
  color: var(--text-faint);
  font: inherit;
  font-size: 0.78rem;
  cursor: pointer;
}
.ml-back:hover {
  color: var(--accent);
}
.ml-section {
  margin: 10px 0 6px;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-faint);
}
.ml-change {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 9px 0;
  border-bottom: 1px solid var(--border-soft);
  cursor: pointer;
}
.ml-change input {
  margin-top: 3px;
  accent-color: var(--accent);
}
.ml-change-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 0.82rem;
}
.ml-change-values {
  display: flex;
  flex-direction: column;
  gap: 1px;
  color: var(--text-faint);
  overflow-wrap: anywhere;
}
.ml-change-to {
  color: var(--text-dim);
}
.ml-change-img {
  flex: none;
  width: 36px;
  height: 50px;
  border-radius: 5px;
  background-color: var(--surface-2);
  background-size: cover;
  background-position: center;
}
.ml-change-img.old {
  opacity: 0.55;
}
</style>
