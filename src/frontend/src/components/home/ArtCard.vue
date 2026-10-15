<script setup lang="ts">
// One title drawn as artwork: the picture fills the card and the name sits on a
// shade over the bottom. With no picture (or a broken one) it becomes a soft
// tinted tile with the first letter, so a card is never an empty box. A kind label
// sits in the top corner; a countdown ("In 3h 20m") sits above the name, so the two
// can never land on top of each other however narrow the card is.
import { computed, ref, watch } from "vue";

const props = withDefaults(
  defineProps<{
    title: string;
    art?: string | null;
    subtitle?: string;
    // 0 to 1
    progress?: number | null;
    to?: string | null;
    // the kind label shown in a corner, for rails that mix kinds
    tag?: string | null;
    // which kind it is, which sets the label's colour
    tagKind?: string | null;
    // a made-up card in a preview: not a link, and marked as an example
    sample?: boolean;
    // a short line above the name, like a countdown
    badge?: string | null;
    // when the name sits on the artwork
    text?: "always" | "hover" | "never";
  }>(),
  {
    art: null,
    subtitle: "",
    progress: null,
    to: null,
    tag: null,
    tagKind: null,
    badge: null,
    text: "always",
  },
);

const broken = ref(false);
watch(
  () => props.art,
  () => (broken.value = false),
);
const showArt = computed(() => !!props.art && !broken.value);

// the same title always gets the same tint
const tint = computed(() => {
  let h = 0;
  for (const ch of props.title) h = (h * 31 + ch.charCodeAt(0)) % 997;
  return {
    "--tint": `${24 + (h % 26)}%`,
    "--tint-2": `${10 + ((h >> 3) % 16)}%`,
  };
});
const initial = computed(() => props.title.trim().charAt(0).toUpperCase());
const link = computed(() => (props.sample ? null : props.to));
// under a day away (no "3d" in it), a countdown is worth a stronger look
const soon = computed(
  () =>
    !!props.badge && (!/\d\s*d/.test(props.badge) || /now/i.test(props.badge)),
);
</script>

<template>
  <component
    :is="link ? 'router-link' : 'div'"
    :to="link ?? undefined"
    class="art"
    :class="[{ plain: !showArt }, `text-${text}`]"
    :style="tint"
    :title="title"
  >
    <img
      v-if="showArt"
      :src="art!"
      alt=""
      loading="lazy"
      draggable="false"
      @error="broken = true"
    />
    <span v-else class="initial" aria-hidden="true">{{ initial }}</span>
    <span v-if="tag" class="tag" :class="tagKind ? `kind-${tagKind}` : ''">
      <i class="dot" aria-hidden="true"></i>{{ tag }}
    </span>
    <span class="shade"></span>
    <span class="text">
      <span v-if="badge" class="air" :class="{ soon }">
        <i class="beat" aria-hidden="true"></i>{{ badge }}
      </span>
      <span class="name">{{ title }}</span>
      <span v-if="subtitle" class="sub">{{ subtitle }}</span>
    </span>
    <!-- the countdown is always visible: with the name hidden (or shown only on
         hover) it sits on its own, and gives way to the one in the name's block
         while that is showing -->
    <span v-if="badge && text !== 'always'" class="air alone" :class="{ soon }">
      <i class="beat" aria-hidden="true"></i>{{ badge }}
    </span>
    <span v-if="progress !== null" class="bar" aria-hidden="true">
      <span :style="{ width: `${Math.round(progress * 100)}%` }"></span>
    </span>
  </component>
</template>

