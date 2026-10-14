<script setup lang="ts">
// The "Look up metadata" panel of the game form. It searches the providers, reads
// the details of the game that is picked, and lists what would change field by
// field. Only the ticked fields are handed back; the form applies them.
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { rankMetadataResults, searchGameMetadata } from "../services/games";
import type { MetadataSearchResult } from "../services/games";

const props = defineProps<{
  // adding a game ticks everything; editing ticks only what is empty
  adding: boolean;
  initialQuery: string;
  // the picture the form shows now, to compare a new cover against
  currentCover?: string | null;
  // the form's current values, as text, keyed by field
  current: Record<string, string>;
}>();

export interface LookupApply {
  key: string;
  value: unknown;
}

const emit = defineEmits<{
  close: [];
  apply: [changes: LookupApply[], provider: string];
}>();

interface Change {
  key: string;
  label: string;
  from: string;
  to: string;
  value: unknown;
  // pictures to show next to the change: the new one, and the one it replaces
  image?: string | null;
  fromImage?: string | null;
  checked: boolean;
}

const query = ref(props.initialQuery);
const results = ref<MetadataSearchResult[]>([]);
const searching = ref(false);
const message = ref<string | null>(null);
const warnings = ref<string[]>([]);
const reading = ref(false);
const picked = ref<MetadataSearchResult | null>(null);
const changes = ref<Change[]>([]);
let timer: ReturnType<typeof setTimeout> | null = null;
let requestId = 0;

const STEAM_IMAGES = "https://cdn.akamai.steamstatic.com/steam/apps";
function art(r: MetadataSearchResult): string | null {
  return r.provider === "Steam"
    ? `${STEAM_IMAGES}/${r.provider_id}/library_600x900.jpg`
    : r.key_art_url;
}
function onArtError(e: Event, r: MetadataSearchResult) {
  const img = e.target as HTMLImageElement;
  const fallback =
    r.provider === "Steam"
      ? `${STEAM_IMAGES}/${r.provider_id}/header.jpg`
      : null;
  if (fallback && img.src !== fallback) img.src = fallback;
  else img.style.visibility = "hidden";
}

async function search() {
  const text = query.value.trim();
  if (text.length < 2) {
    results.value = [];
    message.value = text ? "Enter at least two characters." : null;
    return;
  }
  const id = ++requestId;
  searching.value = true;
  message.value = null;
  try {
    // a quick list: names only. The details are read for the game that is picked.
    const response = await searchGameMetadata(text, {
      includeImages: false,
      light: true,
    });
    if (id !== requestId) return;
    results.value = rankMetadataResults(
      response.results.filter((r) => r.provider !== "SteamGridDB"),
      text,
    );
    warnings.value = response.provider_errors ?? [];
    if (!results.value.length) message.value = "No games found.";
  } catch (err) {
    if (id !== requestId) return;
    message.value = err instanceof Error ? err.message : "Could not search.";
  } finally {
    if (id === requestId) searching.value = false;
  }
}
function onInput() {
  if (timer) clearTimeout(timer);
  timer = setTimeout(() => void search(), 250);
}

// The first of these addresses that loads as a picture. Steam has no tall cover for
// some games (a 404), and a cover address that does not load would leave the form's
// picture blank and fail the save, so they are tried in turn.
function loads(url: string): Promise<boolean> {
  return new Promise((resolve) => {
    const image = new Image();
    const timer = setTimeout(() => resolve(false), 5000);
    image.onload = () => {
      clearTimeout(timer);
      resolve(true);
    };
    image.onerror = () => {
      clearTimeout(timer);
      resolve(false);
    };
    image.src = url;
  });
}
async function firstThatLoads(urls: (string | null | undefined)[]) {
  for (const url of urls) {
    if (url && (await loads(url))) return url;
  }
  return null;
}

const hours = (v: number | string | null | undefined) =>
  v != null && v !== "" ? String(v) : null;

