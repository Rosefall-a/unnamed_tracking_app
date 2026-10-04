<script setup lang="ts">
import { computed, ref } from "vue";
import GameCard from "./GameCard.vue";
import type { Game } from "../types/game";
import type { Bounty } from "../services/bounties";
import type { WeeklyDigest } from "../services/stats";

const props = defineProps<{
  widgetId: string;
  games: Game[];
  bounties: Bounty[];
  digest: WeeklyDigest | null;
}>();
const emit = defineEmits<{
  edit: [game: Game];
  collection: [game: Game];
  random: [];
  changed: [];
}>();
const shelf = ref<HTMLElement | null>(null);
const shelfGames = computed(() => {
  if (props.widgetId === "continue-playing")
    return [...props.games]
      .filter((game) => game.status === "playing")
      .sort((a, b) =>
        (b.lastPlayedAt ?? "").localeCompare(a.lastPlayedAt ?? ""),
      )
      .slice(0, 20);
  if (props.widgetId === "recently-added")
    return [...props.games]
      .filter((game) => game.dateAdded)
      .sort((a, b) => (b.dateAdded ?? "").localeCompare(a.dateAdded ?? ""))
      .slice(0, 20);
  if (props.widgetId.startsWith("collection:"))
    return props.games
      .filter((game) => game.collections.includes(props.widgetId.slice(11)))
      .slice(0, 20);
  return [];
});
const isShelf = computed(
  () =>
    ["continue-playing", "recently-added"].includes(props.widgetId) ||
    props.widgetId.startsWith("collection:"),
);
const shelfLink = computed(() =>
  props.widgetId === "continue-playing"
    ? "/games?status=playing"
    : props.widgetId === "recently-added"
      ? "/games?sort=recent"
      : `/collections/${encodeURIComponent(props.widgetId.slice(11))}`,
);
const collectionsCount = computed(
  () => new Set(props.games.flatMap((game) => game.collections)).size,
);
const backlog = computed(() =>
  props.games.filter(
    (game) =>
      game.status === "backlog" &&
      !game.lastPlayedAt &&
      game.dateAdded &&
      new Date(game.dateAdded).getTime() < Date.now() - 90 * 86_400_000,
  ),
);
const onThisDay = computed(() => {
  const today = new Date();
  return props.games.filter((game) => {
    if (!game.dateAdded) return false;
    const added = new Date(game.dateAdded);
    return (
      added.getMonth() === today.getMonth() &&
      added.getDate() === today.getDate() &&
      added.getFullYear() < today.getFullYear()
    );
  });
});
const steps = computed(() => [
  {
    label: "Connect a library",
    hint: "Choose your metadata sources and account connections.",
    to: "/settings?section=metadata",
    done: props.games.some((game) => game.source),
  },
  {
    label: "Favorite a game",
    hint: "Use the heart on a game card.",
    to: "/games",
    done: props.games.some((game) => game.favorite),
  },
  {
    label: "Set a goal",
    hint: "Create a personal bounty for something you want to finish.",
    to: "/bounties",
    done: props.bounties.length > 0,
  },
]);
const week = computed(() => [
  { label: "Games played", value: props.digest?.games_played ?? 0 },
  {
    label: "Achievements unlocked",
    value: props.digest?.achievements_unlocked ?? 0,
  },
  { label: "Goals completed", value: props.digest?.bounties_completed ?? 0 },
  { label: "Metadata changes", value: props.digest?.metadata_changes ?? 0 },
]);
function scroll(direction: -1 | 1) {
  const reduced =
    document.documentElement.classList.contains("reduce-motion") ||
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  shelf.value?.scrollBy({
    left: direction * shelf.value.clientWidth * 0.85,
    behavior: reduced ? "instant" : "smooth",
  });
}
</script>

