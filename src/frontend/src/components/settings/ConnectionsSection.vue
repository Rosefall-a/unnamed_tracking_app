<script setup lang="ts">
import { ref, computed, defineAsyncComponent, onMounted } from "vue";
import { fetchProviderCredentials } from "../../services/settings";
import type { ProviderCredentialStatus } from "../../services/settings";
import { syncLibrary } from "../../services/librarySync";
import SettingsCard from "./SettingsCard.vue";
import type { LibrarySyncProvider } from "../../services/librarySync";

const MetadataSourcesSection = defineAsyncComponent(
  () => import("./MetadataSourcesSection.vue"),
);

// Only providers you sign in to and pull a library from. Metadata sources
// (TMDB, IGDB, SteamGridDB...) live under Library > Metadata.
const ACCOUNT_PROVIDERS = [
  "Steam",
  "Epic Games",
  "PlayStation",
  "RetroAchievements",
  "Xbox",
];

const credentials = ref<Record<string, ProviderCredentialStatus>>({});
const loading = ref(true);
const error = ref<string | null>(null);
const syncing = ref<string | null>(null);
const syncMessage = ref<string | null>(null);

const SYNCABLE: Record<string, LibrarySyncProvider> = {
  Steam: "steam",
  "Epic Games": "epic",
  PlayStation: "psn",
  RetroAchievements: "retroachievements",
};

const MARKS: Record<string, { bg: string; fg: string; mark: string }> = {
  Steam: { bg: "#12202e", fg: "#66c0f4", mark: "S" },
  SteamGridDB: { bg: "#0e3b3b", fg: "#2dd4bf", mark: "Gr" },
  IGDB: { bg: "#2b1c4a", fg: "#a78bfa", mark: "IG" },
  TMDB: { bg: "#01283d", fg: "#5dd9c1", mark: "TM" },
  OMDb: { bg: "#2a2205", fg: "#f5c518", mark: "OM" },
  TVDB: { bg: "#1a2a3d", fg: "#7ba7d9", mark: "TV" },
  RetroAchievements: { bg: "#3b0a0a", fg: "#f87171", mark: "RA" },
  PlayStation: { bg: "#0a1a3d", fg: "#60a5fa", mark: "PS" },
  "Epic Games": { bg: "#202020", fg: "#f5f5f5", mark: "EG" },
  GOG: { bg: "#2a1a3d", fg: "#c084fc", mark: "GOG" },
};
const FALLBACK = { bg: "#1f1f1f", fg: "#d1d5db", mark: "•" };

function markFor(name: string) {
  return MARKS[name] ?? { ...FALLBACK, mark: name.slice(0, 2) };
}

function isConnected(s: ProviderCredentialStatus): boolean {
  return (
    s.status === "connected" ||
    s.status === "configured" ||
    s.status === "saved"
  );
}

