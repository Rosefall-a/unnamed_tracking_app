<script setup lang="ts">
// Titles you added around this time in earlier years. A day is often empty, so
// the span can be widened to the week or the month.
import { computed } from "vue";
import WidgetFrame from "../WidgetFrame.vue";
import ArtRail from "../ArtRail.vue";
import type { RailItem } from "../ArtRail.vue";
import { titlesOf } from "../../../home/data";
import { libraryLink } from "../../../home/rail";
import { sampleTitles } from "../../../home/samples";
import type { WidgetProps } from "../../../home/registry";

const props = defineProps<WidgetProps>();

const DAY = 86_400_000;
const span = computed(() => String(props.settings.span));
const shape = computed(() => (props.variant === "wide" ? "wide" : "poster"));

const HEADING: Record<string, string> = {
  day: "On this day",
  week: "This week in past years",
  month: "This month in past years",
};

function ago(years: number): string {
  return `${years} year${years === 1 ? "" : "s"} ago`;
}

// whole days between today and the same date in the added year
function daysFromToday(added: Date, now: Date): number {
  const same = new Date(now.getFullYear(), added.getMonth(), added.getDate());
  return Math.round(
    (same.getTime() -
      new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()) /
      DAY,
  );
}

const items = computed<RailItem[]>(() => {
  const count = Number(props.settings.count) || 12;
  if (props.sample)
    return sampleTitles(Math.min(count, 6)).map((t, i) => ({
      key: t.key,
      title: t.title,
      art: null,
      subtitle: `Added ${ago(i + 1)}`,
    }));
  const now = new Date();
  const back = Number(props.settings.yearsBack) || 0;
  const matched = titlesOf(props.settings.kinds)
    .filter((t) => {
      if (!t.addedAt) return false;
      const d = new Date(t.addedAt);
      const years = now.getFullYear() - d.getFullYear();
      if (years < 1 || (back > 0 && years > back)) return false;
      if (span.value === "month") return d.getMonth() === now.getMonth();
      const gap = Math.abs(daysFromToday(d, now));
      return span.value === "day" ? gap === 0 : gap <= 3;
    })
    // the closest date to today first, then the most recent year
    .sort((a, b) => {
      const da = Math.abs(daysFromToday(new Date(a.addedAt), now));
      const db = Math.abs(daysFromToday(new Date(b.addedAt), now));
      return da - db || b.addedAt - a.addedAt;
    })
    .slice(0, count);
  return matched.map((t) => {
    const d = new Date(t.addedAt);
    const when = d.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
    });
    return {
      key: t.key,
      title: t.title,
      art: shape.value === "wide" ? (t.wide ?? t.art) : t.art,
      subtitle: `${ago(now.getFullYear() - d.getFullYear())} · ${when}`,
      to: t.to,
    };
  });
});

const emptyHint = computed(
  () =>
    ({
      day: "Titles you added on today's date in earlier years show here. Try widening it to the week.",
      week: "Titles you added within a few days of today's date in earlier years show here.",
      month: "Titles you added in this month of earlier years show here.",
    })[span.value] ?? "",
);
</script>

<template>
  <WidgetFrame
    :title="HEADING[span] ?? 'Throwback'"
    :sample="sample"
    :link="libraryLink(settings.kinds)"
  >
    <ArtRail
      :items="items"
      :shape="shape"
      :loading="loading"
      :sample="sample"
      empty-title="Nothing from past years yet"
      :empty-hint="emptyHint"
    />
  </WidgetFrame>
</template>
