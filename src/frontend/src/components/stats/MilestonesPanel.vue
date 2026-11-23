<script setup lang="ts">
// Achievement milestones on the Statistics games tab: how close the next ones
// are, then every one reached, newest first, with the game it happened in.
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import {
  fetchAchievementMilestones,
  type AchievementMilestones,
} from "../../services/stats";

const data = ref<AchievementMilestones | null>(null);
const error = ref<string | null>(null);
const showAll = ref(false);
const SHOWN = 8;

onMounted(async () => {
  try {
    data.value = await fetchAchievementMilestones();
  } catch (err) {
    error.value =
      err instanceof Error ? err.message : "Could not load milestones.";
  }
});

const reached = computed(() => {
  const all = data.value?.reached ?? [];
  return showAll.value ? all : all.slice(0, SHOWN);
});

function when(at: number | null): string {
  if (at === null) return "Date unknown";
  return new Date(at * 1000).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

const ICON: Record<string, string> = {
  unlocks: "★",
  perfect: "100",
  rarity: "%",
};
</script>

<template>
  <p v-if="error" class="empty">{{ error }}</p>
  <p v-else-if="!data" class="empty">Loading milestones…</p>
  <p v-else-if="!data.reached.length && !data.next.length" class="empty">
    No achievements unlocked yet.
  </p>
  <template v-else>
    <div v-if="data.next.length" class="next">
      <div v-for="n in data.next" :key="n.kind" class="next-row">
        <div class="next-top">
          <span class="next-label">Next: {{ n.label }}</span>
          <span class="next-count"
            >{{ n.current.toLocaleString() }} /
            {{ n.target.toLocaleString() }}</span
          >
        </div>
        <div class="track">
          <div
            class="fill"
            :style="{
              width: `${Math.min(100, (n.current / n.target) * 100)}%`,
            }"
          />
        </div>
      </div>
    </div>
    <ol v-if="data.reached.length" class="list">
      <li v-for="m in reached" :key="m.id" class="item">
        <span class="badge" :class="m.kind">{{ ICON[m.kind] }}</span>
        <div class="text">
          <strong>{{ m.label }}</strong>
          <span v-if="m.game_id" class="where">
            {{ m.achievement }} in
            <RouterLink :to="`/games/${m.game_id}`">{{
              m.game_title
            }}</RouterLink>
          </span>
        </div>
        <span class="date">{{ when(m.at) }}</span>
      </li>
    </ol>
    <button
      v-if="(data.reached.length ?? 0) > SHOWN"
      class="text-button more"
      type="button"
      @click="showAll = !showAll"
    >
      {{ showAll ? "Show fewer" : `Show all ${data.reached.length}` }}
    </button>
  </template>
</template>

<style scoped>
.empty {
  margin: 0;
  color: var(--ui-dim);
  font-size: 0.86rem;
}
.next {
  display: grid;
  gap: 12px;
  margin-bottom: 18px;
}
.next-top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 6px;
  font-size: 0.84rem;
}
.next-label {
  font-weight: 700;
}
.next-count {
  color: var(--ui-dim);
  font-variant-numeric: tabular-nums;
}
.track {
  height: 6px;
  border-radius: 999px;
  background: var(--ui-surface-2);
  overflow: hidden;
}
.fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--ui-accent), var(--ui-accent-bright));
}
.list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 2px;
}
.item {
  display: grid;
  grid-template-columns: 34px 1fr auto;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
  border-top: 1px solid var(--ui-border-soft);
}
.item:first-child {
  border-top: 0;
}
.badge {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: var(--ui-surface-2);
  color: var(--ui-accent);
  font-size: 0.72rem;
  font-weight: 800;
}
.text {
  display: grid;
  gap: 2px;
  min-width: 0;
  font-size: 0.86rem;
}
.where {
  color: var(--ui-dim);
  font-size: 0.8rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.where a {
  color: var(--ui-text-soft);
}
.date {
  color: var(--ui-faint);
  font-size: 0.78rem;
  white-space: nowrap;
}
.more {
  margin-top: 10px;
}
</style>
