<script setup lang="ts">
// The card at the top of a game's Achievements tab once every achievement is
// unlocked: the count, the day it was done, how long it took, the playtime and
// the rarest unlocks. Each figure is shown only when there is real data for
// it; nothing is estimated.
import { computed } from "vue";
import type { Game } from "../types/game";
import { formatPercent, isUnlocked } from "../utils/achievements";
import TrophyIcon from "./TrophyIcon.vue";

const props = defineProps<{ game: Game; banner?: string | null }>();

const list = computed(() => props.game.achievements);
const got = computed(() => list.value.filter(isUnlocked));

const times = computed(() =>
  got.value
    .map((a) => (a.unlockedAt ? new Date(a.unlockedAt).getTime() : NaN))
    .filter((t) => !Number.isNaN(t))
    .sort((a, b) => a - b),
);

function longDate(ms: number): string {
  return new Date(ms).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

const completedOn = computed(() => {
  // the last unlock is the moment it was done; the saved completion date is
  // the fallback for a set with no unlock times
  if (times.value.length) return longDate(times.value[times.value.length - 1]);
  const d = props.game.completionDate;
  if (!d) return null;
  const ms = new Date(d.length === 10 ? `${d}T12:00:00` : d).getTime();
  return Number.isNaN(ms) ? null : longDate(ms);
});

// from the first unlock to the last, only when every unlock has a time
const timeTo100 = computed(() => {
  if (times.value.length !== got.value.length || times.value.length < 2)
    return null;
  const first = new Date(times.value[0]).setHours(0, 0, 0, 0);
  const last = new Date(times.value[times.value.length - 1]).setHours(
    0,
    0,
    0,
    0,
  );
  const days = Math.round((last - first) / 86_400_000);
  if (days === 0) return "Same day";
  return days === 1 ? "1 day" : `${days} days`;
});

const playtime = computed(() => {
  const minutes = props.game.platforms.reduce(
    (sum, p) => sum + p.playtimeMinutes,
    0,
  );
  if (!minutes) return null;
  return `${(minutes / 60).toFixed(1)} h`;
});

// the three rarest you have, the same three that top the list sorted by Players
const rarest = computed(() =>
  got.value
    .filter((a) => typeof a.rarityPercent === "number")
    .sort((a, b) => (a.rarityPercent ?? 0) - (b.rarityPercent ?? 0))
    .slice(0, 3),
);

const facts = computed(() => {
  const out: { label: string; value: string }[] = [];
  if (completedOn.value)
    out.push({ label: "Completed", value: completedOn.value });
  if (timeTo100.value)
    out.push({ label: "Time to 100%", value: timeTo100.value });
  if (playtime.value) out.push({ label: "Playtime", value: playtime.value });
  if (rarest.value.length)
    out.push({
      label: "Rarest unlock",
      value: `${formatPercent(rarest.value[0].rarityPercent as number)} of players`,
    });
  return out;
});
</script>

<template>
  <section class="done-card" aria-label="100% complete">
    <div
      class="done-bg"
      :style="banner ? { backgroundImage: `url(${banner})` } : undefined"
      aria-hidden="true"
    ></div>
    <div class="done-in">
      <div class="done-main">
        <div class="done-eb"><TrophyIcon />100% complete</div>
        <div class="done-big">
          {{ got.length }} of {{ list.length }} achievements<em>100%</em>
        </div>
        <div class="done-bar"><i></i></div>
      </div>
      <div v-if="facts.length" class="facts">
        <div v-for="f in facts" :key="f.label" class="fact">
          <span>{{ f.label }}</span>
          <b>{{ f.value }}</b>
        </div>
      </div>
    </div>
    <div v-if="rarest.length" class="rares">
      <span class="t">Rarest unlocks</span>
      <span v-for="a in rarest" :key="a.id" class="rare-chip">
        <img v-if="a.iconUrl" :src="a.iconUrl" alt="" />
        <span v-else class="rare-blank"></span>
        <b>{{ a.name }}</b>
        <span>{{ formatPercent(a.rarityPercent as number) }}</span>
      </span>
    </div>
  </section>
</template>

<style scoped>
.done-card {
  position: relative;
  margin: 4px 0 16px;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(241, 205, 106, 0.35);
  background: #141414;
}
.done-bg {
  position: absolute;
  inset: 0;
  background-position: center 30%;
  background-size: cover;
  filter: blur(14px) brightness(0.35) saturate(1.2);
  transform: scale(1.1);
}
.done-in {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 28px;
  align-items: center;
  padding: 20px 22px;
}
.done-eb {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #f1cd6a;
}
.done-eb :deep(svg) {
  width: 15px;
  height: 15px;
}
.done-big {
  margin-top: 6px;
  font-size: 1.35rem;
  font-weight: 800;
  color: #fff;
}
.done-big em {
  font-style: normal;
  color: #f1cd6a;
  margin-left: 8px;
}
.done-bar {
  height: 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
  overflow: hidden;
  margin-top: 10px;
  max-width: 460px;
}
.done-bar i {
  display: block;
  height: 100%;
  width: 100%;
  background: linear-gradient(90deg, #c08a26, #f1cd6a 55%, #d9a63f);
}
.facts {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: auto;
}
.fact {
  padding: 0 20px;
  border-left: 1px solid rgba(255, 255, 255, 0.1);
}
.fact:first-child {
  border-left: 0;
}
.fact span {
  display: block;
  font-size: 12px;
  color: #a5a5a5;
}
.fact b {
  display: block;
  margin-top: 3px;
  font-size: 15px;
  color: #fff;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.rares {
  position: relative;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 0 22px 18px;
  align-items: center;
}
.rares .t {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #a5a5a5;
  margin-right: 4px;
}
.rare-chip {
  display: flex;
  align-items: center;
  gap: 9px;
  min-width: 0;
  background: rgba(0, 0, 0, 0.35);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  padding: 6px 12px 6px 6px;
}
.rare-chip img,
.rare-blank {
  width: 30px;
  height: 30px;
  border-radius: 5px;
  object-fit: cover;
  flex: 0 0 auto;
  box-shadow: 0 0 0 1px rgba(241, 205, 106, 0.7);
}
.rare-blank {
  background: #262626;
}
.rare-chip b {
  font-size: 13px;
  color: #eee;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 220px;
}
.rare-chip > span:last-child {
  font-size: 12.5px;
  color: #f1cd6a;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
/* a narrow window: the facts go under the count, two to a row */
@media (max-width: 900px) {
  .done-in {
    grid-template-columns: 1fr;
    gap: 16px;
  }
  .facts {
    grid-auto-flow: row;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px 0;
  }
  .fact:nth-child(odd) {
    border-left: 0;
    padding-left: 0;
  }
}
</style>
