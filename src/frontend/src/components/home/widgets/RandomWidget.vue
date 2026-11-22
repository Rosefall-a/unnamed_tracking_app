<script setup lang="ts">
// Rolls a title for you. As a banner it is the title's own wide artwork with the
// details over it; as a card it is the poster with the details beside it. What it
// picks from (a pool, kinds, genre, platform, rating, how long it takes) is set
// with the controls on the widget. Narrow, it falls back to the poster and the
// buttons.
import { computed, inject, onBeforeUnmount, onMounted, ref } from "vue";
import WidgetFrame from "../WidgetFrame.vue";
import ArtCard from "../ArtCard.vue";
import { CHROME_KEY } from "../../../home/chrome";
import { KIND_NOUN, titlesOf } from "../../../home/data";
import type { HomeTitle } from "../../../home/data";
import { sampleTitles } from "../../../home/samples";
import { asKinds } from "../../../home/rail";
import { dailyShuffle, narrow, todayKey } from "../../../home/select";
import { WIDGET_CONTEXT } from "../../../home/context";
import { useNow } from "../../../home/clock";
import { getUi, setUi } from "../../../state/uiState";
import type { WidgetProps } from "../../../home/registry";

const props = defineProps<WidgetProps>();
const chrome = inject(CHROME_KEY, null);

const POOL: Record<string, (t: HomeTitle) => boolean> = {
  waiting: (t) => t.group === "queue" || t.group === "wishlist",
  backlog: (t) => t.group === "queue",
  wishlist: (t) => t.group === "wishlist",
  favorites: (t) => t.favorite,
  unfinished: (t) => t.group !== "done" && t.group !== "dropped",
  finished: (t) => t.group === "done",
  everything: () => true,
};

const pool = computed(() => {
  if (props.sample) return sampleTitles(4, asKinds(props.settings.kinds));
  const pick = POOL[String(props.settings.pool)] ?? POOL.waiting;
  return narrow(titlesOf(props.settings.kinds).filter(pick), props.settings);
});
// "Spotlight" is the same daily pick without a Pick again button
const daily = computed(() => props.settings.daily === true);

// One pick a day. Until "Pick again" is pressed it is the day's own choice,
// the same on every visit and every device; a title added to the library
// does not move it, and only one that leaves the pool (started, finished)
// is replaced. "Pick again" chooses another, saved on the server with the day
// it was made, so every device shows it until midnight. It is saved apart from
// the layout so a daily pick never adds a version to the Home layout's history.
const widget = inject(WIDGET_CONTEXT, null);
const widgetId = computed(() => widget?.value?.id ?? "picker");
const now = useNow();
const today = computed(() => todayKey(now.value));
const storageKey = computed(() => `homePick:${widgetId.value}`);

const chosen = computed(() =>
  getUi<{ day: string; key: string } | null>(storageKey.value, null),
);
function keep(key: string) {
  setUi(storageKey.value, { day: today.value, key });
}

const picked = computed(() => {
  const list = pool.value;
  if (!list.length) return null;
  if (props.sample) return list[0];
  const mine = chosen.value;
  if (mine && mine.day === today.value) {
    const kept = list.find((t) => t.key === mine.key);
    if (kept) return kept;
  }
  return dailyShuffle(list, (t) => t.key, widgetId.value, today.value)[0];
});
const position = computed(() =>
  picked.value ? pool.value.indexOf(picked.value) + 1 : 0,
);
const buttonLabel = computed(
  () => String(props.settings.buttonLabel || "").trim() || "Pick again",
);

// always something different from what is showing, kept for the rest of the day
function again() {
  const others = pool.value.filter((t) => t !== picked.value);
  if (!others.length) return;
  keep(others[Math.floor(Math.random() * others.length)].key);
}

const status = computed(() => {
  const s = picked.value?.status ?? "";
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : "";
});
const hours = computed(() => {
  const h = picked.value?.hours;
  return h ? `${Math.round(h * 10) / 10} h` : "";
});
const facts = computed(() =>
  [status.value, picked.value?.subtitle, picked.value?.platform, hours.value]
    .filter(Boolean)
    .join(" · "),
);

// The picture behind the details: the title's own background (a game's page
// background, a film's or show's backdrop) or its cover cropped wide. A background
// that is missing or will not load falls back to the cropped cover.
const failed = ref(new Set<string>());
function bgFailed(url: string) {
  failed.value = new Set(failed.value).add(url);
}

