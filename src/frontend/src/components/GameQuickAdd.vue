<script setup lang="ts">
// The Add Game dialog: the quick add the Movies, TV and Anime libraries have.
// Search, pick, a short form, and the game is in the library; its details and
// artwork are read afterwards, in the background, so adding never waits on the
// metadata providers.
import { ref } from "vue";
import QuickAddDialog from "./library/QuickAddDialog.vue";
import type { QuickAddResult } from "./library/QuickAddDialog.vue";
import {
  createGame,
  rankMetadataResults,
  refreshGameMetadata,
  searchGameMetadata,
} from "../services/games";
import type { GameStatus } from "../types/game";

interface GameResult extends QuickAddResult {
  provider: string;
  releaseDate: string | null;
}

const emit = defineEmits<{
  close: [];
  // the game exists now
  added: [gameId: string];
  // its details and artwork have been read
  refreshed: [];
  // the full form, for a game no provider knows
  manual: [];
}>();

const STATUSES: GameStatus[] = [
  "backlog",
  "playing",
  "on hold",
  "beaten",
  "played",
  "dropped",
  "mastered",
  "wishlist",
];
const status = ref<GameStatus>("backlog");
const platform = ref("");
const rating = ref<number | null>(null);
const saving = ref(false);
const error = ref<string | null>(null);

// the list is a quick search: names, years and (for Steam) the cover Steam shows
async function search(query: string) {
  const response = await searchGameMetadata(query, {
    includeImages: false,
    light: true,
  });
  const ranked = rankMetadataResults(
    response.results.filter((r) => r.provider !== "SteamGridDB"),
    query,
  );
  return {
    results: ranked.map(
      (r): GameResult => ({
        title: r.title,
        poster:
          r.provider === "Steam"
            ? `https://cdn.akamai.steamstatic.com/steam/apps/${r.provider_id}/library_600x900.jpg`
            : null,
        description: r.description,
        releaseYear: r.release_date?.slice(0, 4) ?? null,
        provider: r.provider,
        releaseDate: r.release_date,
      }),
    ),
    providerErrors: response.provider_errors ?? [],
  };
}

async function add(result: GameResult) {
  saving.value = true;
  error.value = null;
  try {
    const created = await createGame({
      title: result.title,
      folderLocation:
        result.title
          .trim()
          .replace(/[^A-Za-z0-9_-]+/g, "-")
          .replace(/^-+|-+$/g, "") || "game",
      status: status.value,
      description: null,
      developer: null,
      publisher: null,
      series: null,
      parentGameId: null,
      relationshipType: null,
      releaseDate: result.releaseDate,
      dateAdded: null,
      completionDate: null,
      source: result.provider,
      platform: platform.value.trim() || null,
      ageRating: null,
      timeToBeatHours: null,
      region: null,
      language: null,
      achievementsProvider: null,
      ratingOverall: rating.value,
      ratingStory: null,
      ratingGameplay: null,
      ratingSound: null,
      tags: [],
      features: [],
      links: [],
      ownership: {
        format: null,
        purchaseDate: null,
        price: null,
        priceCurrency: null,
        condition: null,
      },
      favorite: false,
      collections: [],
      profilesEnabled: false,
      osrsStatsEnabled: false,
    });
    emit("added", created.id);
    void refreshGameMetadata(created).then(() => emit("refreshed"));
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Could not add the game.";
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <QuickAddDialog
    title="Add Game"
    section-label="Your game"
    :search="search"
    :saving="saving"
    :error="error"
    @close="emit('close')"
    @add="add"
  >
    <template #meta="{ result }">
      <span v-if="result.releaseYear">{{ result.releaseYear }}</span>
      <span>{{ result.provider }}</span>
    </template>
    <template #fields>
      <label class="qa-field">
        <span>Status</span>
        <select v-model="status">
          <option v-for="s in STATUSES" :key="s" :value="s">
            {{ s.charAt(0).toUpperCase() + s.slice(1) }}
          </option>
        </select>
      </label>
      <label class="qa-field">
        <span>Platform</span>
        <input v-model="platform" placeholder="e.g. PC" />
      </label>
      <label class="qa-field">
        <span>Your rating (0–10)</span>
        <input
          v-model.number="rating"
          type="number"
          min="0"
          max="10"
          step="0.1"
          placeholder="–"
        />
      </label>
    </template>
    <template #foot>
      <button type="button" @click="emit('manual')">
        Enter details by hand
      </button>
    </template>
  </QuickAddDialog>
</template>
