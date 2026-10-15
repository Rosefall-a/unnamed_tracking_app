<script setup lang="ts">
import { computed, ref } from "vue";
import WidgetFrame from "../WidgetFrame.vue";
import { ago, ensure, homeData, routeFor } from "../../../home/data";
import { markAllNotificationsRead } from "../../../services/notifications";
import { sampleNotifications } from "../../../home/samples";
import type { WidgetProps } from "../../../home/registry";

const props = defineProps<WidgetProps>();

const marking = ref(false);
const unread = computed(() => homeData.notifications.value?.unread ?? 0);
// reads them all on the server, then fetches the list again
async function markAll() {
  marking.value = true;
  try {
    await markAllNotificationsRead();
    await ensure("notifications", true);
  } finally {
    marking.value = false;
  }
}

const items = computed(() => {
  const count = Number(props.settings.count) || 6;
  if (props.sample) return sampleNotifications(count);
  return (homeData.notifications.value?.items ?? [])
    .filter((n) => !props.settings.unreadOnly || !n.read)
    .slice(0, count);
});
</script>

<template>
  <WidgetFrame
    title="Notifications"
    surface
    :sample="sample"
    :link="{ to: '/notifications', label: 'All' }"
  >
    <template #actions>
      <button
        v-if="!sample && unread > 0"
        type="button"
        class="markall"
        :disabled="marking"
        @click="markAll"
      >
        Mark all read
      </button>
    </template>
    <ul v-if="items.length" class="list">
      <li v-for="n in items" :key="n.id">
        <component
          :is="sample ? 'div' : 'router-link'"
          :to="sample ? undefined : routeFor(n.mediaType, n.mediaId)"
          class="row"
        >
          <span
            class="dot"
            :class="{ unread: !n.read }"
            aria-hidden="true"
          ></span>
          <span class="thumb">
            <img v-if="n.posterUrl" :src="n.posterUrl" alt="" loading="lazy" />
            <span v-else>{{ n.title.charAt(0) }}</span>
          </span>
          <span class="words">
            <strong>{{ n.title }}</strong>
            <small>{{ n.body }}</small>
          </span>
          <span class="when">{{ ago(n.eventAt * 1000) }}</span>
        </component>
      </li>
    </ul>
    <div v-else class="empty">
      <strong>{{ loading ? "Loading" : "You are up to date" }}</strong>
      <span v-if="!loading">New episodes, seasons and releases show here.</span>
    </div>
  </WidgetFrame>
</template>

<style scoped>
.markall {
  padding: 2px 9px;
  border: 1px solid var(--ui-border);
  border-radius: 999px;
  background: transparent;
  color: var(--ui-dim);
  font: inherit;
  font-size: 0.72rem;
  font-weight: 600;
  cursor: pointer;
}
.markall:hover:not(:disabled) {
  border-color: var(--ui-accent-line);
  color: var(--ui-text);
}
.list {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 5px 6px;
  border-radius: var(--ui-radius-control);
  color: var(--ui-text);
  text-decoration: none;
}
a.row:hover {
  background: var(--ui-surface-2);
}
.dot {
  flex: none;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: transparent;
}
.dot.unread {
  background: var(--ui-accent);
}
.thumb {
  flex: none;
  display: grid;
  place-items: center;
  width: 30px;
  height: 42px;
  overflow: hidden;
  border-radius: 5px;
  background: var(--ui-surface-3);
  color: var(--ui-dim);
  font-weight: 800;
}
.thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.words {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.86rem;
}
small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--ui-dim);
  font-size: 0.76rem;
}
.when {
  flex: none;
  color: var(--ui-faint);
  font-size: 0.72rem;
}
.empty {
  display: grid;
  place-content: center;
  gap: 4px;
  height: 100%;
  text-align: center;
  color: var(--ui-dim);
  font-size: 0.84rem;
}
.empty strong {
  color: var(--ui-text);
}
</style>
