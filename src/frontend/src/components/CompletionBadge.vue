<script setup lang="ts">
import { computed } from "vue";
import type {
  BadgeStyle,
  BadgePlacement,
} from "../services/appearanceSettings";
import { contrastRatio } from "../services/uiPalette";

const props = defineProps<{
  badgeStyle: BadgeStyle;
  placement: BadgePlacement;
  color: string;
  imageUrl?: string | null;
}>();
const colors = computed(() => {
  const color = /^#[0-9a-f]{6}$/i.test(props.color) ? props.color : "#e5e4e2";
  return {
    "--badge-color": color,
    "--badge-ink":
      contrastRatio(color, "#ffffff") >= contrastRatio(color, "#000000")
        ? "#ffffff"
        : "#000000",
  };
});
</script>

<template>
  <span
    class="completion-badge"
    :class="[badgeStyle, placement]"
    :style="colors"
    aria-label="Mastered game"
  >
    <span class="badge-face">
      <img v-if="imageUrl" :src="imageUrl" alt="" />
      <svg
        v-else
        viewBox="0 0 24 24"
        width="18"
        height="18"
        fill="currentColor"
        aria-hidden="true"
      >
        <path
          d="M12 2l2.4 6.6L21 9l-5 4.6L17.4 21 12 17.3 6.6 21 8 13.6 3 9l6.6-.4z"
        />
      </svg>
    </span>
  </span>
</template>

<style scoped>
.completion-badge {
  position: absolute;
  z-index: 3;
  width: 32px;
  height: 32px;
  color: var(--badge-color);
  pointer-events: none;
}
.top-left {
  top: 8px;
  left: 8px;
}
.top-right {
  top: 8px;
  right: 8px;
}
.bottom-left {
  bottom: 8px;
  left: 8px;
}
.bottom-right {
  bottom: 8px;
  right: 8px;
}
.badge-face {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
}
.badge-face img {
  width: 22px;
  height: 22px;
  object-fit: contain;
}
.corner_badge {
  background: var(--ui-surface);
  border-radius: 50%;
  border: 1px solid color-mix(in srgb, var(--badge-color) 60%, var(--ui-border));
}
.ribbon {
  width: 36px;
  height: 54px;
  color: var(--badge-ink);
  filter: drop-shadow(0 2px 3px #0005);
}
.ribbon .badge-face {
  background: linear-gradient(
    90deg,
    color-mix(in srgb, var(--badge-color) 85%, #000),
    var(--badge-color) 30%,
    var(--badge-color) 70%,
    color-mix(in srgb, var(--badge-color) 85%, #000)
  );
  clip-path: polygon(0 0, 100% 0, 100% 100%, 50% 80%, 0 100%);
  padding-bottom: 12px;
  box-sizing: border-box;
}
.ribbon::before {
  content: "";
  position: absolute;
  width: 8px;
  height: 8px;
  background: color-mix(in srgb, var(--badge-color) 55%, #000);
  top: 0;
  left: -8px;
  clip-path: polygon(100% 0, 100% 100%, 0 100%);
}
.ribbon.top-left,
.ribbon.top-right {
  top: 0;
}
.ribbon.bottom-left,
.ribbon.bottom-right {
  bottom: 0;
}
.ribbon.top-left::before,
.ribbon.bottom-left::before {
  left: auto;
  right: -8px;
  transform: scaleX(-1);
}
.ribbon.bottom-left .badge-face,
.ribbon.bottom-right .badge-face {
  clip-path: polygon(0 0, 50% 20%, 100% 0, 100% 100%, 0 100%);
  padding-top: 12px;
  padding-bottom: 0;
}
.ribbon.bottom-left::before,
.ribbon.bottom-right::before {
  top: auto;
  bottom: 0;
  transform: scaleY(-1);
}
.ribbon.bottom-left::before {
  transform: scale(-1);
}
</style>
