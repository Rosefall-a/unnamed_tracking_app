<script setup lang="ts">
// Four widgets share this, drawn the way Steam draws them. The unlocks (latest or
// rarest) are a grid of just the achievement icons, with the details in a tooltip
// and a "+N" tile for the rest; the games you are working on (or are close to
// finishing) are a short list with a progress bar each. `settings.mode` says which.
import { computed, onBeforeUnmount, ref, watch } from "vue";
import WidgetFrame from "../WidgetFrame.vue";
import { ago, homeData, titlesByKind } from "../../../home/data";
import { sampleFeed, sampleTitles } from "../../../home/samples";
import type { AchievementFeedEntry } from "../../../services/achievementsFeed";
import type { WidgetProps } from "../../../home/registry";

const props = defineProps<WidgetProps>();

const mode = computed(() => String(props.settings.mode));
const count = computed(() => Number(props.settings.count) || 15);
const isFeed = computed(() => mode.value === "recent" || mode.value === "rare");
const asList = computed(() => props.variant === "list");

const HEADING: Record<string, string> = {
  recent: "Recent achievements",
  rare: "Rarest achievements",
  games: "Latest games with achievements",
  close: "Closest to 100%",
};

const feed = computed<AchievementFeedEntry[]>(() => {
  if (props.sample) return sampleFeed(count.value);
  if (mode.value === "rare") {
    const ceiling = Number(props.settings.maxPercent) || 100;
    return homeData.achFeed.value.rarest
      .filter((a) => a.globalPercent === null || a.globalPercent <= ceiling)
      .slice(0, count.value);
  }
  return homeData.achFeed.value.recent.slice(0, count.value);
});

// how many icons fit in the space the widget has, so the grid is whole rows
// that stop at the bottom edge instead of running over what is below it
const gridEl = ref<HTMLElement | null>(null);
const fit = ref(Number.POSITIVE_INFINITY);
const GAP = 8;
function measure() {
  const el = gridEl.value;
  if (!el) return;
  const cols = Math.max(
    1,
    Math.floor((el.clientWidth + GAP) / (iconPx.value + GAP)),
  );
  const rows = Math.max(
    1,
    Math.floor((el.clientHeight + GAP) / (iconPx.value + GAP)),
  );
  fit.value = cols * rows;
}
// the grid only exists once there is something to show, so watch for it
let observer: ResizeObserver | null = null;
watch(gridEl, (el) => {
  observer?.disconnect();
  observer = null;
  if (!el) return;
  observer = new ResizeObserver(measure);
  observer.observe(el);
  measure();
});
onBeforeUnmount(() => observer?.disconnect());

// every achievement unlocked, for the "+N more" tile
const unlockedTotal = computed(() =>
  props.sample
    ? 148
    : Object.values(homeData.achSummary.value).reduce(
        (n, a) => n + a.unlocked,
        0,
      ),
);
// the icons that are drawn, leaving one place for "+N" when there are more
const wantMore = computed(() => props.settings.showMore !== false);
const shown = computed(() => {
  const all = feed.value;
  if (
    all.length <= fit.value &&
    !(wantMore.value && unlockedTotal.value > all.length)
  )
    return all;
  return all.slice(0, Math.max(0, fit.value - (wantMore.value ? 1 : 0)));
});
const more = computed(() =>
  wantMore.value ? Math.max(0, unlockedTotal.value - shown.value.length) : 0,
);

function detail(a: AchievementFeedEntry): string {
  if (mode.value === "rare")
    return a.globalPercent === null
      ? ""
      : `${a.globalPercent.toFixed(1)}% of players have this`;
  return a.unlockedAt ? `Unlocked ${ago(a.unlockedAt * 1000)}` : "";
}

// how rare it is shows as the colour of the icon's edge
function rarity(a: AchievementFeedEntry): string {
  const p = a.globalPercent;
  if (p === null) return "";
  if (p <= 5) return "ultra";
  if (p <= 15) return "rare";
  return "";
}

const brokenIcons = ref(new Set<string>());
function iconFailed(id: string) {
  brokenIcons.value = new Set(brokenIcons.value).add(id);
}

const SIZE: Record<string, number> = { small: 44, medium: 56, large: 72 };
const iconPx = computed(() => SIZE[String(props.settings.iconSize)] ?? 56);
watch(iconPx, () => requestAnimationFrame(measure));

