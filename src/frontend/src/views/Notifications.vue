<script setup lang="ts">
// Every notification in one place, with the detail behind each: which
// title, what happened, and the exact time it happened (the provider's own
// air time, not when the app noticed). The sidebar group shows the latest
// few; this page is the full list with filters and per-item actions.
import { ref, computed, onMounted, watch } from "vue";
import { useRouter } from "vue-router";
import AppTopBar from "../components/AppTopBar.vue";
import SegmentedTabs from "../components/SegmentedTabs.vue";
import type { SegmentOption } from "../components/SegmentedTabs.vue";
import {
  fetchMediaNotifications,
  markNotificationRead,
  markNotificationUnread,
  markAllNotificationsRead,
  deleteMediaNotification,
} from "../services/notifications";
import type { MediaNotification } from "../services/notifications";
import { refreshMediaNotifications } from "../state/notifications";
import { useKeptAlive } from "../utils/useKeptAlive";
import { useConfirm } from "../state/dialog";
import {
  readPluginReminders,
  pluginReminderRevision,
} from "../state/pluginNotifications";
import {
  notificationPresentation,
  notificationDestination,
} from "../utils/notificationPresentation";

type Filter =
  "all" | "unread" | "episodes" | "seasons" | "releases" | "plugins";
const FILTERS: { key: Filter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "unread", label: "Unread" },
  { key: "episodes", label: "Episodes" },
  { key: "seasons", label: "Seasons" },
  { key: "releases", label: "Releases" },
  { key: "plugins", label: "Plugins" },
];

const router = useRouter();
const confirm = useConfirm();
const items = ref<MediaNotification[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);
const filter = ref<Filter>("all");
const openId = ref<string | null>(null);
const reminders = ref<Awaited<ReturnType<typeof readPluginReminders>>>([]);
let reminderGeneration = 0;
async function loadReminders() {
  const generation = ++reminderGeneration;
  const values = await readPluginReminders();
  if (generation === reminderGeneration) reminders.value = values;
}
watch(pluginReminderRevision, () => void loadReminders(), { immediate: true });
const shownReminders = computed(() =>
  filter.value === "all" || filter.value === "plugins" ? reminders.value : [],
);

async function load() {
  error.value = null;
  void loadReminders();
  try {
    items.value = (await fetchMediaNotifications(200)).items;
  } catch (e) {
    error.value =
      e instanceof Error ? e.message : "Failed to load notifications.";
  } finally {
    loading.value = false;
  }
}
onMounted(load);
useKeptAlive(load);

const unreadCount = computed(() => items.value.filter((n) => !n.read).length);
const counts = computed(() => {
  const c: Record<Filter, number> = {
    all: items.value.length + reminders.value.length,
    unread: unreadCount.value,
    episodes: 0,
    seasons: 0,
    releases: 0,
    plugins: reminders.value.length,
  };
  for (const n of items.value) {
    const group = notificationPresentation(n.kind).group;
    if (group) c[group] += 1;
  }
  return c;
});
const filterOptions = computed<SegmentOption[]>(() =>
  FILTERS.map((f) => ({
    value: f.key,
    label: f.label,
    count: counts.value[f.key],
  })),
);
const shown = computed(() => {
  return items.value.filter((n) => {
    if (filter.value === "all") return true;
    if (filter.value === "unread") return !n.read;
    return notificationPresentation(n.kind).group === filter.value;
  });
});

function dayKey(unix: number): string {
  const d = new Date(unix * 1000);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
function dayLabel(key: string): string {
  const now = new Date();
  const today = dayKey(now.getTime() / 1000);
  const yesterday = dayKey(now.getTime() / 1000 - 86400);
  if (key === today) return "Today";
  if (key === yesterday) return "Yesterday";
  return new Date(`${key}T00:00:00`).toLocaleDateString(undefined, {
    weekday: "long",
    month: "short",
    day: "numeric",
  });
}
const grouped = computed(() => {
  const map = new Map<string, MediaNotification[]>();
  for (const n of shown.value) {
    const k = dayKey(n.eventAt);
    const list = map.get(k);
    if (list) list.push(n);
    else map.set(k, [n]);
  }
  return [...map.entries()].sort((a, b) => b[0].localeCompare(a[0]));
});

function exactTime(unix: number): string {
  return new Date(unix * 1000).toLocaleString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  });
}
function timeOnly(unix: number): string {
  return new Date(unix * 1000).toLocaleTimeString(undefined, {
    hour: "numeric",
    minute: "2-digit",
  });
}
function ago(unix: number): string {
  const s = Math.max(0, Math.floor(Date.now() / 1000 - unix));
  if (s < 60) return "just now";
  const unit = (n: number, word: string) =>
    `${n} ${word}${n === 1 ? "" : "s"} ago`;
  if (s < 3600) return unit(Math.floor(s / 60), "minute");
  if (s < 86400) return unit(Math.floor(s / 3600), "hour");
  return unit(Math.floor(s / 86400), "day");
}
const TYPE_LABEL: Record<string, string> = {
  movie: "Movie",
  tv: "TV show",
  anime: "Anime",
  plugin: "Plugin",
};

