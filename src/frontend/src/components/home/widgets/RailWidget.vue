<script setup lang="ts">
import { computed, watch } from "vue";
import WidgetFrame from "../WidgetFrame.vue";
import ArtRail from "../ArtRail.vue";
import {
  ensureListMembers,
  homeData,
  membersOfList,
  titlesOf,
} from "../../../home/data";
import type { HomeTitle } from "../../../home/data";
import { airBadge, asKinds, libraryLink, toRail } from "../../../home/rail";
import { useNow } from "../../../home/clock";
import { sampleTitles } from "../../../home/samples";
import {
  inCollection,
  isUnfinished,
  narrow,
  sortTitles,
} from "../../../home/select";
import { RAIL_SOURCES } from "../../../home/registry";
import type { WidgetProps } from "../../../home/registry";

const props = defineProps<WidgetProps>();
const now = useNow();

const source = computed(() => String(props.settings.source));
const collection = computed(() =>
  source.value === "collection" ? String(props.settings.collection ?? "") : "",
);
// a media list's titles are fetched for the list a shelf actually shows
watch(
  collection,
  (c) => {
    if (c.startsWith("list:") && !props.sample)
      void ensureListMembers(c.slice(5));
  },
  { immediate: true },
);
const shape = computed(() => (props.variant === "wide" ? "wide" : "poster"));

const PICK: Record<string, (t: HomeTitle) => boolean> = {
  "recently-added": () => true,
  "recently-updated": () => true,
  backlog: (t) => t.group === "queue",
  wishlist: (t) => t.group === "wishlist",
  favorites: (t) => t.favorite,
  "highest-rated": (t) => t.rating !== null,
  finished: (t) => t.group === "done",
  dropped: (t) => t.group === "dropped",
  unfinished: (t) => isUnfinished(t, props.settings),
  collection: (t) =>
    inCollection(t, collection.value, membersOfList(collection.value.slice(5))),
  everything: () => true,
};
const DEFAULT_ORDER: Record<string, "added" | "updated" | "rating"> = {
  "recently-updated": "updated",
  "highest-rated": "rating",
};

const label = computed(() => {
  const c = collection.value;
  if (c.startsWith("game:")) return c.slice(5);
  if (c.startsWith("list:"))
    return (
      homeData.lists.value?.find((l) => l.id === c.slice(5))?.name ?? "List"
    );
  if (source.value === "unfinished") return "Unfinished";
  return RAIL_SOURCES.find((s) => s.value === source.value)?.label ?? "Shelf";
});

const EMPTY: Record<string, string> = {
  backlog: "Titles marked backlog or plan to watch show here.",
  wishlist: "Titles on your wishlist show here.",
  favorites: "Favorite a title with the heart and it shows here.",
  finished: "Finished titles show here.",
  dropped: "Titles you dropped show here.",
  "highest-rated": "Rate a few titles and your best show here.",
  unfinished:
    "Games you have played but not finished, and shows you are partway through, show here once you leave them for a while.",
  collection: "Pick a collection or list in this shelf's settings.",
};

const titles = computed(() => {
  const count = Number(props.settings.count) || 16;
  if (props.sample) return sampleTitles(count, asKinds(props.settings.kinds));
  const picked = narrow(
    titlesOf(props.settings.kinds).filter(
      PICK[source.value] ?? PICK["recently-added"],
    ),
    props.settings,
  );
  return sortTitles(
    picked,
    props.settings.sort,
    DEFAULT_ORDER[source.value] ?? "added",
  ).slice(0, count);
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
    :title="label"
    :sample="sample"
    :link="libraryLink(settings.kinds)"
  >
    <ArtRail
      :items="items"
      :shape="shape"
      :loading="loading"
      :sample="sample"
      :empty-title="`Nothing in ${label.toLowerCase()} yet`"
      :empty-hint="
        EMPTY[source] ?? 'Add something to your library and it shows here.'
      "
      empty-to="/games"
      empty-action="Add something"
    />
  </WidgetFrame>
</template>
