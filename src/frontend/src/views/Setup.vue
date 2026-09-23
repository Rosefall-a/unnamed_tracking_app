<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { createInitialAdmin, fetchApplicationBackupFile, fetchApplicationBackupStatus, fetchSetupStatus, importApplicationSettings, previewApplicationSettings } from "../services/setup";
import type { ApplicationBackupPreview } from "../services/setup";

const router = useRouter();
const stage = ref<"choose" | "firstuser" | "oidc" | "smtp">("choose");
const applicationFile = ref<File | null>(null);
const applicationPassword = ref("");
const importingApplication = ref(false);
const applicationImportError = ref<string | null>(null);
const applicationImportSuccess = ref<string | null>(null);
const applicationBackupAvailable = ref(false);
const applicationBackupSource = ref<"file" | "filesystem">("file");
const applicationBackupPreview = ref<ApplicationBackupPreview | null>(null);
const showApplicationImportChoices = ref(false);
const showFilesystemPrompt = ref(false);
const applicationFileInput = ref<HTMLInputElement | null>(null);
const importingApplicationMode = ref(false);
const username = ref("");
const email = ref("");
const password = ref("");
const confirmPassword = ref("");
const configureOidc = ref(false);
const configureSmtp = ref(false);
const loading = ref(false);
const checking = ref(true);
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
const oidcProviderEnabled = ref(true);
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
const passwordRequirements = computed(() => ({
  length: password.value.length >= 9,
  uppercase: /[A-Z]/.test(password.value),
  lowercase: /[a-z]/.test(password.value),
  symbol: /[^A-Za-z0-9]/.test(password.value),
}));
const passwordIsValid = computed(() => Object.values(passwordRequirements.value).every(Boolean));
const oidcSlug = computed(() => slugify(oidcName.value || oidcIssuer.value));
const oidcRedirectUri = computed(() => `${browserOrigin}/api/auth/oidc/callback/${oidcSlug.value}`);
const stages = computed(() => {
  const result = ["Account"];
  if (configureOidc.value) result.push("OIDC");
  if (configureSmtp.value) result.push("SMTP");
  return result;
});

function onApplicationFileSelected(event: Event) {
  const input = event.target as HTMLInputElement;
  applicationFile.value = input.files?.[0] ?? null;
  applicationImportError.value = null;
  applicationImportSuccess.value = null;
}

async function reviewApplicationImport(source: "file" | "filesystem") {
  applicationImportError.value = null;
  applicationImportSuccess.value = null;
  if (source === "file" && !applicationFile.value) {
    applicationImportError.value = "Choose an application settings JSON file first.";
    return;
  }
  if (!applicationPassword.value) {
    applicationImportError.value = "Enter the password used when the settings export was created.";
    return;
  }
  if (applicationPassword.value.length < 12) {
    applicationImportError.value = "The deployment backup password must be at least 12 characters long.";
    return;
  }
  importingApplication.value = true;
  applicationBackupSource.value = source;
  try {
    applicationBackupPreview.value = await previewApplicationSettings(
      source === "file" ? applicationFile.value : null,
      applicationPassword.value,
    );
    showApplicationImportChoices.value = true;
  } catch (err) {
    applicationImportError.value = err instanceof Error ? err.message : "Failed to read the previous installation backup.";
  } finally {
    importingApplication.value = false;
  }
}

