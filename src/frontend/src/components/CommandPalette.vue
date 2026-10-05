<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { fetchGames } from "../services/games";
import type { Game } from "../types/game";
import { searchPluginRecords } from "../state/pluginSearch";
import { isCommandPaletteOpen } from "../state/commandPalette";
import { smartCollections } from "../state/smartCollections";
import { fetchMoviesPage } from "../services/movies";
import { fetchTVShowsPage } from "../services/tvShows";
import { fetchAnimePage } from "../services/anime";
import { currentUser } from "../state/auth";
import {
  pluginNavigation,
  pluginSettingsSections,
} from "../state/pluginExtensions";
import UiModal from "./UiModal.vue";

const router = useRouter();

const open = isCommandPaletteOpen;
const query = ref("");
const inputRef = ref<HTMLInputElement | null>(null);

const gamesCache = ref<Game[]>([]);
const loaded = ref(false);
const loadError = ref("");
const mediaResults = ref<Result[]>([]);
const pluginResults = ref<Result[]>([]);
const mediaLoading = ref(false);
let loadGeneration = 0;
let mediaGeneration = 0;
let mediaTimer: ReturnType<typeof setTimeout> | undefined;
let pluginTimer: ReturnType<typeof setTimeout> | undefined;
let pluginGeneration = 0;

async function ensureLoaded() {
  const generation = ++loadGeneration;
  loadError.value = "";
  const [games] = await Promise.allSettled([fetchGames()]);
  if (generation !== loadGeneration) return;
  if (games.status === "fulfilled") gamesCache.value = games.value;
  if (games.status === "rejected")
    loadError.value =
      "Some library results could not be loaded. Try again when connected.";
  loaded.value = true;
}

interface Result {
  key: string;
  kind: "game" | "movie" | "tv" | "anime" | "collection" | "bounty" | "page";
  label: string;
  sublabel?: string;
  action: () => void;
}

const SETTINGS_SHORTCUTS: {
  label: string;
  section: string;
  adminOnly?: boolean;
}[] = [
  { label: "Profile", section: "profile" },
  { label: "Appearance & interface", section: "appearance" },
  { label: "App installation", section: "app-installation" },
  { label: "Notifications", section: "notifications" },
  { label: "Calendar", section: "calendar" },
  { label: "Keyboard Shortcuts", section: "shortcuts" },
  { label: "Connections", section: "connections" },
  { label: "Library", section: "library" },
  { label: "Media Trash", section: "media-trash" },
  { label: "Metadata", section: "metadata" },
  { label: "Metadata API keys", section: "sources" },
  { label: "Storage & usage", section: "stats" },
  { label: "Export / Import", section: "export" },
  { label: "API Keys", section: "api-keys" },
  { label: "Users", section: "users", adminOnly: true },
  { label: "Single sign-on", section: "oidc", adminOnly: true },
  { label: "Password policy", section: "password-policy", adminOnly: true },
  {
    label: "Server integrations",
    section: "server-integrations",
    adminOnly: true,
  },
  { label: "Limits", section: "limits", adminOnly: true },
  { label: "App branding", section: "branding", adminOnly: true },
  { label: "Plugins", section: "plugins", adminOnly: true },
  { label: "Background tasks", section: "tasks", adminOnly: true },
];

const PAGE_SHORTCUTS: { label: string; to: string }[] = [
  { label: "Home", to: "/" },
  { label: "Games", to: "/games" },
  { label: "Collections", to: "/collections" },
  { label: "Movies", to: "/movies" },
  { label: "TV shows", to: "/tv" },
  { label: "Anime", to: "/anime" },
  { label: "Lists", to: "/lists" },
  { label: "Calendar", to: "/calendar" },
  { label: "Statistics", to: "/statistics" },
  { label: "Notifications", to: "/notifications" },
  { label: "Settings", to: "/settings" },
  { label: "Upload", to: "/upload" },
];

const collectionNames = computed(() => {
  const set = new Set<string>();
  for (const g of gamesCache.value) for (const c of g.collections) set.add(c);
  for (const c of smartCollections.value) set.add(c.name);
  return [...set].sort();
});

