<script setup lang="ts">
import { computed, ref, watch, nextTick, onMounted, onUnmounted } from "vue";
import {
  RouterLink,
  useRoute,
  useRouter,
  type RouteLocationRaw,
} from "vue-router";
import { logout } from "../services/auth";
import {
  pluginNavigation,
  refreshPluginExtensions,
} from "../state/pluginExtensions";
import { currentUser } from "../state/auth";
import {
  approvePluginAction,
  dispatchPluginAction,
} from "../services/pluginUi";
import { inboxCount, refreshInboxCount } from "../state/inbox";
import { mediaUnread, refreshMediaNotifications } from "../state/notifications";
import {
  effectiveSidebarMode,
  navigationViewport,
  sidebarWidth,
  setSidebarWidth,
  resetSidebarWidth,
  sidebarResizing,
  SIDEBAR_MIN_WIDTH,
  SIDEBAR_MAX_WIDTH,
} from "../state/sidebarMode";
import { isCommandPaletteOpen } from "../state/commandPalette";
import AppIcon from "./AppIcon.vue";
import { containModalTab } from "../services/focus";

const route = useRoute();
const router = useRouter();
const open = ref(false);
const railExpanded = ref(false);
const pane = ref<HTMLElement | null>(null);
const isPhone = computed(() => navigationViewport.value === "phone");
const isModal = computed(() => effectiveSidebarMode.value === "overlay");
const visible = computed(() => !isModal.value || open.value);
const collapsed = computed(
  () => effectiveSidebarMode.value === "rail" && !railExpanded.value,
);
const isMockData = import.meta.env.VITE_USE_MOCK_DATA === "true";
const actionError = ref<string | null>(null);