<template>
  <div v-if="isShelf" class="shelf-widget">
    <div v-if="shelfGames.length" ref="shelf" class="home-shelf">
      <GameCard
        v-for="game in shelfGames"
        :key="game.id"
        :game="game"
        @edit="emit('edit', $event)"
        @add-to-collection="emit('collection', $event)"
        @changed="emit('changed')"
      />
    </div>
    <p v-else class="empty-message">
      {{
        widgetId === "continue-playing"
          ? "Nothing in progress right now."
          : "No games here yet."
      }}
    </p>
    <div class="shelf-actions">
      <router-link :to="shelfLink" class="text-link">View all</router-link>
      <div v-if="shelfGames.length > 1" class="scroll-actions">
        <button
          type="button"
          class="ui-btn ui-btn-ghost"
          aria-label="Scroll games left"
          @click="scroll(-1)"
        >
          ←
        </button>
        <button
          type="button"
          class="ui-btn ui-btn-ghost"
          aria-label="Scroll games right"
          @click="scroll(1)"
        >
          →
        </button>
      </div>
    </div>
  </div>
  <dl v-else-if="widgetId === 'library-summary'" class="summary-grid">
    <div>
      <dt>Games</dt>
      <dd>{{ games.length }}</dd>
    </div>
    <div>
      <dt>Favorites</dt>
      <dd>{{ games.filter((game) => game.favorite).length }}</dd>
    </div>
    <div>
      <dt>Collections</dt>
      <dd>{{ collectionsCount }}</dd>
    </div>
  </dl>
  <div v-else-if="widgetId === 'random-picker'">
    <p class="empty-message">
      {{
        games.length
          ? "Let your library surprise you. Choose filters before picking."
          : "Add a game to your library to start picking."
      }}
    </p>
    <button
      type="button"
      class="ui-btn ui-btn-primary"
      :disabled="!games.length"
      @click="emit('random')"
    >
      Pick a game
    </button>
  </div>
  <div v-else-if="widgetId === 'goals'">
    <ul v-if="bounties.length" class="widget-list">
      <li v-for="bounty in bounties.slice(0, 4)" :key="bounty.id">
        <router-link to="/bounties"
          >{{ bounty.title
          }}<small v-if="bounty.game_title">{{
            bounty.game_title
          }}</small></router-link
        >
      </li>
    </ul>
    <p v-else class="empty-message">
      No active goals. Set a personal bounty when you want some extra structure.
    </p>
    <router-link to="/bounties" class="text-link">{{
      bounties.length ? "View all goals" : "Create a goal"
    }}</router-link>
  </div>
  <div v-else-if="widgetId === 'weekly-digest'">
    <p class="period">Over the last seven days</p>
    <dl class="summary-grid weekly-grid">
      <div v-for="item in week" :key="item.label">
        <dt>{{ item.label }}</dt>
        <dd>{{ item.value }}</dd>
      </div>
    </dl>
    <router-link to="/statistics" class="text-link"
      >View statistics</router-link
    >
  </div>
  <div v-else-if="widgetId === 'backlog'">
    <p class="empty-message">
      {{
        backlog.length
          ? `${backlog.length} game${backlog.length === 1 ? "" : "s"} added over 90 days ago, without recorded play.`
          : "No untouched games older than 90 days."
      }}
    </p>
    <ul class="widget-list">
      <li v-for="game in backlog.slice(0, 3)" :key="game.id">
        <router-link :to="`/games/${game.id}`">{{ game.title }}</router-link>
      </li>
    </ul>
    <router-link to="/games?status=backlog" class="text-link"
      >Browse backlog</router-link
    >
  </div>
  <div v-else-if="widgetId === 'on-this-day'">
    <p v-if="!onThisDay.length" class="empty-message">
      No library anniversaries today.
    </p>
    <ul class="widget-list">
      <li v-for="game in onThisDay.slice(0, 4)" :key="game.id">
        <router-link :to="`/games/${game.id}`"
          >{{ game.title
          }}<small
            >Added
            {{
              new Date().getFullYear() - new Date(game.dateAdded!).getFullYear()
            }}
            years ago</small
          ></router-link
        >
      </li>
    </ul>
  </div>
  <ul
    v-else-if="widgetId === 'getting-started'"
    class="widget-list onboarding-list"
  >
    <li v-for="step in steps" :key="step.label">
      <router-link :to="step.to"
        ><span class="step-check" aria-hidden="true">{{
          step.done ? "✓" : "○"
        }}</span
        ><span
          >{{ step.label
          }}<small>{{ step.done ? "Done. " : "" }}{{ step.hint }}</small></span
        ></router-link
      >
    </li>
  </ul>
</template>

<style scoped>
.empty-message,
.period {
  color: var(--ui-dim);
  line-height: 1.6;
  margin: 0 0 16px;
}
.period {
  font-size: var(--ui-font-small);
}
.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin: 0;
}
.summary-grid div {
  display: flex;
  flex-direction: column-reverse;
  gap: 6px;
  min-width: 0;
}
dt {
  color: var(--ui-dim);
  font-size: var(--ui-font-small);
}
dd {
  font-size: 1.875rem;
  font-weight: 600;
  margin: 0;
}
.weekly-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin-bottom: 18px;
}
.widget-list {
  list-style: none;
  padding: 0;
  margin: 0 0 12px;
}
.widget-list a {
  display: block;
  padding: 12px 0;
  color: var(--ui-text);
  text-decoration: none;
  overflow-wrap: anywhere;
}
.widget-list li + li {
  border-top: 1px solid var(--ui-border-soft);
}
.widget-list a:hover,
.text-link:hover {
  color: var(--ui-accent-text);
}
.widget-list small {
  display: block;
  color: var(--ui-dim);
  font-size: var(--ui-font-small);
  margin-top: 4px;
}
.text-link {
  display: inline-flex;
  align-items: center;
  min-height: var(--ui-control-height);
  color: var(--ui-accent-text);
  text-decoration: none;
  font-weight: 600;
}
.onboarding-list a {
  display: flex;
  align-items: center;
  gap: 14px;
}
.step-check {
  color: var(--ui-accent-text);
}
.home-shelf {
  display: flex;
  overflow-x: auto;
  gap: 18px;
  padding: 4px 4px 12px;
  margin: 0 -4px;
  scrollbar-width: thin;
  scroll-snap-type: x proximity;
}
.home-shelf :deep(.game-card-wrap) {
  flex: 0 0 158px;
  width: 158px;
  scroll-snap-align: start;
}
.shelf-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
}
.scroll-actions {
  display: flex;
  gap: 8px;
}
.scroll-actions button {
  min-width: var(--ui-control-height);
  min-height: var(--ui-control-height);
}
@media (max-width: 760px) {
  .home-shelf {
    gap: 14px;
  }
  .home-shelf :deep(.game-card-wrap) {
    flex-basis: 160px;
    width: 160px;
  }
  .summary-grid {
    gap: 10px;
  }
}
</style>
