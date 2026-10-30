<script setup lang="ts">
import { computed } from "vue";
import WidgetFrame from "../WidgetFrame.vue";
import ArtRail from "../ArtRail.vue";
import { titlesOf } from "../../../home/data";
import { airBadge, asKinds, libraryLink, toRail } from "../../../home/rail";
import { useNow } from "../../../home/clock";
import { sampleTitles } from "../../../home/samples";
import { sortTitles } from "../../../home/select";
import type { WidgetProps } from "../../../home/registry";

const props = defineProps<WidgetProps>();
const now = useNow();

const shape = computed(() => (props.variant === "wide" ? "wide" : "poster"));
const titles = computed(() => {
  const count = Number(props.settings.count) || 16;
  if (props.sample) return sampleTitles(count, asKinds(props.settings.kinds));
  const active = titlesOf(props.settings.kinds).filter(
    (t) => t.group === "active",
  );
  return sortTitles(active, props.settings.sort, "updated").slice(0, count);
});
const items = computed(() =>
  titles.value.map((t) => {
    return {
      ...toRail(t, shape.value),
      progress: props.settings.showProgress === false ? null : t.progress,
      badge:
        props.settings.showCountdown === false
          ? null
          : airBadge(t.key, now.value),
    };
  }),
);
</script>

<template>
  <WidgetFrame
    title="Continue"
    :sample="sample"
    :link="libraryLink(settings.kinds)"
  >
    <ArtRail
      :items="items"
      :shape="shape"
      :loading="loading"
      :sample="sample"
      empty-title="Nothing in progress"
      empty-hint="Start a game or a show and it appears here."
      empty-to="/games"
      empty-action="Browse games"
    />
  </WidgetFrame>
</template>
