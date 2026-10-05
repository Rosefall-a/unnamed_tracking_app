<script setup lang="ts">
defineProps<{ name: string; size?: number }>();
const paths: Record<string, string> = {
  home: "M3 11l9-8 9 8 M5 10v10h5v-6h4v6h5V10",
  games:
    "M6 7h12l3 11c.5 2-2 3-3 1l-2-3H8l-2 3c-1 2-3.5 1-3-1L6 7Z M7 10v4 M5 12h4 M16 11h.01 M18 13h.01",
  collections: "M3 7l9-4 9 4-9 4-9-4Z M3 12l9 4 9-4 M3 17l9 4 9-4",
  folder: "M3 7V5h6l3 3h9v12H3V7Z",
  cards: "M3 5h18v15H3z M3 10h18 M7 15h4",
  sets: "M6 3h15v14 M3 7h14v14H3z",
  media: "M3 5h18v15H3z M3 9h18 M7 5v4 M12 5v4 M17 5v4 M10 12l5 3-5 3z",
  tv: "M3 6h18v13H3z M8 22h8 M12 19v3 M8 2l4 4 4-4",
  anime: "M12 3l2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3Z",
  lists: "M8 6h13 M8 12h13 M8 18h13 M3 6h.01 M3 12h.01 M3 18h.01",
  bounties:
    "M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0 M17 12a5 5 0 1 1-10 0 5 5 0 0 1 10 0 M12 12h.01",
  calendar: "M3 5h18v16H3z M3 10h18 M8 3v4 M16 3v4",
  statistics: "M4 20V12 M12 20V4 M20 20v-9",
  notifications: "M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9 M10 21h4",
  upload: "M12 16V3 M7 8l5-5 5 5 M4 16v5h16v-5",
  settings: "M4 7h16 M4 17h16 M9 4v6 M15 14v6",
  account: "M20 21a8 8 0 0 0-16 0 M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0",
  admin: "M12 3l8 4v5c0 5-5 8-8 10-3-2-8-5-8-10V7l8-4Z M9 12l2 2 4-4",
  plugin: "M4 5h16v14H4z M8 9h8 M8 13h5",
  search: "M16 9a7 7 0 1 1-14 0 7 7 0 0 1 14 0 M14 14l7 7",
  menu: "M4 6h16 M4 12h16 M4 18h16",
  close: "M6 6l12 12 M18 6L6 18",
  chevron: "M9 5l7 7-7 7",
  more: "M4 12h.01 M12 12h.01 M20 12h.01",
  logout: "M9 3H3v18h6 M9 12h12 M16 7l5 5-5 5",
};
</script>

<template>
  <svg
    :width="size ?? 20"
    :height="size ?? 20"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.7"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <path :d="paths[name] ?? paths.plugin" />
  </svg>
</template>
