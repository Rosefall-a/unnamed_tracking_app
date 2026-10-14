<script setup lang="ts">
// A row of pictures that scrolls sideways, with an arrow at each end that
// appears only when there is more to see in that direction.
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";

const strip = ref<HTMLElement | null>(null);
const canLeft = ref(false);
const canRight = ref(false);

function update() {
  const el = strip.value;
  if (!el) return;
  canLeft.value = el.scrollLeft > 4;
  canRight.value = el.scrollLeft + el.clientWidth < el.scrollWidth - 4;
}

function scrollBy(direction: -1 | 1) {
  const el = strip.value;
  if (!el) return;
  el.scrollBy({ left: direction * el.clientWidth * 0.8, behavior: "smooth" });
}

let watcher: ResizeObserver | null = null;
let added: MutationObserver | null = null;
onMounted(async () => {
  await nextTick();
  update();
  if (strip.value && typeof ResizeObserver !== "undefined") {
    watcher = new ResizeObserver(update);
    watcher.observe(strip.value);
  }
  // options arrive after the row is drawn, and each picture loads later still
  if (strip.value && typeof MutationObserver !== "undefined") {
    added = new MutationObserver(update);
    added.observe(strip.value, { childList: true });
  }
  strip.value?.addEventListener("load", update, true);
});
onBeforeUnmount(() => {
  watcher?.disconnect();
  added?.disconnect();
  strip.value?.removeEventListener("load", update, true);
});
</script>

<template>
  <div class="strip-wrap">
    <button
      v-show="canLeft"
      type="button"
      class="strip-arrow left"
      aria-label="Scroll left"
      @click="scrollBy(-1)"
    >
      &#8249;
    </button>
    <div ref="strip" class="strip" @scroll.passive="update">
      <slot />
    </div>
    <button
      v-show="canRight"
      type="button"
      class="strip-arrow right"
      aria-label="Scroll right"
      @click="scrollBy(1)"
    >
      &#8250;
    </button>
  </div>
</template>

<style scoped>
.strip-wrap {
  position: relative;
  min-width: 0;
}
.strip {
  display: flex;
  gap: 10px;
  overflow-x: auto;
  scroll-snap-type: x proximity;
  scrollbar-width: none;
  padding: 4px 2px;
}
.strip::-webkit-scrollbar {
  display: none;
}
.strip-arrow {
  position: absolute;
  top: 50%;
  z-index: 2;
  width: 34px;
  height: 34px;
  margin-top: -17px;
  border: 1px solid #2b2b2b;
  border-radius: 50%;
  background: rgba(13, 13, 13, 0.88);
  color: #f0f0f0;
  font-size: 1.4rem;
  line-height: 1;
  cursor: pointer;
}
.strip-arrow:hover {
  border-color: #d68a34;
  color: #d68a34;
}
.strip-arrow:focus-visible {
  outline: 2px solid #d68a34;
  outline-offset: 2px;
}
.strip-arrow.left {
  left: -6px;
}
.strip-arrow.right {
  right: -6px;
}
</style>
