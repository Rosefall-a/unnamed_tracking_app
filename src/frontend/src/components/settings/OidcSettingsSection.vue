<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { fetchDeploymentSettings, updateDeploymentSettings } from "../../services/deploymentSettings";
import ToggleButton from "./ToggleButton.vue";

const loading = ref(true);
const saving = ref(false);
const error = ref<string | null>(null);
const saved = ref(false);
const oidc = reactive({
  issuer_url: "", client_id: "", client_secret: "", scopes: "openid profile email", redirect_uri: "",
  groups_claim: "groups", admin_group: "", user_match_field: "email", default_login_method: "local",
  login_button_text: "Continue with SSO", allow_new_users: true,
});

const defaultRedirectUri = () => `${window.location.origin}/api/auth/oidc/callback`;

onMounted(async () => {
  try {
    const result = await fetchDeploymentSettings();
    oidc.issuer_url = result.oidc.issuer_url ?? "";
    oidc.client_id = result.oidc.client_id ?? "";
    oidc.scopes = result.oidc.scopes ?? "openid profile email";
    oidc.redirect_uri = result.oidc.redirect_uri || defaultRedirectUri();
    oidc.groups_claim = result.oidc.groups_claim ?? "groups";
    oidc.admin_group = result.oidc.admin_group ?? "";
    oidc.user_match_field = result.oidc.user_match_field === "username" ? "username" : "email";
    oidc.default_login_method = result.oidc.default_login_method === "sso" ? "sso" : "local";
    oidc.login_button_text = result.oidc.login_button_text?.trim() || "Continue with SSO";
    oidc.allow_new_users = result.oidc.allow_new_users !== false;
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to load OIDC settings.";
  } finally { loading.value = false; }
});

async function save() {
  saving.value = true; error.value = null; saved.value = false;
  try {
    const payload: Record<string, string | boolean> = {
      oidc_issuer_url: oidc.issuer_url.trim(), oidc_client_id: oidc.client_id.trim(),
      oidc_scopes: oidc.scopes.trim() || "openid profile email", oidc_redirect_uri: oidc.redirect_uri.trim() || defaultRedirectUri(),
      oidc_groups_claim: oidc.groups_claim.trim() || "groups", oidc_admin_group: oidc.admin_group.trim(),
      oidc_user_match_field: oidc.user_match_field, oidc_default_login_method: oidc.default_login_method,
      oidc_login_button_text: oidc.login_button_text.trim() || "Continue with SSO", oidc_allow_new_users: oidc.allow_new_users,
    };
    if (oidc.client_secret) payload.oidc_client_secret = oidc.client_secret;
    const result = await updateDeploymentSettings(payload);
    oidc.redirect_uri = result.oidc.redirect_uri || defaultRedirectUri();
    oidc.login_button_text = result.oidc.login_button_text?.trim() || "Continue with SSO";
    oidc.allow_new_users = result.oidc.allow_new_users !== false;
    oidc.client_secret = ""; saved.value = true;
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to save OIDC settings.";
  } finally { saving.value = false; }
}
</script>

