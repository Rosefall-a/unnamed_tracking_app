<script setup lang="ts">
import { computed } from "vue";
import { currentUser } from "../../../state/auth";
import { allTitles, homeData } from "../../../home/data";
import type { WidgetProps } from "../../../home/registry";

const props = defineProps<WidgetProps>();

const hello = computed(() => {
  const hour = new Date().getHours();
  const part =
    hour < 5
      ? "Still up"
      : hour < 12
        ? "Good morning"
        : hour < 18
          ? "Good afternoon"
          : "Good evening";
  const name = props.sample ? "there" : currentUser.value?.username;
  return name ? `${part}, ${name}` : part;
});
const today = new Date().toLocaleDateString(undefined, {
  weekday: "long",
  month: "long",
  day: "numeric",
});

const weekAgo = () => Date.now() - 7 * 86_400_000;
const recap = computed(() => {
  const played = (homeData.games.value ?? []).filter(
    (g) => g.lastPlayedAt && new Date(g.lastPlayedAt).getTime() >= weekAgo(),
  ).length;
  const digest = homeData.digest.value;
  return [
    { n: played, label: played === 1 ? "game played" : "games played" },
    {
      n: digest?.achievements_unlocked ?? 0,
      label:
        digest?.achievements_unlocked === 1 ? "achievement" : "achievements",
    },
    { n: digest?.games_added ?? 0, label: "added" },
  ];
});
const total = computed(() => allTitles.value.length);
</script>

<template>
  <section class="greet">
    <p v-if="settings.showDate !== false" class="date">{{ today }}</p>
    <div class="line">
      <h1>{{ hello }}</h1>
      <div v-if="settings.recap" class="recap" aria-label="This week">
        <span class="label">This week</span>
        <div v-for="item in recap" :key="item.label" class="chip">
          <strong>{{ sample ? 4 : item.n }}</strong>
          <span>{{ item.label }}</span>
        </div>
      </div>
    </div>
    <p
      v-if="settings.showCount !== false && (!loading || sample)"
      class="count"
    >
      {{ sample ? 128 : total }} titles in your library
    </p>
  </section>
</template>

<style scoped>
.greet {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 0 0 0 2px;
  color: var(--ui-text);
}
/* the greeting and the recap share a line, the recap flush with the right edge */
.line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px 24px;
}
.date {
  /* room on the right for the Customize button, which sits on this line */
  margin: 0 200px 4px 0;
  color: var(--ui-accent);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}
h1 {
  margin: 0;
  font-size: clamp(1.5rem, 3vw, 2.2rem);
  font-weight: 800;
  letter-spacing: -0.01em;
}
.count {
  margin: 4px 0 0;
  color: var(--ui-faint);
  font-size: 0.85rem;
}
.recap {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.label {
  color: var(--ui-faint);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.chip {
  display: flex;
  align-items: baseline;
  gap: 6px;
  padding: 7px 12px;
  border: 1px solid var(--ui-border-soft);
  border-radius: 999px;
  background: var(--ui-surface);
  font-size: 0.8rem;
  color: var(--ui-dim);
}
.chip strong {
  color: var(--ui-text);
  font-size: 1rem;
  font-variant-numeric: tabular-nums;
}
</style>
