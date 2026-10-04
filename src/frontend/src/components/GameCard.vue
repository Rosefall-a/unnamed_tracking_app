<script setup lang="ts">
import { useRouter } from "vue-router";
import type { Game, GameStatus } from "../types/game";
import { setFavorite, setStatus } from "../services/games";
import { ref, computed, nextTick, onUnmounted, watch } from "vue";
import { computeScore } from "../utils/scoring";
import { appearanceSettings } from "../state/appearance";
import CompletionBadge from "./CompletionBadge.vue";

const props = defineProps<{
  game: Game;
  selectMode?: boolean;
  selected?: boolean;
  keyboardFocused?: boolean;
}>();

const emit = defineEmits<{
  edit: [game: Game];
  "add-to-collection": [game: Game];
  "toggle-select": [game: Game, shiftKey: boolean];
  changed: [];
}>();

const router = useRouter();

const score = computed(() => computeScore(props.game));

// completion-badge appearance, customized in Settings > Appearance,
// shared across every card via state/appearance.ts rather than fetched
// per-card
const localStatus = ref(props.game.status);
const isMastered = computed(() => localStatus.value === "mastered");
const badgeStyle = computed(
  () => appearanceSettings.value?.completion_badge_style ?? "none",
);
const badgeColor = computed(
  () => appearanceSettings.value?.completion_badge_color ?? "#e5e4e2",
);
const badgePlacement = computed(
  () => appearanceSettings.value?.completion_badge_placement ?? "top-right",
);
const badgeImageUrl = computed(
  () => appearanceSettings.value?.completion_badge_image_url ?? null,
);
const showBadge = computed(
  () => isMastered.value && badgeStyle.value !== "none",
);
const badgeCardStyle = computed(() => {
  if (
    !showBadge.value ||
    (badgeStyle.value !== "glow" && badgeStyle.value !== "border")
  )
    return {};
  return { "--badge-color": badgeColor.value };
});

const menuOpen = ref(false);
const statusSubmenuOpen = ref(false);
const localFavorite = ref(props.game.favorite);
const favoriteSaving = ref(false);
const actionError = ref<string | null>(null);
watch(
  () => props.game.status,
  (status) => {
    localStatus.value = status;
  },
);
watch(
  () => props.game.favorite,
  (favorite) => {
    if (!favoriteSaving.value) localFavorite.value = favorite;
  },
);

const menuTriggerRef = ref<HTMLElement | null>(null);
const menuRef = ref<HTMLElement | null>(null);
const menuPosition = ref({ top: 0, left: 0 });

function onWindowScroll() {
  closeMenu();
}

async function toggleMenu() {
  menuOpen.value = !menuOpen.value;
  if (menuOpen.value && menuTriggerRef.value) {
    await nextTick();
    const rect = menuTriggerRef.value.getBoundingClientRect();
    const height = menuRef.value?.offsetHeight ?? 0;
    menuPosition.value = {
      top: Math.max(
        8,
        Math.min(rect.bottom + 6, window.innerHeight - height - 8),
      ),
      left: Math.max(8, Math.min(rect.right - 190, window.innerWidth - 198)),
    };
    menuRef.value
      ?.querySelector<HTMLButtonElement>("button:not(:disabled)")
      ?.focus();
    window.addEventListener("scroll", onWindowScroll, true);
  } else {
    window.removeEventListener("scroll", onWindowScroll, true);
  }
}

function closeMenu() {
  const restoreFocus = Boolean(menuRef.value?.contains(document.activeElement));
  menuOpen.value = false;
  statusSubmenuOpen.value = false;
  window.removeEventListener("scroll", onWindowScroll, true);
  if (restoreFocus) menuTriggerRef.value?.focus();
}

// the grid this card lives in is virtualized, a card can be destroyed
// while its menu is still open, which would otherwise leak this listener
// on window forever (one per off-screen unmount)
onUnmounted(() => {
  window.removeEventListener("scroll", onWindowScroll, true);
});