<template>
  <section class="section">
    <h2>OpenID Connect / SSO</h2>
    <p class="hint">Configure browser-based SSO. The client secret stays encrypted on the backend and is never returned to the browser after saving.</p>
    <div v-if="loading">Loading…</div>
    <template v-else>
      <div class="grid">
        <label><span>Issuer / discovery URL</span><input v-model="oidc.issuer_url" placeholder="https://login.example.com/realms/archive" /><small>Enter the issuer URL, or paste the provider's <code>/.well-known/openid-configuration</code> URL directly.</small></label>
        <label><span>Client ID</span><input v-model="oidc.client_id" /></label>
        <label><span>Client secret</span><input v-model="oidc.client_secret" type="password" placeholder="Leave blank to keep the saved secret" /></label>
        <label><span>Scopes</span><input v-model="oidc.scopes" /></label>
        <label class="full"><span>Redirect URI</span><input v-model="oidc.redirect_uri" autocomplete="url" /></label>
        <label><span>Groups claim</span><input v-model="oidc.groups_claim" placeholder="groups" /></label>
        <label><span>Admin group</span><input v-model="oidc.admin_group" placeholder="archive-admins" /></label>
      </div>

      <div class="match-panel">
        <div><strong>Match existing users by</strong><p class="hint">Choose which OIDC identity value is used to connect SSO to an existing local account.</p></div>
        <div class="choices"><label class="choice"><input v-model="oidc.user_match_field" type="radio" value="email" /><span><strong>Email</strong><small>OIDC email → local email</small></span></label><label class="choice"><input v-model="oidc.user_match_field" type="radio" value="username" /><span><strong>Username</strong><small>OIDC preferred_username → local username</small></span></label></div>
      </div>

      <div class="login-panel">
        <div><strong>Login experience</strong><p class="hint">Choose which method is presented first on the login page. The other method remains available in the login-method dropdown.</p></div>
        <div class="login-controls"><label><span>Default login method</span><select v-model="oidc.default_login_method"><option value="sso">SSO</option><option value="local">Local username & password</option></select></label><label><span>SSO button text</span><input v-model="oidc.login_button_text" maxlength="100" /></label></div>
      </div>

      <div class="policy-panel">
        <div><strong>Account creation</strong><p class="hint">Allow users who successfully authenticate with OIDC but do not already have a local account to be created automatically.</p></div>
        <ToggleButton v-model="oidc.allow_new_users" label="Create new users" />
      </div>

      <p class="hint">Direct SSO start: <code>/login/oidcstart</code>. The redirect URI defaults to the URL you are currently using plus <code>/api/auth/oidc/callback</code>. If an admin group is configured, membership in that IdP group controls administrator status at SSO login.</p>
      <p v-if="error" class="error">{{ error }}</p><p v-if="saved" class="success">OIDC settings saved.</p>
      <button :disabled="saving" @click="save">{{ saving ? "Saving…" : "Save OIDC settings" }}</button>
    </template>
  </section>
</template>

<style scoped>
.section{display:flex;flex-direction:column;gap:16px}.hint{color:#999;font-size:13px;line-height:1.5}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.grid label{display:flex;flex-direction:column;gap:6px;color:#ccc;font-size:13px}.grid label.full{grid-column:1/-1}.grid input,.login-controls input,.login-controls select{background:#111;border:1px solid #3a3a3a;border-radius:8px;color:#fff;padding:10px;font:inherit}.grid input:focus,.login-controls input:focus,.login-controls select:focus{outline:none;border-color:#d68a34}.grid small{color:#888;font-size:11px;line-height:1.4}.match-panel,.login-panel,.policy-panel{border:1px solid #2f2f2f;border-radius:10px;padding:14px;background:#151515;display:flex;justify-content:space-between;gap:24px}.match-panel strong,.login-panel strong,.policy-panel strong{color:#fff}.match-panel .hint,.login-panel .hint,.policy-panel .hint{margin:6px 0 0}.choices{display:flex;gap:10px;flex-shrink:0}.choice{display:flex;align-items:flex-start;gap:8px;min-width:170px;padding:10px 12px;border:1px solid #333;border-radius:8px;background:#111;cursor:pointer;color:#ccc}.choice input{accent-color:#d68a34;margin-top:3px}.choice span{display:flex;flex-direction:column;gap:3px}.choice strong{font-size:13px}.choice small{font-size:11px;color:#888}.choice:has(input:checked){border-color:#d68a34;background:rgba(214,138,52,.08)}.login-panel{align-items:flex-start}.login-controls{display:flex;gap:12px;min-width:420px}.login-controls label{display:flex;flex-direction:column;gap:6px;color:#ccc;font-size:13px;flex:1}.login-controls select{appearance:auto}.policy-panel{align-items:center}.policy-panel :deep(.toggle-button){min-width:180px}button{align-self:flex-start;background:#d68a34;border:0;border-radius:8px;padding:10px 14px;font-weight:600;cursor:pointer}button:disabled{opacity:.6}.error{color:#fca5a5}.success{color:#86efac}@media(max-width:900px){.match-panel,.login-panel,.policy-panel{flex-direction:column}.choices{flex-wrap:wrap}.login-controls{min-width:0;width:100%;flex-direction:column}}@media(max-width:760px){.grid{grid-template-columns:1fr}.grid label.full{grid-column:auto}}
</style>