const gameRows = computed(() => {
  if (props.sample)
    return sampleTitles(count.value, ["game"]).map((t, i) => ({
      key: t.key,
      title: t.title,
      art: null as string | null,
      to: "",
      unlocked: 5 + i * 6,
      total: 40,
    }));
  const minTotal = Number(props.settings.minTotal) || 0;
  const withAch = titlesByKind.value.game.filter(
    (t) =>
      t.ach &&
      t.ach.total > 0 &&
      t.ach.total >= minTotal &&
      !(props.settings.hideCompleted && t.ach.unlocked >= t.ach.total),
  );
  let chosen: typeof withAch;
  if (mode.value === "close") {
    chosen = withAch
      .filter((t) => t.ach!.unlocked > 0 && t.ach!.unlocked < t.ach!.total)
      .sort(
        (a, b) =>
          a.ach!.total - a.ach!.unlocked - (b.ach!.total - b.ach!.unlocked) ||
          b.ach!.total - a.ach!.total,
      );
  } else {
    // the games behind your latest unlocks first, then the rest by last played
    const order = new Map<string, number>();
    homeData.achFeed.value.recent.forEach((a, i) => {
      if (!order.has(a.gameId)) order.set(a.gameId, i);
    });
    chosen = withAch
      .filter((t) => t.ach!.unlocked > 0)
      .sort(
        (a, b) =>
          (order.get(a.id) ?? 999) - (order.get(b.id) ?? 999) ||
          b.touchedAt - a.touchedAt,
      );
  }
  return chosen.slice(0, count.value).map((t) => ({
    key: t.key,
    title: t.title,
    art: t.art,
    to: t.to,
    unlocked: t.ach!.unlocked,
    total: t.ach!.total,
  }));
});

const EMPTY_HINT =
  "Sync a Steam, PlayStation or RetroAchievements library and your achievements show up here.";
</script>

<template>
  <WidgetFrame
    :title="HEADING[mode] ?? 'Achievements'"
    :sample="sample"
    :link="{ to: '/games', label: 'Games' }"
    :surface="isFeed && asList"
  >
    <!-- unlocks as icons, the way Steam shows them -->
    <div
      v-if="isFeed && !asList && feed.length"
      ref="gridEl"
      class="grid"
      :style="{ '--icon': `${iconPx}px` }"
    >
      <component
        :is="sample ? 'div' : 'router-link'"
        v-for="a in shown"
        :key="a.id"
        :to="sample ? undefined : `/games/${a.gameId}/achievements/${a.id}`"
        class="tile"
        :class="rarity(a)"
      >
        <img
          v-if="a.iconUrl && !brokenIcons.has(a.id)"
          :src="a.iconUrl"
          alt=""
          loading="lazy"
          @error="iconFailed(a.id)"
        />
        <span v-else class="letter">{{ a.name.charAt(0) }}</span>
        <span class="tip" role="tooltip">
          <strong>{{ a.name }}</strong>
          <span v-if="settings.showGame !== false">{{ a.gameTitle }}</span>
          <small>{{ detail(a) }}</small>
        </span>
      </component>
      <component
        :is="sample ? 'div' : 'router-link'"
        v-if="more > 0"
        :to="sample ? undefined : '/games'"
        class="tile more"
      >
        <span>+{{ more.toLocaleString() }}</span>
      </component>
    </div>

    <!-- unlocks as a list -->
    <ul v-else-if="isFeed && asList && feed.length" class="list">
      <li v-for="a in feed" :key="a.id">
        <component
          :is="sample ? 'div' : 'router-link'"
          :to="sample ? undefined : `/games/${a.gameId}/achievements/${a.id}`"
          class="row"
        >
          <span class="icon">
            <img
              v-if="a.iconUrl && !brokenIcons.has(a.id)"
              :src="a.iconUrl"
              alt=""
              loading="lazy"
              @error="iconFailed(a.id)"
            />
            <span v-else>{{ a.name.charAt(0) }}</span>
          </span>
          <span class="words">
            <strong>{{ a.name }}</strong>
            <small v-if="settings.showGame !== false">{{ a.gameTitle }}</small>
          </span>
          <span class="detail">{{ detail(a) }}</span>
        </component>
      </li>
    </ul>

    <!-- games, with how far along each is -->
    <ul v-else-if="!isFeed && gameRows.length" class="games">
      <li v-for="g in gameRows" :key="g.key">
        <component
          :is="sample ? 'div' : 'router-link'"
          :to="sample ? undefined : g.to"
          class="game"
        >
          <span class="cover">
            <img v-if="g.art" :src="g.art" alt="" loading="lazy" />
            <span v-else>{{ g.title.charAt(0) }}</span>
          </span>
          <span class="game-words">
            <strong>{{ g.title }}</strong>
            <span class="bar"
              ><span
                :style="{ width: `${(g.unlocked / g.total) * 100}%` }"
              ></span
            ></span>
          </span>
          <span class="count">
            <template v-if="mode === 'close'"
              >{{ g.total - g.unlocked }} left</template
            >
            <template v-else>{{ g.unlocked }} / {{ g.total }}</template>
          </span>
        </component>
      </li>
    </ul>

    <div v-else class="empty">
      <strong>{{ loading ? "Loading" : "No achievements yet" }}</strong>
      <span v-if="!loading">{{
        mode === "close"
          ? "Games with only a few left to unlock show here."
          : EMPTY_HINT
      }}</span>
      <router-link v-if="!loading" to="/settings?section=connections">
        Open Connections
      </router-link>
    </div>
  </WidgetFrame>
