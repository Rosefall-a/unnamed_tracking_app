<script setup lang="ts">
import { computed, inject } from "vue";
import { CHROME_KEY } from "../../home/chrome";
import WidgetGear from "./WidgetGear.vue";
// The outside of every Home widget: a heading, an optional link to the full
// page, and a body that gets whatever height the grid gave it. A widget whose
// data failed to load says so here and offers a retry, so no widget has to.
const props = defineProps<{
  title: string;
  link?: { to: string; label: string } | null;
  // give the body its own panel, for lists and numbers (artwork sits bare)
  surface?: boolean;
  error?: string | null;
  sample?: boolean;
}>();

// what this widget's look options say about the heading and the background
const chrome = inject(CHROME_KEY, null);
const heading = computed(() => chrome?.value.heading.trim() || props.title);
const showHeading = computed(
  () => chrome?.value.showHeading !== false && !!heading.value,
);
const panelled = computed(() => {
  const mode = chrome?.value.panel ?? "auto";
  return mode === "auto" ? !!props.surface : mode === "panel";
});

const emit = defineEmits<{ retry: [] }>();
</script>

<template>
  <section class="wf" :class="{ surface: panelled }">
    <header v-if="showHeading" class="head">
      <h2>
        <router-link
          v-if="link && !sample"
          :to="link.to"
          class="title-link"
          :title="link.label"
        >
          {{ heading }}<span class="chev" aria-hidden="true">&#8250;</span>
        </router-link>
        <template v-else>{{ heading }}</template>
      </h2>
      <span v-if="sample" class="sample">Example</span>
      <span class="grow"></span>
      <slot name="actions" />
      <WidgetGear />
    </header>
    <div class="body">
      <div v-if="error" class="failed">
        <p>{{ error }}</p>
        <button type="button" @click="emit('retry')">Try again</button>
      </div>
      <slot v-else />
    </div>
  </section>
</template>

<style scoped>
.wf {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  color: var(--ui-text);
}
.head {
  flex: none;
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 26px;
}
.head h2 {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  letter-spacing: 0.01em;
}
.grow {
  flex: 1;
}
.sample {
  padding: 1px 8px;
  border-radius: 999px;
  background: var(--ui-accent-soft);
  color: var(--ui-accent);
  font-size: 0.66rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.title-link {
  color: inherit;
  text-decoration: none;
}
.title-link .chev {
  margin-left: 5px;
  color: var(--ui-faint);
  font-size: 1.1em;
  transition:
    color 0.15s,
    margin-left 0.15s;
}
.title-link:hover,
.title-link:focus-visible {
  color: var(--ui-accent);
}
.title-link:hover .chev {
  margin-left: 8px;
  color: var(--ui-accent);
}
.body {
  flex: 1;
  min-height: 0;
  container-type: size;
}
.surface .body {
  padding: 14px;
  overflow: auto;
  border: 1px solid var(--ui-border-soft);
  border-radius: var(--ui-radius-card);
  background: var(--ui-surface);
}
.failed {
  display: grid;
  place-content: center;
  gap: 8px;
  height: 100%;
  text-align: center;
  color: var(--ui-dim);
  font-size: 0.85rem;
}
.failed p {
  margin: 0;
}
.failed button {
  justify-self: center;
  padding: 6px 14px;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-control);
  background: transparent;
  color: var(--ui-text);
  font: inherit;
  cursor: pointer;
}
.failed button:hover {
  border-color: var(--ui-accent-line);
}
</style>
