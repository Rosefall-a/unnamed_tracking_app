<script setup lang="ts">
// The light edit the Games library opens from a game's Edit button: the same dialog
// as Add Game, with the four things most often changed (status, platform, rating and
// artwork) and an "Edit more" button for the full form.
import { ref } from "vue";
import GameArtSection from "./GameArtSection.vue";
import QuickAddDialog from "./library/QuickAddDialog.vue";
import type { QuickAddResult } from "./library/QuickAddDialog.vue";
import { attachGameAssetFromUrl, patchGame } from "../services/games";
import type { Game, GameStatus } from "../types/game";

const props = defineProps<{ game: Game }>();

const emit = defineEmits<{
  close: [];
  saved: [game: Game];
  more: [];
}>();

interface GameResult extends QuickAddResult {
  provider: string;
  providerId: string;
}

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

const status = ref<GameStatus>(props.game.status);
const platform = ref(props.game.platform ?? "");
const rating = ref<number | null>(props.game.ratingOverall);
// artwork picked in the dialog; null keeps what the game has
const pickedCover = ref<string | null>(null);
const pickedBanner = ref<string | null>(null);
const saving = ref(false);
const error = ref<string | null>(null);

const initial: GameResult = {
  title: props.game.title,
  poster: props.game.coverImageUrl,
  description: props.game.description,
  releaseYear: props.game.releaseDate?.slice(0, 4) ?? null,
  provider: props.game.source || "Steam",
  providerId: "",
};

// a cleared number box reads "" rather than null
const rated = () =>
  rating.value === null || Number.isNaN(rating.value) ? null : rating.value;

async function save() {
  saving.value = true;
  error.value = null;
  try {
    const saved = await patchGame(props.game.id, {
      status: status.value,
      platform: platform.value.trim() || null,
      ratingOverall: rated(),
    });
    // a chosen picture is saved with the game and shown as soon as it is
    if (pickedCover.value)
      await attachGameAssetFromUrl(saved.id, "key_art", pickedCover.value);
    if (pickedBanner.value)
      await attachGameAssetFromUrl(saved.id, "banner", pickedBanner.value);
    emit("saved", saved);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Could not save the game.";
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <QuickAddDialog
    title="Edit game"
    section-label="Your game"
    submit-label="Save"
    more-label="Edit more"
    :initial="initial"
    :search="async () => ({ results: [], providerErrors: [] })"
    :saving="saving"
    :error="error"
    @close="emit('close')"
    @add="save"
    @more="emit('more')"
  >
    <template #meta="{ result }">
      <span v-if="result.releaseYear">{{ result.releaseYear }}</span>
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
        v-model:cover="pickedCover"
        v-model:banner="pickedBanner"
        :title="result.title"
        :provider="result.provider"
        :provider-id="result.providerId"
        :current-cover="result.poster"
        current-label="Current"
      />
    </template>
  </QuickAddDialog>
</template>

<style scoped>
/* the status picker takes the whole row, so platform and rating pair up below it */
.qa-wide {
  grid-column: 1 / -1;
}
</style>
