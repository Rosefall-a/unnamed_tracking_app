<script setup lang="ts">
import { useRoute } from "vue-router";
import SidebarNav from "./components/SidebarNav.vue";
import HomeProfileButton from "./components/HomeProfileButton.vue";
import TaskProgressToast from "./components/TaskProgressToast.vue";
import ShortcutsHelp from "./components/ShortcutsHelp.vue";
import CommandPalette from "./components/CommandPalette.vue";
import { authChecked } from "./state/auth";

const route=useRoute();
</script>
<template><template v-if="authChecked||route.path==='/setup'||route.path==='/login/oidcstart'||route.path==='/reset-password"><SidebarNav v-if="route.path!=='/login'&&route.path!=='/setup'&&route.path!=='/login/oidcstart'&&route.path!=='/reset-password'"/><router-view/><HomeProfileButton v-if="route.path==='/'"/><TaskProgressToast v-if="route.path!=='/setup'&&route.path!=='/login/oidcstart'&&route.path!=='/reset-password'"/><ShortcutsHelp v-if="route.path!=='/login'&&route.path!=='/setup'&&route.path!=='/login/oidcstart'&&route.path!=='/reset-password'"/><CommandPalette v-if="route.path!=='/login'&&route.path!=='/setup'&&route.path!=='/login/oidcstart'&&route.path!=='/reset-password'"/></template><main v-else class="app-loading"><p>Loading…</p></main></template>
<style scoped>.app-loading{min-height:100vh;display:flex;align-items:center;justify-content:center;background:#121212;color:#999;font-family:system-ui,sans-serif}:global(.home .profile-chip){pointer-events:none}</style>
