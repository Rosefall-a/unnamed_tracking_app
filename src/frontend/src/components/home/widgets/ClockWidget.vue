<script setup lang="ts">
// The time and the date, for a page you leave open.
import { computed } from "vue";
import WidgetFrame from "../WidgetFrame.vue";
import { useNow } from "../../../home/clock";
import type { WidgetProps } from "../../../home/registry";

const props = defineProps<WidgetProps>();
const now = useNow();

const parts = computed(() => {
  const d = new Date(now.value);
  const twelve = props.settings.format === "12h";
  const h = d.getHours();
  const hour = twelve ? h % 12 || 12 : h;
  return {
    h: twelve ? String(hour) : String(hour).padStart(2, "0"),
    m: String(d.getMinutes()).padStart(2, "0"),
    s: String(d.getSeconds()).padStart(2, "0"),
    ampm: twelve ? (h < 12 ? "AM" : "PM") : "",
  };
});
const date = computed(() =>
  new Date(now.value).toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
  }),
);
</script>

<template>
  <WidgetFrame title="Clock" surface :sample="sample">
    <div class="clock">
      <div class="time">
        <span>{{ parts.h }}</span
        ><span class="colon">:</span><span>{{ parts.m }}</span>
        <template v-if="settings.showSeconds"
          ><span class="colon">:</span
          ><span class="secs">{{ parts.s }}</span></template
        >
        <small v-if="parts.ampm">{{ parts.ampm }}</small>
      </div>
      <p v-if="settings.showDate !== false" class="date">{{ date }}</p>
    </div>
  </WidgetFrame>
</template>

<style scoped>
.clock {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
  height: 100%;
}
.time {
  display: flex;
  align-items: baseline;
  font-size: clamp(1.8rem, 9cqw, 3.4rem);
  font-weight: 800;
  line-height: 1;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.01em;
}
.colon {
  margin: 0 2px;
  color: var(--ui-accent);
}
.secs {
  color: var(--ui-dim);
  font-size: 0.6em;
}
.time small {
  margin-left: 8px;
  color: var(--ui-dim);
  font-size: 0.32em;
  font-weight: 700;
  letter-spacing: 0.08em;
}
.date {
  margin: 0;
  color: var(--ui-dim);
  font-size: 0.86rem;
}
</style>