// ---- actions ----
async function setRead(n: MediaNotification, read: boolean) {
  const before = n.read;
  n.read = read;
  try {
    if (read) await markNotificationRead(n.id);
    else await markNotificationUnread(n.id);
    refreshMediaNotifications();
  } catch (e) {
    n.read = before;
    error.value = e instanceof Error ? e.message : "Failed to update.";
  }
}
async function readAll() {
  const before = items.value.map((n) => n.read);
  items.value.forEach((n) => (n.read = true));
  try {
    await markAllNotificationsRead();
    refreshMediaNotifications();
  } catch (e) {
    items.value.forEach((n, i) => (n.read = before[i]));
    error.value = e instanceof Error ? e.message : "Failed to update.";
  }
}
async function dismiss(n: MediaNotification) {
  const ok = await confirm({
    message: "Remove this notification?",
    confirmLabel: "Remove",
  });
  if (!ok) return;
  try {
    await deleteMediaNotification(n.id);
    items.value = items.value.filter((x) => x.id !== n.id);
    refreshMediaNotifications();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to remove.";
  }
}
async function open(n: MediaNotification) {
  const destination = notificationDestination(n);
  if (!destination) return;
  if (!n.read) await setRead(n, true);
  router.push(destination);
}
function toggleOpen(n: MediaNotification) {
  openId.value = openId.value === n.id ? null : n.id;
}
</script>

<template>
  <main class="ui-page">
    <AppTopBar>
      <SegmentedTabs
        :options="filterOptions"
        :model-value="filter"
        aria-label="Filter notifications"
        @update:model-value="filter = $event as Filter"
      />
      <template #actions>
        <button
          type="button"
          class="ui-btn ui-btn-secondary"
          :disabled="!unreadCount"
          @click="readAll"
        >
          Mark All Read
        </button>
      </template>
    </AppTopBar>

    <div class="ui-content narrow">
      <div class="ui-head">
        <div>
          <h1>Notifications</h1>
          <div class="sub">
            {{ unreadCount ? `${unreadCount} unread` : "All caught up" }}
          </div>
        </div>
      </div>
      <p v-if="error" class="ui-state error">{{ error }}</p>
      <p v-if="loading" class="ui-state">Loading…</p>

      <template v-else>
        <section v-if="shownReminders.length" class="plugin-reminders">
          <h2>Plugin reminders</h2>
          <button
            v-for="reminder in shownReminders"
            :key="`${reminder.pluginId}:${reminder.id}`"
            type="button"
            class="ui-panel plugin-reminder"
            @click="router.push(reminder.path)"
          >
            <strong>{{ reminder.label }}</strong>
            <span>{{ reminder.description }}</span>
            <small>{{ reminder.pluginId }}</small>
          </button>
        </section>
        <div v-if="!grouped.length && !shownReminders.length" class="empty">
          <p class="empty-title">
            {{
              filter === "unread"
                ? "You're all caught up."
                : "Nothing here yet."
            }}
          </p>
          <p class="empty-sub">
            Episodes, season starts, new seasons and movie releases show up here
            as they happen, using the exact time the provider lists. Choose
            which ones you get under Settings, Calendar and Notifications.
          </p>
        </div>

        <section v-for="[key, day] in grouped" :key="key" class="day">
          <h2 class="day-heading">{{ dayLabel(key) }}</h2>
          <div class="list">
            <article
              v-for="n in day"
              :key="n.id"
              class="card"
              :class="{ unread: !n.read, open: openId === n.id }"
            >
              <button type="button" class="card-row" @click="toggleOpen(n)">
                <span
                  class="poster"
                  :style="
                    n.posterUrl
                      ? { backgroundImage: `url(${n.posterUrl})` }
                      : {}
                  "
                >
                  <span v-if="!n.posterUrl" class="poster-initial">{{
                    n.title.slice(0, 1)
                  }}</span>
                </span>
                <span class="card-main">
                  <span class="card-title">{{ n.title }}</span>
                  <span class="card-body">{{ n.body }}</span>
                  <span class="card-time"
                    >{{ timeOnly(n.eventAt) }} · {{ ago(n.eventAt) }}</span
                  >
                </span>
                <span
                  class="badge"
                  :class="notificationPresentation(n.kind).tone"
                  >{{ notificationPresentation(n.kind).label }}</span
                >
                <span v-if="!n.read" class="unread-dot" title="Unread"></span>
              </button>

              <div v-if="openId === n.id" class="detail">
                <dl>
                  <div>
                    <dt>What happened</dt>
                    <dd>
                      {{ notificationPresentation(n.kind).label }}: {{ n.body }}
                    </dd>
                  </div>
                  <div>
                    <dt>Title</dt>
                    <dd>
                      {{ n.title }} ({{
                        TYPE_LABEL[n.mediaType] ?? "Notification"
                      }})
                    </dd>
                  </div>
                  <div>
                    <dt>
                      {{
                        n.kind === "sequel_announced" ? "Noticed" : "Exact time"
                      }}
                    </dt>
                    <dd>{{ exactTime(n.eventAt) }}</dd>
                  </div>
                </dl>
                <div class="detail-actions">
                  <button
                    v-if="notificationDestination(n)"
                    type="button"
                    class="ui-btn ui-btn-sm ui-btn-primary"
                    @click="open(n)"
                  >
                    Open Title
                  </button>
                  <button
                    type="button"
                    class="ui-btn ui-btn-sm ui-btn-secondary"
                    @click="setRead(n, !n.read)"
                  >
                    {{ n.read ? "Mark Unread" : "Mark Read" }}
                  </button>
                  <button
                    type="button"
                    class="ui-btn ui-btn-sm ui-btn-danger-soft"
                    @click="dismiss(n)"
                  >
                    Remove
                  </button>
                </div>
              </div>
            </article>
          </div>
        </section>
      </template>
    </div>
  </main>
