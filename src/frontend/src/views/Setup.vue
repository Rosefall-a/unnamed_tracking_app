<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { createInitialAdmin } from "../services/setup";
import { checkAuth } from "../state/auth";

const route = useRoute();
const router = useRouter();
const username = ref(""); const email = ref(""); const password = ref(""); const confirmPassword = ref("");
const oidcEnabled = ref(false);
const oidcIssuer = ref(""); const oidcClientId = ref(""); const oidcClientSecret = ref("");
const oidcScopes = ref("openid profile email"); const oidcRedirectUri = ref(`${window.location.origin}/api/auth/oidc/callback`);
const oidcGroupsClaim = ref("groups"); const oidcAdminGroup = ref(""); const oidcUserMatchField = ref("email");
const error = ref<string | null>(route.query.backend_error ? "The frontend cannot reach the backend yet. Start the backend service, then reload this page." : null);
const loading = ref(false);

async function submit() {
  error.value = null;
  if (password.value !== confirmPassword.value) { error.value = "Passwords do not match."; return; }
  if (oidcEnabled.value && (!oidcIssuer.value.trim() || !oidcClientId.value.trim() || !oidcClientSecret.value)) {
    error.value = "OIDC requires an issuer URL, client ID, and client secret."; return;
  }
  loading.value = true;
  try {
    await createInitialAdmin(username.value.trim(), email.value.trim(), password.value, {
      oidc_enabled: oidcEnabled.value,
      ...(oidcEnabled.value ? {
        oidc_issuer_url: oidcIssuer.value.trim(),
        oidc_client_id: oidcClientId.value.trim(),
        oidc_client_secret: oidcClientSecret.value,
        oidc_scopes: oidcScopes.value.trim(),
        oidc_redirect_uri: oidcRedirectUri.value.trim() || `${window.location.origin}/api/auth/oidc/callback`,
        oidc_groups_claim: oidcGroupsClaim.value.trim() || "groups",
        oidc_admin_group: oidcAdminGroup.value.trim(),
        oidc_user_match_field: oidcUserMatchField.value,
      } : {}),
    });
    await checkAuth();
    await router.replace("/");
  } catch (err) { error.value = err instanceof Error ? err.message : "Setup failed."; }
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

    <label class="toggle"><input v-model="oidcEnabled" type="checkbox" /><span>Configure OpenID Connect / SSO now</span></label>
    <div v-if="oidcEnabled" class="oidc-panel">
      <p class="hint">Optional. You can configure SSO later from Settings → OIDC / SSO.</p>
      <label><span>Issuer URL</span><input v-model="oidcIssuer" placeholder="https://login.example.com/realms/archive" /></label>
      <label><span>Client ID</span><input v-model="oidcClientId" /></label>
      <label><span>Client secret</span><input v-model="oidcClientSecret" type="password" /></label>
      <label><span>Scopes</span><input v-model="oidcScopes" /></label>
      <label><span>Redirect URI</span><input v-model="oidcRedirectUri" autocomplete="url" /></label>
      <label><span>Groups claim</span><input v-model="oidcGroupsClaim" placeholder="groups" /></label>
      <label><span>Admin group</span><input v-model="oidcAdminGroup" placeholder="archive-admins" /></label>
      <div class="match-options">
        <span class="match-title">Match existing users by</span>
        <label class="radio"><input v-model="oidcUserMatchField" type="radio" value="email" /><span>Email <small>OIDC email → local email</small></span></label>
        <label class="radio"><input v-model="oidcUserMatchField" type="radio" value="username" /><span>Username <small>OIDC preferred_username → local username</small></span></label>
      </div>
      <p class="hint">The redirect URI is automatically set from the URL you are currently using. If you are behind a proxy, use the public URL shown here. If an admin group is set, SSO membership in that group controls administrator status.</p>
    </div>

    <div v-if="error" class="error">{{ error }}</div>
    <button :disabled="loading || Boolean(route.query.backend_error)">{{ loading ? "Creating account…" : "Create administrator" }}</button>
  </form></main>
</template>
<style scoped>
.setup-page{min-height:100vh;display:flex;align-items:center;justify-content:center;background:#121212;font-family:system-ui,sans-serif;padding:32px 16px}.setup-card{width:100%;max-width:440px;background:#1a1a1a;border:1px solid #2a2a2a;border-radius:14px;padding:32px;display:flex;flex-direction:column;gap:14px}.brand{display:flex;align-items:center;gap:10px;justify-content:center;color:#fff}.brand h1{font-size:1.4rem;margin:0}.subtitle,.hint{color:#999;font-size:13px;text-align:center}.hint{line-height:1.5;margin:0}.setup-card label{display:flex;flex-direction:column;gap:6px;color:#ccc;font-size:13px}.setup-card input{background:#111;border:1px solid #3a3a3a;border-radius:8px;color:#fff;padding:10px;font:inherit}.setup-card input:focus{outline:none;border-color:#d68a34}.toggle{flex-direction:row!important;align-items:center;padding-top:4px}.toggle input{width:16px;height:16px;accent-color:#d68a34}.oidc-panel{display:flex;flex-direction:column;gap:12px;padding:14px;border:1px solid #2f2f2f;border-radius:10px;background:#151515}.oidc-panel .hint{text-align:left}.match-options{display:flex;flex-direction:column;gap:8px;padding:10px;border:1px solid #2f2f2f;border-radius:8px;background:#111}.match-title{color:#fff;font-size:13px;font-weight:600}.radio{flex-direction:row!important;align-items:flex-start;gap:8px!important}.radio input{width:16px;height:16px;accent-color:#d68a34;margin-top:1px}.radio span{display:flex;flex-direction:column;gap:2px}.radio small{color:#888;font-size:11px}.setup-card button{background:#d68a34;border:0;border-radius:8px;padding:11px;font-weight:600;cursor:pointer}.setup-card button:disabled{opacity:.6}.error{color:#fca5a5;background:rgba(220,38,38,.1);border:1px solid rgba(220,38,38,.3);border-radius:8px;padding:8px;font-size:13px}
</style>
