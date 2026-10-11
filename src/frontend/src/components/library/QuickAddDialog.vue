<script setup lang="ts" generic="T extends QuickAddResult">
// The dialog the Add buttons open: search, pick a result, fill in a short form,
// add. The Movies, TV, Anime and Games libraries all use this one, so adding
// something looks and works the same everywhere. The page decides what the form
// asks (the `fields` slot), how a result's details read (`meta`), and what adding does.
import { onBeforeUnmount, onMounted, ref, shallowRef } from "vue";

export interface QuickAddResult {
  title: string;
  poster: string | null;
  // shown behind the poster, so a poster that fails to load falls back to these
  fallbackPosters?: string[];
  description: string | null;
  releaseYear: string | null;
}

const props = defineProps<{
  title: string;
  search: (
    query: string,
  ) => Promise<{ results: T[]; providerErrors: string[] }>;
  saving: boolean;
  // shown under the short form when adding failed
  error?: string | null;
  submitLabel?: string;
  sectionLabel?: string;
}>();

const emit = defineEmits<{
  close: [];
  pick: [result: T];
  add: [result: T];
}>();

const step = ref<"search" | "form">("search");
const query = ref("");
// shallow: unwrapping a generic result type is what the type checker cannot follow
const results = shallowRef<T[]>([]);
const providerErrors = ref<string[]>([]);
const searching = ref(false);
const picked = shallowRef<T | null>(null);

async function runSearch() {
  if (!query.value.trim()) {
    results.value = [];
    return;
  }
  searching.value = true;
  try {
    const found = await props.search(query.value);
    results.value = found.results;
    providerErrors.value = found.providerErrors;
  } finally {
    searching.value = false;
  }
}
// layered, top one first: an image that fails to load leaves the next one showing
function hasArt(r: QuickAddResult): boolean {
  return !!r.poster || !!r.fallbackPosters?.length;
}

function artStyle(r: QuickAddResult) {
  const urls = [r.poster, ...(r.fallbackPosters ?? [])].filter(Boolean);
  return urls.length
    ? { backgroundImage: urls.map((u) => `url(${u})`).join(", ") }
    : {};
}

function pick(result: T) {
  picked.value = result;
  step.value = "form";
  emit("pick", result);
}

function onEscape(e: KeyboardEvent) {
  if (e.key === "Escape") emit("close");
}
onMounted(() => window.addEventListener("keydown", onEscape));
onBeforeUnmount(() => window.removeEventListener("keydown", onEscape));
</script>