<style scoped>
.art {
  position: relative;
  display: block;
  width: 100%;
  height: 100%;
  min-width: 0;
  overflow: hidden;
  isolation: isolate;
  border: 1px solid var(--ui-border-soft);
  border-radius: var(--ui-radius-row);
  background: var(--ui-surface-2);
  color: var(--ui-on-art);
  text-decoration: none;
  transition:
    border-color 0.15s,
    transform 0.2s;
}
a.art:hover {
  border-color: var(--ui-accent-line);
  transform: translateY(-2px);
}
a.art:focus-visible {
  outline: 2px solid var(--ui-accent);
  outline-offset: 2px;
}
.art img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.35s;
}
a.art:hover img {
  transform: scale(1.04);
}
.plain {
  background: linear-gradient(
    150deg,
    color-mix(in srgb, var(--ui-accent) var(--tint), var(--ui-surface-2)),
    color-mix(in srgb, var(--ui-accent) var(--tint-2), var(--ui-bg-2))
  );
}
.initial {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  padding-bottom: 18%;
  font-size: clamp(1.6rem, 6cqw, 3.2rem);
  font-weight: 800;
  color: color-mix(in srgb, var(--ui-on-art) 42%, transparent);
}
.shade {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    to top,
    color-mix(in srgb, var(--ui-scrim-base) 88%, transparent),
    color-mix(in srgb, var(--ui-scrim-base) 34%, transparent) 46%,
    transparent 72%
  );
}
.text {
  position: absolute;
  inset: auto 0 0 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 10px 10px 10px;
}
.name {
  font-size: 0.84rem;
  font-weight: 700;
  line-height: 1.2;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.sub {
  font-size: 0.72rem;
  color: color-mix(in srgb, var(--ui-on-art) 72%, transparent);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.air {
  align-self: flex-start;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 5px;
  padding: 3px 9px 3px 7px;
  border: 1px solid color-mix(in srgb, var(--ui-wash-base) 16%, transparent);
  border-radius: 999px;
  background: color-mix(in srgb, var(--ui-scrim-base) 58%, transparent);
  backdrop-filter: blur(4px);
  color: var(--ui-on-art);
  font-size: 0.68rem;
  font-weight: 700;
  line-height: 1.2;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}
.beat {
  flex: none;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--ui-dim-3);
}
/* under a day away: the dot is lit and slowly pulses */
.air.soon {
  border-color: color-mix(in srgb, var(--ui-accent) 55%, transparent);
  background: color-mix(in srgb, var(--ui-accent) 26%, var(--ui-scrim-base));
}
.air.soon .beat {
  background: var(--ui-accent-bright);
  box-shadow: 0 0 0 0 color-mix(in srgb, var(--ui-accent) 70%, transparent);
  animation: beat 1.8s ease-out infinite;
}
@keyframes beat {
  70% {
    box-shadow: 0 0 0 6px color-mix(in srgb, var(--ui-accent) 0%, transparent);
  }
  100% {
    box-shadow: 0 0 0 0 color-mix(in srgb, var(--ui-accent) 0%, transparent);
  }
}
.air.alone {
  position: absolute;
  left: 8px;
  bottom: 8px;
  margin: 0;
  transition: opacity 0.18s;
}
.text-hover:hover .air.alone,
.text-hover:focus-visible .air.alone {
  opacity: 0;
}
.tag {
  --kind: var(--ui-accent);
  position: absolute;
  top: 7px;
  left: 7px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 18px;
  padding: 0 8px 0 6px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--ui-scrim-base) 60%, transparent);
  backdrop-filter: blur(4px);
  color: var(--ui-on-art);
  font-size: 0.6rem;
  font-weight: 700;
  letter-spacing: 0.07em;
  line-height: 1;
  text-transform: uppercase;
  white-space: nowrap;
}
.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--kind);
  box-shadow: 0 0 6px color-mix(in srgb, var(--kind) 80%, transparent);
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
.text-hover .shade,
.text-hover .text {
  opacity: 0;
  transition: opacity 0.18s;
}
.text-hover:hover .shade,
.text-hover:hover .text,
.text-hover:focus-visible .shade,
.text-hover:focus-visible .text {
  opacity: 1;
}
.text-never .shade,
.text-never .text {
  display: none;
}
.bar {
  position: absolute;
  inset: auto 0 0 0;
  height: 3px;
  background: color-mix(in srgb, var(--ui-wash-base) 18%, transparent);
}
.bar span {
  display: block;
  height: 100%;
  background: var(--ui-accent);
}
@media (prefers-reduced-motion: reduce) {
  .art,
  .art img {
    transition: none;
  }
  .air.soon .beat {
    animation: none;
  }
}
</style>
