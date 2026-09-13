<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { currentUser } from "../state/auth";
import { logout } from "../services/auth";

const route = useRoute();
const router = useRouter();
const width = ref(260);
const collapsed = ref(false);
const resizing = ref(false);

const WIDTH_KEY = "archiveDesktopSidebarWidth";
const COLLAPSED_KEY = "archiveDesktopSidebarCollapsed";

onMounted(() => {
  const savedWidth = Number(localStorage.getItem(WIDTH_KEY));
  if (Number.isFinite(savedWidth)) width.value = Math.min(360, Math.max(220, savedWidth));
  collapsed.value = localStorage.getItem(COLLAPSED_KEY) === "true";
  applySidebarWidth();
});

function applySidebarWidth() {
  document.documentElement.style.setProperty(
    "--desktop-sidebar-width",
    `${collapsed.value ? 72 : width.value}px`,
  );
}

watch([width, collapsed], () => {
  applySidebarWidth();
  if (!resizing.value) {
    localStorage.setItem(WIDTH_KEY, String(width.value));
    localStorage.setItem(COLLAPSED_KEY, String(collapsed.value));
  }
});

function isActive(path: string) {
  if (path === "/") return route.path === "/";
  return route.path === path || route.path.startsWith(`${path}/`);
}

const gamesExpanded = ref(isActive("/games") || isActive("/collections"));
const cardsExpanded = ref(isActive("/cards") || isActive("/sets"));

const initials = computed(() => currentUser.value?.username?.slice(0, 2).toUpperCase() || "?");

