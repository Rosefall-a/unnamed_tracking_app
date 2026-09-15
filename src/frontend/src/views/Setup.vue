<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { createInitialAdmin } from "../services/setup";
import { updateDeploymentSettings } from "../services/deploymentSettings";

const route = useRoute();
const router = useRouter();
const step = computed(() => {
  if (route.path === "/setup/firstuser") return "firstuser";
  if (route.path === "/setup/oidc") return "oidc";
  if (route.path === "/setup/smtp") return "smtp";
  return "choose";
});

const username = ref("");
const email = ref("");
const password = ref("");
const confirmPassword = ref("");
const configureOidc = ref(false);
const configureSmtp = ref(false);
const loading = ref(false);
const error = ref<string | null>(null);

const oidcName = ref("");
const oidcIssuer = ref("");
const oidcClientId = ref("");
const oidcClientSecret = ref("");
const oidcScopes = ref("openid profile email");
const oidcGroupsClaim = ref("groups");
const oidcAdminGroup = ref("");
const oidcUserMatchField = ref("email");
const oidcAllowNewUsers = ref(true);
const oidcButtonText = ref("Continue with SSO");
const oidcButtonImageUrl = ref("");
const oidcButtonColor = ref("#d68a34");
const oidcEnabled = ref(true);
const oidcShowOnLogin = ref(true);
const oidcAutostartEnabled = ref(true);
const oidcDefaultLoginMethod = ref("local");

const smtpEnabled = ref(true);
const smtpHost = ref("");
const smtpPort = ref(587);
const smtpUsername = ref("");
const smtpPassword = ref("");
const smtpUseTls = ref(true);
const smtpUseSsl = ref(false);
const smtpFromEmail = ref("");
const smtpFromName = ref("Archive");

const browserOrigin = window.location.origin;

function slugify(value: string) {
  return value.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 80) || "oidc";
}

const oidcSlug = computed(() => slugify(oidcName.value || oidcIssuer.value));
const oidcRedirectUri = computed(() => `${browserOrigin}/api/auth/oidc/callback/${oidcSlug.value}`);

function persistSelection() {
  sessionStorage.setItem("archive_setup_selection", JSON.stringify({ oidc: configureOidc.value, smtp: configureSmtp.value }));
}

function readSelection() {
  try {
    const saved = JSON.parse(sessionStorage.getItem("archive_setup_selection") || "{}");
    configureOidc.value = saved.oidc === true;
    configureSmtp.value = saved.smtp === true;
  } catch {
    configureOidc.value = false;
    configureSmtp.value = false;
  }
}

function nextSetupPage() {
  if (configureOidc.value) return "/setup/oidc";
  if (configureSmtp.value) return "/setup/smtp";
  return "/login";
}

function previousSetupPage() {
  return "/setup/firstuser";
}

onMounted(() => {
  readSelection();
});

async function submitFirstUser() {
  error.value = null;
  if (password.value !== confirmPassword.value) {
    error.value = "Passwords do not match.";
    return;
  }
  persistSelection();
  loading.value = true;
  try {
    await createInitialAdmin(username.value.trim(), email.value.trim(), password.value);
    // The setup POST creates the session cookie and changes the server's setup
    // state. Reloading the SPA makes the router read the new state from scratch.
    window.location.assign(nextSetupPage());
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Setup failed.";
  } finally {
    loading.value = false;
  }
}

async function submitOidc() {
  error.value = null;
  if (!oidcIssuer.value.trim() || !oidcClientId.value.trim() || !oidcClientSecret.value) {
    error.value = "OIDC requires an issuer URL, client ID, and client secret.";
    return;
  }
  loading.value = true;
  try {
    await updateDeploymentSettings({
      oidc_default_login_method: oidcDefaultLoginMethod.value,
      oidc_providers_json: JSON.stringify([{
        name: oidcName.value.trim() || oidcSlug.value,
        slug: oidcSlug.value,
        issuer_url: oidcIssuer.value.trim(),
        client_id: oidcClientId.value.trim(),
        client_secret: oidcClientSecret.value,
        scopes: oidcScopes.value.trim() || "openid profile email",
        redirect_uri: oidcRedirectUri.value,
        groups_claim: oidcGroupsClaim.value.trim() || "groups",
        admin_group: oidcAdminGroup.value.trim() || null,
        user_match_field: oidcUserMatchField.value,
        allow_new_users: oidcAllowNewUsers.value,
        button_text: oidcButtonText.value.trim() || "Continue with SSO",
        button_image_url: oidcButtonImageUrl.value.trim() || null,
        button_color: oidcButtonColor.value,
        enabled: oidcEnabled.value,
        show_on_login: oidcShowOnLogin.value,
        autostart_enabled: oidcAutostartEnabled.value,
      }]),
    });
    const saved = JSON.parse(sessionStorage.getItem("archive_setup_selection") || "{}");
    sessionStorage.removeItem("archive_setup_selection");
    window.location.assign(saved.smtp === true ? "/setup/smtp" : "/login");
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to save OIDC settings.";
  } finally {
    loading.value = false;
  }
}

