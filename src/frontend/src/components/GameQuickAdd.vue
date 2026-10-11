<script setup lang="ts">
// The Add Game dialog: the quick add the Movies, TV and Anime libraries have.
// Search, pick, a short form, and the game is in the library; its details and
// artwork are read afterwards, in the background, so adding never waits on the
// metadata providers.
import { ref } from "vue";
import GameArtSection from "./GameArtSection.vue";
import QuickAddDialog from "./library/QuickAddDialog.vue";
import type { QuickAddResult } from "./library/QuickAddDialog.vue";
import {
  attachGameAssetFromUrl,
  createGame,
  rankMetadataResults,
  searchGameMetadata,
} from "../services/games";
import {
  addFeedItem,
  errorTask,
  startTask,
  updateTask,
} from "../state/taskProgress";
import type { Game, GameLink, GameStatus } from "../types/game";

interface GameResult extends QuickAddResult {
  provider: string;
  providerId: string;
  releaseDate: string | null;
  developer: string | null;
  publisher: string | null;
  series: string | null;
  tags: string[];
  links: GameLink[];
}

const emit = defineEmits<{
  close: [];
  // the game exists now; the page that opened this reads its details and artwork,
  // since this dialog is gone by then
  added: [game: Game, taskId: string];
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
// artwork picked in the form; null keeps what the search showed
const pickedCover = ref<string | null>(null);
const pickedBanner = ref<string | null>(null);
const saving = ref(false);
const error = ref<string | null>(null);

const steamImages = "https://cdn.akamai.steamstatic.com/steam/apps";

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
    results: ranked.map((r): GameResult => ({
      title: r.title,
      // Steam has no tall cover for some games, so its wide header sits behind it
      poster:
        r.provider === "Steam"
          ? `${steamImages}/${r.provider_id}/library_600x900.jpg`
          : r.key_art_url,
      fallbackPosters: [
        ...(r.provider === "Steam" && r.key_art_url ? [r.key_art_url] : []),
        ...(r.provider === "Steam"
          ? [`${steamImages}/${r.provider_id}/header.jpg`]
          : []),
      ],
      description: r.description,
      releaseYear: r.release_date?.slice(0, 4) ?? null,
      provider: r.provider,
      providerId: r.provider_id,
      releaseDate: r.release_date,
      developer: r.developer,
      publisher: r.publisher,
      series: r.series,
      tags: r.tags,
      links: r.links,
    })),
    providerErrors: response.provider_errors ?? [],
  };
}

// The cover the list showed is saved at once, so the game has one the moment it
// appears; the full lookup afterwards adds the banner and the rest. The first
// address that works is kept (Steam has no tall cover for some games).
async function saveListedCover(gameId: string, result: GameResult) {
  const urls = [
    pickedCover.value,
    result.poster,
    ...(result.fallbackPosters ?? []),
  ];
  for (const url of urls) {
    if (!url) continue;
    try {
      await attachGameAssetFromUrl(gameId, "key_art", url);
      return;
    } catch {
      // try the next one
    }
  }
}

async function add(result: GameResult) {
  saving.value = true;
  error.value = null;
  // shown bottom right and carried on by the library page once this dialog is
  // gone: adding, the cover, then the details and banner
  const taskId = startTask(`Adding ${result.title}`, 4);
  try {
    const created = await createGame({
      title: result.title,
      folderLocation:
        result.title
          .trim()
          .replace(/[^A-Za-z0-9_-]+/g, "-")
          .replace(/^-+|-+$/g, "") || "game",
      status: status.value,
      // what the list already showed, so the game is not bare while the
      // artwork and the rest are read
      description: result.description,
      developer: result.developer,
      publisher: result.publisher,
      series: result.series,
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
      tags: result.tags,
      features: [],
      links: result.links,
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
    updateTask(taskId, 1);
    addFeedItem(taskId, "Added to your library");
    await saveListedCover(created.id, result);
    updateTask(taskId, 2);
    addFeedItem(taskId, "Cover saved");
    if (pickedBanner.value) {
      try {
        await attachGameAssetFromUrl(created.id, "banner", pickedBanner.value);
      } catch {
        // the lookup after adding fills in a banner
      }
    }
    emit("added", created, taskId);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Could not add the game.";
    errorTask(taskId, error.value);
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
      <span class="qa-chip">{{ result.provider }}</span>
    </template>
    <template #fields="{ result }">
      <label class="qa-field qa-wide">
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
      <GameArtSection
        :key="`${result.provider}-${result.providerId}`"
        v-model:cover="pickedCover"
        v-model:banner="pickedBanner"
        :title="result.title"
        :provider="result.provider"
        :provider-id="result.providerId"
        :current-cover="result.poster"
      />
    </template>
    <template #foot>
      <button type="button" @click="emit('manual')">
        Enter details by hand
      </button>
    </template>
  </QuickAddDialog>
</template>

<style scoped>
/* the status picker takes the whole row, so platform and rating pair up below it */
.qa-wide {
  grid-column: 1 / -1;
}
.qa-chip {
  padding: 1px 8px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 999px;
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.02em;
}
</style>