function timeAgo(unix: number | null | undefined): string {
  if (!unix) return "Never synced";
  const s = Math.max(0, Math.floor(Date.now() / 1000 - unix));
  if (s < 60) return "Synced now";
  if (s < 3600) return `Synced ${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `Synced ${Math.floor(s / 3600)}h ago`;
  return `Synced ${Math.floor(s / 86400)}d ago`;
}

interface Row {
  name: string;
  connected: boolean;
  error: boolean;
  detail: string;
  syncable: LibrarySyncProvider | null;
}

const accountRows = computed<Row[]>(() =>
  Object.entries(credentials.value)
    .filter(([name]) => ACCOUNT_PROVIDERS.includes(name))
    .map(([name, s]) => {
      const connected = isConnected(s);
      const bits: string[] = [];
      // The server reports a game count of 0 for providers that were never
      // set up; only a connected account has a real count to show.
      if (connected) {
        if (s.display_name) bits.push(s.display_name);
        if (s.library_games != null)
          bits.push(
            `${s.library_games} ${s.library_games === 1 ? "Game" : "Games"}`,
          );
        if (SYNCABLE[name]) bits.push(timeAgo(s.last_synced_at));
      }
      return {
        name,
        connected,
        error: s.status === "error",
        detail:
          bits.join(" · ") ||
          (s.status === "error"
            ? (s.detail ?? "Connection error")
            : "Not connected"),
        syncable: SYNCABLE[name] ?? null,
      };
    })
    .sort((a, b) => Number(b.connected) - Number(a.connected)),
);

async function load() {
  // a refresh after closing a card keeps the list on screen
  loading.value = !Object.keys(credentials.value).length;
  try {
    credentials.value = await fetchProviderCredentials();
  } catch (e) {
    error.value =
      e instanceof Error ? e.message : "Could not load connections.";
  }
  loading.value = false;
}
onMounted(load);

const managing = ref<string | null>(null);
function toggleManage(name: string) {
  const closing = managing.value === name;
  managing.value = closing ? null : name;
  // what was changed in the card shows on the row
  if (closing) void load();
}

const syncableRows = computed(() =>
  accountRows.value.filter((r) => r.syncable && r.connected),
);

// one at a time, so two libraries never write the same games at once
async function syncAll() {
  for (const row of syncableRows.value) {
    await sync(row);
  }
}

async function sync(row: Row) {
  if (!row.syncable) return;
  syncing.value = row.name;
  syncMessage.value = null;
  try {
    const r = await syncLibrary(row.syncable, (step, done, total) => {
      syncMessage.value = `${row.name}: ${step} (${done} of ${total})…`;
    });
    const wishlist = r.wishlist_added ? `, ${r.wishlist_added} wishlisted` : "";
    syncMessage.value = `${row.name}: ${r.games_added} added, ${r.games_updated} updated${wishlist}.`;
    await load();
  } catch (e) {
    syncMessage.value = e instanceof Error ? e.message : "Sync failed.";
  } finally {
    syncing.value = null;
  }
}
</script>

<template>
  <SettingsCard
    title="Linked accounts"
    description="Where your games and achievements come from. Each one shows when it last synced, and can sync on its own."
  >
    <template #actions>
      <button
        v-if="syncableRows.length > 1"
        type="button"
        class="st-btn"
        :disabled="syncing !== null"
        @click="syncAll"
      >
        {{ syncing ? "Syncing…" : "Sync all now" }}
      </button>
    </template>
    <p v-if="error" class="st-error">{{ error }}</p>
    <p v-if="syncMessage" class="note">{{ syncMessage }}</p>

    <p v-if="loading" class="st-muted">Loading…</p>
    <ul v-else class="rows">
      <li v-for="row in accountRows" :key="row.name" class="st-list-row-block">
        <div class="st-list-row">
          <span
            class="st-avatar"
            :style="{
              background: markFor(row.name).bg,
              color: markFor(row.name).fg,
            }"
            >{{ markFor(row.name).mark }}</span
          >
          <span class="st-lbl info">
            <strong>{{ row.name }}</strong>
            <span class="detail">{{ row.detail }}</span>
          </span>
          <span
            class="st-chip pill"
            :class="{ good: row.connected, bad: row.error }"
            >{{
              row.error
                ? "Error"
                : row.connected
                  ? "Connected"
                  : "Not connected"
            }}</span
          >
          <button
            v-if="row.syncable && row.connected"
            type="button"
            class="st-btn"
            :disabled="syncing !== null"
            @click="sync(row)"
          >
            {{ syncing === row.name ? "Syncing…" : "Sync now" }}
          </button>
          <button
            type="button"
            class="st-btn"
            :aria-expanded="managing === row.name"
            @click="toggleManage(row.name)"
          >
            {{
              managing === row.name
                ? "Close"
                : row.connected
                  ? "Manage"
                  : "Connect"
            }}
          </button>
        </div>
        <MetadataSourcesSection
          v-if="managing === row.name"
          :only="row.name"
          class="manage-card"
        />
      </li>
    </ul>
  </SettingsCard>
</template>

<style scoped>
.note {
  color: var(--ui-good-text);
  font-size: 0.85rem;
  margin: 0 0 6px;
}
.rows {
  list-style: none;
  margin: 0;
  padding: 0;
}
.st-list-row-block + .st-list-row-block .st-list-row {
  border-top: 1px solid #242424;
}
.manage-card {
  margin: 4px 0 12px;
}
.info {
  min-width: 0;
}
.detail {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
/* a phone can't fit the name, the status and both buttons on one line: the
   buttons move to a second line, and the status goes, since the line under
   the name already says "Not connected" or what went wrong */
@media (max-width: 560px) {
  .info {
    flex-basis: calc(100% - 48px) !important;
  }
  .pill {
    display: none;
  }
  .pill + .st-btn {
    margin-left: auto;
  }
}
</style>