function build(match: MetadataSearchResult, cover: string | null): Change[] {
  const out: Change[] = [];
  const cur = props.current;
  // empty fields are ticked, fields that already have a value are not
  const offer = (
    key: string,
    label: string,
    to: string | null | undefined,
    value: unknown = to,
  ) => {
    const next = (to ?? "").toString().trim();
    const from = cur[key] ?? "";
    if (!next || next === from.trim()) return;
    out.push({
      key,
      label,
      from,
      to: next,
      value,
      checked: props.adding || !from.trim(),
    });
  };
  offer("title", "Title", match.title);
  offer("description", "Description", match.description);
  offer("developer", "Developer", match.developer);
  offer("publisher", "Publisher", match.publisher);
  offer("series", "Series", match.series);
  offer("releaseDate", "Release date", match.release_date);
  offer("ageRating", "Age rating", match.age_rating);
  offer("timeToBeatHours", "Main story", hours(match.time_to_beat_hours));
  offer(
    "timeToBeatExtras",
    "Main story and extras",
    hours(match.time_to_beat_extras_hours),
  );
  offer(
    "timeToBeatCompletionist",
    "Completionist",
    hours(match.time_to_beat_completionist_hours),
  );
  offer(
    "timeToBeatAll",
    "All play styles",
    hours(match.time_to_beat_all_hours),
  );
  offer("tags", "Tags", match.tags.join(", "));
  offer("features", "Features", match.features.join(", "));
  if (match.links.length && JSON.stringify(match.links) !== cur.links) {
    const count = (n: number) => `${n} link${n === 1 ? "" : "s"}`;
    out.push({
      key: "links",
      label: "Links",
      from: cur.linksCount === "0" ? "" : count(Number(cur.linksCount)),
      to: count(match.links.length),
      value: match.links.map((l) => ({ ...l })),
      checked: props.adding || cur.linksCount === "0",
    });
  }
  offer("source", "Source", match.provider);
  if (cover) {
    out.push({
      key: "cover",
      label: "Cover",
      from: props.currentCover ? "Current cover" : "",
      to: "New cover",
      value: cover,
      image: cover,
      fromImage: props.currentCover,
      checked: props.adding,
    });
  }
  if (match.banner_url) {
    out.push({
      key: "banner",
      label: "Banner",
      from: "",
      to: "New banner",
      value: match.banner_url,
      image: match.banner_url,
      checked: props.adding,
    });
  }
  return out;
}

async function pick(result: MetadataSearchResult) {
  picked.value = result;
  changes.value = [];
  reading.value = true;
  let match = result;
  try {
    const found = await searchGameMetadata(result.title, {
      includeImages: false,
      limit: 3,
    });
    match =
      found.results.find(
        (r) =>
          r.provider === result.provider &&
          r.provider_id === result.provider_id,
      ) ??
      found.results.find(
        (r) => r.title.toLowerCase() === result.title.toLowerCase(),
      ) ??
      result;
  } catch {
    // the listed result is still enough to offer a few fields
  }
  const cover = await firstThatLoads([
    art(result),
    match.key_art_url,
    result.key_art_url,
    result.provider === "Steam"
      ? `${STEAM_IMAGES}/${result.provider_id}/header.jpg`
      : null,
  ]);
  if (picked.value?.provider_id !== result.provider_id) return;
  reading.value = false;
  changes.value = build(match, cover);
  picked.value = match;
}

function back() {
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
  if (query.value.trim().length >= 2) void search();
});
onBeforeUnmount(() => {
  window.removeEventListener("keydown", onKey, true);
  if (timer) clearTimeout(timer);
});
</script>

