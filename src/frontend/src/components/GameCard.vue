<script setup lang="ts">
import { useRouter } from "vue-router";
import type { Game, GameStatus } from "../types/game";
import { setFavorite, setStatus } from "../services/games";
import { ref, computed, nextTick, onUnmounted } from "vue";
import { computeScore } from "../utils/scoring";
import { appearanceSettings } from "../state/appearance";

const props = defineProps<{
  game: Game;
  selectMode?: boolean;
  selected?: boolean;
  keyboardFocused?: boolean;
  rank?: number | null;
}>();

const emit = defineEmits<{
  edit: [game: Game];
  "add-to-collection": [game: Game];
  "toggle-select": [game: Game, shiftKey: boolean];
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

const coverRef = ref<HTMLElement | null>(null);
const menuPosition = ref({ top: 0, left: 0 });

function onWindowScroll() {
  closeMenu();
}

// the menu has no button on the cover anymore (the hover buttons match the
// Media shelf), so it opens from a right-click, or a left swipe on touch
async function openMenuAt(x: number, y: number) {
  menuPosition.value = { top: y + 6, left: Math.max(8, x - 190) };
  menuOpen.value = true;
  await nextTick();
  window.addEventListener("scroll", onWindowScroll, true);
}
function onContextMenu(e: MouseEvent) {
  if (props.selectMode) return;
  e.preventDefault();
  void openMenuAt(e.clientX, e.clientY);
}

function closeMenu() {
  menuOpen.value = false;
  statusSubmenuOpen.value = false;
  window.removeEventListener("scroll", onWindowScroll, true);
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
  try {
    await setFavorite(props.game.id, next);
  } catch {
    localFavorite.value = !next;
  } finally {
    favoriteSaving.value = false;
  }
}

async function chooseStatus(status: GameStatus) {
  try {
    await setStatus(props.game.id, status);
    localStatus.value = status;
  } catch {
    // silently ignore, card just keeps showing the old status
  }
  closeMenu();
}

const totalPlaytimeMinutes = computed(() =>
  props.game.platforms.reduce((sum, p) => sum + p.playtimeMinutes, 0),
);
const playtimeLabel = computed(() => {
  const m = totalPlaytimeMinutes.value;
  if (m === 0) return "Not played";
  const h = Math.floor(m / 60);
  const rest = m % 60;
  return h > 0 ? `${h}h${rest > 0 ? ` ${rest}m` : ""}` : `${rest}m`;
});
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
  } else if (coverRef.value) {
    const rect = coverRef.value.getBoundingClientRect();
    void openMenuAt(rect.right, rect.bottom);
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
        ref="coverRef"
        class="cover"
        @click="openGame($event)"
        @contextmenu="onContextMenu"
        @touchstart="onTouchStart"
        @touchmove="onTouchMove"
        @touchend="onTouchEnd"
      >
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

        <span v-if="rank" class="shelf-rank rank-badge">#{{ rank }}</span>

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

        <div
          v-if="
            showBadge &&
            (badgeStyle === 'ribbon' || badgeStyle === 'corner_badge')
          "
          class="completion-badge"
          :class="[badgeStyle, badgePlacement]"
          :style="{ '--badge-color': badgeColor }"
        >
          <img
            v-if="badgeImageUrl"
            :src="badgeImageUrl"
            alt=""
            class="completion-badge-image"
          />
          <svg
            v-else
            viewBox="0 0 24 24"
            width="16"
            height="16"
            fill="currentColor"
          >
            <path
              d="M12 2l2.4 6.6L21 9l-5 4.6L17.4 21 12 17.3 6.6 21 8 13.6 3 9l6.6-.4z"
            />
          </svg>
        </div>

        <div v-if="!selectMode" class="cover-actions">
          <button
            type="button"
            class="favorite-button"
            :class="{ active: localFavorite }"
            :disabled="favoriteSaving"
            title="Favorite"
            @click.stop="toggleFavorite"
          >
            <svg
              viewBox="0 0 24 24"
              :fill="localFavorite ? 'currentColor' : 'none'"
              stroke="currentColor"
              stroke-width="2"
              stroke-linejoin="round"
            >
              <path
                d="M12 21s-7.5-4.9-10.2-9.4C.2 8.6 1.4 5 4.9 4.1c2-.5 3.9.3 5.1 2C11.2 4.4 13.1 3.6 15.1 4.1c3.5.9 4.7 4.5 3.1 7.5C15.5 16.1 12 21 12 21z"
              />
            </svg>
          </button>

          <button
            type="button"
            class="collection-button"
            title="Add to collection"
            @click.stop="emit('add-to-collection', game)"
          >
            <svg
              viewBox="0 0 24 24"
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
            class="edit-button"
            title="Edit"
            @click.stop="emit('edit', game)"
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M12 20h9" />
              <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" />
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
            :style="{
              top: menuPosition.top + 'px',
              left: menuPosition.left + 'px',
            }"
            @click.stop
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
      <div class="title-row">
        <h3 class="title">{{ game.title }}</h3>
        <span class="score-tag" :class="{ empty: !score }">{{
          score ? `★ ${score.sum.toFixed(1)}` : "–"
        }}</span>
      </div>
      <div class="meta-row">
        <span class="status">{{ localStatus }}</span>
        <span class="playtime">{{ playtimeLabel }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Media's page sets border-box on everything inside it; without the same
   here the rating box and the rest of the card come out a few px off */
.game-card-wrap,
.game-card-wrap * {
  box-sizing: border-box;
}
.game-card-wrap svg {
  display: block;
}
.game-card-wrap {
  width: 200px;
  flex-shrink: 0;
  min-width: 0;
}
.game-card {
  position: relative;
  width: 100%;
  border-radius: 10px;
  transition: transform 0.28s cubic-bezier(0.22, 1, 0.36, 1);
  will-change: transform;
  z-index: 1;
}
.game-card:hover,
.game-card.menu-open {
  transform: translateY(-3px);
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
.completion-badge {
  position: absolute;
  z-index: 3;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--badge-color);
  pointer-events: none;
}
.completion-badge.top-left {
  top: 8px;
  left: 8px;
}
.completion-badge.top-right {
  top: 8px;
  right: 8px;
}
.completion-badge.bottom-left {
  bottom: 8px;
  left: 8px;
}
.completion-badge.bottom-right {
  bottom: 8px;
  right: 8px;
}
.completion-badge.corner_badge {
  background: rgba(20, 20, 20, 0.55);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  border-radius: 50%;
  border: 1px solid color-mix(in srgb, var(--badge-color) 60%, transparent);
}
.completion-badge.ribbon {
  width: 46px;
  height: 46px;
  filter: drop-shadow(0 2px 6px rgba(0, 0, 0, 0.5));
}
.completion-badge-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
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
  background: var(--surface-2, #222222);
  border: 1px solid var(--border-soft, #202020);
  box-sizing: border-box;
  transition:
    box-shadow 0.28s ease,
    border-color 0.2s ease;
}
.shelf-rank {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 2;
}
.rank-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 20px;
  padding: 0 5px;
  border-radius: 5px;
  background: var(--accent-soft, rgba(214, 138, 52, 0.16));
  color: var(--accent, #d68a34);
  border: 1px solid var(--accent-line, rgba(214, 138, 52, 0.4));
  font-size: 0.68rem;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}
.cover-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.2s ease;
}
.game-card:hover .cover,
.game-card.menu-open .cover {
  border-color: var(--border, #2b2b2b);
  box-shadow: 0 14px 30px rgba(0, 0, 0, 0.45);
}
.game-card:hover .cover-image {
  transform: scale(1.04);
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
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 3;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 6px;
  padding: 26px 8px 8px;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.65), transparent);
  opacity: 0;
  transform: translateY(6px);
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
  pointer-events: none;
}
.game-card:hover .cover-actions,
.game-card:focus-within .cover-actions,
.game-card.menu-open .cover-actions {
  opacity: 1;
  transform: translateY(0);
  pointer-events: auto;
}
.favorite-button,
.collection-button,
.edit-button {
  width: 28px;
  height: 28px;
  padding: 0;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.16);
  background: rgba(20, 20, 20, 0.6);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s ease;
}
.favorite-button svg,
.collection-button svg,
.edit-button svg {
  width: 13px;
  height: 13px;
}
.favorite-button.active {
  color: #ff6f91;
  border-color: rgba(255, 111, 145, 0.4);
  background: rgba(224, 86, 122, 0.2);
}
.edit-button:hover,
.favorite-button:hover,
.collection-button:hover {
  background: rgba(60, 60, 60, 0.9);
}
.menu-backdrop {
  position: fixed;
  inset: 0;
  z-index: 20;
}
.card-menu {
  position: fixed;
  width: 190px;
  background: #1e1e1e;
  border: 1px solid #333;
  border-radius: 10px;
  padding: 6px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.5);
  z-index: 30;
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
  color: #ddd;
  padding: 8px 10px;
  font-size: 13px;
  border-radius: 6px;
  cursor: pointer;
  text-transform: capitalize;
}
.menu-item:hover:not(.disabled) {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}
.menu-item.disabled {
  color: #555;
  cursor: not-allowed;
}
.menu-item.destructive {
  color: #f87171;
}
.menu-item.destructive:hover {
  background: rgba(220, 38, 38, 0.15);
}
.menu-item.active {
  color: #d68a34;
  font-weight: 600;
}
.menu-item.back {
  color: #999;
}
.menu-divider {
  height: 1px;
  background: #2a2a2a;
  margin: 4px 2px;
}
.card-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
  margin-top: 8px;
}
.title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 6px;
}
.title {
  margin: 0;
  min-width: 0;
  font-size: 0.85rem;
  font-weight: 700;
  line-height: 1.3;
  color: var(--text, #f2f2f2);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  /* two lines are always reserved so a one-line title doesn't pull the
     rows below it up and leave cards in the same row misaligned */
  min-height: calc(1.3em * 2);
}
.score-tag {
  font-size: 0.82rem;
  font-weight: 700;
  color: var(--accent, #d68a34);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  text-align: right;
}
.score-tag.empty {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 20px;
  padding: 0 5px;
  border-radius: 5px;
  background: var(--surface-2, #222222);
  border: 1px solid var(--border, #2b2b2b);
  color: var(--text-faint, #666);
  font-weight: 600;
}
.meta-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  margin-top: 2px;
  min-width: 0;
  font-size: 0.7rem;
  color: var(--text-faint, #666);
}
.meta-row .status {
  text-transform: capitalize;
}
.meta-row .playtime {
  font-size: 0.72rem;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
