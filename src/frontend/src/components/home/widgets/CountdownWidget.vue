<script setup lang="ts">
// A countdown to a day you choose: a release, a trip, anything. It counts days,
// and hours once it is under two days away, and says how long ago once it is past.
import { computed } from "vue";
import WidgetFrame from "../WidgetFrame.vue";
import { useNow } from "../../../home/clock";
import type { WidgetProps } from "../../../home/registry";

const props = defineProps<WidgetProps>();
const now = useNow();

const label = computed(() => String(props.settings.label ?? "").trim());
const target = computed(() => {
  if (props.sample) return Date.now() + 17 * 86_400_000 + 3 * 3_600_000;
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(props.settings.date ?? ""));
  return m
    ? new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])).getTime()
    : 0;
});

const view = computed(() => {
  if (!target.value) return null;
  const diff = target.value - now.value;
  const abs = Math.abs(diff);
  const days = Math.floor(abs / 86_400_000);
  const hours = Math.floor((abs % 86_400_000) / 3_600_000);
  const mins = Math.floor((abs % 3_600_000) / 60_000);
  if (diff <= 0 && abs < 86_400_000)
    return { big: "Today", unit: "", note: "" };
  if (diff > 0 && abs < 2 * 86_400_000)
    return { big: `${days * 24 + hours}`, unit: "hours", note: `${mins} min` };
  return {
    big: String(days),
    unit: days === 1 ? "day" : "days",
    note: diff > 0 ? "to go" : "ago",
  };
});
const dateText = computed(() =>
  target.value
    ? new Date(target.value).toLocaleDateString(undefined, {
        weekday: "short",
        month: "long",
        day: "numeric",
        year: "numeric",
      })
    : "",
);
</script>

<template>
  <WidgetFrame :title="label || 'Countdown'" surface :sample="sample">
    <div v-if="view" class="count">
      <div class="big">
        <strong>{{ view.big }}</strong>
        <span v-if="view.unit">{{ view.unit }}</span>
      </div>
      <p v-if="view.note" class="note">{{ view.note }}</p>
      <p class="date">{{ dateText }}</p>
    </div>
    <div v-else class="none">
      <strong>No date yet</strong>
      <span>Pick one in this widget's settings.</span>
    </div>
  </WidgetFrame>
</template>

<style scoped>
.count {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
  height: 100%;
}
.big {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.big strong {
  font-size: clamp(2rem, 11cqw, 3.6rem);
  font-weight: 800;
  line-height: 1;
  font-variant-numeric: tabular-nums;
  color: var(--ui-accent);
}
.big span {
  font-size: 1rem;
  font-weight: 700;
}
.note,
.date {
  margin: 0;
  color: var(--ui-dim);
  font-size: 0.84rem;
}
.date {
  color: var(--ui-faint);
  font-size: 0.78rem;
}
.none {
  display: grid;
  place-content: center;
  gap: 4px;
  height: 100%;
  text-align: center;
  color: var(--ui-dim);
  font-size: 0.84rem;
}
.none strong {
  color: var(--ui-text);
}
</style>
