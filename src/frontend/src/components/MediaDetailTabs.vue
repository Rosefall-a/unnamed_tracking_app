<script setup lang="ts" generic="K extends string">
// The row of tabs under a Movie, TV or Anime hero.
defineProps<{
  tabs: { key: K; label: string }[];
  active: K;
}>();

const emit = defineEmits<{
  select: [key: K];
}>();
</script>

<template>
  <div class="tabbar-wrap">
    <div class="tabbar">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        type="button"
        class="tab-btn"
        :class="{ active: active === tab.key }"
        @click="emit('select', tab.key)"
      >
        {{ tab.label }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.tabbar-wrap {
  max-width: 1180px;
  margin: 22px auto 0;
  padding: 0 24px;
}

.tabbar {
  display: flex;
  gap: 4px;
  background: var(--ui-surface);
  border-radius: var(--ui-radius-row);
  width: fit-content;
  max-width: 100%;
  overflow-x: auto;
  padding: 5px;
}

.tab-btn {
  flex-shrink: 0;
  white-space: nowrap;
  background: transparent;
  border: none;
  color: var(--ui-dim);
  font-family: inherit;
  font-size: 0.84rem;
  font-weight: 600;
  padding: 8px 18px;
  border-radius: var(--ui-radius-control);
  cursor: pointer;
}

.tab-btn.active {
  background: var(--ui-accent);
  color: var(--ui-on-accent);
}
.tabbar {
  max-width: 100%;
}
.tab-btn {
  min-height: var(--ui-control-height);
}
.tabbar-wrap {
  padding-inline: var(--ui-edge-left) var(--ui-edge-right);
}
</style>
