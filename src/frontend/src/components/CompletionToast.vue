<script setup lang="ts">
// The pop-up when a game reaches 100%. It comes from the same notification
// the bell lists, so it shows once: viewing it, dismissing it or letting it
// time out marks it read, and it stays in the bell to find later.
import { computed, onUnmounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import {
  mediaNotifications,
  readMediaNotification,
} from "../state/notifications";
import { preferences } from "../state/preferences";
import type { MediaNotification } from "../services/notifications";
import TrophyIcon from "./TrophyIcon.vue";

const router = useRouter();
// shown this visit, so one that is still being marked read never comes back
const shown = new Set<string>();
const current = ref<MediaNotification | null>(null);
let timer: number | undefined;

const waiting = computed(() =>
  preferences.value.notify_game_complete
    ? mediaNotifications.value.filter(
        (n) => n.kind === "game_complete" && !n.read && !shown.has(n.id),
      )
    : [],
);

// one at a time, oldest first
watch(
  waiting,
  (list) => {
    if (current.value || !list.length) return;
    const next = [...list].sort((a, b) => a.eventAt - b.eventAt)[0];
    shown.add(next.id);
    current.value = next;
    startTimer();
  },
  { immediate: true },
);

// it goes by itself after a while, but never while the mouse is on it
function startTimer() {
  window.clearTimeout(timer);
  timer = window.setTimeout(() => close(), 12_000);
}
function pause() {
  window.clearTimeout(timer);
}
onUnmounted(() => window.clearTimeout(timer));

function close() {
  const n = current.value;
  window.clearTimeout(timer);
  current.value = null;
  if (n) void readMediaNotification(n.id);
  // the next one, if several came in together
  window.setTimeout(() => {
    const list = waiting.value;
    if (!current.value && list.length) {
      const next = [...list].sort((a, b) => a.eventAt - b.eventAt)[0];
      shown.add(next.id);
      current.value = next;
      startTimer();
    }
  }, 400);
}
function view() {
  const n = current.value;
  close();
  if (n) void router.push(`/games/${n.mediaId}?tab=Achievements`);
}
</script>

<template>
  <Transition name="done-toast">
    <div
      v-if="current"
      class="done-toast"
      role="status"
      aria-live="polite"
      @mouseenter="pause"
      @mouseleave="startTimer"
    >
      <div class="toast-cv">
        <img v-if="current.posterUrl" :src="current.posterUrl" alt="" />
      </div>
      <div class="toast-body">
        <div class="toast-eb"><TrophyIcon />100% complete</div>
        <b>{{ current.title }}</b>
        <p>{{ current.body }}</p>
        <div class="toast-actions">
          <button type="button" class="btn pri" @click="view">View</button>
          <button type="button" class="btn" @click="close">Dismiss</button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.done-toast {
  position: fixed;
  right: 20px;
  top: 76px;
  z-index: 320;
  display: flex;
  gap: 14px;
  width: 400px;
  max-width: calc(100vw - 32px);
  box-sizing: border-box;
  background: #1c1c1c;
  border: 1px solid #2e2e2e;
  border-radius: 12px;
  padding: 14px;
  box-shadow: 0 14px 36px rgba(0, 0, 0, 0.5);
  overflow: hidden;
}
.done-toast::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: linear-gradient(#f1cd6a, #c08a26);
}
.toast-cv {
  width: 56px;
  flex: 0 0 auto;
  align-self: flex-start;
  aspect-ratio: 2 / 3;
  border-radius: 4px;
  overflow: hidden;
  background: #262626;
}
.toast-cv img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.toast-body {
  flex: 1;
  min-width: 0;
}
.toast-eb {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #e9be5a;
}
.toast-eb :deep(svg) {
  width: 14px;
  height: 14px;
}
.toast-body b {
  display: block;
  margin-top: 4px;
  font-size: 15px;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.toast-body p {
  margin: 3px 0 0;
  font-size: 12.5px;
  color: #9c9c9c;
}
.toast-actions {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}
.btn {
  font: inherit;
  font-size: 13px;
  font-weight: 600;
  border-radius: 8px;
  padding: 6px 12px;
  border: 1px solid #333;
  background: #232323;
  color: #e5e5e5;
  cursor: pointer;
}
.btn:hover {
  border-color: #444;
  background: #2a2a2a;
}
.btn.pri {
  background: var(--ui-accent);
  border-color: var(--ui-accent);
  color: var(--ui-on-accent);
}
.btn.pri:hover {
  filter: brightness(1.08);
}
.done-toast-enter-active {
  transition:
    opacity 0.2s ease,
    transform 0.32s cubic-bezier(0.22, 1, 0.36, 1);
}
.done-toast-leave-active {
  transition:
    opacity 0.16s ease,
    transform 0.16s ease;
}
.done-toast-enter-from,
.done-toast-leave-to {
  opacity: 0;
  transform: translateY(-10px) scale(0.98);
}
@media (prefers-reduced-motion: reduce) {
  .done-toast-enter-active,
  .done-toast-leave-active {
    transition: none;
  }
}
</style>
