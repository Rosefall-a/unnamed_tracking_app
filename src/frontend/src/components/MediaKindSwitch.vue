<script setup lang="ts">
// The pill switcher between the 5 Media-section pages — Movies/TV/Anime
// already had this (MediaLibraryView.vue's own "kind-switch"); pulled
// out into a shared component so Calendar and Lists are reachable from
// Movies/TV/Anime in one click, and vice versa, instead of only through
// the sidebar's nested Media submenu. Kept as two visually separate pill
// groups rather than one five-way row — Movies/TV/Anime are library
// switches (same page, different data source), Calendar/Lists are
// different pages entirely, and the gap between the groups says so.
//
// No Stats entry here — each library page already has its own Stats
// tab (List/Shelf/Board/Stats). A second "Stats" button here duplicated
// it instead of surfacing something new.
defineProps<{
  active: "movie" | "tv" | "anime" | "calendar" | "lists";
}>();
</script>

<template>
  <div class="kind-switch-row">
    <div class="kind-switch">
      <RouterLink to="/movies" class="kind-tab" :class="{ active: active === 'movie' }">
        Movies
      </RouterLink>
      <RouterLink to="/tv" class="kind-tab" :class="{ active: active === 'tv' }">
        TV Shows
      </RouterLink>
      <RouterLink to="/anime" class="kind-tab" :class="{ active: active === 'anime' }">
        Anime
      </RouterLink>
    </div>
    <div class="kind-switch">
      <RouterLink to="/calendar" class="kind-tab" :class="{ active: active === 'calendar' }">
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="4" width="18" height="18" rx="2" />
          <line x1="3" y1="10" x2="21" y2="10" />
          <line x1="8" y1="2" x2="8" y2="6" />
          <line x1="16" y1="2" x2="16" y2="6" />
        </svg>
        Calendar
      </RouterLink>
      <RouterLink to="/lists" class="kind-tab" :class="{ active: active === 'lists' }">
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="8" y1="6" x2="21" y2="6" />
          <line x1="8" y1="12" x2="21" y2="12" />
          <line x1="8" y1="18" x2="21" y2="18" />
          <line x1="3" y1="6" x2="3.01" y2="6" />
          <line x1="3" y1="12" x2="3.01" y2="12" />
          <line x1="3" y1="18" x2="3.01" y2="18" />
        </svg>
        Lists
      </RouterLink>
    </div>
  </div>
</template>

<style scoped>
.kind-switch-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}
.kind-switch {
  display: inline-flex;
  gap: 4px;
  background: #1a1a1a;
  border-radius: 10px;
  padding: 4px;
  flex-wrap: wrap;
}
.kind-tab {
  background: transparent;
  border: none;
  color: #9c9c9c;
  display: flex;
  align-items: center;
  gap: 6px;
  justify-content: center;
  height: 30px;
  box-sizing: border-box;
  font-family: inherit;
  font-size: 0.8rem;
  font-weight: 700;
  padding: 0 16px;
  border-radius: 7px;
  cursor: pointer;
  text-decoration: none;
  transition:
    background 0.15s ease,
    color 0.15s ease;
}
.kind-tab:hover {
  color: #f2f2f2;
}
.kind-tab.active {
  background: #d68a34;
  color: #14100a;
}
</style>