const backdrop = computed<string | null>(() => {
  const t = picked.value;
  if (!t) return null;
  const order = props.variant === "banner-cover" ? [t.art] : [t.wide, t.art];
  return order.find((url) => url && !failed.value.has(url)) ?? null;
});
// a cover is tall, so it fills the box (cropped) instead of lying along the top
const cropped = computed(() => backdrop.value === picked.value?.art);

const banner = computed(() => props.variant !== "card");

// beside or over the artwork when there is room, just the poster when there is not
const el = ref<HTMLElement | null>(null);
const wide = ref(true);
let observer: ResizeObserver | null = null;
onMounted(() => {
  if (!el.value) return;
  observer = new ResizeObserver(
    ([entry]) => (wide.value = entry.contentRect.width >= 300),
  );
  observer.observe(el.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>

<template>
  <WidgetFrame title="Pick something" :sample="sample">
    <div ref="el" class="wrap" :class="{ wide, banner, card: !banner && wide }">
      <template v-if="picked">
        <div v-if="banner" class="bg" aria-hidden="true">
          <img
            v-if="backdrop"
            :src="backdrop"
            alt=""
            :class="{ cropped }"
            draggable="false"
            @error="bgFailed(backdrop)"
          />
          <span class="scrim"></span>
        </div>
        <div v-if="!banner" class="art">
          <ArtCard
            :title="picked.title"
            :art="picked.art"
            :subtitle="wide ? '' : picked.subtitle"
            :to="picked.to"
            :tag="wide ? null : KIND_NOUN[picked.kind]"
            :tag-kind="picked.kind"
            :text="wide ? 'never' : (chrome?.cardText ?? 'always')"
            :sample="sample"
          />
        </div>
        <div class="info">
          <div class="mid">
            <span class="kind" :class="`kind-${picked.kind}`">{{
              KIND_NOUN[picked.kind]
            }}</span>
            <h3>{{ picked.title }}</h3>
            <p v-if="facts" class="meta">{{ facts }}</p>
            <p v-if="picked.rating !== null" class="rating">
              Your rating {{ picked.rating }}
            </p>
            <p class="count">
              {{
                daily ? "Today's pick" : `${position} of ${pool.length} matches`
              }}
            </p>
          </div>
          <div class="buttons">
            <button
              v-if="!daily"
              type="button"
              :disabled="pool.length < 2"
              @click="again"
            >
              {{ buttonLabel }}
            </button>
            <component
              :is="sample ? 'span' : 'router-link'"
              :to="sample ? undefined : picked.to"
              class="open"
            >
              Open
            </component>
          </div>
        </div>
      </template>
      <div v-else class="none">
        <strong>{{ loading ? "Loading" : "Nothing matches" }}</strong>
        <span v-if="!loading"
          >Loosen the filters using the controls above.</span
        >
      </div>
    </div>
  </WidgetFrame>
</template>

<style scoped>
.wrap {
  box-sizing: border-box;
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 10px;
  height: 100%;
  overflow: hidden;
}
.wrap.wide {
  flex-direction: row;
  gap: 16px;
}
.wrap.card {
  padding: 12px;
  border: 1px solid var(--ui-border-soft);
  border-radius: var(--ui-radius-card);
  background: var(--ui-surface);
}
.wrap.banner {
  padding: 18px 20px;
  border: 1px solid var(--ui-border-soft);
  border-radius: var(--ui-radius-card);
  background: var(--ui-surface);
}
/* A banner is much wider than the widget is tall, so filling the box with it crops
   it to a zoomed-in slice. It is drawn at its own width and shape instead, along the
   top, and fades into the card below it. */
.bg {
  position: absolute;
  inset: 0;
  overflow: hidden;
  background: var(--ui-surface);
}
.bg img {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: auto;
  min-height: 56%;
  object-fit: cover;
  object-position: center top;
}
/* a cover has no banner shape, so it is cropped to fill the box instead */
.bg img.cropped {
  height: 100%;
  min-height: 0;
  object-position: center 30%;
}
.scrim {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(
      to top,
      var(--ui-surface) 0%,
      color-mix(in srgb, var(--ui-surface) 82%, transparent) 32%,
      transparent 74%
    ),
    linear-gradient(
      90deg,
      color-mix(in srgb, var(--ui-scrim-base) 62%, transparent) 0%,
      transparent 70%
    );
}
.art {
  flex: 1;
  min-height: 0;
  display: flex;
  justify-content: center;
}
.wide .art {
  flex: none;
}
.art > :deep(.art) {
  width: auto;
  max-width: 100%;
  aspect-ratio: 2 / 3;
}
.info {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
  min-height: 0;
}
/* what describes the title gives way when there is no room, but the buttons stay */
.mid {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  overflow: hidden;
}
@container (max-height: 270px) {
  .count {
    display: none;
  }
}
@container (max-height: 215px) {
  .rating {
    display: none;
  }
  h3 {
    -webkit-line-clamp: 2;
    line-clamp: 2;
  }
}
@container (max-height: 170px) {
  .meta {
    display: none;
  }
}
@container (max-width: 260px) {
  h3,
  .banner h3 {
    font-size: 0.9rem;
  }
  .wrap.banner {
    padding: 12px;
  }
  /* too narrow for two buttons side by side */
  .buttons {
    flex-direction: column;
    gap: 6px;
  }
  .buttons button,
  .buttons .open {
    flex: none;
    padding: 6px 8px;
    font-size: 0.76rem;
  }
}
.wrap:not(.wide):not(.banner) .mid {
  display: none;
}
.wide .info,
.banner .info {
  flex: 1;
}
.banner .info {
  max-width: min(520px, 100%);
  color: var(--ui-on-art);
}
.kind {
  --kind: var(--ui-accent);
  align-self: flex-start;
  padding: 2px 8px;
  white-space: nowrap;
  line-height: 1.2;
  border: 1px solid color-mix(in srgb, var(--kind) 45%, transparent);
  border-radius: 6px;
  background: color-mix(in srgb, var(--ui-scrim-base) 55%, transparent);
  color: var(--kind);
  font-size: 0.62rem;
  font-weight: 700;
  letter-spacing: 0.07em;
  text-transform: uppercase;
}
.kind-game {
  --kind: var(--ui-kind-game);
}
.kind-movie {
  --kind: var(--ui-kind-movie);
}
.kind-tv {
  --kind: var(--ui-kind-tv);
}
.kind-anime {
  --kind: var(--ui-kind-anime);
}
h3 {
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  font-size: 1rem;
  line-height: 1.2;
}
.banner h3 {
  font-size: clamp(1rem, 1.6vw, 1.3rem);
  font-weight: 800;
}
.meta,
.rating,
.count {
  margin: 0;
  color: var(--ui-dim);
  font-size: 0.82rem;
}
.banner .meta,
.banner .rating {
  color: color-mix(in srgb, var(--ui-on-art) 80%, transparent);
}
.count {
  color: var(--ui-faint);
  font-size: 0.74rem;
}
.banner .count {
  color: color-mix(in srgb, var(--ui-on-art) 55%, transparent);
}
.grow {
  flex: 1;
}
.buttons {
  flex: none;
  display: flex;
  gap: 8px;
}
.banner .buttons {
  max-width: 320px;
}
button,
.open {
  flex: 1;
  min-width: 0;
  padding: 8px 12px;
  white-space: nowrap;
  border-radius: var(--ui-radius-control);
  font: inherit;
  font-size: 0.82rem;
  font-weight: 700;
  line-height: 1.2;
  text-align: center;
  text-decoration: none;
  cursor: pointer;
}
button {
  border: 1px solid var(--ui-border-strong);
  background: color-mix(in srgb, var(--ui-scrim-base) 40%, var(--ui-surface));
  color: var(--ui-text);
}
button:hover:not(:disabled) {
  border-color: var(--ui-accent-line);
}
button:disabled {
  opacity: 0.5;
  cursor: default;
}
.open {
  border: 1px solid var(--ui-accent);
  background: var(--ui-accent);
  color: var(--ui-on-accent);
}
.none {
  display: grid;
  place-content: center;
  gap: 4px;
  width: 100%;
  padding: 10px;
  border: 1px dashed var(--ui-border);
  border-radius: var(--ui-radius-row);
  color: var(--ui-dim);
  font-size: 0.82rem;
  text-align: center;
}
.none strong {
  color: var(--ui-text);
}
</style>
