<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { createInitialAdmin } from "../services/setup";
import { checkAuth } from "../state/auth";

const route = useRoute();
const router = useRouter();
const username = ref(""); const email = ref(""); const password = ref(""); const confirmPassword = ref("");
const error = ref<string | null>(route.query.backend_error ? "The frontend cannot reach the backend yet. Start the backend service, then reload this page." : null);
const loading = ref(false);
async function submit() {
  error.value = null;
  if (password.value !== confirmPassword.value) { error.value = "Passwords do not match."; return; }
  loading.value = true;
  try { await createInitialAdmin(username.value.trim(), email.value.trim(), password.value); await checkAuth(); router.push("/"); }
  catch (err) { error.value = err instanceof Error ? err.message : "Setup failed."; }
  finally { loading.value = false; }
}
</script>
<template>
  <main class="setup-page"><form class="setup-card" @submit.prevent="submit">
    <div class="brand"><span>🎮</span><h1>Archive setup</h1></div>
    <p class="subtitle">Create the administrator account for this installation.</p>
    <label><span>Username</span><input v-model="username" autocomplete="username" required /></label>
    <label><span>Email</span><input v-model="email" type="email" autocomplete="email" required /></label>
    <label><span>Password</span><input v-model="password" type="password" autocomplete="new-password" minlength="9" required /></label>
    <label><span>Confirm password</span><input v-model="confirmPassword" type="password" autocomplete="new-password" minlength="9" required /></label>
    <p class="hint">Use at least 9 characters with uppercase, lowercase, and a symbol.</p>
    <div v-if="error" class="error">{{ error }}</div>
    <button :disabled="loading || Boolean(route.query.backend_error)">{{ loading ? "Creating account…" : "Create administrator" }}</button>
  </form></main>
</template>
<style scoped>
.setup-page{min-height:100vh;display:flex;align-items:center;justify-content:center;background:#121212;font-family:system-ui,sans-serif}.setup-card{width:100%;max-width:400px;background:#1a1a1a;border:1px solid #2a2a2a;border-radius:14px;padding:32px;display:flex;flex-direction:column;gap:14px}.brand{display:flex;align-items:center;gap:10px;justify-content:center;color:#fff}.brand h1{font-size:1.4rem;margin:0}.subtitle,.hint{color:#999;font-size:13px;text-align:center}.setup-card label{display:flex;flex-direction:column;gap:6px;color:#ccc;font-size:13px}.setup-card input{background:#111;border:1px solid #3a3a3a;border-radius:8px;color:#fff;padding:10px;font:inherit}.setup-card button{background:#d68a34;border:0;border-radius:8px;padding:11px;font-weight:600;cursor:pointer}.setup-card button:disabled{opacity:.6}.error{color:#fca5a5;background:rgba(220,38,38,.1);border:1px solid rgba(220,38,38,.3);border-radius:8px;padding:8px;font-size:13px}
</style>