<template>
  <div class="modal-overlay" @click.self="emit('close')">
    <div class="modal-card qa-card">
      <div v-if="step === 'search'">
        <div class="qa-header">
          <div class="qa-header-row">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
            >
              <circle cx="11" cy="11" r="7" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            <h3>{{ title }}</h3>
          </div>
          <div class="sub">Search, then pick the right result.</div>
        </div>
        <div class="qa-body">
          <div class="qa-search-row">
            <input
              v-model="query"
              autofocus
              placeholder="Search by title..."
              @keyup.enter="runSearch"
            />
            <button type="button" class="qa-add-btn" @click="runSearch">
              Search
            </button>
          </div>
          <p
            v-if="providerErrors.length"
            class="empty-state error"
            style="padding: 8px 0; font-size: 0.78rem"
          >
            {{ providerErrors.join(" · ") }}
          </p>
          <p v-if="searching" class="empty-state">Searching…</p>
          <p v-else-if="!results.length" class="empty-state">
            No results yet. Search above.
          </p>
          <div v-else class="qa-results">
            <div v-for="(r, i) in results" :key="i" class="qa-result">
              <div class="qa-result-art" :style="artStyle(r)">
                <span v-if="!hasArt(r)" class="qa-art-initial">{{
                  r.title.charAt(0)
                }}</span>
              </div>
              <div class="qa-result-titles">
                <div class="qa-result-english">{{ r.title }}</div>
                <div class="qa-result-meta">
                  <slot name="meta" :result="r">
                    <span v-if="r.releaseYear">{{ r.releaseYear }}</span>
                  </slot>
                </div>
                <div v-if="r.description" class="qa-result-desc">
                  {{ r.description }}
                </div>
              </div>
              <button type="button" class="qa-add-btn" @click="pick(r)">
                + Add
              </button>
            </div>
          </div>
          <div class="qa-search-foot">
            <slot name="foot" />
            <button type="button" class="btn-outline" @click="emit('close')">
              Cancel
            </button>
          </div>
        </div>
      </div>

      <div v-else-if="picked">
        <div class="qa-body">
          <button type="button" class="qa-back-link" @click="step = 'search'">
            &larr; Back to results
          </button>
          <div class="qa-form-header">
            <div class="qa-form-art" :style="artStyle(picked)">
              <span v-if="!hasArt(picked)" class="qa-art-initial">{{
                picked.title.charAt(0)
              }}</span>
            </div>
            <div class="qa-form-titles">
              <div class="qa-result-english">{{ picked.title }}</div>
              <div class="qa-result-meta">
                <slot name="meta" :result="picked">
                  <span v-if="picked.releaseYear">{{
                    picked.releaseYear
                  }}</span>
                </slot>
              </div>
            </div>
          </div>
          <p class="qa-section-label">{{ sectionLabel ?? "Your progress" }}</p>
          <div class="qa-field-grid">
            <slot name="fields" :result="picked" />
          </div>
          <p v-if="error" class="empty-state error" style="padding: 0 0 8px">
            {{ error }}
          </p>
          <div class="modal-actions">
            <button type="button" class="btn-outline" @click="emit('close')">
              Cancel
            </button>
            <button
              type="button"
              class="btn-solid"
              :disabled="saving"
              @click="emit('add', picked)"
            >
              {{ saving ? "Adding…" : (submitLabel ?? "Add to Library") }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* The look is the media library's own quick-add, moved here unchanged so the
   Games library can use it too. */
.modal-overlay {
  --bg: #0d0d0d;
  --surface: #1a1a1a;
  --surface-2: #222222;
  --border: #2b2b2b;
  --border-soft: #202020;
  --accent: #d68a34;
  --accent-soft: rgba(214, 138, 52, 0.16);
  --accent-line: rgba(214, 138, 52, 0.4);
  --good: #6fbf73;
  --good-soft: rgba(111, 191, 115, 0.16);
  --hold: #7ba7d9;
  --hold-soft: rgba(123, 167, 217, 0.16);
  --dropped: #d96f6f;
  --dropped-soft: rgba(217, 111, 111, 0.16);
  --plan: #9d8cd9;
  --plan-soft: rgba(157, 140, 217, 0.16);
  --live: #e5484d;
  --text: #f2f2f2;
  --text-dim: #9c9c9c;
  --text-faint: #666;
  font-family: system-ui, sans-serif;
  color: var(--text);
}
.modal-overlay * {
  box-sizing: border-box;
}
.modal-overlay svg {
  display: block;
}
.empty-state {
  color: var(--text-faint);
  font-size: 0.9rem;
  padding: 40px 0;
  text-align: center;
}
.empty-state.error {
  color: #e57373;
}
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: var(--ui-z-modal);
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.modal-card {
  width: 100%;
  max-width: 440px;
  background: var(--ui-popover);
  border: 1px solid var(--border);
  border-radius: var(--ui-radius-dialog);
  padding: 22px;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.6);
}
.modal-card h3 {
  margin: 0 0 4px;
  font-size: 1.05rem;
  font-weight: 800;
}
.modal-card .sub {
  font-size: 0.78rem;
  color: var(--text-faint);
  margin-bottom: 14px;
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 14px;
}
.btn-outline {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text-dim);
  border-radius: 8px;
  padding: 0 16px;
  height: 36px;
  font-family: inherit;
  font-size: 0.82rem;
  font-weight: 700;
  cursor: pointer;
}
.btn-solid {
  background: var(--accent);
  border: none;
  color: #14100a;
  border-radius: 8px;
  padding: 0 16px;
  height: 36px;
  font-family: inherit;
  font-size: 0.82rem;
  font-weight: 700;
  cursor: pointer;
}
.btn-solid:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.qa-card {
  max-width: 540px;
  padding: 0;
  overflow: hidden;
}
.qa-header {
  padding: 22px 24px 18px;
  border-bottom: 1px solid var(--border-soft);
  background: linear-gradient(160deg, var(--accent-soft), transparent 70%);
}
.qa-search-foot :slotted(button) {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text-dim);
  border-radius: 8px;
  padding: 0 16px;
  height: 36px;
  margin-right: 8px;
  font-family: inherit;
  font-size: 0.82rem;
  font-weight: 700;
  cursor: pointer;
}
.qa-search-foot {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}
.qa-header-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.qa-header-row svg {
  width: 20px;
  height: 20px;
  color: var(--accent);
  flex-shrink: 0;
}
.qa-header h3 {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 800;
}
.qa-header .sub {
  margin: 4px 0 0;
}
.qa-body {
  padding: 20px 24px 24px;
}
.qa-search-row {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}
.qa-search-row input {
  flex: 1;
  background: var(--surface-2);
  border: 1px solid var(--border);
  color: var(--text);
  border-radius: 9px;
  padding: 11px 14px;
  font-family: inherit;
  font-size: 0.9rem;
}
.qa-search-row input:focus {
  outline: none;
  border-color: var(--accent-line);
}
.qa-results {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 360px;
  overflow-y: auto;
}
.qa-result {
  display: grid;
  grid-template-columns: 58px 1fr auto;
  gap: 14px;
  align-items: center;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px;
  transition: border-color 0.15s ease;
}
.qa-result:hover {
  border-color: var(--accent-line);
}
.qa-result-art {
  width: 58px;
  aspect-ratio: 2 / 3;
  border-radius: 6px;
  background-size: cover;
  background-repeat: no-repeat;
  background-position: center;
  background-color: var(--surface);
  box-shadow: 0 8px 18px -6px rgba(0, 0, 0, 0.6);
}
.qa-art-initial {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  font-size: 1.4rem;
  font-weight: 800;
  text-transform: uppercase;
  color: var(--text-faint, #5a5a5a);
}
.qa-result-titles {
  min-width: 0;
}
.qa-result-english {
  font-size: 0.94rem;
  font-weight: 700;
  margin: 1px 0 4px;
}
.qa-result-meta {
  display: flex;
  gap: 8px;
  font-size: 0.74rem;
  color: var(--text-faint);
  margin: 0 0 4px;
}
.qa-result-desc {
  font-size: 0.78rem;
  color: var(--text-dim);
  line-height: 1.45;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.qa-add-btn {
  background: var(--accent);
  border: none;
  color: #14100a;
  border-radius: 8px;
  padding: 0 18px;
  height: 40px;
  font-family: inherit;
  font-size: 0.82rem;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
}
.qa-add-btn:hover {
  filter: brightness(1.08);
}
.qa-form-header {
  display: flex;
  gap: 14px;
  align-items: center;
  margin: -20px -24px 20px;
  padding: 20px 24px;
  background: var(--surface);
  border-bottom: 1px solid var(--border-soft);
}
.qa-form-art {
  width: 64px;
  aspect-ratio: 2 / 3;
  border-radius: 7px;
  background-size: cover;
  background-repeat: no-repeat;
  background-position: center;
  background-color: var(--surface);
  flex-shrink: 0;
  box-shadow: 0 10px 22px -8px rgba(0, 0, 0, 0.6);
}
.qa-form-titles .qa-result-english {
  font-size: 1.05rem;
}
.qa-section-label {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  font-weight: 700;
  color: var(--text-faint);
  margin: 0 0 10px;
}
.qa-field-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-bottom: 18px;
}
.qa-back-link {
  background: none;
  border: none;
  color: var(--text-faint);
  font-family: inherit;
  font-size: 0.78rem;
  cursor: pointer;
  margin-bottom: 14px;
  padding: 0;
  display: flex;
  align-items: center;
  gap: 4px;
}
.qa-back-link:hover {
  color: var(--accent);
}
</style>

<style>
/* the form fields are filled in by the page, so these are not scoped */
.qa-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.qa-field.full {
  grid-column: 1 / -1;
}
.qa-field span {
  font-size: 0.74rem;
  color: var(--text-dim);
  font-weight: 600;
}
.qa-field select,
.qa-field input {
  background: var(--surface-2);
  border: 1px solid var(--border);
  color: var(--text);
  border-radius: 8px;
  padding: 9px 11px;
  font-family: inherit;
  font-size: 0.86rem;
}
.qa-field select:focus,
.qa-field input:focus {
  outline: none;
  border-color: var(--accent-line);
}
</style>
