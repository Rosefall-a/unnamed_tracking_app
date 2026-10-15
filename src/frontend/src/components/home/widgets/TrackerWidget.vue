<script setup lang="ts">
// Counts anything you can describe: finished horror games, anime from a studio,
// films from the 90s, games on one platform. Choose what to match and it keeps the
// count, with a goal to work toward if you set one. Add as many as you like.
import { computed } from "vue";
import WidgetFrame from "../WidgetFrame.vue";
import { titlesOf } from "../../../home/data";
import type { HomeTitle } from "../../../home/data";
import { sampleTitles } from "../../../home/samples";
import { narrow } from "../../../home/select";
import type { WidgetProps } from "../../../home/registry";

const props = defineProps<WidgetProps>();

const STATUS: Record<string, (t: HomeTitle) => boolean> = {
  any: () => true,
  active: (t) => t.group === "active",
  queue: (t) => t.group === "queue",
  wishlist: (t) => t.group === "wishlist",
  done: (t) => t.group === "done",
  dropped: (t) => t.group === "dropped",
  favorite: (t) => t.favorite,
};
const STATUS_WORD: Record<string, string> = {
  any: "in your library",
  active: "in progress",
  queue: "waiting",
  wishlist: "on your wishlist",
  done: "finished",
  dropped: "dropped",
  favorite: "favorites",
};

const matches = computed<HomeTitle[]>(() => {
  if (props.sample) return sampleTitles(17, ["game"]);
  const s = props.settings;
  const maker = String(s.maker ?? "")
    .trim()
    .toLowerCase();
  const from = Number(s.yearFrom) || 0;
  const to = Number(s.yearTo) || 0;
  const list = narrow(
    titlesOf(s.kinds).filter(STATUS[String(s.status)] ?? STATUS.any),
    s,
  );
  return list.filter((t) => {
    if (maker && !t.makers.some((m) => m.toLowerCase().includes(maker)))
      return false;
    if (from || to) {
      if (!t.release) return false;
      const y = new Date(t.release).getFullYear();
      if ((from && y < from) || (to && y > to)) return false;
    }
    return true;
  });
});

const count = computed(() => matches.value.length);
const goal = computed(() => Number(props.settings.goal) || 0);
const share = computed(() =>
  goal.value ? Math.min(1, count.value / goal.value) : 0,
);
const style = computed(() => String(props.settings.style || "number"));
const label = computed(() => String(props.settings.label ?? "").trim());
const heading = computed(() => label.value || "Tracker");
const covers = computed(() =>
  matches.value
    .filter((t) => t.art)
    .slice(0, Number(props.settings.covers) || 0),
);
const word = computed(() => STATUS_WORD[String(props.settings.status)] ?? "");

// a ring drawn as a stroked circle
const R = 44;
const CIRC = 2 * Math.PI * R;
</script>

<template>
  <WidgetFrame :title="heading" surface :sample="sample">
    <div class="tracker" :class="style">
      <div v-if="style === 'ring'" class="ring" aria-hidden="true">
        <svg viewBox="0 0 100 100">
          <circle class="back" cx="50" cy="50" :r="R" />
          <circle
            class="front"
            cx="50"
            cy="50"
            :r="R"
            :stroke-dasharray="`${share * CIRC} ${CIRC}`"
          />
        </svg>
        <strong>{{ goal ? Math.round(share * 100) + "%" : count }}</strong>
      </div>
      <div class="info">
        <div class="big">
          <strong v-if="style !== 'ring'">{{ count }}</strong>
          <span v-if="goal">of {{ goal }}</span>
          <span v-else-if="style === 'ring'">{{ count }}</span>
        </div>
        <p class="what">{{ word }}</p>
        <span v-if="goal && style === 'bar'" class="bar"
          ><span :style="{ width: `${share * 100}%` }"></span
        ></span>
        <p v-if="goal && count >= goal" class="done">Goal reached</p>
        <p v-else-if="goal" class="left">{{ goal - count }} to go</p>
      </div>
      <ul v-if="covers.length" class="covers">
        <li v-for="t in covers" :key="t.key">
          <component
            :is="sample ? 'span' : 'router-link'"
            :to="sample ? undefined : t.to"
            :title="t.title"
          >
            <img :src="t.art!" alt="" loading="lazy" />
          </component>
        </li>
      </ul>
    </div>
  </WidgetFrame>
</template>

<style scoped>
.tracker {
  display: flex;
  align-items: center;
  gap: 16px;
  height: 100%;
}
.ring {
  position: relative;
  flex: none;
  width: min(96px, 100%);
  aspect-ratio: 1;
}
.ring svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}
.ring circle {
  fill: none;
  stroke-width: 9;
}
.ring .back {
  stroke: var(--ui-surface-3);
}
.ring .front {
  stroke: var(--ui-accent);
  stroke-linecap: round;
  transition: stroke-dasharray 0.4s;
}
.ring strong {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  font-size: 1.15rem;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}
.info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  flex: 1;
}
.big {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.big strong {
  font-size: clamp(2rem, 9cqw, 3.2rem);
  font-weight: 800;
  line-height: 1;
  font-variant-numeric: tabular-nums;
  color: var(--ui-accent);
}
.big span {
  color: var(--ui-dim);
  font-size: 1rem;
  font-weight: 600;
}
.what,
.left,
.done {
  margin: 0;
  color: var(--ui-dim);
  font-size: 0.84rem;
}
.done {
  color: var(--ui-good-text);
  font-weight: 700;
}
.bar {
  display: block;
  height: 7px;
  margin: 4px 0;
  overflow: hidden;
  border-radius: 999px;
  background: var(--ui-surface-3);
}
.bar span {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: var(--ui-accent);
}
.covers {
  display: flex;
  flex-direction: row;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.covers li {
  width: 42px;
  height: 60px;
  overflow: hidden;
  border-radius: 6px;
  background: var(--ui-surface-3);
}
.covers a,
.covers span {
  display: block;
  height: 100%;
}
.covers img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
</style>
