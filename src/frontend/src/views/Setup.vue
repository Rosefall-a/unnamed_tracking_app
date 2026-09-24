<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { createInitialAdmin, fetchSetupConfiguration, fetchSetupStatus, type SetupConfiguration } from "../services/setup";
import { checkAuth } from "../state/auth";

const route = useRoute();
const router = useRouter();
const browserOrigin = window.location.origin;
const stage = ref<"account" | "oidc">("account");
const username = ref("");
const email = ref("");
const password = ref("");
const confirmPassword = ref("");
const oidcEnabled = ref(false);
const oidcName = ref("");
const oidcIssuer = ref("");
const oidcClientId = ref("");
const oidcClientSecret = ref("");
const oidcScopes = ref("openid profile email");
const oidcGroupsClaim = ref("groups");
const oidcAdminGroup = ref("");
const oidcUserMatchField = ref<"email" | "username">("email");
const oidcAllowNewUsers = ref(true);
const oidcButtonText = ref("Continue with SSO");
const oidcButtonImageUrl = ref("");
const oidcButtonColor = ref("#d68a34");
const oidcProviderEnabled = ref(true);
const oidcShowOnLogin = ref(true);
const oidcAutostartEnabled = ref(true);
const oidcDefaultLoginMethod = ref<"local" | "sso">("local");
const configuration = ref<SetupConfiguration | null>(null);
const loading = ref(false);
const configurationLoading = ref(true);
const error = ref<string | null>(route.query.backend_error ? "The backend is not ready yet. Reload once it is available." : null);

const forced = computed(() => configuration.value?.forced === true);
const locked = (name: string) => configuration.value?.settings.find((item) => item.name === name)?.locked === true;
const envValue = (name: string) => configuration.value?.settings.find((item) => item.name === name)?.resolved;
const passwordValid = computed(() => password.value.length >= 9 && /[A-Z]/.test(password.value) && /[a-z]/.test(password.value) && /[^A-Za-z0-9]/.test(password.value));
const oidcConfiguredByEnv = computed(() => Boolean(envValue("OIDC_ISSUER_URL")));

function applyConfiguration(config: SetupConfiguration) {
  configuration.value = config;
  const value = (name: string, fallback: string) => {
    const resolved = envValue(name);
    return typeof resolved === "string" && resolved.trim() ? resolved : fallback;
  };
  const issuer = value("OIDC_ISSUER_URL", "");
  oidcEnabled.value = Boolean(issuer);
  oidcIssuer.value = issuer;
  oidcClientId.value = value("OIDC_CLIENT_ID", "");
  oidcScopes.value = value("OIDC_SCOPES", "openid profile email");
  oidcGroupsClaim.value = value("OIDC_GROUPS_CLAIM", "groups");
  oidcAdminGroup.value = value("OIDC_ADMIN_GROUP", "");
  oidcUserMatchField.value = value("OIDC_USER_MATCH_FIELD", "email") === "username" ? "username" : "email";
  if (issuer) {
    try { oidcName.value = new URL(issuer).hostname; } catch { oidcName.value = "OIDC"; }
  }
}

onMounted(async () => {
  try {
    const [status, config] = await Promise.all([fetchSetupStatus(), fetchSetupConfiguration()]);
    if (!status.setup_required && !status.forced) {
      await checkAuth();
      await router.replace("/");
      return;
    }
    applyConfiguration(config);
    if (config.forced && Boolean(config.settings.find((item) => item.name === "OIDC_ISSUER_URL")?.resolved)) stage.value = "oidc";
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Unable to load setup configuration.";
  } finally {
    configurationLoading.value = false;
  }
});

function next() {
  error.value = null;
  if (forced.value) return;
  if (!passwordValid.value) { error.value = "Password must be at least 9 characters and contain uppercase, lowercase, and a symbol."; return; }
  if (password.value !== confirmPassword.value) { error.value = "Passwords do not match."; return; }
  if (oidcEnabled.value) stage.value = "oidc"; else void submit();
}