function applySetupPreview(preview: ApplicationBackupPreview) {
  const oidc = preview.oidc;
  const smtp = preview.smtp;
  const value = (record: Record<string, unknown>, key: string) => record[key];
  configureOidc.value = preview.options.include_oidc_settings !== false && Boolean(value(oidc, "issuer_url"));
  oidcName.value = String(value(oidc, "name") ?? "");
  oidcIssuer.value = String(value(oidc, "issuer_url") ?? "");
  oidcClientId.value = String(value(oidc, "client_id") ?? "");
  oidcClientSecret.value = String(value(oidc, "client_secret") ?? "");
  oidcScopes.value = String(value(oidc, "scopes") ?? "openid profile email");
  oidcGroupsClaim.value = String(value(oidc, "groups_claim") ?? "groups");
  oidcAdminGroup.value = String(value(oidc, "admin_group") ?? "");
  oidcUserMatchField.value = String(value(oidc, "user_match_field") ?? "email");
  oidcAllowNewUsers.value = Boolean(value(oidc, "allow_new_users") ?? true);
  oidcButtonText.value = String(value(oidc, "login_button_text") ?? value(oidc, "button_text") ?? "Continue with SSO");
  oidcButtonImageUrl.value = String(value(oidc, "button_image_url") ?? "");
  oidcButtonColor.value = String(value(oidc, "button_color") ?? "#d68a34");
  oidcProviderEnabled.value = Boolean(value(oidc, "provider_enabled") ?? value(oidc, "enabled") ?? true);
  oidcShowOnLogin.value = Boolean(value(oidc, "show_on_login") ?? true);
  oidcAutostartEnabled.value = Boolean(value(oidc, "autostart_enabled") ?? true);
  oidcDefaultLoginMethod.value = String(value(oidc, "default_login_method") ?? "local");
  configureSmtp.value = Boolean(value(smtp, "smtp_enabled")) && Boolean(value(smtp, "smtp_host") || value(smtp, "smtp_from_email"));
  smtpEnabled.value = Boolean(value(smtp, "smtp_enabled"));
  smtpHost.value = String(value(smtp, "smtp_host") ?? "");
  smtpPort.value = Number(value(smtp, "smtp_port") ?? 587);
  smtpUsername.value = String(value(smtp, "smtp_username") ?? "");
  smtpPassword.value = String(value(smtp, "smtp_password") ?? "");
  smtpUseTls.value = Boolean(value(smtp, "smtp_use_tls") ?? true);
  smtpUseSsl.value = Boolean(value(smtp, "smtp_use_ssl") ?? false);
  smtpFromEmail.value = String(value(smtp, "smtp_from_email") ?? "");
  smtpFromName.value = String(value(smtp, "smtp_from_name") ?? "Archive");
  showApplicationImportChoices.value = false;
  applicationImportSuccess.value = "The setup pages have been populated from the backup. Review them before finishing setup.";
  stage.value = "firstuser";
}

async function acceptApplicationImport() {
  importingApplicationMode.value = true;
  applicationImportError.value = null;
  try {
    const result = await importApplicationSettings(
      applicationBackupSource.value === "file" ? applicationFile.value : null,
      applicationPassword.value,
    );
    showApplicationImportChoices.value = false;
    if (result.authenticated) {
      window.location.assign("/");
      return;
    }
    if (result.users) {
      window.location.assign("/login");
      return;
    }
    applicationImportSuccess.value = "Previous installation settings imported. Continue by creating the new administrator.";
    stage.value = "firstuser";
  } catch (err) {
    applicationImportError.value = err instanceof Error ? err.message : "Failed to import the previous installation.";
  } finally {
    importingApplicationMode.value = false;
  }
}

function nextAfterAccount() {
  if (configureOidc.value) stage.value = "oidc";
  else if (configureSmtp.value) stage.value = "smtp";
  else void submitSetup();
}
function nextAfterOidc() {
  if (configureSmtp.value) stage.value = "smtp";
  else void submitSetup();
}
function back() {
  if (stage.value === "firstuser") stage.value = "choose";
  else if (stage.value === "oidc") stage.value = "firstuser";
  else if (stage.value === "smtp") stage.value = configureOidc.value ? "oidc" : "firstuser";
}

