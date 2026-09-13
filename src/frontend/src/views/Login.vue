<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { login } from "../services/auth";
import { oidcEnabled, startOidcLogin } from "../services/oidc";
import { checkAuth } from "../state/auth";

const route = useRoute(); const router = useRouter();
const usernameOrEmail = ref(""); const password = ref(""); const error = ref<string | null>(null);
const loading = ref(false); const oidcAvailable = ref(false); const oidcLoading = ref(false);
const oidcMessages: Record<string,string> = { not_configured:"SSO is not configured yet.", provider_unavailable:"The SSO provider is currently unavailable.", authentication_failed:"SSO authentication failed. Please try again.", verified_email_required:"Your SSO account must provide a verified email address.", account_disabled:"This account is disabled.", identity_conflict:"This SSO identity is already linked to another account." };

onMounted(async () => {
  oidcAvailable.value = await oidcEnabled();
  if (route.query.oidc === "success") { await checkAuth(); if (route.query.oidc) router.replace("/"); }
  else if (typeof route.query.oidc_error === "string") error.value = oidcMessages[route.query.oidc_error] ?? "SSO sign-in failed.";
});
async function submit() {
  if (!usernameOrEmail.value.trim() || !password.value) { error.value = "Enter your username/email and password."; return; }
  loading.value = true; error.value = null;
  try { await login(usernameOrEmail.value.trim(), password.value); await checkAuth(); router.push("/"); }
  catch (err) { error.value = err instanceof Error ? err.message : "Login failed"; }
  finally { loading.value = false; }
}
async function sso() { oidcLoading.value = true; error.value = null; try { await startOidcLogin(); } catch (err) { error.value = err instanceof Error ? err.message : "Unable to start SSO."; oidcLoading.value = false; } }
</script>
<template><main class="login-page"><form class="login-card" @submit.prevent="submit">
  <div class="login-brand"><span class="brand-icon">🎮</span><h1>Archive</h1></div><p class="login-subtitle">Sign in to your library</p>
  <label class="field"><span>Username or email</span><input v-model="usernameOrEmail" type="text" autocomplete="username" required /></label>
  <label class="field"><span>Password</span><input v-model="password" type="password" autocomplete="current-password" required /></label>
  <div v-if="error" class="login-error">{{ error }}</div>
  <button type="submit" class="login-button" :disabled="loading || oidcLoading">{{ loading ? "Signing in…" : "Sign in" }}</button>
  <div v-if="oidcAvailable" class="divider"><span>or</span></div>
  <button v-if="oidcAvailable" type="button" class="oidc-button" :disabled="oidcLoading" @click="sso">{{ oidcLoading ? "Opening SSO…" : "Continue with SSO" }}</button>
</form></main></template>
<style scoped>
.login-page{min-height:100vh;display:flex;align-items:center;justify-content:center;background:#121212;font-family:system-ui,sans-serif;position:relative;overflow:hidden}.login-page::before{content:"";position:absolute;width:600px;height:600px;background:radial-gradient(circle,rgba(214,138,52,.18) 0%,transparent 70%);top:50%;left:50%;transform:translate(-50%,-50%)}.login-card{position:relative;z-index:1;width:100%;max-width:360px;background:rgba(26,26,26,.9);backdrop-filter:blur(12px);border:1px solid #2a2a2a;border-radius:14px;padding:32px;box-shadow:0 24px 64px rgba(0,0,0,.5);display:flex;flex-direction:column;gap:16px}.login-brand{display:flex;align-items:center;gap:10px;justify-content:center}.brand-icon{font-size:26px}.login-brand h1{margin:0;color:#fff;font-size:1.4rem}.login-subtitle{margin:-8px 0 4px;color:#999;font-size:13px;text-align:center}.field{display:flex;flex-direction:column;gap:6px;font-size:.85rem;color:#ccc}.field input{background:#111;border:1px solid #3a3a3a;border-radius:8px;color:#fff;padding:10px 12px;font:inherit}.login-error{color:#fca5a5;font-size:13px;background:rgba(220,38,38,.1);border:1px solid rgba(220,38,38,.3);border-radius:8px;padding:8px 10px}.login-button,.oidc-button{border:0;border-radius:8px;padding:11px;font-weight:600;cursor:pointer}.login-button{background:#d68a34;color:#111}.login-button:disabled,.oidc-button:disabled{opacity:.6;cursor:not-allowed}.oidc-button{background:#2a2a2a;color:#fff;border:1px solid #444}.divider{text-align:center;color:#777;font-size:12px;border-top:1px solid #2a2a2a;line-height:0}.divider span{background:#1a1a1a;padding:0 8px;position:relative;top:-1px}
</style>