const results = computed<Result[]>(() => {
  const q = query.value.trim().toLowerCase();
  const out: Result[] = [];

  if (!q) {
    for (const p of PAGE_SHORTCUTS) {
      out.push({
        key: "page:" + p.to,
        kind: "page",
        label: p.label,
        action: () => go(p.to),
      });
    }
    return out;
  }

  const games = gamesCache.value
    .filter((g) => g.title.toLowerCase().includes(q))
    .slice(0, 6);
  for (const g of games) {
    out.push({
      key: "game:" + g.id,
      kind: "game",
      label: g.title,
      sublabel: g.status,
      action: () => go(`/games/${g.id}`),
    });
  }

  const collections = collectionNames.value
    .filter((c) => c.toLowerCase().includes(q))
    .slice(0, 4);
  for (const c of collections) {
    out.push({
      key: "collection:" + c,
      kind: "collection",
      label: c,
      sublabel: "Collection",
      action: () => go(`/collections/${encodeURIComponent(c)}`),
    });
  }

  out.push(...mediaResults.value);
  out.push(...pluginResults.value);

  for (const s of SETTINGS_SHORTCUTS) {
    if (s.adminOnly && !currentUser.value?.is_admin) continue;
    if (s.label.toLowerCase().includes(q)) {
      out.push({
        key: "settings:" + s.section,
        kind: "page",
        label: s.label,
        sublabel: "Settings",
        action: () => go(`/settings?section=${s.section}`),
      });
    }
  }

  for (const item of pluginSettingsSections.value) {
    if (
      (item.adminOnly && !currentUser.value?.is_admin) ||
      !item.label.toLowerCase().includes(q)
    )
      continue;
    out.push({
      key: "plugin-settings:" + item.contributionId,
      kind: "page",
      label: item.label,
      sublabel: "Extension settings",
      action: () =>
        go(`/settings?section=${encodeURIComponent(item.contributionId)}`),
    });
  }
  for (const item of pluginNavigation.value) {
    if (
      (item.adminOnly && !currentUser.value?.is_admin) ||
      item.action ||
      !item.label.toLowerCase().includes(q)
    )
      continue;
    if (
      item.location !== "main.sidebar" &&
      item.location !== "settings.sidebar" &&
      item.location !== "administration"
    )
      continue;
    if (item.location === "administration" && !currentUser.value?.is_admin)
      continue;
    const destination = item.settingsSectionId
      ? `/settings?section=${encodeURIComponent(item.settingsSectionId)}`
      : `/plugins/${encodeURIComponent(item.pluginId)}/${(item.routePath || item.pageId || "").split("/").map(encodeURIComponent).join("/")}`;
    out.push({
      key: "plugin-navigation:" + item.contributionId,
      kind: "page",
      label: item.label,
      sublabel: "Extension",
      action: () => go(destination),
    });
  }
  for (const p of PAGE_SHORTCUTS) {
    if (p.label.toLowerCase().includes(q)) {
      out.push({
        key: "page:" + p.to,
        kind: "page",
        label: p.label,
        action: () => go(p.to),
      });
    }
  }

  return out.slice(0, 20);
});

const activeIndex = ref(0);
watch(results, () => {
  activeIndex.value = 0;
});

function go(to: string) {
  close();
  router.push(to);
}

function close() {
  open.value = false;
  query.value = "";
}

async function openPalette() {
  open.value = true;
}

watch(
  open,
  async (value) => {
    if (!value) {
      query.value = "";
      return;
    }
    void ensureLoaded();
    await nextTick();
    inputRef.value?.focus();
  },
  { immediate: true },
);

watch(
  () => currentUser.value?.id,
  () => {
    ++loadGeneration;
    ++mediaGeneration;
    ++pluginGeneration;
    clearTimeout(mediaTimer);
    clearTimeout(pluginTimer);
    gamesCache.value = [];
    mediaResults.value = [];
    pluginResults.value = [];
    loaded.value = false;
    loadError.value = "";
    mediaLoading.value = false;
    close();
  },
);

function searchMedia(value: string) {
  const generation = ++mediaGeneration;
  clearTimeout(mediaTimer);
  mediaResults.value = [];
  const search = value.trim();
  mediaLoading.value = Boolean(search);
  if (!search) return;
  mediaTimer = setTimeout(async () => {
    const sources = [
      {
        kind: "movie" as const,
        label: "Movie",
        path: "/movies",
        fetch: fetchMoviesPage,
      },
      {
        kind: "tv" as const,
        label: "TV show",
        path: "/tv",
        fetch: fetchTVShowsPage,
      },
      {
        kind: "anime" as const,
        label: "Anime",
        path: "/anime",
        fetch: fetchAnimePage,
      },
    ];
    const responses = await Promise.allSettled(
      sources.map((source) => source.fetch(0, 6, search)),
    );
    if (generation !== mediaGeneration) return;
    mediaResults.value = responses.flatMap((response, index) => {
      if (response.status !== "fulfilled") return [];
      const source = sources[index]!;
      return response.value.items.map((item) => ({
        key: source.kind + ":" + item.id,
        kind: source.kind,
        label: item.title,
        sublabel: source.label,
        action: () => go(`${source.path}/${item.id}`),
      }));
    });
    mediaLoading.value = false;
    if (responses.some((response) => response.status === "rejected"))
      loadError.value =
        "Some library results could not be loaded. Try again when connected.";
  }, 160);
}
function searchPlugins(value: string) {
  const generation = ++pluginGeneration;
  clearTimeout(pluginTimer);
  pluginResults.value = [];
  if (!value.trim()) return;
  pluginTimer = setTimeout(async () => {
    const matches = await searchPluginRecords(value.trim());
    if (generation !== pluginGeneration) return;
    pluginResults.value = matches.map((item) => ({
      key: `plugin-record:${item.pluginId}:${item.id}`,
      kind: "page",
      label: item.label,
      sublabel: item.description ?? "Extension",
      action: () => go(item.path),
    }));
  }, 160);
}
watch(query, (value) => {
  searchMedia(value);
  searchPlugins(value);
});

