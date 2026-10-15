<script setup lang="ts">
// The light edit the Games library opens from a game's Edit button: the same dialog
// as Add Game, with the four things most often changed (status, platform, rating and
// artwork) and an "Edit more" button for the full form.
import { computed, ref } from "vue";
import GameArtSection from "./GameArtSection.vue";
import QuickAddDialog from "./library/QuickAddDialog.vue";
import type { QuickAddResult } from "./library/QuickAddDialog.vue";
import {
  attachGameAssetFromUrl,
  patchGame,
  setRatings,
} from "../services/games";
import type { GameRatings } from "../services/games";
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
// a game is scored in four parts, the same four the game page asks for
const RATING_FIELDS: { key: keyof GameRatings; label: string }[] = [
  { key: "ratingOverall", label: "Atmosphere" },
  { key: "ratingStory", label: "Story" },
  { key: "ratingGameplay", label: "Gameplay" },
  { key: "ratingSound", label: "Sound" },
];
const ratings = ref<Record<keyof GameRatings, number | null>>({
  ratingOverall: props.game.ratingOverall,
  ratingStory: props.game.ratingStory,
  ratingGameplay: props.game.ratingGameplay,
  ratingSound: props.game.ratingSound,
});
const total = computed(() => {
  const given = RATING_FIELDS.map((f) => cleaned(ratings.value[f.key])).filter(
    (v): v is number => v !== null,
  );
  return given.length ? given.reduce((a, b) => a + b, 0) : null;
});
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
function cleaned(value: number | null): number | null {
  if (value === null || (value as unknown) === "" || Number.isNaN(value))
    return null;
  return Math.min(10, Math.max(0, value));
}

async function save() {
  saving.value = true;
  error.value = null;
  try {
    let saved = await patchGame(props.game.id, {
      status: status.value,
      platform: platform.value.trim() || null,
    });
    const next: GameRatings = {
      ratingOverall: cleaned(ratings.value.ratingOverall),
      ratingStory: cleaned(ratings.value.ratingStory),
      ratingGameplay: cleaned(ratings.value.ratingGameplay),
      ratingSound: cleaned(ratings.value.ratingSound),
    };
    const changed = RATING_FIELDS.some(
      (f) => next[f.key] !== props.game[f.key],
    );
    if (changed) saved = await setRatings(props.game.id, next);
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
      <div class="qa-field qa-wide ratings">
        <span>
          Your rating
          <em v-if="total !== null">★ {{ total.toFixed(1) }}</em>
        </span>
        <div class="rating-grid">
          <label v-for="f in RATING_FIELDS" :key="f.key">
            <small>{{ f.label }}</small>
            <input
              v-model.number="ratings[f.key]"
              type="number"
              min="0"
              max="10"
              step="0.5"
              placeholder="–"
              :aria-label="`${f.label} rating, 0 to 10`"
            />
          </label>
        </div>
      </div>
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
.ratings > span em {
  margin-left: 8px;
  color: var(--ui-accent);
  font-style: normal;
  font-weight: 700;
}
.rating-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}
.rating-grid label {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.rating-grid small {
  color: var(--ui-faint);
  font-size: 0.72rem;
}
@media (max-width: 520px) {
  .rating-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
/* the status picker takes the whole row, so platform and rating pair up below it */
.qa-wide {
  grid-column: 1 / -1;
}
</style>
