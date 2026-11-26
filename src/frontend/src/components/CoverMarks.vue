<script setup lang="ts">
// What sits on the art of a 100% game's cover, for whichever marks are on in
// Settings › Look and feel › Appearance. The cover clips all of it to its
// own rounded corners. Marks under the title live in GameCard itself.
import { computed } from "vue";
import type { CompletionMark } from "../utils/completionMarks";
import type { AchievementsSummaryEntry } from "../services/games";
import { formatPercent } from "../utils/achievements";
import TrophyIcon from "./TrophyIcon.vue";

const props = defineProps<{
  marks: Set<CompletionMark>;
  entry?: AchievementsSummaryEntry;
  // the custom badge picture from Settings, used in place of the trophy
  imageUrl?: string | null;
}>();

const on = (m: CompletionMark) => props.marks.has(m);
const rarest = computed(() => props.entry?.rarest ?? null);
// the corner holds one thing: the rarest unlock when there is one to show,
// otherwise the Seal
const corner = computed(() =>
  on("rarest_pin") && rarest.value ? "pin" : on("seal") ? "seal" : null,
);
</script>

<template>
  <span v-if="on('sheen')" class="sheen" aria-hidden="true"></span>

  <template v-if="corner">
    <span v-if="corner === 'seal'" class="scrim" aria-hidden="true"></span>
    <span v-if="corner === 'seal'" class="seal corner" title="100% complete">
      <img v-if="imageUrl" :src="imageUrl" alt="" />
      <TrophyIcon v-else />
    </span>
    <span
      v-else-if="rarest"
      class="pinach corner"
      :title="`Rarest unlock: ${rarest.name}`"
    >
      <img v-if="rarest.icon_url" :src="rarest.icon_url" alt="" />
      <em>{{ formatPercent(rarest.percent) }}</em>
    </span>
  </template>
</template>

<style scoped>
.sheen,
.scrim,
.corner {
  position: absolute;
  pointer-events: none;
}
.sheen {
  inset: 0;
  border-radius: inherit;
  z-index: 2;
}
.scrim,
.corner {
  z-index: 3;
}

.scrim {
  left: 0;
  right: 0;
  bottom: 0;
  height: 38%;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.55), transparent);
}
.corner {
  right: 7px;
  bottom: 7px;
}
.seal {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: rgba(14, 14, 14, 0.72);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  box-shadow:
    inset 0 0 0 1px var(--mk-ring),
    0 2px 8px rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--mk-hi);
}
.seal :deep(svg) {
  width: 14px;
  height: 14px;
}
.seal img {
  width: 18px;
  height: 18px;
  object-fit: contain;
}
.pinach {
  right: 6px;
  bottom: 6px;
  display: flex;
  align-items: center;
  gap: 5px;
  background: rgba(12, 12, 12, 0.78);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  border-radius: 999px;
  padding: 3px 8px 3px 3px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.45);
}
.pinach img {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  object-fit: cover;
  box-shadow: 0 0 0 1.5px var(--mk-hi);
}
.pinach em {
  font-style: normal;
  font-size: 11px;
  font-weight: 700;
  color: var(--mk-hi);
  font-variant-numeric: tabular-nums;
}

/* Foil sheen: one sweep across each time the mouse arrives */
.sheen {
  background: linear-gradient(
    115deg,
    transparent 30%,
    rgba(255, 240, 200, 0.08) 42%,
    rgba(255, 236, 180, 0.45) 50%,
    rgba(255, 240, 200, 0.08) 58%,
    transparent 70%
  );
  background-size: 250% 100%;
  background-position: 120% 0;
  background-repeat: no-repeat;
  mix-blend-mode: screen;
  opacity: 0;
}
.game-card:hover .sheen {
  animation: sweep 0.9s ease forwards;
}
@keyframes sweep {
  0% {
    opacity: 1;
    background-position: 120% 0;
  }
  100% {
    opacity: 1;
    background-position: -20% 0;
  }
}

/* the cover's own buttons take the bottom on hover, so the corner mark and
   its shade step aside for them */
.scrim,
.corner {
  transition: opacity 0.18s ease;
}
.game-card:hover .corner,
.game-card:hover .scrim {
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .game-card:hover .sheen {
    animation: none;
  }
  .scrim,
  .corner {
    transition: none;
  }
}
</style>