const statuses: GameStatus[] = [
  "playing",
  "beaten",
  "mastered",
  "played",
  "on hold",
  "dropped",
  "backlog",
  "wishlist",
];

function openGame(e?: MouseEvent) {
  if (props.selectMode) {
    emit("toggle-select", props.game, e?.shiftKey ?? false);
    return;
  }
  router.push(`/games/${props.game.id}`);
}

async function toggleFavorite() {
  const next = !localFavorite.value;
  localFavorite.value = next;
  favoriteSaving.value = true;
  actionError.value = null;
  try {
    await setFavorite(props.game.id, next);
    emit("changed");
  } catch (reason) {
    localFavorite.value = !next;
    actionError.value =
      reason instanceof Error ? reason.message : "Could not change favorite.";
  } finally {
    favoriteSaving.value = false;
  }
}

async function chooseStatus(status: GameStatus) {
  actionError.value = null;
  try {
    await setStatus(props.game.id, status);
    localStatus.value = status;
    emit("changed");
  } catch (reason) {
    actionError.value =
      reason instanceof Error ? reason.message : "Could not change status.";
  }
  closeMenu();
}

// a quick at-a-glance read on a card without opening it: never launched at
// all, vs. picked up again recently, anything in between just stays quiet
const totalPlaytimeMinutes = computed(() =>
  props.game.platforms.reduce((sum, p) => sum + p.playtimeMinutes, 0),
);
const activityDot = computed<"never" | "recent" | null>(() => {
  if (totalPlaytimeMinutes.value === 0) return "never";
  if (props.game.lastPlayedAt) {
    const daysSince =
      (Date.now() - new Date(props.game.lastPlayedAt).getTime()) / 86_400_000;
    if (daysSince <= 14) return "recent";
  }
  return null;
});

// short plain-text synopsis for the hover preview, game.description can be
// rich HTML (Steam's "About This Game"), so strip tags rather than render
// markup inside a small overlay
const previewSynopsis = computed(() => {
  const raw =
    props.game.description
      ?.replace(/<[^>]*>/g, " ")
      .replace(/\s+/g, " ")
      .trim() ?? "";
  if (!raw) return "";
  return raw.length > 140 ? raw.slice(0, 140).trimEnd() + "…" : raw;
});
const lastPlayedLabel = computed(() => {
  if (!props.game.lastPlayedAt) return "Not played yet";
  return `Last played ${new Date(props.game.lastPlayedAt).toLocaleDateString()}`;
});
function formatPlaytime(minutes: number): string {
  if (minutes === 0) return "No playtime logged";
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return hours > 0
    ? `${hours}h${mins > 0 ? ` ${mins}m` : ""} played`
    : `${mins}m played`;
}

// swipe gestures, a touch-only mirror of the desktop hover actions, which
// obviously never appear on a device with no cursor to hover with
const touchStartX = ref(0);
const touchStartY = ref(0);
const swiping = ref(false);
const SWIPE_THRESHOLD = 60;
function onTouchStart(e: TouchEvent) {
  if (props.selectMode) return;
  touchStartX.value = e.touches[0].clientX;
  touchStartY.value = e.touches[0].clientY;
  swiping.value = false;
}
function onTouchMove(e: TouchEvent) {
  if (props.selectMode) return;
  const dx = e.touches[0].clientX - touchStartX.value;
  const dy = e.touches[0].clientY - touchStartY.value;
  // only claim the gesture once it's clearly more horizontal than
  // vertical, otherwise a normal vertical scroll gets hijacked
  if (
    !swiping.value &&
    Math.abs(dx) > 16 &&
    Math.abs(dx) > Math.abs(dy) * 1.5
  ) {
    swiping.value = true;
  }
  if (swiping.value) e.preventDefault();
}
function onTouchEnd(e: TouchEvent) {
  if (!swiping.value) return;
  swiping.value = false;
  const dx = e.changedTouches[0].clientX - touchStartX.value;
  if (Math.abs(dx) < SWIPE_THRESHOLD) return;
  if (dx > 0) {
    void toggleFavorite();
  } else if (menuTriggerRef.value) {
    toggleMenu();
  }
}