function retrySearch() {
  void ensureLoaded();
  searchMedia(query.value);
  searchPlugins(query.value);
}

function onGlobalKeydown(e: KeyboardEvent) {
  const isMeta = e.metaKey || e.ctrlKey;
  if (isMeta && e.key.toLowerCase() === "k") {
    if (
      e.defaultPrevented ||
      (!open.value &&
        document.querySelector(
          'dialog[open], [role="dialog"], [role="alertdialog"]',
        ))
    )
      return;
    e.preventDefault();
    if (open.value) close();
    else void openPalette();
    return;
  }
  if (!open.value) return;
  if (e.key !== "Escape" && e.target !== inputRef.value) return;
  if (e.key === "Escape") {
    close();
  } else if (e.key === "ArrowDown") {
    e.preventDefault();
    activeIndex.value = Math.min(
      activeIndex.value + 1,
      Math.max(0, results.value.length - 1),
    );
  } else if (e.key === "ArrowUp") {
    e.preventDefault();
    activeIndex.value = Math.max(activeIndex.value - 1, 0);
  } else if (e.key === "Enter") {
    e.preventDefault();
    results.value[activeIndex.value]?.action();
  }
}

onMounted(() => window.addEventListener("keydown", onGlobalKeydown));
onUnmounted(() => {
  window.removeEventListener("keydown", onGlobalKeydown);
  clearTimeout(mediaTimer);
  clearTimeout(pluginTimer);
  ++loadGeneration;
  ++mediaGeneration;
  ++pluginGeneration;
  open.value = false;
});

const KIND_ICON: Record<Result["kind"], string> = {
  game: "🎮",
  movie: "🎬",
  tv: "📺",
  anime: "🎞",
  collection: "📁",
  bounty: "🎯",
  page: "→",
};
</script>

<template>
  <UiModal v-if="open" title="Search library" @close="close">
    <div class="palette">
      <input
        ref="inputRef"
        v-model="query"
        type="text"
        aria-label="Search library"
        class="palette-input"
        placeholder="Search games, media, collections, goals and pages…"
      />
      <p v-if="loadError" role="status" class="palette-empty">
        {{ loadError }}
        <button type="button" class="ui-btn ui-btn-ghost" @click="retrySearch">
          Retry
        </button>
      </p>
      <div v-if="!loaded" class="palette-loading">Loading…</div>
      <div v-else-if="!results.length" class="palette-empty">
        {{ mediaLoading ? "Searching media…" : "No matches." }}
      </div>
      <div v-else class="palette-results">
        <button
          v-for="(r, i) in results"
          :key="r.key"
          type="button"
          class="palette-item"
          :class="{ active: i === activeIndex }"
          @mouseenter="activeIndex = i"
          @click="r.action()"
        >
          <span class="palette-item-icon">{{ KIND_ICON[r.kind] }}</span>
          <span class="palette-item-label">{{ r.label }}</span>
          <span v-if="r.sublabel" class="palette-item-sub">{{
            r.sublabel
          }}</span>
        </button>
      </div>
      <div class="palette-footer">
        <span><kbd>↑↓</kbd> navigate</span>
        <span><kbd>Enter</kbd> open</span>
        <span><kbd>Esc</kbd> close</span>
      </div>
    </div>
  </UiModal>
</template>

<style scoped>
.palette {
  overflow: hidden;
}
.palette-input {
  width: 100%;
  box-sizing: border-box;
  background: none;
  border: none;
  border-bottom: 1px solid var(--ui-border);
  color: var(--ui-text);
  padding: 16px 18px;
  font: inherit;
  font-size: 15px;
}
.palette-input:focus {
  outline: none;
}
.palette-loading,
.palette-empty {
  color: var(--ui-dim);
  font-size: 13px;
  padding: 20px 18px;
}
.palette-results {
  max-height: 360px;
  overflow-y: auto;
  padding: 6px;
}
.palette-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  background: none;
  border: none;
  color: var(--ui-text);
  text-align: left;
  padding: 9px 10px;
  min-height: var(--ui-control-height);
  border-radius: 8px;
  cursor: pointer;
  font-size: 13.5px;
}
.palette-item.active {
  background: var(--ui-accent-soft);
  color: var(--ui-text);
}
.palette-item-icon {
  font-size: 14px;
  width: 18px;
  text-align: center;
  flex-shrink: 0;
}
.palette-item-label {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.palette-item-sub {
  color: var(--ui-dim);
  font-size: 11px;
  text-transform: capitalize;
  flex-shrink: 0;
}
.palette-item.active .palette-item-sub {
  color: var(--ui-accent);
}
.palette-footer {
  display: flex;
  gap: 16px;
  padding: 10px 16px;
  border-top: 1px solid var(--ui-border);
  color: var(--ui-dim);
  font-size: 11px;
}
.palette-footer kbd {
  background: var(--ui-surface-2);
  border: 1px solid var(--ui-border-strong);
  border-radius: 4px;
  padding: 1px 5px;
  font-family: ui-monospace, monospace;
  color: var(--ui-dim);
  margin-right: 4px;
}
</style>
