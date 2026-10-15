<script setup lang="ts">
// What is coming out, and what just did: games, films, shows and anime in your
// library with a release date, soonest first. Used for "Upcoming releases" and
// for "Upcoming game releases", which only differ in what they start with.
import { computed } from "vue";
import WidgetFrame from "../WidgetFrame.vue";
import ArtRail from "../ArtRail.vue";
import type { RailItem } from "../ArtRail.vue";
import { titlesOf } from "../../../home/data";
import { asKinds, libraryLink, toRail } from "../../../home/rail";
import { sampleTitles } from "../../../home/samples";
import type { WidgetProps } from "../../../home/registry";

const props = defineProps<WidgetProps>();

const DAY = 86_400_000;
const shape = computed(() => (props.variant === "wide" ? "wide" : "poster"));

function dayStart(t: number): number {
  const d = new Date(t);
  return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
}

function when(release: number, today: number): { label: string; days: number } {
  const days = Math.round((release - today) / DAY);
  const date = new Date(release).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year:
      new Date(release).getFullYear() === new Date(today).getFullYear()
        ? undefined
        : "numeric",
  });
  if (days === 0) return { label: `${date} · today`, days };
  if (days === 1) return { label: `${date} · tomorrow`, days };
  if (days > 1) return { label: `${date} · in ${days} days`, days };
  if (days === -1) return { label: `${date} · yesterday`, days };
  return { label: `${date} · ${-days} days ago`, days };
}

const items = computed<RailItem[]>(() => {
  const count = Number(props.settings.count) || 14;
  const today = dayStart(Date.now());
  if (props.sample)
    return sampleTitles(Math.min(count, 8), asKinds(props.settings.kinds)).map(
      (t) => ({
        ...toRail(t, shape.value),
        subtitle: when(t.release, today).label,
        badge: `In ${when(t.release, today).days} days`,
      }),
    );
  const mode = String(props.settings.when);
  const within = Number(props.settings.within) || 0;
  const scope = String(props.settings.scope);
  const list = titlesOf(props.settings.kinds).filter((t) => {
    if (!t.release) return false;
    if (scope === "wishlist" && t.group !== "wishlist") return false;
    if (scope === "waiting" && t.group !== "wishlist" && t.group !== "queue")
      return false;
    const days = Math.round((t.release - today) / DAY);
    const upcoming = days >= 0 && (!within || days <= within);
    const recent = days < 0 && days >= -(within || 30);
    if (mode === "upcoming") return upcoming;
    if (mode === "recent") return recent;
    return upcoming || recent;
  });
  const soon = list
    .filter((t) => t.release >= today)
    .sort((a, b) => a.release - b.release);
  const past = list
    .filter((t) => t.release < today)
    .sort((a, b) => b.release - a.release);
  return [...soon, ...past].slice(0, count).map((t) => {
    const w = when(t.release, today);
    return {
      ...toRail(t, shape.value),
      subtitle: w.label,
      badge:
        w.days >= 0 ? (w.days === 0 ? "Out today" : `In ${w.days} days`) : null,
    };
  });
});

const heading = computed(() => {
  const mode = String(props.settings.when);
  const kinds = asKinds(props.settings.kinds);
  const noun =
    kinds.length === 1 && kinds[0] === "game" ? "game releases" : "releases";
  if (mode === "recent") return `Recent ${noun}`;
  if (mode === "both") return `${noun.charAt(0).toUpperCase()}${noun.slice(1)}`;
  return `Upcoming ${noun}`;
});
</script>

<template>
  <WidgetFrame
    :title="heading"
    :sample="sample"
    :link="libraryLink(settings.kinds)"
  >
    <ArtRail
      :items="items"
      :shape="shape"
      :loading="loading"
      :sample="sample"
      empty-title="No release dates to show"
      empty-hint="Titles in your library with a release date in this window show here. Widen it, or include more kinds, using the controls above."
    />
  </WidgetFrame>
</template>