function isActive(path: string) {
  return (
    route.path === path || (path !== "/" && route.path.startsWith(`${path}/`))
  );
}
const groups = [
  {
    id: "games",
    label: "Games",
    icon: "games",
    paths: ["/games", "/collections"],
    entries: [
      { path: "/games", label: "All games", icon: "games" },
      { path: "/collections", label: "Collections", icon: "collections" },
    ],
  },
  {
    id: "cards",
    label: "Cards",
    icon: "cards",
    paths: ["/cards", "/sets"],
    entries: [
      { path: "/cards", label: "All cards", icon: "cards" },
      { path: "/sets", label: "Sets", icon: "sets" },
    ],
  },
  {
    id: "media",
    label: "Media",
    icon: "media",
    paths: ["/movies", "/tv", "/anime", "/lists"],
    entries: [
      { path: "/movies", label: "Movies", icon: "media" },
      { path: "/tv", label: "TV shows", icon: "tv" },
      { path: "/anime", label: "Anime", icon: "anime" },
      { path: "/lists", label: "Lists", icon: "lists" },
    ],
  },
];
const expandedGroups = ref(
  new Set(
    groups
      .filter((group) => group.paths.some(isActive))
      .map((group) => group.id),
  ),
);
function toggleGroup(id: string) {
  if (collapsed.value) railExpanded.value = true;
  const next = new Set(expandedGroups.value);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  expandedGroups.value = next;
}
const tools = [
  { path: "/bounties", label: "Bounties", icon: "bounties" },
  { path: "/calendar", label: "Calendar", icon: "calendar" },
  { path: "/statistics", label: "Statistics", icon: "statistics" },
  { path: "/notifications", label: "Notifications", icon: "notifications" },
];
const mainPluginNavigation = computed(() =>
  pluginNavigation.value.filter(
    (item) =>
      (item.location === "main.sidebar" ||
        (item.location === "administration" && currentUser.value?.is_admin)) &&
      (!item.adminOnly || currentUser.value?.is_admin),
  ),
);
function pluginNavigationTarget(
  item: (typeof mainPluginNavigation.value)[number],
): RouteLocationRaw {
  if (item.settingsSectionId)
    return { path: "/settings", query: { section: item.settingsSectionId } };
  return {
    name: "plugin-route",
    params: {
      pluginId: item.pluginId,
      pluginPath: item.routePath || item.pageId,
    },
  };
}
async function activatePluginNavigation(
  item: (typeof mainPluginNavigation.value)[number],
) {
  if (!item.action || !approvePluginAction(item.action, window.confirm)) return;
  actionError.value = null;
  try {
    await dispatchPluginAction(
      item.pluginId,
      item.action.id,
      {},
      undefined,
      Boolean(item.action.confirmation),
    );
    close();
  } catch (error) {
    actionError.value =
      error instanceof Error
        ? error.message
        : "Could not run the plugin action.";
  }
}
function close() {
  if (pane.value instanceof HTMLDialogElement && pane.value.open)
    pane.value.close();
  open.value = false;
}
function openMenu(group?: string) {
  if (group) expandedGroups.value = new Set([group]);
  open.value = true;
}
watch(
  () => route.fullPath,
  () => {
    close();
    const next = new Set(expandedGroups.value);
    groups
      .filter((group) => group.paths.some(isActive))
      .forEach((group) => next.add(group.id));
    expandedGroups.value = next;
  },
);
watch(effectiveSidebarMode, () => {
  close();
  railExpanded.value = false;
});
// Native modal dialogs provide focus containment, background inertness and
// Escape handling. Close before removing the dialog to restore trigger focus.
let previousOverflow = "";
watch([open, isModal], async ([opened, modal]) => {
  if (!opened || !modal) {
    if (scrollLocked) {
      document.body.style.overflow = previousOverflow;
      scrollLocked = false;
    }
    return;
  }
  await nextTick();
  if (
    !open.value ||
    !isModal.value ||
    !(pane.value instanceof HTMLDialogElement)
  )
    return;
  if (!scrollLocked) {
    previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    scrollLocked = true;
  }
  if (!pane.value.open) pane.value.showModal();
});
let scrollLocked = false;
function onBackdropClick(event: MouseEvent) {
  if (!isModal.value || !pane.value || event.target !== pane.value) return;
  const rect = pane.value.getBoundingClientRect();
  if (
    event.clientX < rect.left ||
    event.clientX > rect.right ||
    event.clientY < rect.top ||
    event.clientY > rect.bottom
  )
    close();
}
function search() {
  close();
  isCommandPaletteOpen.value = true;
}
function startResize(event: PointerEvent) {
  if (isPhone.value || effectiveSidebarMode.value === "rail") return;
  event.preventDefault();
  sidebarResizing.value = true;
  document.addEventListener("pointermove", resize);
  document.addEventListener("pointerup", stopResize);
  document.addEventListener("pointercancel", stopResize);
}
function resize(event: PointerEvent) {
  setSidebarWidth(event.clientX - 12);
}
function stopResize() {
  sidebarResizing.value = false;
  document.removeEventListener("pointermove", resize);
  document.removeEventListener("pointerup", stopResize);
  document.removeEventListener("pointercancel", stopResize);
}
function resizeWithKeyboard(event: KeyboardEvent) {
  if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
    event.preventDefault();
    setSidebarWidth(
      sidebarWidth.value + (event.key === "ArrowRight" ? 10 : -10),
    );
  } else if (event.key === "Home" || event.key === "End") {
    event.preventDefault();
    setSidebarWidth(
      event.key === "Home" ? SIDEBAR_MIN_WIDTH : SIDEBAR_MAX_WIDTH,
    );
  }
}
async function handleLogout() {
  try {
    await logout();
    currentUser.value = null;
    close();
    await router.push("/login");
  } catch {
    actionError.value = "Could not sign out. Please try again.";
  }
}
let notificationTimer: number | undefined;
onMounted(() => {
  void refreshInboxCount();
  void refreshPluginExtensions();
  void refreshMediaNotifications();
  notificationTimer = window.setInterval(
    refreshMediaNotifications,
    5 * 60 * 1000,
  );
});
onUnmounted(() => {
  window.clearInterval(notificationTimer);
  stopResize();
  if (scrollLocked) document.body.style.overflow = previousOverflow;
});
</script>

