<script setup lang="ts">
import { computed } from "vue";
import WidgetFrame from "../WidgetFrame.vue";
import type { WidgetProps } from "../../../home/registry";

const props = defineProps<WidgetProps>();

// a label and a small line icon for each place
const PLACES: Record<string, { label: string; icon: string }> = {
  "/games": {
    label: "Games",
    icon: "M6 9h12a3 3 0 0 1 3 3v3a3 3 0 0 1-5.2 2L14 15h-4l-1.8 2A3 3 0 0 1 3 15v-3a3 3 0 0 1 3-3Z M8 11v3 M6.5 12.5h3 M15.5 12h.01 M17.5 13.5h.01",
  },
  "/movies": {
    label: "Movies",
    icon: "M4 5h16v14H4Z M8 5v14 M16 5v14 M4 9h4 M4 15h4 M16 9h4 M16 15h4",
  },
  "/tv": {
    label: "TV",
    icon: "M3 7h18v12H3Z M8 3l4 4 4-4",
  },
  "/anime": {
    label: "Anime",
    icon: "M12 3l2.4 5 5.6.8-4 4 1 5.6-5-2.7-5 2.7 1-5.6-4-4 5.6-.8Z",
  },
  "/calendar": {
    label: "Calendar",
    icon: "M3 5h18v16H3z M3 10h18 M8 3v4 M16 3v4",
  },
  "/statistics": {
    label: "Statistics",
    icon: "M4 20V10 M11 20V4 M18 20v-7",
  },
  "/games/collections": {
    label: "Game collections",
    icon: "M4 7h16v12H4Z M7 4h10 M9 2h6",
  },
  "/media/collections": {
    label: "Media lists",
    icon: "M4 6h16 M4 12h16 M4 18h10",
  },
  "/notifications": {
    label: "Notifications",
    icon: "M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9 M13.7 21a2 2 0 0 1-3.4 0",
  },
  "/settings": {
    label: "Settings",
    icon: "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z M19 12a7 7 0 0 0-.1-1.2l2-1.5-2-3.4-2.3 1a7 7 0 0 0-2-1.2L14.2 3h-4l-.4 2.7a7 7 0 0 0-2 1.2l-2.3-1-2 3.4 2 1.5A7 7 0 0 0 5 12c0 .4 0 .8.1 1.2l-2 1.5 2 3.4 2.3-1a7 7 0 0 0 2 1.2l.4 2.7h4l.4-2.7a7 7 0 0 0 2-1.2l2.3 1 2-3.4-2-1.5c.1-.4.1-.8.1-1.2Z",
  },
};

const links = computed(() =>
  (Array.isArray(props.settings.links)
    ? (props.settings.links as string[])
    : []
  )
    .filter((to) => PLACES[to])
    .map((to) => ({ to, ...PLACES[to] })),
);
</script>

<template>
  <WidgetFrame title="Quick links" :sample="sample">
    <nav v-if="links.length" class="links" aria-label="Quick links">
      <component
        :is="sample ? 'span' : 'router-link'"
        v-for="l in links"
        :key="l.to"
        :to="sample ? undefined : l.to"
        class="link"
      >
        <svg
          viewBox="0 0 24 24"
          width="20"
          height="20"
          fill="none"
          stroke="currentColor"
          stroke-width="1.7"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <path :d="l.icon" />
        </svg>
        <span>{{ l.label }}</span>
      </component>
    </nav>
    <div v-else class="none">
      Choose the links to show in this widget's settings.
    </div>
  </WidgetFrame>
</template>

<style scoped>
.links {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(120px, 1fr);
  gap: 10px;
  height: 100%;
  overflow-x: auto;
  scrollbar-width: thin;
}
.link {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 8px 14px;
  border: 1px solid var(--ui-border-soft);
  border-radius: var(--ui-radius-card);
  background: linear-gradient(
    160deg,
    var(--ui-accent-soft),
    var(--ui-surface) 70%
  );
  color: var(--ui-text);
  font-size: 0.9rem;
  font-weight: 700;
  text-decoration: none;
  white-space: nowrap;
  transition: border-color 0.15s;
}
.link svg {
  color: var(--ui-accent);
}
a.link:hover {
  border-color: var(--ui-accent-line);
}
.none {
  display: grid;
  place-content: center;
  height: 100%;
  color: var(--ui-dim);
  font-size: 0.85rem;
}
</style>
