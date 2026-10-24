<script setup lang="ts">
// Titles you added around this time in earlier years. A day is often empty, so
// the span can be widened to the week or the month.
import { computed } from "vue";
import WidgetFrame from "../WidgetFrame.vue";
import ArtRail from "../ArtRail.vue";
import type { RailItem } from "../ArtRail.vue";
import { nearestAnniversary } from "../../../home/anniversary";
import { titlesOf } from "../../../home/data";
import { libraryLink } from "../../../home/rail";
import { sampleTitles } from "../../../home/samples";
import type { WidgetProps } from "../../../home/registry";

const props = defineProps<WidgetProps>();

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
      if (span.value === "month") {
        const years = now.getFullYear() - d.getFullYear();
        if (years < 1 || (back > 0 && years > back)) return false;
        return d.getMonth() === now.getMonth();
      }
      // the anniversary has to fall in a later year than the day it was added
      const { days, years } = nearestAnniversary(d, now);
      if (years < 1 || (back > 0 && years > back)) return false;
      return span.value === "day" ? days === 0 : Math.abs(days) <= 3;
    })
    // the closest date to today first, then the most recent year
    .sort((a, b) => {
      const da = Math.abs(nearestAnniversary(new Date(a.addedAt), now).days);
      const db = Math.abs(nearestAnniversary(new Date(b.addedAt), now).days);
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
      subtitle: `${ago(
        span.value === "month"
          ? now.getFullYear() - d.getFullYear()
          : nearestAnniversary(d, now).years,
      )} · ${when}`,
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