<template>
  <div class="nav-shell">
    <a href="#main-content" class="skip-link">Skip to content</a>
    <button
      v-if="isModal && !isPhone"
      type="button"
      class="menu-toggle"
      aria-label="Open menu"
      aria-controls="app-navigation"
      :aria-expanded="open"
      @click="openMenu()"
    >
      <AppIcon name="menu" />
    </button>
    <component
      :is="isModal ? 'dialog' : 'aside'"
      v-if="visible"
      id="app-navigation"
      ref="pane"
      class="navigation"
      :class="{
        collapsed,
        'phone-navigation': isPhone,
        resizing: sidebarResizing,
      }"
      :style="{ '--sidebar-width': `${sidebarWidth}px` }"
      aria-label="Main navigation"
      @cancel.prevent="close"
      @close="open = false"
      @click="onBackdropClick"
      @keydown="isModal && containModalTab($event, pane)"
    >
      <header class="nav-brand">
        <RouterLink
          to="/"
          class="brand-link"
          aria-label="Archive Home"
          @click="close"
          ><span class="brand-symbol"><AppIcon name="collections" /></span
          ><span class="nav-label brand-name">Archive</span></RouterLink
        >
        <button
          v-if="isModal"
          type="button"
          class="nav-icon-button"
          aria-label="Close menu"
          autofocus
          @click="close"
        >
          <AppIcon name="close" />
        </button>
        <button
          v-else-if="effectiveSidebarMode === 'rail'"
          type="button"
          class="nav-icon-button rail-toggle"
          :aria-label="collapsed ? 'Expand navigation' : 'Collapse navigation'"
          :aria-expanded="railExpanded"
          @click="railExpanded = !railExpanded"
        >
          <AppIcon :name="collapsed ? 'menu' : 'close'" :size="18" />
        </button>
      </header>
      <span v-if="isMockData && !collapsed" class="mock-badge"
        >Sample data</span
      >
      <button
        type="button"
        class="nav-item nav-search"
        aria-label="Search library"
        title="Search library"
        @click="search"
      >
        <AppIcon name="search" /><span class="nav-label">Search library</span
        ><kbd class="nav-label">Ctrl K</kbd>
      </button>
      <nav class="nav-scroll" aria-label="Library and tools">
        <RouterLink
          to="/"
          class="nav-item"
          :class="{ active: isActive('/') }"
          :aria-current="isActive('/') ? 'page' : undefined"
          title="Home"
          @click="close"
          ><AppIcon name="home" /><span class="nav-label"
            >Home</span
          ></RouterLink
        >
        <p class="nav-group-label nav-label">Your library</p>
        <div v-for="group in groups" :key="group.id" class="nav-group">
          <button
            type="button"
            class="nav-item"
            :class="{ 'group-active': group.paths.some(isActive) }"
            :aria-label="group.label"
            :title="group.label"
            :aria-expanded="!collapsed && expandedGroups.has(group.id)"
            :aria-controls="`nav-${group.id}`"
            @click="toggleGroup(group.id)"
          >
            <AppIcon :name="group.icon" /><span class="nav-label">{{
              group.label
            }}</span
            ><AppIcon
              class="nav-chevron nav-label"
              :class="{ expanded: expandedGroups.has(group.id) }"
              name="chevron"
              :size="14"
            />
          </button>
          <div
            v-if="!collapsed && expandedGroups.has(group.id)"
            :id="`nav-${group.id}`"
            class="nav-children"
          >
            <RouterLink
              v-for="entry in group.entries"
              :key="entry.path"
              :to="entry.path"
              class="nav-item"
              :class="{ active: isActive(entry.path) }"
              :aria-current="isActive(entry.path) ? 'page' : undefined"
              @click="close"
              ><AppIcon :name="entry.icon" :size="17" /><span>{{
                entry.label
              }}</span></RouterLink
            >
          </div>
        </div>
        <p class="nav-group-label nav-label">Keep track</p>
        <RouterLink
          v-for="tool in tools"
          :key="tool.path"
          :to="tool.path"
          class="nav-item"
          :class="{ active: isActive(tool.path) }"
          :aria-current="isActive(tool.path) ? 'page' : undefined"
          :title="tool.label"
          :aria-label="tool.label"
          @click="close"
          ><AppIcon :name="tool.icon" /><span class="nav-label">{{
            tool.label
          }}</span
          ><span
            v-if="tool.path === '/notifications' && mediaUnread"
            class="nav-badge"
            >{{ mediaUnread > 99 ? "99+" : mediaUnread }}</span
          ></RouterLink
        >
        <template v-if="mainPluginNavigation.length">
          <p class="nav-group-label nav-label">Extensions</p>
          <component
            :is="item.action ? 'button' : RouterLink"
            v-for="item in mainPluginNavigation"
            :key="`${item.pluginId}:${item.contributionId}`"
            :to="item.action ? undefined : pluginNavigationTarget(item)"
            :type="item.action ? 'button' : undefined"
            class="nav-item plugin-sidebar-item"
            :class="{ active: isActive(`/plugins/${item.pluginId}`) }"
            :title="item.label"
            :aria-label="item.label"
            @click="item.action ? activatePluginNavigation(item) : close()"
            ><span
              v-if="item.icon"
              class="plugin-navigation-icon"
              aria-hidden="true"
              >{{ item.icon }}</span
            ><AppIcon v-else name="plugin" /><span class="nav-label">{{
              item.label
            }}</span></component
          >
        </template>
        <RouterLink
          to="/settings?section=upload"
          class="nav-item"
          title="Upload"
          aria-label="Upload"
          @click="close"
          ><AppIcon name="upload" /><span class="nav-label">Upload</span
          ><span v-if="inboxCount" class="nav-badge">{{
            inboxCount
          }}</span></RouterLink
        >
      </nav>
      <footer class="nav-footer">
        <RouterLink
          to="/settings?section=appearance"
          class="nav-item"
          :class="{
            active:
              isActive('/settings') &&
              route.query.section !== 'profile' &&
              route.query.section !== 'admin',
          }"
          title="Preferences"
          aria-label="Preferences"
          @click="close"
          ><AppIcon name="settings" /><span class="nav-label"
            >Preferences</span
          ></RouterLink
        >
        <RouterLink
          v-if="currentUser?.is_admin"
          to="/settings?section=admin"
          class="nav-item"
          :class="{
            active: isActive('/settings') && route.query.section === 'admin',
          }"
          title="Administration"
          aria-label="Administration"
          @click="close"
          ><AppIcon name="admin" /><span class="nav-label"
            >Administration</span
          ></RouterLink
        >
        <div v-if="actionError" class="nav-error" role="alert">
          {{ actionError }}
        </div>
        <div class="nav-account">
          <RouterLink
            to="/settings?section=profile"
            class="nav-account-link"
            :title="currentUser?.username"
            aria-label="Your account"
            @click="close"
            ><span class="nav-avatar">{{
              currentUser?.username.slice(0, 2).toUpperCase()
            }}</span
            ><span class="nav-label account-label"
              ><strong>{{ currentUser?.username }}</strong
              ><small>Your account</small></span
            ></RouterLink
          >
          <button
            type="button"
            class="nav-icon-button nav-label"
            title="Sign out"
            aria-label="Sign out"
            @click="handleLogout"
          >
            <AppIcon name="logout" :size="18" />
          </button>
        </div>
      </footer>
      <div
        v-if="!isPhone && effectiveSidebarMode !== 'rail'"
        class="nav-resize"
        role="separator"
        aria-label="Navigation width"
        aria-orientation="vertical"
        tabindex="0"
        :aria-valuemin="SIDEBAR_MIN_WIDTH"
        :aria-valuemax="SIDEBAR_MAX_WIDTH"
        :aria-valuenow="sidebarWidth"
        title="Drag or use arrow keys to resize; double-click to reset"
        @pointerdown="startResize"
        @keydown="resizeWithKeyboard"
        @dblclick="resetSidebarWidth"
      ></div>
    </component>
    <nav v-if="isPhone" class="mobile-tabs" aria-label="Primary navigation">
      <RouterLink
        to="/"
        :class="{ active: isActive('/') }"
        :aria-current="isActive('/') ? 'page' : undefined"
        ><AppIcon name="home" /><span>Home</span></RouterLink
      >
      <button
        type="button"
        :class="{
          active:
            isActive('/games') ||
            isActive('/collections') ||
            isActive('/cards') ||
            isActive('/sets'),
        }"
        aria-controls="app-navigation"
        :aria-expanded="open"
        @click="openMenu('games')"
      >
        <AppIcon name="collections" /><span>Library</span>
      </button>
      <button
        type="button"
        :class="{
          active: ['/movies', '/tv', '/anime', '/lists'].some(isActive),
        }"
        aria-controls="app-navigation"
        :aria-expanded="open"
        @click="openMenu('media')"
      >
        <AppIcon name="media" /><span>Media</span>
      </button>
      <button
        type="button"
        aria-controls="app-navigation"
        :aria-expanded="open"
        @click="openMenu()"
      >
        <AppIcon name="more" /><span>More</span>
      </button>
    </nav>
  </div>