function copyFolderPath() {
  if (props.game.folderLocation) {
    navigator.clipboard.writeText(props.game.folderLocation);
  }
  closeMenu();
}
</script>

<template>
  <div class="game-card-wrap">
    <div
      class="game-card"
      :class="{
        'menu-open': menuOpen,
        'select-mode': selectMode,
        [`badge-${badgeStyle}`]: showBadge,
        'keyboard-focused': keyboardFocused,
      }"
      :style="badgeCardStyle"
    >
      <div
        class="cover"
        @click="openGame($event)"
        @touchstart="onTouchStart"
        @touchmove="onTouchMove"
        @touchend="onTouchEnd"
      >
        <button
          type="button"
          class="cover-open"
          :aria-label="`${selectMode ? 'Select' : 'Open'} ${game.title}`"
          :aria-pressed="selectMode ? selected : undefined"
        ></button>
        <img class="cover-image" :src="game.coverImageUrl" alt="" />
        <div
          v-if="selectMode"
          class="select-checkbox"
          :class="{ checked: selected }"
        >
          <svg
            v-if="selected"
            viewBox="0 0 24 24"
            width="14"
            height="14"
            fill="none"
            stroke="currentColor"
            stroke-width="3"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M20 6L9 17l-5-5" />
          </svg>
        </div>

        <div
          v-if="game.staleSince && !selectMode"
          class="stale-indicator"
          :title="`No longer seen in your ${game.source ?? 'account'} library as of the last sync.`"
        >
          <svg
            viewBox="0 0 24 24"
            width="12"
            height="12"
            fill="none"
            stroke="currentColor"
            stroke-width="2.5"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path
              d="M12 9v4M12 17h.01M10.3 3.9L2.5 17a1.6 1.6 0 0 0 1.4 2.4h16.2a1.6 1.6 0 0 0 1.4-2.4L13.7 3.9a1.6 1.6 0 0 0-2.8 0z"
            />
          </svg>
        </div>

        <CompletionBadge
          v-if="
            showBadge &&
            (badgeStyle === 'ribbon' || badgeStyle === 'corner_badge')
          "
          :badge-style="badgeStyle"
          :placement="badgePlacement"
          :color="badgeColor"
          :image-url="badgeImageUrl"
        />

        <div
          v-if="activityDot && !selectMode"
          class="activity-dot"
          :class="activityDot"
          :title="
            activityDot === 'never'
              ? 'Never launched'
              : 'Played in the last 2 weeks'
          "
        ></div>

        <div v-if="!selectMode && previewSynopsis" class="hover-preview">
          <p class="hover-preview-synopsis">{{ previewSynopsis }}</p>
          <p class="hover-preview-meta">
            {{ formatPlaytime(totalPlaytimeMinutes) }} · {{ lastPlayedLabel }}
          </p>
        </div>

        <div v-if="!selectMode" class="cover-actions">
          <button
            type="button"
            class="collection-button"
            :aria-label="`Add ${game.title} to a collection`"
            @click.stop="emit('add-to-collection', game)"
          >
            <svg
              viewBox="0 0 24 24"
              width="15"
              height="15"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
            </svg>
          </button>

          <button
            type="button"
            class="favorite-button"
            :class="{ active: localFavorite }"
            :disabled="favoriteSaving"
            :aria-label="`${localFavorite ? 'Unfavorite' : 'Favorite'} ${game.title}`"
            :aria-pressed="localFavorite"
            @click.stop="toggleFavorite"
          >
            <svg
              viewBox="0 0 24 24"
              width="15"
              height="15"
              :fill="localFavorite ? 'currentColor' : 'none'"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path
                d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.6l-1-1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 21l7.8-7.8 1-1a5.5 5.5 0 0 0 0-7.6z"
              />
            </svg>
          </button>

          <button
            type="button"
            class="menu-trigger"
            ref="menuTriggerRef"
            :aria-label="`Actions for ${game.title}`"
            :aria-expanded="menuOpen"
            @click.stop="toggleMenu"
          >
            <svg viewBox="0 0 24 24" width="15" height="15" fill="currentColor">
              <circle cx="5" cy="12" r="2" />
              <circle cx="12" cy="12" r="2" />
              <circle cx="19" cy="12" r="2" />
            </svg>
          </button>
        </div>
      </div>

      <Teleport to="body">
        <div v-if="menuOpen" class="menu-backdrop" @click="closeMenu"></div>
        <Transition name="menu-pop">
          <div
            v-if="menuOpen"
            class="card-menu"
            ref="menuRef"
            role="group"
            :aria-label="`Actions for ${game.title}`"
            :style="{
              top: menuPosition.top + 'px',
              left: menuPosition.left + 'px',
            }"
            @click.stop
            @keydown.esc.prevent.stop="closeMenu"
          >
            <template v-if="!statusSubmenuOpen">
              <button type="button" class="menu-item" @click="openGame">
                Open
              </button>
              <div class="menu-divider"></div>
              <button
                type="button"
                class="menu-item"
                @click="
                  emit('edit', game);
                  closeMenu();
                "
              >
                Edit
              </button>
              <button
                type="button"
                class="menu-item"
                @click="statusSubmenuOpen = true"
              >
                Change Status
              </button>
              <button type="button" class="menu-item disabled" disabled>
                Refresh Metadata
              </button>
              <div class="menu-divider"></div>
              <button type="button" class="menu-item disabled" disabled>
                Add Screenshot
              </button>
              <button type="button" class="menu-item disabled" disabled>
                Add Clip
              </button>
              <div class="menu-divider"></div>
              <button type="button" class="menu-item" @click="copyFolderPath">
                Copy Folder Path
              </button>
            </template>
            <template v-else>
              <button
                type="button"
                class="menu-item back"
                @click="statusSubmenuOpen = false"
              >
                ← Back
              </button>
              <div class="menu-divider"></div>
              <button
                v-for="s in statuses"
                :key="s"
                type="button"
                class="menu-item"
                :class="{ active: s === localStatus }"
                @click="chooseStatus(s)"
              >
                {{ s }}
              </button>
            </template>
          </div>
        </Transition>
      </Teleport>
    </div>

    <div class="card-info">
      <h3 class="title">{{ game.title }}</h3>
      <div class="meta-row">
        <span class="status">{{ localStatus }}</span>
        <span v-if="score" class="rating">★ {{ score.sum.toFixed(1) }}</span>
        <span v-if="game.achievementPercent > 0" class="achievements">
          <svg
            viewBox="0 0 24 24"
            width="11"
            height="11"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M8 4h8v5a4 4 0 0 1-8 0z" />
            <path d="M8 4H5a2 2 0 0 0 0 4h1.5M16 4h3a2 2 0 0 1 0 4h-1.5" />
            <path d="M12 13v3" />
            <path d="M9 20h6" />
            <path d="M10 16.5h4l.8 3.5H9.2z" />
          </svg>
          {{ game.achievementPercent }}%
        </span>
      </div>
    </div>
    <p v-if="actionError" class="card-error" role="alert">{{ actionError }}</p>
  </div>