function startResize(event: PointerEvent) {
  if (collapsed.value) return;
  resizing.value = true;
  (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
  const move = (e: PointerEvent) => {
    width.value = Math.min(360, Math.max(220, e.clientX));
    applySidebarWidth();
  };
  const stop = () => {
    resizing.value = false;
    localStorage.setItem(WIDTH_KEY, String(width.value));
    window.removeEventListener("pointermove", move);
    window.removeEventListener("pointerup", stop);
  };
  window.addEventListener("pointermove", move);
  window.addEventListener("pointerup", stop);
}

async function handleLogout() {
  await logout();
  currentUser.value = null;
  router.push("/login");
}
</script>

<template>
  <aside class="desktop-sidebar" :class="{ collapsed }" :style="{ width: `${collapsed ? 72 : width}px` }">
    <div class="desktop-sidebar-brand">
      <router-link to="/" class="brand-link" aria-label="Go to Archive home">
        <span class="brand-icon">🎮</span>
        <span v-if="!collapsed" class="brand-name">Archive</span>
      </router-link>
      <button type="button" class="collapse-button" :title="collapsed ? 'Expand sidebar' : 'Collapse sidebar'" :aria-label="collapsed ? 'Expand sidebar' : 'Collapse sidebar'" @click="collapsed = !collapsed">
        {{ collapsed ? "›" : "‹" }}
      </button>
    </div>

    <nav class="desktop-sidebar-nav" aria-label="Main navigation">
      <router-link to="/" class="desktop-sidebar-item" :class="{ active: isActive('/') }" :title="collapsed ? 'Home' : undefined">
        <span class="nav-icon">⌂</span><span v-if="!collapsed">Home</span>
      </router-link>

      <div class="desktop-sidebar-parent" :class="{ active: isActive('/games') && !isActive('/collections') }">
        <router-link to="/games" class="desktop-sidebar-item parent-link" :title="collapsed ? 'Games' : undefined">
          <span class="nav-icon">🎮</span><span v-if="!collapsed">Games</span>
        </router-link>
        <button v-if="!collapsed" type="button" class="expand-button" :class="{ expanded: gamesExpanded }" :title="gamesExpanded ? 'Collapse Games' : 'Expand Games'" @click="gamesExpanded = !gamesExpanded">›</button>
      </div>
      <div v-if="gamesExpanded && !collapsed" class="desktop-sidebar-subitems">
        <router-link to="/collections" class="desktop-sidebar-subitem" :class="{ active: isActive('/collections') }">▰ <span>Collections</span></router-link>
      </div>

      <div class="desktop-sidebar-parent" :class="{ active: isActive('/cards') && !isActive('/sets') }">
        <router-link to="/cards" class="desktop-sidebar-item parent-link" :title="collapsed ? 'Cards' : undefined">
          <span class="nav-icon">▤</span><span v-if="!collapsed">Cards</span>
        </router-link>
        <button v-if="!collapsed" type="button" class="expand-button" :class="{ expanded: cardsExpanded }" :title="cardsExpanded ? 'Collapse Cards' : 'Expand Cards'" @click="cardsExpanded = !cardsExpanded">›</button>
      </div>
      <div v-if="cardsExpanded && !collapsed" class="desktop-sidebar-subitems">
        <router-link to="/cards" class="desktop-sidebar-subitem" :class="{ active: route.path === '/cards' }">▤ <span>All Cards</span></router-link>
        <router-link to="/sets" class="desktop-sidebar-subitem" :class="{ active: isActive('/sets') }">▦ <span>Sets</span></router-link>
      </div>

      <router-link to="/inbox" class="desktop-sidebar-item" :class="{ active: isActive('/inbox') }" :title="collapsed ? 'Inbox' : undefined">
        <span class="nav-icon">✉</span><span v-if="!collapsed">Inbox</span>
      </router-link>
      <router-link to="/bounties" class="desktop-sidebar-item" :class="{ active: isActive('/bounties') }" :title="collapsed ? 'Bounties' : undefined">
        <span class="nav-icon">◎</span><span v-if="!collapsed">Bounties</span>
      </router-link>
      <div class="desktop-sidebar-item disabled" :title="collapsed ? 'Movies & TV — soon' : undefined">
        <span class="nav-icon">▣</span><span v-if="!collapsed">Movies & TV</span><small v-if="!collapsed">soon</small>
      </div>
    </nav>

    <div class="desktop-sidebar-spacer"></div>

    <router-link to="/settings?section=profile" class="desktop-sidebar-profile" :title="collapsed ? 'Profile' : undefined">
      <span class="desktop-profile-avatar">{{ initials }}</span>
      <span v-if="!collapsed" class="desktop-profile-copy"><strong>{{ currentUser?.username || "Profile" }}</strong><small>Profile</small></span>
    </router-link>
    <router-link to="/settings" class="desktop-sidebar-item" :class="{ active: isActive('/settings') }" :title="collapsed ? 'Settings' : undefined">
      <span class="nav-icon">⚙</span><span v-if="!collapsed">Settings</span>
    </router-link>
    <button type="button" class="desktop-sidebar-item logout" @click="handleLogout" :title="collapsed ? 'Log out' : undefined">
      <span class="nav-icon">↪</span><span v-if="!collapsed">Log out</span>
    </button>

    <div v-if="!collapsed" class="resize-handle" aria-hidden="true" @pointerdown="startResize"></div>
  </aside>
</template>

<style scoped>
.desktop-sidebar{position:fixed;inset:0 auto 0 0;z-index:120;box-sizing:border-box;display:flex;flex-direction:column;gap:6px;padding:16px 12px 14px;background:#151515;border-right:1px solid #2a2a2a;color:#ccc;font-family:system-ui,sans-serif;transition:width .16s ease;box-shadow:10px 0 30px rgba(0,0,0,.18)}
.desktop-sidebar.collapsed{padding-left:10px;padding-right:10px}
.desktop-sidebar-brand{display:flex;align-items:center;gap:8px;min-height:40px;padding:2px 4px 14px}
.brand-link{min-width:0;display:flex;align-items:center;gap:10px;color:#fff;text-decoration:none;font-weight:800;font-size:17px;flex:1}
.brand-icon{font-size:21px;flex:0 0 auto}.brand-name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.collapse-button{width:30px;height:30px;flex:0 0 30px;border:1px solid #303030;border-radius:7px;background:#1c1c1c;color:#aaa;cursor:pointer;font-size:18px;line-height:1}.collapse-button:hover{color:#fff;background:#252525}
.desktop-sidebar-nav{display:flex;flex-direction:column;gap:3px}.desktop-sidebar-item,.desktop-sidebar-profile{min-height:40px;box-sizing:border-box;display:flex;align-items:center;gap:11px;padding:9px 10px;border-radius:8px;border:0;background:transparent;color:#aaa;font:inherit;font-size:13px;text-decoration:none;cursor:pointer;text-align:left;width:100%}.desktop-sidebar-item:hover,.desktop-sidebar-profile:hover,.desktop-sidebar-item.active{color:#fff;background:rgba(255,255,255,.06)}.desktop-sidebar-item.active{color:#d68a34}.nav-icon{width:18px;text-align:center;flex:0 0 18px}.desktop-sidebar-parent{display:flex;align-items:center;border-radius:8px}.desktop-sidebar-parent.active{background:rgba(255,255,255,.06)}.desktop-sidebar-parent>.parent-link{flex:1}.desktop-sidebar-parent.active>.parent-link{color:#d68a34}.expand-button{width:30px;height:34px;border:0;background:transparent;color:#777;cursor:pointer;font-size:19px;transform:rotate(0deg)}.expand-button.expanded{transform:rotate(90deg);color:#aaa}.desktop-sidebar-subitems{display:flex;flex-direction:column;gap:2px;margin:0 0 3px 30px;padding-left:8px;border-left:1px solid #303030}.desktop-sidebar-subitem{display:flex;align-items:center;gap:9px;min-height:34px;padding:7px 9px;border-radius:7px;color:#888;text-decoration:none;font-size:12px}.desktop-sidebar-subitem:hover{color:#fff;background:rgba(255,255,255,.04)}.desktop-sidebar-subitem.active{color:#d68a34;background:rgba(214,138,52,.08)}.disabled{cursor:default!important;color:#666!important}.disabled small{margin-left:auto;color:#555;font-size:9px;text-transform:uppercase;letter-spacing:.06em}.desktop-sidebar-spacer{flex:1}.desktop-sidebar-profile{border-top:1px solid #2a2a2a;border-radius:0;padding:14px 10px 8px}.desktop-profile-avatar{width:32px;height:32px;flex:0 0 32px;display:grid;place-items:center;border-radius:50%;background:#d68a34;color:#111;font-size:11px;font-weight:800}.desktop-profile-copy{min-width:0;display:flex;flex-direction:column;gap:1px}.desktop-profile-copy strong{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#fff}.desktop-profile-copy small{color:#777;font-size:10px}.logout{color:#888}.resize-handle{position:absolute;top:0;right:-3px;width:6px;height:100%;cursor:col-resize;z-index:2}.resize-handle:hover{background:rgba(214,138,52,.18)}
@media(max-width:1024px){.desktop-sidebar{display:none}}
</style>