</template>

<style scoped>
.skip-link {
  position: fixed;
  top: -100px;
  left: 20px;
  z-index: var(--ui-z-dialog);
  background: var(--ui-surface);
  color: var(--ui-text);
  padding: 12px 20px;
  border-radius: var(--ui-radius-control);
}
.skip-link:focus {
  top: 16px;
}
.navigation {
  position: fixed;
  inset: 12px auto 12px 12px;
  width: var(--sidebar-width);
  max-width: calc(100vw - 24px);
  height: calc(100dvh - 24px);
  max-height: none;
  margin: 0;
  padding: 16px 10px 10px;
  box-sizing: border-box;
  border: 1px solid var(--ui-border-soft);
  border-radius: var(--ui-radius-nav);
  background: var(--ui-surface);
  color: var(--ui-text);
  z-index: var(--ui-z-drawer);
  font-family: var(--ui-font-family);
  box-shadow: 0 3px 16px rgb(0 0 0 / 3%);
  transition: width var(--ui-motion-normal) var(--ui-motion-easing);
  overflow: visible;
  flex-direction: column;
}
aside.navigation,
.navigation[open] {
  display: flex;
}
dialog.navigation {
  box-shadow: var(--ui-elevation);
}
.navigation::backdrop {
  background: var(--ui-overlay);
  backdrop-filter: blur(4px);
}
.navigation.resizing {
  transition: none;
}
.nav-brand {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 40px;
  gap: 4px;
  margin: 0 4px 18px;
}
.brand-link {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--ui-text);
  text-decoration: none;
  min-width: 0;
}
.brand-symbol {
  display: grid;
  place-items: center;
  background: var(--ui-accent-soft);
  color: var(--ui-accent-text);
  width: 36px;
  height: 36px;
  border-radius: 12px;
  flex-shrink: 0;
}
.brand-name {
  font-size: 20px;
  font-weight: 650;
  letter-spacing: -0.7px;
}
.nav-icon-button {
  display: grid;
  place-items: center;
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  border-radius: 12px;
  border: 0;
  background: transparent;
  color: var(--ui-dim);
  cursor: pointer;
}
.nav-icon-button:hover {
  background: var(--ui-surface-2);
  color: var(--ui-text);
}
.nav-search {
  border: 1px solid var(--ui-border-soft) !important;
  margin-bottom: 16px;
  background: var(--ui-bg) !important;
  font-size: 12px !important;
}
.nav-search kbd {
  margin-left: auto;
  font-size: 10px;
  white-space: nowrap;
  color: var(--ui-faint);
}
.nav-scroll {
  flex: 1;
  overflow-y: auto;
  overscroll-behavior: contain;
  min-height: 0;
  scrollbar-width: thin;
  scrollbar-color: var(--ui-border) transparent;
  padding: 0 2px;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 11px;
  width: 100%;
  min-height: 42px;
  padding: 10px 12px;
  margin: 2px 0;
  box-sizing: border-box;
  border: 0;
  border-radius: var(--ui-radius-row);
  background: transparent;
  color: var(--ui-dim);
  text-align: left;
  font: inherit;
  font-size: 13px;
  font-weight: 500;
  text-decoration: none;
  cursor: pointer;
  line-height: 1.35;
  transition:
    background var(--ui-motion-fast),
    color var(--ui-motion-fast);
}
.nav-item > svg {
  flex-shrink: 0;
}
.nav-item:hover {
  background: var(--ui-surface-2);
  color: var(--ui-text);
}
.nav-item.active {
  color: var(--ui-accent-text);
  background: var(--ui-accent-soft);
}
.nav-item.group-active {
  color: var(--ui-text);
}
.nav-label {
  overflow: hidden;
  text-overflow: ellipsis;
}
.nav-group-label {
  font-size: 10px;
  letter-spacing: 1.1px;
  text-transform: uppercase;
  font-weight: 600;
  color: var(--ui-faint);
  padding: 0 12px;
  margin: 24px 0 10px;
}
.nav-chevron {
  margin-left: auto;
  transition: transform var(--ui-motion-fast);
}
.nav-chevron.expanded {
  transform: rotate(90deg);
}
.nav-children {
  margin: 3px 0 6px 22px;
  padding-left: 5px;
  border-left: 1px solid var(--ui-border-soft);
}
.nav-children .nav-item {
  font-size: 12px;
  min-height: 38px;
  gap: 9px;
  padding-left: 12px;
}
.nav-badge {
  margin-left: auto;
  font-size: 10px;
  background: var(--ui-accent-soft);
  color: var(--ui-accent-text);
  padding: 2px 6px;
  border-radius: 999px;
}
.nav-footer {
  border-top: 1px solid var(--ui-border-soft);
  padding: 10px 2px 0;
  margin-top: 10px;
}
.nav-account {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
  padding: 9px 6px 3px;
  gap: 3px;
}
.nav-account-link {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  text-decoration: none;
  color: var(--ui-text);
  border-radius: 12px;
}
.nav-avatar {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: var(--ui-surface-2);
  color: var(--ui-accent-text);
  font-size: 11px;
  font-weight: 600;
  flex-shrink: 0;
}
.account-label {
  display: flex;
  flex-direction: column;
  gap: 3px;
  font-size: 12px;
}
.account-label strong {
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
}
.account-label small {
  font-size: 10px;
  color: var(--ui-faint);
}
.nav-error {
  color: var(--ui-error);
  font-size: 12px;
  padding: 10px;
}
.plugin-navigation-icon {
  min-width: 20px;
  text-align: center;
}
.mock-badge {
  margin: 0 12px 12px;
  font-size: 11px;
  color: var(--ui-accent-text);
}
.nav-resize {
  position: absolute;
  right: -5px;
  top: 20px;
  bottom: 20px;
  width: 10px;
  cursor: ew-resize;
  touch-action: none;
  border-radius: 10px;
}
.nav-resize:hover,
.nav-resize:focus-visible {
  background: var(--ui-accent-soft);
}
.menu-toggle {
  display: grid;
  place-items: center;
  position: fixed;
  top: 16px;
  left: 16px;
  z-index: var(--ui-z-topbar);
  width: 40px;
  height: 40px;
  border-radius: 14px;
  border: 1px solid var(--ui-border);
  background: var(--ui-surface);
  color: var(--ui-text);
  cursor: pointer;
}
.collapsed {
  width: 64px;
  padding: 12px 6px;
}
.collapsed .nav-label,
.collapsed .brand-link {
  display: none;
}
.collapsed .nav-brand {
  justify-content: center;
  margin: 0 0 16px;
}
.collapsed .nav-item {
  justify-content: center;
  padding: 12px 8px;
  position: relative;
}
.collapsed .nav-badge {
  position: absolute;
  top: 1px;
  right: 0;
  padding: 1px 3px;
  font-size: 9px;
}
.collapsed .nav-account {
  justify-content: center;
  padding: 6px 0;
}
.mobile-tabs {
  display: none;
}
@media (max-width: 760px) {
  .navigation.phone-navigation {
    inset: 10px;
    width: calc(100vw - 20px);
    max-width: none;
    height: calc(100dvh - 20px);
    padding: 20px 16px max(16px, env(safe-area-inset-bottom));
    border-radius: 28px;
  }
  .nav-brand {
    margin-bottom: 20px;
  }
  .brand-name {
    font-size: 23px;
  }
  .nav-item {
    min-height: 50px;
    padding: 14px 16px;
    font-size: 15px;
    gap: 14px;
    border-radius: 18px;
  }
  .nav-children .nav-item {
    min-height: 48px;
    font-size: 14px;
  }
  .nav-icon-button {
    width: 44px;
    height: 44px;
    border-radius: 16px;
  }
  .nav-group-label {
    font-size: 11px;
    margin-top: 20px;
  }
  .nav-account-link {
    min-height: 48px;
  }
  .account-label {
    font-size: 14px;
  }
  .account-label small {
    font-size: 12px;
  }
  .nav-avatar {
    width: 40px;
    height: 40px;
  }
  .mobile-tabs {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    position: fixed;
    bottom: calc(12px + env(safe-area-inset-bottom));
    left: 16px;
    right: 16px;
    padding: 6px;
    border-radius: 26px;
    border: 1px solid var(--ui-border-soft);
    background: var(--ui-surface);
    box-shadow: var(--ui-elevation);
    z-index: var(--ui-z-topbar);
  }
  .mobile-tabs a,
  .mobile-tabs button {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 5px;
    min-height: 56px;
    border: 0;
    border-radius: 20px;
    background: transparent;
    font: inherit;
    font-size: 10px;
    font-weight: 600;
    color: var(--ui-dim);
    text-decoration: none;
    cursor: pointer;
  }
  .mobile-tabs .active {
    background: var(--ui-accent-soft);
    color: var(--ui-accent-text);
  }
}
</style>
