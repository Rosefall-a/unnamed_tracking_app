<script setup lang="ts">
// The artwork part of the add form, folded away so the form stays short. The
// choices are only fetched once it is opened, so a quick add that never opens
// it makes no extra requests.
import { computed, ref } from "vue";
import GameArtPicker from "./GameArtPicker.vue";

const props = defineProps<{
  title: string;
  provider: string;
  providerId: string;
  currentCover: string | null;
  // what the picture already in place is called; the search list's, when adding
  currentLabel?: string;
}>();
const cover = defineModel<string | null>("cover", { required: true });
const banner = defineModel<string | null>("banner", { required: true });

const opened = ref(false);

const summary = computed(() => {
  const parts = [
    cover.value
      ? "Cover picked"
      : `Cover ${props.currentLabel ? props.currentLabel.toLowerCase() : "from search"}`,
  ];
  if (banner.value) parts.push("banner picked");
  return parts.join(", ");
});
</script>

<template>
  <details class="art-section" @toggle="opened = true">
    <summary>
      <span class="art-section-title">Artwork</span>
      <span class="art-section-summary">{{ summary }}</span>
    </summary>
    <GameArtPicker
      v-if="opened"
      v-model:cover="cover"
      v-model:banner="banner"
      :title="title"
      :provider="provider"
      :provider-id="providerId"
      :current-cover="currentCover"
      :current-label="currentLabel"
    />
  </details>
</template>

<style scoped>
.art-section {
  grid-column: 1 / -1;
  min-width: 0;
  border: 1px solid var(--ui-border);
  border-radius: 10px;
  background: var(--ui-surface);
  padding: 0 12px;
}
.art-section[open] {
  padding-bottom: 10px;
}
.art-section summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 0;
  cursor: pointer;
  list-style: none;
}
.art-section summary::-webkit-details-marker {
  display: none;
}
.art-section summary::after {
  content: "\25BE";
  color: var(--ui-dim-2);
  transition: transform 0.12s ease;
}
.art-section[open] summary::after {
  transform: rotate(180deg);
}
.art-section summary:focus-visible {
  outline: 2px solid var(--ui-accent);
  outline-offset: 2px;
  border-radius: 6px;
}
.art-section-title {
  font-size: 0.86rem;
  font-weight: 600;
}
.art-section-summary {
  margin-left: auto;
  font-size: 0.75rem;
  color: var(--ui-dim-2);
}
</style>
