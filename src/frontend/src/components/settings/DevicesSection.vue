<script setup lang="ts">
// Account, Signed-in devices: every browser and app signed in as you, with a
// way to end any of them except this one (Log Out does that).
import { computed, onMounted, ref } from "vue";
import { useConfirm } from "../../state/dialog";
import {
  fetchSessions,
  signOutOtherSessions,
  signOutSession,
  type SignedInSession,
} from "../../services/auth";
import SettingsCard from "./SettingsCard.vue";

const confirm = useConfirm();
const sessions = ref<SignedInSession[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);
const busy = ref<string | null>(null);
const others = computed(() => sessions.value.filter((s) => !s.current));

async function load() {
  error.value = null;
  try {
    sessions.value = await fetchSessions();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Could not load devices.";
  } finally {
    loading.value = false;
  }
}
onMounted(load);

// A readable name from the browser's own description, e.g. "Firefox on
// Windows". Unknown ones say so rather than guessing.
function deviceName(agent: string | null): string {
  if (!agent) return "Unknown browser";
  const a = agent.toLowerCase();
  const browser = a.includes("edg/")
    ? "Edge"
    : a.includes("firefox/")
      ? "Firefox"
      : a.includes("chrome/")
        ? "Chrome"
        : a.includes("safari/")
          ? "Safari"
          : a.includes("python") || a.includes("curl")
            ? "Script"
            : "Browser";
  const os =
    a.includes("iphone") || a.includes("ipad")
      ? "iOS"
      : a.includes("android")
        ? "Android"
        : a.includes("windows")
          ? "Windows"
          : a.includes("mac os")
            ? "macOS"
            : a.includes("linux")
              ? "Linux"
              : "";
  return os ? `${browser} on ${os}` : browser;
}
function initials(agent: string | null): string {
  const name = deviceName(agent);
  return name.includes(" on ")
    ? name.split(" on ")[1].slice(0, 2)
    : name.slice(0, 2);
}
function lastSeen(s: SignedInSession): string {
  if (s.current) return "Active now";
  const at = s.last_seen_at ?? s.created_at;
  const minutes = Math.floor((Date.now() / 1000 - at) / 60);
  if (minutes < 10) return "Active a few minutes ago";
  if (minutes < 60) return `Active ${minutes} minutes ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `Active ${hours} hour${hours === 1 ? "" : "s"} ago`;
  return `Active ${new Date(at * 1000).toLocaleDateString()}`;
}

async function signOut(s: SignedInSession) {
  busy.value = s.id;
  error.value = null;
  try {
    await signOutSession(s.id);
    await load();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Could not sign out.";
  } finally {
    busy.value = null;
  }
}
async function signOutAll() {
  const ok = await confirm({
    title: "Sign out everywhere else?",
    message: `${others.value.length} other device${others.value.length === 1 ? "" : "s"} will need to sign in again. This browser stays signed in.`,
    confirmLabel: "Sign out",
  });
  if (!ok) return;
  busy.value = "all";
  error.value = null;
  try {
    await signOutOtherSessions();
    await load();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Could not sign out.";
  } finally {
    busy.value = null;
  }
}
</script>

<template>
  <SettingsCard
    title="Signed-in devices"
    description="Every browser and app signed in as you. Signing one out ends it right away."
  >
    <template #actions>
      <button
        type="button"
        class="st-btn"
        :disabled="!others.length || busy !== null"
        @click="signOutAll"
      >
        Sign out everywhere else
      </button>
    </template>
    <p v-if="error" class="st-error">{{ error }}</p>
    <p v-if="loading" class="st-muted">Loading…</p>
    <div v-for="s in sessions" :key="s.id" class="st-list-row">
      <span class="st-avatar">{{ initials(s.user_agent) }}</span>
      <div class="st-lbl">
        <strong>{{
          s.current ? "This browser" : deviceName(s.user_agent)
        }}</strong>
        <span
          >{{ s.current ? deviceName(s.user_agent) + " · " : ""
          }}{{ lastSeen(s) }} · signed in
          {{ new Date(s.created_at * 1000).toLocaleDateString() }}</span
        >
      </div>
      <span v-if="s.current" class="st-chip good">This device</span>
      <button
        v-else
        type="button"
        class="st-btn"
        :disabled="busy !== null"
        @click="signOut(s)"
      >
        {{ busy === s.id ? "Signing out…" : "Sign out" }}
      </button>
    </div>
    <p v-if="!loading && !others.length" class="st-muted none">
      No other devices are signed in.
    </p>
  </SettingsCard>
</template>

<style scoped>
.none {
  margin: 10px 0 0;
}
</style>