<template>
  <aside class="gl" aria-label="Look up metadata">
    <div class="gl-head">
      <div>
        <div class="gl-kicker">Look up metadata</div>
        <p class="gl-hint">Pick a game, then choose which fields to fill in.</p>
      </div>
      <button
        type="button"
        class="gl-close"
        aria-label="Close lookup"
        @click="emit('close')"
      >
        &#10005;
      </button>
    </div>
    <div class="gl-search">
      <input
        v-model="query"
        type="search"
        placeholder="Search for a game"
        autofocus
        @input="onInput"
        @keydown.enter.prevent="search"
      />
    </div>

    <div class="gl-body">
      <template v-if="!picked">
        <p v-if="searching" class="gl-hint">Searching…</p>
        <p v-else-if="message" class="gl-hint">{{ message }}</p>
        <p v-for="w in warnings" :key="w" class="gl-hint">{{ w }}</p>
        <button
          v-for="r in results"
          :key="`${r.provider}-${r.provider_id}`"
          type="button"
          class="gl-result"
          @click="pick(r)"
        >
          <span class="gl-result-art">
            <img
              v-if="art(r)"
              :src="art(r)!"
              alt=""
              loading="lazy"
              @error="onArtError($event, r)"
            />
          </span>
          <span class="gl-result-text">
            <strong>{{ r.title }}</strong>
            <span class="gl-result-meta">
              {{
                [r.release_date?.slice(0, 4), r.developer]
                  .filter(Boolean)
                  .join(" · ")
              }}
            </span>
          </span>
          <span class="gl-chip">{{ r.provider }}</span>
        </button>
      </template>

      <template v-else>
        <button type="button" class="gl-back" @click="back">
          &larr; Back to results
        </button>
        <p class="gl-section">
          {{ reading ? "Reading the details…" : picked.title }}
        </p>
        <p v-if="!reading && !changes.length" class="gl-hint">
          Nothing new to fill in from {{ picked.provider }}.
        </p>
        <label v-for="change in changes" :key="change.key" class="gl-change">
          <input v-model="change.checked" type="checkbox" />
          <span class="gl-change-text">
            <strong>{{ change.label }}</strong>
            <span class="gl-change-values">
              <s v-if="change.from">{{ change.from }}</s>
              <span class="gl-change-to">{{ change.to }}</span>
            </span>
          </span>
          <span
            v-if="change.fromImage"
            class="gl-change-img old"
            :style="{ backgroundImage: `url(${change.fromImage})` }"
          ></span>
          <span
            v-if="change.image"
            class="gl-change-img"
            :style="{ backgroundImage: `url(${change.image})` }"
          ></span>
        </label>
      </template>
    </div>

    <div v-if="picked && changes.length" class="gl-foot">
      <button type="button" class="gl-btn" @click="emit('close')">
        Cancel
      </button>
      <button
        type="button"
        class="gl-btn solid"
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
.gl {
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
.gl * {
  box-sizing: border-box;
}
.gl-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  padding: 14px 16px 6px;
}
.gl-kicker {
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--accent);
}
.gl-hint {
  margin: 4px 0 8px;
  font-size: 0.78rem;
  color: var(--text-faint);
  line-height: 1.5;
}
.gl-close {
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
.gl-close:hover {
  background: var(--surface-2);
  color: var(--text);
}
.gl-search {
  padding: 4px 16px 12px;
  border-bottom: 1px solid var(--border-soft);
}
.gl-search input {
  width: 100%;
  background: var(--surface-2);
  border: 1px solid var(--border);
  color: var(--text);
  border-radius: 8px;
  padding: 9px 11px;
  font: inherit;
  font-size: 0.86rem;
}
.gl-search input:focus {
  outline: none;
  border-color: var(--accent-line);
}
.gl-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 10px 16px;
}
.gl-foot {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid var(--border-soft);
  background: var(--surface);
}
.gl-btn {
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
.gl-btn:hover {
  color: var(--text);
  border-color: var(--accent-line);
}
.gl-btn.solid {
  background: var(--accent);
  border-color: var(--accent);
  color: var(--ui-on-accent);
}
.gl-btn.solid:disabled {
  opacity: 0.6;
  cursor: default;
}
.gl-result {
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
.gl-result:hover {
  border-color: var(--accent-line);
}
.gl-btn:focus-visible,
.gl-result:focus-visible,
.gl-close:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
.gl-result-art {
  flex: none;
  width: 42px;
  height: 58px;
  border-radius: 6px;
  background: var(--surface);
  overflow: hidden;
}
.gl-result-art img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.gl-result-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.gl-result-text strong {
  font-size: 0.86rem;
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.gl-result-meta {
  font-size: 0.74rem;
  color: var(--text-faint);
}
.gl-chip {
  flex: none;
  padding: 1px 8px;
  border: 1px solid var(--border);
  border-radius: 999px;
  font-size: 0.68rem;
  color: var(--text-dim);
}
.gl-back {
  margin-bottom: 4px;
  padding: 0;
  border: 0;
  background: none;
  color: var(--text-faint);
  font: inherit;
  font-size: 0.78rem;
  cursor: pointer;
}
.gl-back:hover {
  color: var(--accent);
}
.gl-section {
  margin: 10px 0 6px;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-faint);
}
.gl-change {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 9px 0;
  border-bottom: 1px solid var(--border-soft);
  cursor: pointer;
}
.gl-change input {
  margin-top: 3px;
  accent-color: var(--accent);
}
.gl-change-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 0.82rem;
}
.gl-change-values {
  display: flex;
  flex-direction: column;
  gap: 1px;
  color: var(--text-faint);
  overflow-wrap: anywhere;
}
.gl-change-to {
  color: var(--text-dim);
}
.gl-change-img.old {
  opacity: 0.55;
}
.gl-change-img {
  flex: none;
  width: 36px;
  height: 50px;
  border-radius: 5px;
  background-color: var(--surface-2);
  background-size: cover;
  background-position: center;
}
</style>