async function submit() {
  if (forced.value) return;
  error.value = null;
  if (oidcEnabled.value && !oidcConfiguredByEnv.value && (!oidcIssuer.value.trim() || !oidcClientId.value.trim() || !oidcClientSecret.value)) {
    error.value = "OIDC requires an issuer URL, client ID, and client secret.";
    stage.value = "oidc";
    return;
  }
  loading.value = true;
  try {
    await createInitialAdmin(username.value.trim(), email.value.trim(), password.value, {
      oidc_enabled: oidcEnabled.value,
      oidc_name: oidcName.value.trim() || undefined,
      oidc_issuer_url: locked("OIDC_ISSUER_URL") ? undefined : oidcIssuer.value.trim() || undefined,
      oidc_client_id: locked("OIDC_CLIENT_ID") ? undefined : oidcClientId.value.trim() || undefined,
      oidc_client_secret: locked("OIDC_CLIENT_SECRET") ? undefined : oidcClientSecret.value || undefined,
      oidc_scopes: oidcScopes.value.trim(),
      oidc_redirect_uri: locked("OIDC_REDIRECT_URI") ? undefined : browserOrigin + "/api/auth/oidc/callback/" + slugify(oidcName.value || oidcIssuer.value),
      oidc_groups_claim: oidcGroupsClaim.value.trim(),
      oidc_admin_group: oidcAdminGroup.value.trim() || undefined,
      oidc_user_match_field: oidcUserMatchField.value,
      oidc_allow_new_users: oidcAllowNewUsers.value,
      oidc_button_text: oidcButtonText.value.trim() || "Continue with SSO",
      oidc_button_image_url: oidcButtonImageUrl.value.trim() || null,
      oidc_button_color: oidcButtonColor.value,
      oidc_provider_enabled: oidcProviderEnabled.value,
      oidc_show_on_login: oidcShowOnLogin.value,
      oidc_autostart_enabled: oidcAutostartEnabled.value,
      oidc_default_login_method: oidcDefaultLoginMethod.value,
    });
    await checkAuth();
    await router.replace("/");
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Setup failed.";
  } finally { loading.value = false; }
}

function slugify(value: string) {
  return value.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 80) || "oidc";
}
</script>

<template>
  <main class="setup-page">
    <form v-if="configurationLoading" class="setup-card"><div class="brand"><span>🎮</span><h1>Archive setup</h1></div><p class="subtitle">Loading deployment configuration…</p></form>
    <form v-else-if="stage === 'account'" class="setup-card" @submit.prevent="next">
      <div class="brand"><span>🎮</span><h1>{{ forced ? "Application configuration" : "Archive setup" }}</h1></div>
      <p class="subtitle">{{ forced ? "Startup UI is forced. Environment-managed values are shown for reference and cannot be changed here." : "Create the administrator account and configure optional SSO." }}</p>
      <div v-if="forced" class="forced-banner">STARTUP_UI=forced — this page is intentionally available on every restart.</div>
      <label><span>Username</span><input v-model="username" autocomplete="username" required :disabled="forced" /></label>
      <label><span>Email</span><input v-model="email" type="email" autocomplete="email" required :disabled="forced" /></label>
      <label><span>Password</span><input v-model="password" type="password" autocomplete="new-password" minlength="9" required :disabled="forced" /></label>
      <label><span>Confirm password</span><input v-model="confirmPassword" type="password" autocomplete="new-password" minlength="9" required :disabled="forced" /></label>
      <label class="toggle"><input v-model="oidcEnabled" type="checkbox" :disabled="oidcConfiguredByEnv || forced" /><span>Configure OpenID Connect / SSO now</span></label>
      <div v-if="oidcConfiguredByEnv" class="env-notice">OIDC credentials are managed by the deployment environment. The SSO section will be populated from <code>.env</code>; deployment-managed fields are locked.</div>
      <div v-if="error" class="error">{{ error }}</div>
      <button :disabled="loading || forced || Boolean(route.query.backend_error)">{{ forced ? "Configuration is deployment-managed" : oidcEnabled ? "Continue to OIDC" : "Create administrator" }}</button>
    </form>
    <form v-else class="setup-card wide" @submit.prevent="submit">
      <div class="brand"><span>🔐</span><h1>Configure OIDC / SSO</h1></div>
      <p class="subtitle">Environment-provided credentials are read-only. Presentation options remain configurable.</p>
      <div class="grid">
        <label><span>Provider name</span><input v-model="oidcName" placeholder="Authentik" /></label>
        <label><span>Slug</span><input :value="slugify(oidcName || oidcIssuer)" readonly class="generated-input" /></label>
        <label class="full"><span>Issuer / discovery URL</span><input v-model="oidcIssuer" required :disabled="locked('OIDC_ISSUER_URL')" /></label>
        <label><span>Client ID</span><input v-model="oidcClientId" required :disabled="locked('OIDC_CLIENT_ID')" /></label>
        <label><span>Client secret</span><input v-model="oidcClientSecret" type="password" :placeholder="locked('OIDC_CLIENT_SECRET') ? 'Managed by .env' : 'Required'" :disabled="locked('OIDC_CLIENT_SECRET')" /></label>
        <label><span>Scopes</span><input v-model="oidcScopes" :disabled="locked('OIDC_SCOPES')" /></label>
        <label><span>Groups claim</span><input v-model="oidcGroupsClaim" :disabled="locked('OIDC_GROUPS_CLAIM')" /></label>
        <label><span>Admin group</span><input v-model="oidcAdminGroup" :disabled="locked('OIDC_ADMIN_GROUP')" /></label>
        <label><span>Match users by</span><select v-model="oidcUserMatchField" :disabled="locked('OIDC_USER_MATCH_FIELD')"><option value="email">Email</option><option value="username">Username</option></select></label>
        <label><span>Login button text</span><input v-model="oidcButtonText" /></label>
        <label><span>Button image URL</span><input v-model="oidcButtonImageUrl" /></label>
        <label><span>Button color</span><input v-model="oidcButtonColor" type="color" /></label>
        <label class="full"><span>Redirect URI</span><input :value="browserOrigin + '/api/auth/oidc/callback/' + slugify(oidcName || oidcIssuer)" readonly class="generated-input" /></label>
      </div>
      <div class="options">
        <label><input v-model="oidcAllowNewUsers" type="checkbox" :disabled="locked('OIDC_ISSUER_URL')" /> Allow new users</label>
        <label><input v-model="oidcProviderEnabled" type="checkbox" /> Provider enabled</label>
        <label><input v-model="oidcShowOnLogin" type="checkbox" /> Show on login page</label>
        <label><input v-model="oidcAutostartEnabled" type="checkbox" /> Enable autostart URLs</label>
      </div>
      <label><span>Default login method</span><select v-model="oidcDefaultLoginMethod"><option value="local">Local username &amp; password</option><option value="sso">SSO</option></select></label>
      <div v-if="error" class="error">{{ error }}</div>
      <div class="actions"><button type="button" class="secondary" @click="stage='account'">Back</button><button :disabled="loading">{{ loading ? "Saving…" : "Finish setup" }}</button></div>
    </form>
  </main>