</template>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, var(--icon));
  grid-auto-rows: var(--icon);
  justify-content: start;
  align-content: start;
  gap: 8px;
  height: 100%;
}
.tile {
  --edge: var(--ui-border);
  position: relative;
  display: block;
  width: var(--icon);
  height: var(--icon);
  border: 1.5px solid var(--edge);
  border-radius: 9px;
  background: var(--ui-surface-3);
  color: var(--ui-dim);
  text-decoration: none;
  transition:
    border-color 0.15s,
    transform 0.15s;
}
.tile img {
  width: 100%;
  height: 100%;
  border-radius: 7.5px;
  object-fit: cover;
}
.tile.rare {
  --edge: var(--ui-accent-line);
}
.tile.ultra {
  --edge: var(--ui-accent-bright);
  box-shadow: 0 0 10px color-mix(in srgb, var(--ui-accent) 45%, transparent);
}
a.tile:hover {
  --edge: var(--ui-accent);
  transform: translateY(-2px);
  z-index: 5;
}
.letter,
.more span {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  font-weight: 800;
}
.letter {
  font-size: 1.3rem;
}
.more {
  border-style: dashed;
  background: transparent;
}
.more span {
  font-size: 0.8rem;
  color: var(--ui-dim);
}
.tip {
  position: absolute;
  bottom: calc(100% + 8px);
  left: 50%;
  z-index: 30;
  display: flex;
  flex-direction: column;
  gap: 2px;
  width: max-content;
  max-width: 230px;
  padding: 8px 10px;
  border: 1px solid var(--ui-border-strong);
  border-radius: var(--ui-radius-control);
  background: var(--ui-popover);
  box-shadow: 0 10px 28px
    color-mix(in srgb, var(--ui-scrim-base) 55%, transparent);
  color: var(--ui-text);
  font-size: 0.78rem;
  line-height: 1.3;
  text-align: left;
  opacity: 0;
  visibility: hidden;
  transform: translateX(-50%) translateY(4px);
  transition:
    opacity 0.12s,
    transform 0.12s;
  pointer-events: none;
}
.tip strong {
  font-size: 0.82rem;
}
.tip span {
  color: var(--ui-dim);
}
.tip small {
  color: var(--ui-accent);
  font-size: 0.72rem;
  font-weight: 600;
}
.tile:hover .tip,
.tile:focus-visible .tip {
  opacity: 1;
  visibility: visible;
  transform: translateX(-50%) translateY(0);
}
.list,
.games {
  display: flex;
  flex-direction: column;
  gap: 2px;
  height: 100%;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  list-style: none;
  scrollbar-width: thin;
}
.row,
.game {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 5px 8px;
  border-radius: var(--ui-radius-control);
  color: var(--ui-text);
  text-decoration: none;
}
a.row:hover,
a.game:hover {
  background: var(--ui-surface-2);
}
.icon,
.cover {
  flex: none;
  display: grid;
  place-items: center;
  overflow: hidden;
  border-radius: 7px;
  background: var(--ui-surface-3);
  color: var(--ui-dim);
  font-weight: 800;
}
.icon {
  width: 38px;
  height: 38px;
}
.cover {
  width: 34px;
  height: 46px;
}
.icon img,
.cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.words,
.game-words {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
}
.words {
  gap: 1px;
}
strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.86rem;
}
.words small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--ui-faint);
  font-size: 0.74rem;
}
.detail,
.count {
  flex: none;
  color: var(--ui-dim);
  font-size: 0.75rem;
  font-variant-numeric: tabular-nums;
}
.bar {
  display: block;
  height: 5px;
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
.empty {
  display: grid;
  place-content: center;
  gap: 6px;
  height: 100%;
  text-align: center;
  color: var(--ui-dim);
  font-size: 0.84rem;
}
.empty strong {
  color: var(--ui-text);
}
.empty a {
  color: var(--ui-accent);
  font-weight: 700;
  text-decoration: none;
}
</style>
