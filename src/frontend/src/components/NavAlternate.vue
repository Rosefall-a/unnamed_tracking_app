<script setup lang="ts">
// The three navigation styles without a sidebar: a top bar across the page
// (like Plex), one button that opens a big panel (like the Xbox Guide), and a
// small floating dock at the bottom (like macOS). Same pages, Jump back in,
// Pinned and search as the sidebar styles.
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import NotificationBell from "./NotificationBell.vue";
import ProfileMenu from "./ProfileMenu.vue";
import { currentUser } from "../state/auth";
import { inboxCount } from "../state/inbox";
import {
  ICONS,
  MEDIA_PAGES,
  counts,
  isActivePath,
  jumpItems,
  loadNavData,
  navPages,
  openMenu,
  openSearch,
  pins,
  recentTitles,
} from "../state/navData";
import {
  sidebarShowCounts,
  sidebarShowJump,
  sidebarShowSearch,
  sidebarStyle,
} from "../state/sidebarPrefs";

const route = useRoute();
const router = useRouter();
onMounted(loadNavData);

const active = (to: string) => isActivePath(to, route.path);
function go(to: string) {
  openMenu.value = "";
  void router.push(to);
}
// Top bar menus open under the button that opened them, kept on screen.
const menuX = ref(0);
function toggle(name: string, e?: MouseEvent) {
  const btn = e?.currentTarget as HTMLElement | undefined;
  if (btn) {
    const r = btn.getBoundingClientRect();
    const width = name === "recent" ? 320 : name === "pages" ? 260 : 300;
    menuX.value = Math.max(
      8,
      Math.min(
        name === "recent" ? r.right - width : r.left,
        window.innerWidth - width - 8,
      ),
    );
  }
  openMenu.value = openMenu.value === name ? "" : name;
}
// whatever was open is for this trip only
watch(
  () => route.fullPath,
  () => (openMenu.value = ""),
);
function search() {
  openMenu.value = "";
  openSearch();
}

// anything open closes on Escape or a click outside it
function onKey(e: KeyboardEvent) {
  if (e.key === "Escape" && openMenu.value) openMenu.value = "";
}
function onDown(e: MouseEvent) {
  if (!openMenu.value) return;
  const t = e.target as HTMLElement | null;
  if (t?.closest(".nav-menu, .nav-menu-trigger")) return;
  openMenu.value = "";
}
onMounted(() => {
  document.addEventListener("keydown", onKey);
  document.addEventListener("mousedown", onDown);
});
onUnmounted(() => {
  document.removeEventListener("keydown", onKey);
  document.removeEventListener("mousedown", onDown);
  openMenu.value = "";
});

const mediaRecent = computed(() =>
  recentTitles.value.filter((t) => t.kind !== "game").slice(0, 4),
);
const guideCovers = computed(() => {
  const seen = new Set<string>();
  const out: {
    key: string;
    title: string;
    art: string | null;
    to: string;
    meta: string;
  }[] = [];
  for (const p of pins.value) {
    if (seen.has(p.key)) continue;
    seen.add(p.key);
    out.push({ ...p, meta: "Pinned" });
  }
  if (sidebarShowJump.value)
    for (const j of jumpItems.value) {
      if (seen.has(j.key)) continue;
      seen.add(j.key);
      out.push(j);
    }
  return out.slice(0, 6);
});
const dockCovers = computed(() =>
  [...pins.value, ...(sidebarShowJump.value ? jumpItems.value : [])]
    .filter((v, i, a) => a.findIndex((x) => x.key === v.key) === i)
    .slice(0, 4),
);
const countFor = (id: string) =>
  !sidebarShowCounts.value
    ? 0
    : id === "anime"
      ? counts.value.anime
      : id === "movies"
        ? counts.value.movie
        : id === "tv"
          ? counts.value.tv
          : 0;
</script>