</template>

<style scoped>
.setup-page{min-height:100vh;display:flex;align-items:center;justify-content:center;background:#121212;font-family:system-ui,sans-serif;padding:32px 16px}
.setup-card{width:100%;max-width:520px;background:#1a1a1a;border:1px solid #2a2a2a;border-radius:14px;padding:32px;display:flex;flex-direction:column;gap:14px;color:#ccc}.setup-card.wide{max-width:820px}
.brand{display:flex;align-items:center;gap:10px;justify-content:center;color:#fff}.brand h1{font-size:1.4rem;margin:0}.subtitle{color:#999;font-size:13px;text-align:center;line-height:1.5}
.setup-card label{display:flex;flex-direction:column;gap:6px;color:#ccc;font-size:13px}.setup-card input,.setup-card select{background:#111;border:1px solid #3a3a3a;border-radius:8px;color:#fff;padding:10px;font:inherit}.setup-card input:focus,.setup-card select:focus{outline:none;border-color:#d68a34}.setup-card input:disabled,.setup-card select:disabled{opacity:.55;cursor:not-allowed}
.toggle,.options label{flex-direction:row!important;align-items:center}.toggle input,.options input{width:16px;height:16px;accent-color:#d68a34}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.grid label.full{grid-column:1/-1}.generated-input{background:#202020!important;color:#777!important;cursor:not-allowed}.options{display:flex;gap:18px;flex-wrap:wrap;color:#bbb;font-size:13px}
.forced-banner,.env-notice{padding:10px;border:1px solid #57411f;background:#211b11;border-radius:8px;color:#d8c39a;font-size:12px;line-height:1.5}.actions{display:flex;gap:10px}.actions button{flex:1}.setup-card button{background:#d68a34;border:0;border-radius:8px;padding:11px;font-weight:600;cursor:pointer}.setup-card button.secondary{background:#252525;color:#ddd;border:1px solid #3a3a3a}.setup-card button:disabled{opacity:.6;cursor:not-allowed}.error{color:#fca5a5;background:rgba(220,38,38,.1);border:1px solid rgba(220,38,38,.3);border-radius:8px;padding:8px;font-size:13px}
@media(max-width:760px){.grid{grid-template-columns:1fr}.grid label.full{grid-column:auto}}
</style>