</template>

<style scoped>
.plugin-reminders {
  display: grid;
  gap: 10px;
  margin-bottom: var(--ui-space-6);
}
.plugin-reminders h2 {
  font-size: var(--ui-font-heading);
}
.plugin-reminder {
  display: grid;
  text-align: left;
  gap: 6px;
  padding: 16px;
  color: var(--ui-text);
  cursor: pointer;
}
.plugin-reminder span,
.plugin-reminder small {
  color: var(--ui-dim);
}
.empty {
  text-align: center;
  padding: 56px 16px;
}
.empty-title {
  margin: 0 0 8px;
  font-size: 1.05rem;
  font-weight: var(--ui-weight-title);
}
.empty-sub {
  margin: 0 auto;
  max-width: 460px;
  color: var(--ui-dim);
  font-size: 0.84rem;
  line-height: 1.6;
}
.day {
  margin-bottom: 26px;
}
.day-heading {
  margin: 0 0 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--ui-border);
  font-size: 0.74rem;
  font-weight: var(--ui-weight-title);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--ui-accent-text);
}
.list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.card {
  background: var(--ui-surface);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-card);
  overflow: hidden;
  transition: border-color 0.15s ease;
}
.card:hover,
.card.open {
  border-color: color-mix(in srgb, var(--ui-accent) 40%, transparent);
}
.card.unread {
  border-left: 3px solid var(--ui-accent-text);
}
.card.plain {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  text-decoration: none;
  color: inherit;
}
.card-row {
  display: flex;
  align-items: center;
  gap: 14px;
  width: 100%;
  padding: 10px 14px 10px 10px;
  background: none;
  border: none;
  text-align: left;
  color: inherit;
  font-family: inherit;
  cursor: pointer;
}
.poster {
  width: 46px;
  height: 66px;
  flex-shrink: 0;
  border-radius: 6px;
  background: var(--ui-surface-2) center / cover;
  display: flex;
  align-items: center;
  justify-content: center;
}
.poster-initial {
  font-size: 1.2rem;
  font-weight: var(--ui-weight-title);
  color: var(--ui-faint);
}
.card-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.card-title {
  font-size: 0.92rem;
  font-weight: var(--ui-weight-title);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.card-body {
  font-size: 0.82rem;
  color: var(--ui-text);
}
.card-time {
  font-size: 0.72rem;
  color: var(--ui-faint);
}
.badge {
  flex-shrink: 0;
  font-size: 0.66rem;
  font-weight: var(--ui-weight-title);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  padding: 4px 10px;
  border-radius: 999px;
}
.badge.amber {
  background: color-mix(in srgb, var(--ui-accent) 16%, transparent);
  color: var(--ui-accent-text);
}
.badge.green {
  background: color-mix(in srgb, var(--ui-good) 16%, transparent);
  color: var(--ui-good);
}
.badge.blue {
  background: color-mix(in srgb, var(--ui-info) 16%, transparent);
  color: var(--ui-info);
}
.badge.violet {
  background: color-mix(in srgb, var(--ui-purple) 16%, transparent);
  color: var(--ui-purple);
}
.badge.red {
  background: color-mix(in srgb, var(--ui-error) 16%, transparent);
  color: var(--ui-error);
}
.unread-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--ui-accent);
  flex-shrink: 0;
}
.detail {
  border-top: 1px solid var(--ui-border);
  padding: 14px 16px 16px 70px;
  background: var(--ui-surface-2);
}
.detail dl {
  margin: 0 0 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.detail dt {
  font-size: 0.66rem;
  font-weight: var(--ui-weight-title);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--ui-faint);
}
.detail dd {
  margin: 2px 0 0;
  font-size: 0.84rem;
  color: var(--ui-text);
}
.detail-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
@media (max-width: 720px) {
  .badge {
    display: none;
  }
  .detail {
    padding-left: 16px;
  }
}
</style>