<template>
  <!-- F: top bar -->
  <header v-if="sidebarStyle === 'topbar'" class="topnav">
    <span class="topnav-brand">
      <span class="brand-mark">🎮</span>
      <b>Archive</b>
    </span>
    <!-- a phone has no room for the links, so they fold into one menu -->
    <button
      type="button"
      class="icon-btn nav-menu-trigger pages-btn"
      :class="{ open: openMenu === 'pages' }"
      aria-label="Pages"
      :aria-expanded="openMenu === 'pages'"
      @click="toggle('pages', $event)"
    >
      <svg class="i" viewBox="0 0 24 24">
        <path d="M4 6h16M4 12h16M4 18h16" />
      </svg>
    </button>
    <nav class="topnav-links" aria-label="Main">
      <template v-for="p in navPages" :key="p.id">
        <button
          v-if="p.id === 'media'"
          type="button"
          class="tn nav-menu-trigger"
          :class="{ on: active(p.to), open: openMenu === 'media' }"
          :aria-expanded="openMenu === 'media'"
          @click="toggle('media', $event)"
        >
          Media
          <svg class="i s" viewBox="0 0 24 24"><path :d="ICONS.down" /></svg>
        </button>
        <router-link
          v-else
          :to="p.to"
          class="tn"
          :class="{ on: active(p.to) }"
          @click="openMenu = ''"
          >{{ p.label }}</router-link
        >
      </template>
      <router-link to="/settings?section=upload" class="tn">
        Upload
        <span v-if="inboxCount" class="dot-count">{{ inboxCount }}</span>
      </router-link>
    </nav>
    <div class="topnav-right">
      <button
        v-if="sidebarShowSearch"
        type="button"
        class="search-pill"
        @click="search"
      >
        <svg class="i s" viewBox="0 0 24 24"><path :d="ICONS.search" /></svg>
        <span>Search</span>
        <kbd>Ctrl K</kbd>
      </button>
      <button
        type="button"
        class="icon-btn nav-menu-trigger"
        :class="{ open: openMenu === 'recent' }"
        aria-label="Jump back in and pinned"
        title="Jump back in and pinned"
        :aria-expanded="openMenu === 'recent'"
        @click="toggle('recent', $event)"
      >
        <svg class="i" viewBox="0 0 24 24"><path :d="ICONS.clock" /></svg>
      </button>
      <NotificationBell class="topnav-bell" />
      <router-link
        to="/settings"
        class="icon-btn"
        title="Settings"
        :class="{ on: active('/settings') }"
        aria-label="Settings"
      >
        <svg class="i" viewBox="0 0 24 24"><path :d="ICONS.settings" /></svg>
      </router-link>
      <ProfileMenu
        v-if="currentUser"
        :initials="currentUser.username.slice(0, 2).toUpperCase()"
      />
    </div>
    <Transition name="nav-pop">
      <div
        v-if="openMenu === 'media'"
        class="nav-menu media-menu"
        :style="{ left: `${menuX}px` }"
      >
        <button
          v-for="m in MEDIA_PAGES"
          :key="m.id"
          type="button"
          class="menu-row"
          :class="{ on: active(m.to) && route.path.startsWith(m.to) }"
          @click="go(m.to)"
        >
          <svg class="i" viewBox="0 0 24 24"><path :d="m.icon" /></svg>
          <span>{{ m.label }}</span>
          <span v-if="countFor(m.id)" class="count">{{ countFor(m.id) }}</span>
        </button>
        <template v-if="mediaRecent.length && sidebarShowJump">
          <div class="menu-label">Recently watched</div>
          <button
            v-for="t in mediaRecent"
            :key="t.key"
            type="button"
            class="menu-row title-row"
            @click="go(t.to)"
          >
            <img v-if="t.art" :src="t.art" alt="" />
            <span class="t">{{ t.title }}</span>
            <span class="count">{{ t.meta }}</span>
          </button>
        </template>
      </div>
    </Transition>
    <Transition name="nav-pop">
      <div
        v-if="openMenu === 'pages'"
        class="nav-menu pages-menu"
        :style="{ left: `${menuX}px` }"
      >
        <template v-for="p in navPages" :key="p.id">
          <button
            v-if="p.id !== 'media'"
            type="button"
            class="menu-row"
            :class="{ on: active(p.to) }"
            @click="go(p.to)"
          >
            <svg class="i" viewBox="0 0 24 24"><path :d="p.icon" /></svg>
            <span>{{ p.label }}</span>
          </button>
          <button
            v-for="m in p.id === 'media' ? MEDIA_PAGES : []"
            :key="m.id"
            type="button"
            class="menu-row"
            :class="{ on: route.path.startsWith(m.to) }"
            @click="go(m.to)"
          >
            <svg class="i" viewBox="0 0 24 24"><path :d="m.icon" /></svg>
            <span>{{ m.label }}</span>
            <span v-if="countFor(m.id)" class="count">{{
              countFor(m.id)
            }}</span>
          </button>
        </template>
        <button
          type="button"
          class="menu-row"
          @click="go('/settings?section=upload')"
        >
          <svg class="i" viewBox="0 0 24 24"><path :d="ICONS.upload" /></svg>
          <span>Upload</span>
          <span v-if="inboxCount" class="dot-count">{{ inboxCount }}</span>
        </button>
      </div>
    </Transition>
    <Transition name="nav-pop">
      <div
        v-if="openMenu === 'recent'"
        class="nav-menu recent-menu"
        :style="{ left: `${menuX}px` }"
      >
        <template v-if="sidebarShowJump && jumpItems.length">
          <div class="menu-label">Jump back in</div>
          <button
            v-for="t in jumpItems"
            :key="t.key"
            type="button"
            class="menu-row title-row"
            @click="go(t.to)"
          >
            <img v-if="t.art" :src="t.art" alt="" />
            <span class="t">{{ t.title }}</span>
            <span class="count">{{ t.meta }}</span>
          </button>
        </template>
        <template v-if="pins.length">
          <div class="menu-label">Pinned</div>
          <button
            v-for="p in pins"
            :key="p.key"
            type="button"
            class="menu-row title-row"
            @click="go(p.to)"
          >
            <img v-if="p.art" :src="p.art" alt="" />
            <span class="t">{{ p.title }}</span>
          </button>
        </template>
        <p v-if="!jumpItems.length && !pins.length" class="menu-empty">
          Nothing here yet. Play or watch something, or pin a title in Settings.
        </p>
      </div>
    </Transition>
  </header>

  <!-- G: guide button -->
  <template v-else-if="sidebarStyle === 'guide'">
    <button
      type="button"
      class="guide-btn nav-menu-trigger"
      :class="{ open: openMenu === 'guide' }"
      :aria-expanded="openMenu === 'guide'"
      aria-label="Open the menu"
      @click="toggle('guide')"
    >
      <svg class="i" viewBox="0 0 24 24"><path :d="ICONS.games" /></svg>
    </button>
    <Transition name="guide-pop">
      <div v-if="openMenu === 'guide'" class="nav-menu guide">
        <div class="guide-tabs">
          <button
            v-for="p in navPages"
            :key="p.id"
            type="button"
            class="gt"
            :class="{ on: active(p.to) }"
            @click="go(p.to)"
          >
            <svg class="i" viewBox="0 0 24 24"><path :d="p.icon" /></svg>
            {{ p.label }}
          </button>
          <button
            type="button"
            class="gt"
            :class="{ on: active('/settings') }"
            @click="go('/settings')"
          >
            <svg class="i" viewBox="0 0 24 24">
              <path :d="ICONS.settings" />
            </svg>
            Settings
          </button>
        </div>
        <button
          v-if="sidebarShowSearch"
          type="button"
          class="search-pill wide"
          @click="search"
        >
          <svg class="i s" viewBox="0 0 24 24"><path :d="ICONS.search" /></svg>
          <span>Search</span>
          <kbd>Ctrl K</kbd>
        </button>
        <template v-if="guideCovers.length">
          <div class="menu-label">Jump back in</div>
          <div class="guide-covers">
            <button
              v-for="c in guideCovers"
              :key="c.key"
              type="button"
              class="gcov"
              @click="go(c.to)"
            >
              <img v-if="c.art" :src="c.art" alt="" />
              <span v-else class="gcov-blank"></span>
              <b>{{ c.title }}</b>
              <small>{{ c.meta }}</small>
            </button>
          </div>
        </template>
        <div class="menu-label">Go to</div>
        <div class="quick">
          <button
            v-for="m in MEDIA_PAGES"
            :key="m.id"
            type="button"
            class="qa"
            @click="go(m.to)"
          >
            {{ m.label }}
          </button>
          <button type="button" class="qa" @click="go('/games/collections')">
            Game collections
          </button>
          <button
            type="button"
            class="qa"
            @click="go('/settings?section=upload')"
          >
            Upload
            <span v-if="inboxCount" class="dot-count">{{ inboxCount }}</span>
          </button>
        </div>
      </div>
    </Transition>
  </template>

  <!-- H: dock -->
  <nav v-else-if="sidebarStyle === 'dock'" class="dock" aria-label="Main">
    <router-link
      v-for="p in navPages"
      :key="p.id"
      :to="p.to"
      class="dk"
      :class="{ on: active(p.to) }"
      :aria-label="p.label"
    >
      <svg class="i" viewBox="0 0 24 24"><path :d="p.icon" /></svg>
      <span class="tip">{{ p.label }}</span>
    </router-link>
    <template v-if="dockCovers.length">
      <span class="dsep"></span>
      <router-link
        v-for="c in dockCovers"
        :key="c.key"
        :to="c.to"
        class="dk cover"
        :aria-label="c.title"
      >
        <img v-if="c.art" :src="c.art" alt="" />
        <span class="tip">{{ c.title }}</span>
      </router-link>
    </template>
    <span class="dsep"></span>
    <button
      v-if="sidebarShowSearch"
      type="button"
      class="dk"
      aria-label="Search"
      @click="search"
    >
      <svg class="i" viewBox="0 0 24 24"><path :d="ICONS.search" /></svg>
      <span class="tip">Search</span>
    </button>
    <router-link to="/settings?section=upload" class="dk" aria-label="Upload">
      <svg class="i" viewBox="0 0 24 24"><path :d="ICONS.upload" /></svg>
      <span class="tip">Upload</span>
      <span v-if="inboxCount" class="dk-badge">{{ inboxCount }}</span>
    </router-link>
    <router-link
      to="/settings"
      class="dk"
      :class="{ on: active('/settings') }"
      aria-label="Settings"
    >
      <svg class="i" viewBox="0 0 24 24"><path :d="ICONS.settings" /></svg>
      <span class="tip">Settings</span>
    </router-link>
  </nav>