async function submitSetup() {
  error.value = null;
  if (!passwordIsValid.value) {
    error.value = "Password must be at least 9 characters and contain uppercase, lowercase, and a symbol.";
    stage.value = "firstuser";
    return;
  }
  if (password.value !== confirmPassword.value) {
    error.value = "Passwords do not match.";
    stage.value = "firstuser";
    return;
  }
  if (configureOidc.value && (!oidcIssuer.value.trim() || !oidcClientId.value.trim() || !oidcClientSecret.value)) {
    error.value = "OIDC requires an issuer URL, client ID, and client secret.";
    stage.value = "oidc";
    return;
  }
  if (configureSmtp.value && (!smtpHost.value.trim() || !smtpFromEmail.value.trim())) {
    error.value = "SMTP requires a host and sender email address.";
    stage.value = "smtp";
    return;
  }
  loading.value = true;
  try {
    await createInitialAdmin(username.value.trim(), email.value.trim(), password.value, {
      oidc_enabled: configureOidc.value,
      oidc_name: oidcName.value.trim() || oidcSlug.value,
      oidc_issuer_url: configureOidc.value ? oidcIssuer.value.trim() : undefined,
      oidc_client_id: configureOidc.value ? oidcClientId.value.trim() : undefined,
      oidc_client_secret: configureOidc.value ? oidcClientSecret.value : undefined,
      oidc_scopes: oidcScopes.value.trim() || "openid profile email",
      oidc_redirect_uri: configureOidc.value ? oidcRedirectUri.value : undefined,
      oidc_groups_claim: oidcGroupsClaim.value.trim() || "groups",
      oidc_admin_group: configureOidc.value ? (oidcAdminGroup.value.trim() || undefined) : undefined,
      oidc_user_match_field: oidcUserMatchField.value,
      oidc_allow_new_users: oidcAllowNewUsers.value,
      oidc_button_text: oidcButtonText.value.trim() || "Continue with SSO",
      oidc_button_image_url: oidcButtonImageUrl.value.trim() || null,
      oidc_button_color: oidcButtonColor.value,
      oidc_provider_enabled: oidcProviderEnabled.value,
      oidc_show_on_login: oidcShowOnLogin.value,
      oidc_autostart_enabled: oidcAutostartEnabled.value,
      oidc_default_login_method: oidcDefaultLoginMethod.value,
      smtp_enabled: configureSmtp.value,
      smtp_host: configureSmtp.value ? smtpHost.value.trim() : undefined,
      smtp_port: smtpPort.value,
      smtp_username: configureSmtp.value ? smtpUsername.value.trim() : undefined,
      smtp_password: configureSmtp.value ? smtpPassword.value : undefined,
      smtp_use_tls: smtpUseTls.value,
      smtp_use_ssl: smtpUseSsl.value,
      smtp_from_email: configureSmtp.value ? smtpFromEmail.value.trim() : undefined,
      smtp_from_name: configureSmtp.value ? smtpFromName.value.trim() : undefined,
    });
    sessionStorage.removeItem("archive_setup_selection");
    window.location.assign("/login");
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Setup failed.";
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  try {
    const status = await fetchSetupStatus();
    if (!status.setup_required) {
      await router.replace("/login");
      return;
    }
    applicationBackupAvailable.value = (await fetchApplicationBackupStatus()).available;
    if (applicationBackupAvailable.value) {
      try {
        applicationFile.value = await fetchApplicationBackupFile();
        if (applicationFileInput.value) {
          const transfer = new DataTransfer();
          transfer.items.add(applicationFile.value);
          applicationFileInput.value.files = transfer.files;
        }
        showFilesystemPrompt.value = true;
      } catch (err) {
        applicationImportError.value = err instanceof Error ? err.message : "The detected application.json could not be loaded.";
      }
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Unable to check setup status.";
  } finally {
    checking.value = false;
  }
});
</script>

<template>
  <main class="setup-page">
    <form v-if="checking" class="setup-card"><div class="brand"><span>🎮</span><h1>Archive setup</h1></div><p class="subtitle">Checking whether this installation needs setup…</p></form>
    <form v-else-if="stage === 'choose'" class="setup-card" @submit.prevent="stage = 'firstuser'">
      <div class="brand"><span>🎮</span><h1>Archive setup</h1></div><p class="subtitle">Start from a previous deployment export, or configure this installation manually.</p>
      <div class="tile">
        <h2>Import previous installation</h2>
        <p class="hint">Use the password-protected JSON exported from Settings → Backup. This restores deployment settings, provider credentials, SMTP/OIDC configuration, and encryption keys. Your administrator account is deliberately not included, so you will create a new administrator next.</p>
        <label><span>Settings JSON</span><input ref="applicationFileInput" type="file" accept="application/json" @change="onApplicationFileSelected" /></label>
        <label><span>Settings JSON password</span><input v-model="applicationPassword" type="password" autocomplete="off" placeholder="Enter export password" /></label>
        <button type="button" :disabled="importingApplication" @click="reviewApplicationImport('file')">{{ importingApplication ? "Reading backup…" : "Review imported settings" }}</button>
        <div v-if="applicationBackupAvailable" class="filesystem-backup"><strong>application.json found on the setup filesystem.</strong><span>The configured setup path contains a deployment backup. You can use it directly without selecting a file.</span><button type="button" class="secondary" :disabled="importingApplication" @click="reviewApplicationImport('filesystem')">Use application.json from the filesystem</button></div>
        <div v-if="applicationImportError" class="error">{{ applicationImportError }}</div>
        <div v-if="applicationImportSuccess" class="success">{{ applicationImportSuccess }}</div>
      </div>
      <div class="or-divider">or configure manually</div>
      <div class="progress"><span v-for="(item, index) in stages" :key="item" :class="{ active: index === 0 }">{{ index + 1 }}. {{ item }}</span></div>
      <label class="toggle"><input v-model="configureOidc" type="checkbox" /><span>Configure OpenID Connect / SSO</span></label><label class="toggle"><input v-model="configureSmtp" type="checkbox" /><span>Configure SMTP / password-reset email</span></label>
      <p class="hint">These settings can be changed later from Settings.</p><button>Continue</button>
    </form>
    <form v-else-if="stage === 'firstuser'" class="setup-card" @submit.prevent="nextAfterAccount">
      <div class="brand"><span>🎮</span><h1>Create administrator</h1></div><div class="progress"><span class="active">1. Account</span><span v-if="configureOidc">2. OIDC</span><span v-if="configureSmtp">{{ configureOidc ? 3 : 2 }}. SMTP</span></div>
      <label><span>Username</span><input v-model="username" autocomplete="username" required /></label><label><span>Email</span><input v-model="email" type="email" autocomplete="email" required /></label><label><span>Password</span><input v-model="password" type="password" autocomplete="new-password" minlength="9" required /><small v-if="password" class="password-check" :class="{ valid: passwordRequirements.length }">{{ passwordRequirements.length ? "✓" : "✗" }} At least 9 characters</small><small v-if="password" class="password-check" :class="{ valid: passwordRequirements.uppercase }">{{ passwordRequirements.uppercase ? "✓" : "✗" }} Uppercase letter</small><small v-if="password" class="password-check" :class="{ valid: passwordRequirements.lowercase }">{{ passwordRequirements.lowercase ? "✓" : "✗" }} Lowercase letter</small><small v-if="password" class="password-check" :class="{ valid: passwordRequirements.symbol }">{{ passwordRequirements.symbol ? "✓" : "✗" }} Symbol</small></label><label><span>Confirm password</span><input v-model="confirmPassword" type="password" autocomplete="new-password" minlength="9" required /></label>
      <p class="hint">Use at least 9 characters with uppercase, lowercase, and a symbol.</p><div class="actions"><button type="button" class="secondary" @click="back">Back</button><button :disabled="loading">{{ configureOidc || configureSmtp ? 'Continue' : 'Finish setup' }}</button></div><div v-if="error" class="error">{{ error }}</div>
    </form>
    <form v-else-if="stage === 'oidc'" class="setup-card wide" @submit.prevent="nextAfterOidc">
      <div class="brand"><span>🔐</span><h1>Configure OIDC / SSO</h1></div><div class="progress"><span>1. Account</span><span class="active">2. OIDC</span><span v-if="configureSmtp">3. SMTP</span></div>
      <div class="grid"><label><span>Provider name</span><input v-model="oidcName" placeholder="Authentik" required /></label><label><span>Slug</span><input :value="oidcSlug" readonly class="generated-input" /></label><label class="full"><span>Issuer / discovery URL</span><input v-model="oidcIssuer" placeholder="https://id.example.com" required /></label><label><span>Client ID</span><input v-model="oidcClientId" required /></label><label><span>Client secret</span><input v-model="oidcClientSecret" type="password" required /></label><label><span>Scopes</span><input v-model="oidcScopes" /></label><label><span>Groups claim</span><input v-model="oidcGroupsClaim" /></label><label><span>Admin group</span><input v-model="oidcAdminGroup" /></label><label><span>Match users by</span><select v-model="oidcUserMatchField"><option value="email">Email</option><option value="username">Username</option></select></label><label><span>Login button text</span><input v-model="oidcButtonText" /></label><label><span>Button image URL</span><input v-model="oidcButtonImageUrl" /></label><label><span>Button color</span><input v-model="oidcButtonColor" type="color" /></label><label class="full"><span>Redirect URI</span><input :value="oidcRedirectUri" readonly class="generated-input" /></label></div>
      <div class="options"><label><input v-model="oidcAllowNewUsers" type="checkbox" /> Allow new users</label><label><input v-model="oidcProviderEnabled" type="checkbox" /> Provider enabled</label><label><input v-model="oidcShowOnLogin" type="checkbox" /> Show on login</label><label><input v-model="oidcAutostartEnabled" type="checkbox" /> Enable autostart URL</label></div><label><span>Default login method</span><select v-model="oidcDefaultLoginMethod"><option value="local">Local username &amp; password</option><option value="sso">SSO</option></select></label>
      <div class="actions"><button type="button" class="secondary" @click="back">Back</button><button :disabled="loading">{{ configureSmtp ? 'Continue to SMTP' : 'Finish setup' }}</button></div><div v-if="error" class="error">{{ error }}</div>
    </form>
    <form v-else class="setup-card wide" @submit.prevent="submitSetup">
      <div class="brand"><span>✉️</span><h1>Configure SMTP</h1></div><div class="progress"><span>1. Account</span><span v-if="configureOidc">2. OIDC</span><span class="active">{{ configureOidc ? 3 : 2 }}. SMTP</span></div>
      <div class="grid"><label><span>SMTP host</span><input v-model="smtpHost" placeholder="smtp.example.com" required /></label><label><span>Port</span><input v-model.number="smtpPort" type="number" min="1" max="65535" required /></label><label><span>Username</span><input v-model="smtpUsername" autocomplete="off" /></label><label><span>Password</span><input v-model="smtpPassword" type="password" autocomplete="new-password" /></label><label><span>Sender email</span><input v-model="smtpFromEmail" type="email" placeholder="noreply@example.com" required /></label><label><span>Sender name</span><input v-model="smtpFromName" /></label></div>
      <div class="options"><label><input v-model="smtpEnabled" type="checkbox" /> SMTP enabled</label><label><input v-model="smtpUseTls" type="checkbox" /> STARTTLS</label><label><input v-model="smtpUseSsl" type="checkbox" /> SSL/TLS</label></div><div class="actions"><button type="button" class="secondary" @click="back">Back</button><button :disabled="loading">{{ loading ? 'Finishing setup…' : 'Finish setup' }}</button></div><div v-if="error" class="error">{{ error }}</div>
    </form>
  </main>
  <div v-if="showFilesystemPrompt" class="modal-backdrop">
    <div class="modal" role="dialog" aria-modal="true" aria-labelledby="filesystem-backup-title">
      <h2 id="filesystem-backup-title">application.json detected</h2>
      <p>A deployment backup was found at the configured setup path and has been placed in the upload field. Would you like to use it to restore this installation?</p>
      <label><span>Backup password</span><input v-model="applicationPassword" type="password" autocomplete="off" placeholder="Enter export password" /></label>
      <div class="actions"><button type="button" class="secondary" @click="showFilesystemPrompt = false">Not now</button><button type="button" :disabled="importingApplication" @click="showFilesystemPrompt = false; reviewApplicationImport('filesystem')">{{ importingApplication ? "Reading…" : "Use application.json" }}</button></div>
      <div v-if="applicationImportError" class="error">{{ applicationImportError }}</div>
    </div>
  </div>
  <div v-if="showApplicationImportChoices && applicationBackupPreview" class="modal-backdrop">
    <div class="modal" role="dialog" aria-modal="true" aria-labelledby="backup-import-title">
      <h2 id="backup-import-title">How should this deployment backup be used?</h2>
      <p>We found {{ applicationBackupPreview.has_users ? "user accounts" : "no user accounts" }}{{ applicationBackupPreview.has_sessions ? " and active sessions" : "" }} in the backup.</p>
      <button type="button" :disabled="importingApplicationMode" @click="acceptApplicationImport">Accept all imported settings</button>
      <button type="button" class="secondary" :disabled="importingApplicationMode" @click="applySetupPreview(applicationBackupPreview)">Populate the setup pages instead</button>
      <button type="button" class="secondary" :disabled="importingApplicationMode" @click="showApplicationImportChoices = false">Cancel</button>
    </div>
  </div>
</template>

<style scoped>
.setup-page{min-height:100vh;display:flex;align-items:center;justify-content:center;background:#121212;font-family:system-ui,sans-serif;padding:32px 16px}.setup-card{width:100%;max-width:520px;background:#1a1a1a;border:1px solid #2a2a2a;border-radius:14px;padding:32px;display:flex;flex-direction:column;gap:14px;color:#fff}.setup-card.wide{max-width:760px}.tile{border:1px solid #2f2f2f;border-radius:10px;background:#151515;padding:16px;display:flex;flex-direction:column;gap:10px}.tile h2{font-size:.95rem;margin:0;color:#fff}.or-divider{text-align:center;color:#777;font-size:12px}.filesystem-backup{display:flex;flex-direction:column;gap:7px;padding:12px;border:1px solid #3a3a3a;border-radius:9px;background:#111;color:#ccc;font-size:13px}.filesystem-backup span{color:#999;line-height:1.45}.modal-backdrop{position:fixed;inset:0;background:rgba(0,0,0,.72);display:flex;align-items:center;justify-content:center;padding:20px;z-index:100}.modal{width:min(500px,100%);background:#1a1a1a;border:1px solid #363636;border-radius:12px;padding:22px;box-shadow:0 24px 64px rgba(0,0,0,.65);display:flex;flex-direction:column;gap:12px;color:#fff}.modal h2{margin:0;font-size:1.05rem}.modal p{margin:0;color:#999;line-height:1.5;font-size:13px}.modal button{background:#d68a34;border:0;border-radius:8px;padding:10px 14px;font-weight:600;cursor:pointer}.modal .secondary,.filesystem-backup .secondary{background:#252525;color:#ddd;border:1px solid #3a3a3a}.modal button:disabled{opacity:.6}.password-check{font-size:11px;color:#fca5a5}.password-check.valid{color:#86efac}.success{color:#86efac;background:rgba(34,197,94,.1);border:1px solid rgba(34,197,94,.3);border-radius:8px;padding:8px;font-size:13px}.brand{display:flex;align-items:center;gap:10px;justify-content:center}.brand h1{font-size:1.4rem;margin:0}.subtitle,.hint{color:#999;font-size:13px;text-align:center;line-height:1.5}.toggle{flex-direction:row!important;align-items:center;padding:10px;border:1px solid #2f2f2f;border-radius:8px;background:#151515}.toggle input{width:16px;height:16px;accent-color:#d68a34}.setup-card label{display:flex;flex-direction:column;gap:6px;color:#ccc;font-size:13px}.setup-card input,.setup-card select{background:#111;border:1px solid #3a3a3a;border-radius:8px;color:#fff;padding:10px;font:inherit}.generated-input{background:#202020!important;color:#777!important;cursor:not-allowed}.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.full{grid-column:1/-1}.options{display:flex;gap:18px;flex-wrap:wrap;color:#bbb;font-size:13px}.options label{flex-direction:row;align-items:center;gap:6px}.options input{accent-color:#d68a34}.progress{display:flex;gap:8px;flex-wrap:wrap}.progress span{padding:6px 9px;border-radius:999px;background:#151515;color:#777;font-size:12px}.progress span.active{background:#2b2117;color:#f0c18a}.actions{display:flex;gap:10px;justify-content:flex-end}.actions button,.setup-card>button{background:#d68a34;border:0;border-radius:8px;padding:11px 14px;font-weight:600;cursor:pointer}.actions .secondary{background:#252525;color:#ddd;border:1px solid #3a3a3a}.setup-card button:disabled{opacity:.6}.error{color:#fca5a5;background:rgba(220,38,38,.1);border:1px solid rgba(220,38,38,.3);border-radius:8px;padding:8px;font-size:13px}@media(max-width:760px){.grid{grid-template-columns:1fr}.full{grid-column:auto}}
</style>