</template>

<style scoped>
.game-card-wrap {
  width: 200px;
  flex-shrink: 0;
  min-width: 0;
}
.game-card {
  position: relative;
  width: 100%;
  border-radius: 10px;
  transition:
    transform 0.32s cubic-bezier(0.22, 1, 0.36, 1),
    box-shadow 0.32s cubic-bezier(0.22, 1, 0.36, 1);
  will-change: transform;
  z-index: 1;
}
.game-card:hover,
.game-card.menu-open {
  transform: scale(1.07) translateY(-4px);
  box-shadow: 0 24px 56px rgba(0, 0, 0, 0.5);
  z-index: 10;
}
.game-card.keyboard-focused .cover {
  outline: 3px solid #d68a34;
  outline-offset: 3px;
}

/* completion badge, "glow"/"border" style the whole card (via --badge-color,
   set inline from Settings > Appearance); "ribbon"/"corner_badge" are
   positioned elements inside .cover instead, see .completion-badge below */
.game-card.badge-glow {
  box-shadow:
    0 0 0 1px color-mix(in srgb, var(--badge-color) 55%, transparent),
    0 0 22px 2px color-mix(in srgb, var(--badge-color) 45%, transparent);
}
.game-card.badge-glow:hover,
.game-card.badge-glow.menu-open {
  box-shadow:
    0 0 0 1px var(--badge-color),
    0 0 32px 6px color-mix(in srgb, var(--badge-color) 65%, transparent),
    0 24px 56px rgba(0, 0, 0, 0.5);
}
.game-card.badge-border {
  box-shadow: 0 0 0 2px var(--badge-color);
}
.game-card.badge-border:hover,
.game-card.badge-border.menu-open {
  box-shadow:
    0 0 0 2px var(--badge-color),
    0 24px 56px rgba(0, 0, 0, 0.5);
}
.cover {
  position: relative;
  width: 100%;
  /* 2:3, matches SteamGridDB's Steam-vertical grid size (600x900) so
     cover art fills the box instead of getting cropped by object-fit */
  aspect-ratio: 2 / 3;
  border-radius: 10px;
  overflow: hidden;
  cursor: pointer;
  background: #1a1a1a;
}
.cover-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.cover-open {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  z-index: 2;
  padding: 0;
  border: 0;
  border-radius: inherit;
  background: transparent;
  cursor: pointer;
}
.cover-open:focus-visible {
  outline: 3px solid var(--ui-accent);
  outline-offset: -3px;
}
.select-checkbox {
  position: absolute;
  top: 8px;
  left: 8px;
  width: 24px;
  height: 24px;
  border-radius: 6px;
  border: 2px solid rgba(255, 255, 255, 0.6);
  background: rgba(20, 20, 20, 0.55);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #111;
  z-index: 3;
  transition:
    background 0.15s ease,
    border-color 0.15s ease;
}
.select-checkbox.checked {
  background: #d68a34;
  border-color: #d68a34;
}
.hover-preview {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 26px 10px 10px;
  background: linear-gradient(
    to top,
    rgba(0, 0, 0, 0.92) 40%,
    rgba(0, 0, 0, 0.5) 75%,
    transparent
  );
  opacity: 0;
  transform: translateY(6px);
  transition:
    opacity 0.18s ease,
    transform 0.18s ease;
  transition-delay: 0.15s;
  pointer-events: none;
}
.game-card:hover .hover-preview {
  opacity: 1;
  transform: translateY(0);
}
.hover-preview-synopsis {
  margin: 0 0 6px;
  color: #eee;
  font-size: 11px;
  line-height: 1.45;
}
.hover-preview-meta {
  margin: 0;
  color: #d68a34;
  font-size: 10.5px;
  font-weight: 600;
}
.activity-dot {
  position: absolute;
  bottom: 8px;
  left: 8px;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  box-shadow: 0 0 0 2px rgba(0, 0, 0, 0.55);
}
.activity-dot.never {
  background: #6a6a6a;
}
.activity-dot.recent {
  background: #4ade80;
}
.stale-indicator {
  position: absolute;
  top: 8px;
  left: 8px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: rgba(220, 38, 38, 0.85);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  z-index: 3;
}
.cover-actions {
  position: absolute;
  bottom: 8px;
  right: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
  z-index: 3;
}
.favorite-button,
.collection-button,
.menu-trigger {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(20, 20, 20, 0.55);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  color: #fff;
  font-size: 13px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transform: translateY(4px);
  transition:
    opacity 0.2s ease,
    transform 0.2s ease,
    background 0.15s ease,
    color 0.15s ease,
    border-color 0.15s ease;
}
.game-card:hover .favorite-button,
.game-card:hover .collection-button,
.game-card:hover .menu-trigger,
.game-card.menu-open .favorite-button,
.game-card.menu-open .collection-button,
.game-card.menu-open .menu-trigger {
  opacity: 1;
  transform: translateY(0);
}
.favorite-button.active {
  color: #ff6f91;
  border-color: rgba(255, 111, 145, 0.4);
  background: rgba(224, 86, 122, 0.18);
}
.menu-trigger:hover,
.favorite-button:hover,
.collection-button:hover {
  background: rgba(40, 40, 40, 0.85);
  border-color: rgba(255, 255, 255, 0.3);
  transform: translateY(0) scale(1.1);
}
.menu-backdrop {
  position: fixed;
  inset: 0;
  z-index: calc(var(--ui-z-popover) - 1);
}
.card-menu {
  position: fixed;
  width: 190px;
  background: var(--ui-popover);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-control);
  padding: 6px;
  box-shadow: var(--ui-elevation);
  z-index: var(--ui-z-popover);
  max-height: calc(100dvh - 16px);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
  transform-origin: top right;
}
.menu-pop-enter-active,
.menu-pop-leave-active {
  transition:
    opacity 0.15s ease,
    transform 0.15s ease;
}
.menu-pop-enter-from,
.menu-pop-leave-to {
  opacity: 0;
  transform: translateY(-6px) scale(0.96);
}
.menu-item {
  text-align: left;
  background: none;
  border: none;
  color: var(--ui-text);
  padding: 8px 10px;
  font-size: 13px;
  border-radius: 6px;
  cursor: pointer;
  text-transform: capitalize;
  min-height: var(--ui-control-height);
}
.menu-item:hover:not(.disabled) {
  background: var(--ui-surface-2);
  color: var(--ui-text);
}
.menu-item.disabled {
  color: var(--ui-faint);
  cursor: not-allowed;
}
.menu-item.destructive {
  color: var(--ui-error);
}
.menu-item.destructive:hover {
  background: rgba(220, 38, 38, 0.15);
}
.menu-item.active {
  color: var(--ui-accent-text);
  font-weight: 600;
}
.menu-item.back {
  color: var(--ui-dim);
}
.menu-divider {
  height: 1px;
  background: var(--ui-border-soft);
  margin: 4px 2px;
}
.card-info {
  padding: 10px 2px 0;
}
.title {
  margin: 0 0 2px;
  font-size: 14px;
  font-weight: 600;
  color: var(--ui-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.meta-row {
  display: flex;
  gap: 8px;
  font-size: 12px;
  color: var(--ui-dim);
}
.meta-row .status {
  text-transform: capitalize;
}
.meta-row .rating {
  color: var(--ui-accent-text);
}
.meta-row .achievements {
  display: inline-flex;
  align-items: center;
  gap: 3px;
}
.meta-row .achievements svg {
  flex-shrink: 0;
  opacity: 0.75;
}
.card-error {
  color: var(--ui-error);
  font-size: var(--ui-font-small);
  overflow-wrap: anywhere;
}
.game-card:focus-within .favorite-button,
.game-card:focus-within .collection-button,
.game-card:focus-within .menu-trigger {
  opacity: 1;
  transform: none;
}
@media (max-width: 760px), (hover: none) {
  .favorite-button,
  .collection-button,
  .menu-trigger {
    opacity: 1;
    transform: none;
    width: 44px;
    height: 44px;
  }
  .cover-actions {
    gap: 4px;
    right: 4px;
    bottom: 4px;
  }
  .game-card:hover,
  .game-card.menu-open {
    transform: none;
    box-shadow: none;
  }
}
</style>