async function submitSmtp() {
  error.value = null;
  if (!smtpHost.value.trim() || !smtpFromEmail.value.trim()) {
    error.value = "SMTP requires a host and sender email address.";
    return;
  }
  loading.value = true;
  try {
    await updateDeploymentSettings({
      smtp_enabled: smtpEnabled.value,
      smtp_host: smtpHost.value.trim(),
      smtp_port: smtpPort.value,
      smtp_username: smtpUsername.value.trim(),
      smtp_password: smtpPassword.value,
      smtp_use_tls: smtpUseTls.value,
      smtp_use_ssl: smtpUseSsl.value,
      smtp_from_email: smtpFromEmail.value.trim(),
      smtp_from_name: smtpFromName.value.trim(),
    });
    sessionStorage.removeItem("archive_setup_selection");
    window.location.assign("/login");
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to save SMTP settings.";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <main class="setup-page">
    <form v-if="step === 'choose'" class="setup-card" @submit.prevent="persistSelection(); router.replace('/setup/firstuser')">
      <div class="brand"><span>🎮</span><h1>Archive setup</h1></div>
      <p class="subtitle">Choose which optional services you want to configure before creating the administrator account.</p>
      <label class="toggle"><input v-model="configureOidc" type="checkbox" /><span>Configure OpenID Connect / SSO</span></label>
      <label class="toggle"><input v-model="configureSmtp" type="checkbox" /><span>Configure SMTP / password-reset email</span></label>
      <p class="hint">You can configure either service later from Settings. OIDC setup supports one provider; additional providers can be added later from Settings.</p>
      <button>Continue</button>
    </form>

    <form v-else-if="step === 'firstuser'" class="setup-card" @submit.prevent="submitFirstUser">
      <div class="brand"><span>🎮</span><h1>Create administrator</h1></div>
      <p class="subtitle">Create the administrator account for this installation.</p>
      <label><span>Username</span><input v-model="username" autocomplete="username" required /></label>
      <label><span>Email</span><input v-model="email" type="email" autocomplete="email" required /></label>
      <label><span>Password</span><input v-model="password" type="password" autocomplete="new-password" minlength="9" required /></label>
      <label><span>Confirm password</span><input v-model="confirmPassword" type="password" autocomplete="new-password" minlength="9" required /></label>
      <p class="hint">Use at least 9 characters with uppercase, lowercase, and a symbol.</p>
      <p class="step-summary">Next: {{ configureOidc ? 'OIDC' : configureSmtp ? 'SMTP' : 'finish setup' }}</p>
      <div class="actions"><button type="button" class="secondary" @click="router.replace('/setup')">Back</button><button :disabled="loading">{{ loading ? 'Creating account…' : 'Create administrator' }}</button></div>
      <div v-if="error" class="error">{{ error }}</div>
    </form>

    <form v-else-if="step === 'oidc'" class="setup-card wide" @submit.prevent="submitOidc">
      <div class="brand"><span>🔐</span><h1>Configure OIDC / SSO</h1></div>
      <p class="subtitle">Configure one identity provider. Additional providers can be added later in Settings.</p>
      <div class="grid">
        <label><span>Provider name</span><input v-model="oidcName" placeholder="Authentik" required /></label>
        <label><span>Slug</span><input :value="oidcSlug" readonly class="generated-input" /></label>
        <label class="full"><span>Issuer / discovery URL</span><input v-model="oidcIssuer" placeholder="https://id.example.com" required /></label>
        <label><span>Client ID</span><input v-model="oidcClientId" required /></label>
        <label><span>Client secret</span><input v-model="oidcClientSecret" type="password" required /></label>
        <label><span>Scopes</span><input v-model="oidcScopes" /></label>
        <label><span>Groups claim</span><input v-model="oidcGroupsClaim" /></label>
        <label><span>Admin group</span><input v-model="oidcAdminGroup" /></label>
        <label><span>Match users by</span><select v-model="oidcUserMatchField"><option value="email">Email</option><option value="username">Username</option></select></label>
        <label><span>Login button text</span><input v-model="oidcButtonText" /></label>
        <label><span>Button image URL</span><input v-model="oidcButtonImageUrl" /></label>
        <label><span>Button color</span><input v-model="oidcButtonColor" type="color" /></label>
        <label class="full"><span>Redirect URI <small>Automatically generated</small></span><input :value="oidcRedirectUri" readonly class="generated-input" /></label>
      </div>
      <div class="options"><label><input v-model="oidcAllowNewUsers" type="checkbox" /> Allow new users</label><label><input v-model="oidcEnabled" type="checkbox" /> Provider enabled</label><label><input v-model="oidcShowOnLogin" type="checkbox" /> Show on login page</label><label><input v-model="oidcAutostartEnabled" type="checkbox" /> Enable autostart URL</label></div>
      <label><span>Default login method</span><select v-model="oidcDefaultLoginMethod"><option value="local">Local username &amp; password</option><option value="sso">SSO</option></select></label>
      <div class="actions"><button type="button" class="secondary" @click="router.replace(previousSetupPage())">Back</button><button :disabled="loading">{{ loading ? 'Saving OIDC…' : 'Save OIDC and continue' }}</button></div>
      <div v-if="error" class="error">{{ error }}</div>
    </form>

    <form v-else class="setup-card wide" @submit.prevent="submitSmtp">
      <div class="brand"><span>✉️</span><h1>Configure SMTP</h1></div>
      <p class="subtitle">SMTP is used for password-reset and other email notifications.</p>
      <div class="grid">
        <label><span>SMTP host</span><input v-model="smtpHost" placeholder="smtp.example.com" required /></label>
        <label><span>Port</span><input v-model.number="smtpPort" type="number" min="1" max="65535" required /></label>
        <label><span>Username</span><input v-model="smtpUsername" autocomplete="off" /></label>
        <label><span>Password</span><input v-model="smtpPassword" type="password" autocomplete="new-password" /></label>
        <label><span>Sender email</span><input v-model="smtpFromEmail" type="email" placeholder="noreply@example.com" required /></label>
        <label><span>Sender name</span><input v-model="smtpFromName" /></label>
      </div>
      <div class="options"><label><input v-model="smtpEnabled" type="checkbox" /> SMTP enabled</label><label><input v-model="smtpUseTls" type="checkbox" /> STARTTLS</label><label><input v-model="smtpUseSsl" type="checkbox" /> SSL/TLS</label></div>
      <div class="actions"><button type="button" class="secondary" @click="router.replace(previousSetupPage())">Back</button><button :disabled="loading">{{ loading ? 'Saving SMTP…' : 'Save SMTP and finish' }}</button></div>
      <div v-if="error" class="error">{{ error }}</div>
    </form>
  </main>
</template>

<style scoped>
.setup-page{min-height:100vh;display:flex;align-items:center;justify-content:center;background:#121212;font-family:system-ui,sans-serif;padding:32px 16px}.setup-card{width:100%;max-width:500px;background:#1a1a1a;border:1px solid #2a2a2a;border-radius:14px;padding:32px;display:flex;flex-direction:column;gap:14px;color:#fff}.setup-card.wide{max-width:760px}.brand{display:flex;align-items:center;gap:10px;justify-content:center}.brand h1{font-size:1.4rem;margin:0}.subtitle,.hint{color:#999;font-size:13px;text-align:center;line-height:1.5}.toggle{flex-direction:row!important;align-items:center;padding:10px;border:1px solid #2f2f2f;border-radius:8px;background:#151515}.toggle input{width:16px;height:16px;accent-color:#d68a34}.setup-card label{display:flex;flex-direction:column;gap:6px;color:#ccc;font-size:13px}.setup-card input,.setup-card select{background:#111;border:1px solid #3a3a3a;border-radius:8px;color:#fff;padding:10px;font:inherit}.generated-input{background:#202020!important;color:#777!important;cursor:not-allowed}.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.full{grid-column:1/-1}.options{display:flex;gap:18px;flex-wrap:wrap;color:#bbb;font-size:13px}.options label{flex-direction:row;align-items:center;gap:6px}.options input{accent-color:#d68a34}.step-summary{color:#aaa;font-size:13px;text-align:center}.actions{display:flex;gap:10px;justify-content:flex-end}.actions button,.setup-card>button{background:#d68a34;border:0;border-radius:8px;padding:11px 14px;font-weight:600;cursor:pointer}.actions .secondary{background:#252525;color:#ddd;border:1px solid #3a3a3a}.setup-card button:disabled{opacity:.6}.error{color:#fca5a5;background:rgba(220,38,38,.1);border:1px solid rgba(220,38,38,.3);border-radius:8px;padding:8px;font-size:13px}@media(max-width:760px){.grid{grid-template-columns:1fr}.full{grid-column:auto}.actions{flex-direction:column-reverse}}
</style>