</template>

<style scoped>
.i {
  width: 18px;
  height: 18px;
  flex: 0 0 auto;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.i.s {
  width: 15px;
  height: 15px;
}
kbd {
  margin-left: auto;
  font-family: ui-monospace, Consolas, monospace;
  font-size: 10.5px;
  background: var(--ui-surface-2);
  border: 1px solid var(--ui-border-strong);
  border-bottom-width: 2px;
  border-radius: 6px;
  padding: 1px 6px;
  color: var(--ui-text-soft);
}
.dot-count {
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  box-sizing: border-box;
  border-radius: 999px;
  background: var(--ui-accent);
  color: var(--ui-on-accent);
  font-size: 10.5px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-left: 6px;
}
.glass {
  background: color-mix(in srgb, var(--ui-popover) 92%, transparent);
  backdrop-filter: blur(18px) saturate(1.15);
}

/* ---- top bar ---- */
.topnav {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 56px;
  z-index: 110;
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 0 18px;
  box-sizing: border-box;
  background: color-mix(in srgb, var(--ui-popover) 92%, transparent);
  backdrop-filter: blur(18px) saturate(1.15);
  border-bottom: 1px solid var(--ui-border);
}
.topnav-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--ui-heading);
  font-size: 16px;
}
.brand-mark {
  font-size: 20px;
}
.topnav-links {
  display: flex;
  align-items: center;
  gap: 2px;
  min-width: 0;
  overflow-x: auto;
  scrollbar-width: none;
}
.tn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 34px;
  padding: 0 12px;
  border: 0;
  border-radius: 8px;
  background: none;
  color: var(--ui-text-soft);
  font: inherit;
  font-size: 13.5px;
  font-weight: 600;
  text-decoration: none;
  cursor: pointer;
  white-space: nowrap;
}
.tn:hover {
  background: color-mix(in srgb, var(--ui-wash-base) 6%, transparent);
  color: var(--ui-heading);
}
.tn.on {
  color: var(--ui-heading);
  background: color-mix(in srgb, var(--ui-wash-base) 8%, transparent);
}
.tn.open {
  background: color-mix(in srgb, var(--ui-wash-base) 10%, transparent);
}
.topnav-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
}
.search-pill {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 240px;
  height: 34px;
  box-sizing: border-box;
  padding: 0 10px;
  border-radius: 9px;
  border: 1px solid color-mix(in srgb, var(--ui-wash-base) 8%, transparent);
  background: color-mix(in srgb, var(--ui-wash-base) 4%, transparent);
  color: var(--ui-dim-2);
  font: inherit;
  font-size: 13px;
  cursor: pointer;
}
.search-pill:hover {
  color: var(--ui-text-soft);
  border-color: var(--ui-border-strong);
}
.search-pill.wide {
  width: 100%;
  margin: 14px 0 2px;
}
.icon-btn {
  width: 36px;
  height: 36px;
  border-radius: 9px;
  border: 0;
  background: none;
  color: var(--ui-text-soft);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.icon-btn:hover,
.icon-btn.open,
.icon-btn.on {
  background: color-mix(in srgb, var(--ui-wash-base) 8%, transparent);
  color: var(--ui-heading);
}

/* shared drop-down look; solid, so big page text never shows through */
.nav-menu {
  position: fixed;
  z-index: 130;
  background: var(--ui-popover);
  border: 1px solid var(--ui-border-strong);
  border-radius: 14px;
  box-shadow:
    0 24px 60px color-mix(in srgb, var(--ui-scrim-base) 55%, transparent),
    0 2px 10px color-mix(in srgb, var(--ui-scrim-base) 30%, transparent);
  padding: 6px;
}
.media-menu {
  top: 52px;
  width: 300px;
}
.pages-menu {
  top: 52px;
  width: 260px;
}
.pages-btn {
  display: none;
}
.recent-menu {
  top: 52px;
  width: 320px;
  max-height: calc(100vh - 72px);
  overflow-y: auto;
}
.menu-label {
  padding: 10px 10px 4px;
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: color-mix(in srgb, var(--ui-wash-base) 38%, transparent);
}
.menu-row {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  min-height: 34px;
  padding: 0 10px;
  box-sizing: border-box;
  border: 0;
  border-radius: 8px;
  background: none;
  color: var(--ui-text-soft);
  font: inherit;
  font-size: 13.5px;
  text-align: left;
  cursor: pointer;
}
.menu-row:hover,
.menu-row.on {
  background: color-mix(in srgb, var(--ui-wash-base) 7%, transparent);
  color: var(--ui-heading);
}
.title-row img {
  width: 20px;
  height: 28px;
  border-radius: 4px;
  object-fit: cover;
  flex-shrink: 0;
}
.title-row .t {
  flex: 1;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.count {
  margin-left: auto;
  font-size: 12px;
  color: var(--ui-faint-2);
  flex-shrink: 0;
}
.menu-empty {
  margin: 0;
  padding: 12px;
  font-size: 13px;
  color: var(--ui-dim-2);
}

/* ---- guide button ---- */
.guide-btn {
  position: fixed;
  left: 16px;
  bottom: 16px;
  z-index: 120;
  width: 50px;
  height: 50px;
  border: 0;
  border-radius: 15px;
  background: var(--ui-accent);
  color: var(--ui-on-accent);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 10px 28px
    color-mix(in srgb, var(--ui-scrim-base) 55%, transparent);
  transition:
    transform 0.2s cubic-bezier(0.22, 1, 0.36, 1),
    box-shadow 0.2s ease;
}
.guide-btn:hover {
  transform: translateY(-2px);
}
.guide-btn.open {
  box-shadow:
    0 0 0 4px color-mix(in srgb, var(--ui-accent) 30%, transparent),
    0 10px 28px color-mix(in srgb, var(--ui-scrim-base) 55%, transparent);
}
.guide-btn .i {
  width: 22px;
  height: 22px;
}
.guide {
  left: 16px;
  bottom: 78px;
  width: min(680px, calc(100vw - 32px));
  max-height: calc(100vh - 96px);
  overflow-y: auto;
  box-sizing: border-box;
  padding: 16px 18px 18px;
  border-radius: 18px;
}
.guide-tabs {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 6px;
}
.gt {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 12px 4px;
  border: 0;
  border-radius: 11px;
  background: color-mix(in srgb, var(--ui-wash-base) 5%, transparent);
  color: var(--ui-text-soft);
  font: inherit;
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
}
.gt:hover {
  background: color-mix(in srgb, var(--ui-wash-base) 9%, transparent);
  color: var(--ui-heading);
}
.gt.on {
  background: color-mix(in srgb, var(--ui-accent) 16%, transparent);
  color: var(--ui-accent-bright);
}
.guide-covers {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 10px;
  padding: 0 2px;
}
.gcov {
  display: block;
  min-width: 0;
  padding: 0;
  border: 0;
  background: none;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.gcov img,
.gcov-blank {
  display: block;
  width: 100%;
  aspect-ratio: 2 / 3;
  object-fit: cover;
  border-radius: 7px;
  background: var(--ui-surface-2);
  transition: transform 0.18s cubic-bezier(0.22, 1, 0.36, 1);
}
.gcov:hover img {
  transform: translateY(-3px);
}
.gcov b {
  display: block;
  margin-top: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--ui-text-soft);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.gcov small {
  display: block;
  font-size: 11px;
  color: var(--ui-faint-2);
}
.quick {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 0 2px;
}
.qa {
  display: inline-flex;
  align-items: center;
  font: inherit;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--ui-text-soft);
  background: color-mix(in srgb, var(--ui-wash-base) 5%, transparent);
  border: 1px solid var(--ui-border);
  border-radius: 999px;
  padding: 6px 12px;
  cursor: pointer;
}
.qa:hover {
  border-color: var(--ui-accent-line);
  color: var(--ui-heading);
}

/* ---- dock ---- */
.dock {
  position: fixed;
  left: 50%;
  bottom: 16px;
  transform: translateX(-50%);
  z-index: 110;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 7px 9px;
  border-radius: 18px;
  border: 1px solid var(--ui-border-strong);
  background: color-mix(in srgb, var(--ui-popover) 88%, transparent);
  backdrop-filter: blur(18px) saturate(1.15);
  box-shadow: 0 18px 44px
    color-mix(in srgb, var(--ui-scrim-base) 55%, transparent);
}
.dk {
  position: relative;
  width: 42px;
  height: 42px;
  border: 0;
  border-radius: 12px;
  background: none;
  color: var(--ui-text-soft);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  text-decoration: none;
  transition:
    transform 0.18s cubic-bezier(0.22, 1, 0.36, 1),
    background 0.15s ease;
}
.dk:hover {
  transform: translateY(-3px);
  background: color-mix(in srgb, var(--ui-wash-base) 8%, transparent);
  color: var(--ui-heading);
}
.dk.on {
  color: var(--ui-accent);
}
.dk.on::after {
  content: "";
  position: absolute;
  bottom: -4px;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--ui-accent);
}
.dk.cover img {
  width: 30px;
  height: 42px;
  object-fit: cover;
  border-radius: 6px;
}
.tip {
  position: absolute;
  bottom: 54px;
  left: 50%;
  transform: translate(-50%, 4px);
  opacity: 0;
  pointer-events: none;
  font-size: 12px;
  font-weight: 600;
  color: var(--ui-heading);
  background: var(--ui-popover);
  border: 1px solid var(--ui-border-strong);
  border-radius: 7px;
  padding: 3px 8px;
  white-space: nowrap;
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  transition:
    opacity 0.12s ease,
    transform 0.12s ease;
}
.dk:hover .tip {
  opacity: 1;
  transform: translate(-50%, 0);
}
.dk-badge {
  position: absolute;
  top: 2px;
  right: 2px;
  min-width: 15px;
  height: 15px;
  padding: 0 3px;
  box-sizing: border-box;
  border-radius: 999px;
  background: var(--ui-accent);
  color: var(--ui-on-accent);
  font-size: 10px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}
.dsep {
  width: 1px;
  height: 28px;
  margin: 0 5px;
  background: var(--ui-border-strong);
}

/* ---- motion ---- */
.nav-pop-enter-active,
.guide-pop-enter-active {
  transition:
    opacity 0.16s ease,
    transform 0.22s cubic-bezier(0.22, 1, 0.36, 1);
}
.nav-pop-leave-active,
.guide-pop-leave-active {
  transition:
    opacity 0.12s ease,
    transform 0.12s ease;
}
.nav-pop-enter-from,
.nav-pop-leave-to {
  opacity: 0;
  transform: translateY(-6px) scale(0.98);
}
.guide-pop-enter-from,
.guide-pop-leave-to {
  opacity: 0;
  transform: translateY(10px) scale(0.97);
  transform-origin: bottom left;
}
@media (prefers-reduced-motion: reduce) {
  .nav-pop-enter-active,
  .nav-pop-leave-active,
  .guide-pop-enter-active,
  .guide-pop-leave-active,
  .dk,
  .guide-btn {
    transition: none;
  }
}
/* a narrow window: the brand gives up its name, and the dock keeps only the
   pages (no covers) and never runs past the edges */
@media (max-width: 900px) {
  .topnav {
    gap: 10px;
    padding: 0 10px;
  }
  .topnav-brand b {
    display: none;
  }
}
@media (max-width: 620px) {
  .topnav-links {
    display: none;
  }
  .pages-btn {
    display: inline-flex;
  }
  .topnav-right {
    gap: 2px;
  }
  .dock .cover,
  .dock .dsep {
    display: none;
  }
  .dock {
    max-width: calc(100vw - 24px);
    gap: 2px;
    padding: 6px;
  }
  .dk {
    width: 38px;
    height: 38px;
  }
  .guide-tabs,
  .guide-covers {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
@media (max-width: 760px) {
  .search-pill:not(.wide) {
    width: 36px;
    padding: 0;
    justify-content: center;
  }
  .search-pill:not(.wide) span,
  .search-pill:not(.wide) kbd {
    display: none;
  }
}
</style>
