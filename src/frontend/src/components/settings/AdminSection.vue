<script setup lang="ts">
import { onMounted, ref } from "vue";
import { currentUser } from "../../state/auth";
import { createUser, deleteUser, listUsers, setUserAdmin, signOutAllUsers } from "../../services/admin";
import { fetchDeploymentSettings } from "../../services/deploymentSettings";
import { createInvitation, listInvitations, resendInvitation, revokeInvitation } from "../../services/invitations";
import type { AdminUser } from "../../services/admin";
import type { Invitation } from "../../services/invitations";
import ToggleButton from "./ToggleButton.vue";

const users = ref<AdminUser[]>([]);
const invitations = ref<Invitation[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);
const smtpReady = ref(false);
const signingOut = ref(false);
const signOutMessage = ref<string | null>(null);
const showSignOutConfirm = ref(false);

async function loadUsers() {
  loading.value = true;
  error.value = null;
  try {
    const [loadedUsers, loadedInvitations, deployment] = await Promise.all([
      listUsers(),
      listInvitations(),
      fetchDeploymentSettings(),
    ]);
    users.value = loadedUsers;
    invitations.value = loadedInvitations;
    const smtp = deployment.smtp;
    smtpReady.value = Boolean(
      smtp.enabled &&
      smtp.host &&
      smtp.from_email &&
      smtp.port &&
      (!smtp.username || smtp.password_configured),
    );
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to load users";
  } finally {
    loading.value = false;
  }
}

onMounted(loadUsers);

function requestSignOutEveryone() { showSignOutConfirm.value = true; }

async function signOutEveryone() {
  showSignOutConfirm.value = false;
  signingOut.value = true;
  signOutMessage.value = null;
  try {
    const result = await signOutAllUsers();
    signOutMessage.value = `Revoked ${result.sessions_revoked} active session${result.sessions_revoked === 1 ? "" : "s"}. Everyone must sign in again.`;
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to sign out all users";
  } finally { signingOut.value = false; }
}

const deletingUser = ref<AdminUser | null>(null);
const deleting = ref(false);
const deleteError = ref<string | null>(null);

async function confirmDeleteUser() {
  if (!deletingUser.value) return;
  deleting.value = true;
  deleteError.value = null;
  try {
    await deleteUser(deletingUser.value.id);
    deletingUser.value = null;
    await loadUsers();
  } catch (err) {
    deleteError.value = err instanceof Error ? err.message : "Failed to delete user";
  } finally { deleting.value = false; }
}

const togglingAdminId = ref<string | null>(null);
async function toggleAdmin(user: AdminUser) {
  togglingAdminId.value = user.id;
  try {
    const updated = await setUserAdmin(user.id, !user.is_admin);
    const index = users.value.findIndex((u) => u.id === user.id);
    if (index !== -1) users.value[index] = updated;
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to update user";
  } finally { togglingAdminId.value = null; }
}

const showCreateForm = ref(false);
const createUsername = ref("");
const createEmail = ref("");
const createPassword = ref("");
const createIsAdmin = ref(false);
const creating = ref(false);
const createError = ref<string | null>(null);
const createMessage = ref<string | null>(null);

function openCreateForm() {
  createUsername.value = ""; createEmail.value = ""; createPassword.value = "";
  createIsAdmin.value = false; createError.value = null; createMessage.value = null;
  showCreateForm.value = true;
}

async function handleCreateUser() {
  creating.value = true; createError.value = null; createMessage.value = null;
  try {
    await createUser({ username: createUsername.value.trim(), email: createEmail.value.trim(), password: createPassword.value, isAdmin: createIsAdmin.value });
    showCreateForm.value = false; createUsername.value = ""; createEmail.value = ""; createPassword.value = ""; createIsAdmin.value = false;
    createMessage.value = "User created successfully.";
    await loadUsers();
  } catch (err) {
    createError.value = err instanceof Error ? err.message : "Failed to create user";
  } finally { creating.value = false; }
}

const showInviteForm = ref(false);
const inviteUsername = ref("");
const inviteEmail = ref("");
const inviteIsAdmin = ref(false);
const inviting = ref(false);
const inviteError = ref<string | null>(null);
const inviteMessage = ref<string | null>(null);

function openInviteForm() {
  if (!smtpReady.value) return;
  inviteUsername.value = ""; inviteEmail.value = ""; inviteIsAdmin.value = false;
  inviteError.value = null; inviteMessage.value = null; showInviteForm.value = true;
}

async function handleInviteUser() {
  if (!smtpReady.value) return;
  inviting.value = true; inviteError.value = null; inviteMessage.value = null;
  try {
    await createInvitation({ username: inviteUsername.value.trim(), email: inviteEmail.value.trim(), isAdmin: inviteIsAdmin.value });
    inviteUsername.value = ""; inviteEmail.value = ""; inviteIsAdmin.value = false; showInviteForm.value = false;
    inviteMessage.value = "Invitation sent. The user can finish setting up their account from the email.";
    invitations.value = await listInvitations();
  } catch (err) {
    inviteError.value = err instanceof Error ? err.message : "Failed to send invitation";
  } finally { inviting.value = false; }
}

const invitationActionId = ref<string | null>(null);
async function resend(id: string) {
  invitationActionId.value = id; error.value = null;
  try { await resendInvitation(id); invitations.value = await listInvitations(); }
  catch (err) { error.value = err instanceof Error ? err.message : "Failed to resend invitation"; }
  finally { invitationActionId.value = null; }
}

async function revoke(id: string) {
  invitationActionId.value = id; error.value = null;
  try { await revokeInvitation(id); invitations.value = await listInvitations(); }
  catch (err) { error.value = err instanceof Error ? err.message : "Failed to revoke invitation"; }
  finally { invitationActionId.value = null; }
}

function invitationStatus(invitation: Invitation): string {
  if (invitation.status) return invitation.status.charAt(0).toUpperCase() + invitation.status.slice(1);
  if (invitation.accepted_at) return "Accepted";
  if (invitation.revoked_at) return "Revoked";
  if (invitation.expires_at * 1000 <= Date.now()) return "Expired";
  return "Pending";
}
</script>

<template>
  <section class="settings-section">
    <h2>Users</h2>
    <p class="section-hint">Manage accounts and invite people to create their own passwords.</p>
    <div class="security-panel">
      <div><h3>Session management</h3><p>Immediately invalidate every active login session. This includes your current session.</p></div>
      <button type="button" class="danger-button" :disabled="signingOut" @click="requestSignOutEveryone">{{ signingOut ? "Signing out…" : "Sign out all users" }}</button>
    </div>
    <p v-if="signOutMessage" class="form-success">{{ signOutMessage }}</p>
    <p v-if="loading">Loading…</p>
    <p v-else-if="error" class="form-error">{{ error }}</p>
    <template v-else>
      <div class="section-heading">
        <div><h3>Accounts</h3><p>Existing users can be created directly, or invited to choose their own password.</p></div>
        <div class="heading-actions">
          <button type="button" class="secondary-button compact" @click="showCreateForm ? (showCreateForm = false) : openCreateForm()">{{ showCreateForm ? "Cancel create" : "+ Create user" }}</button>
          <button v-if="smtpReady" type="button" class="primary-button compact" @click="showInviteForm ? (showInviteForm = false) : openInviteForm()">{{ showInviteForm ? "Cancel invite" : "+ Invite user" }}</button>
          <span v-else class="smtp-required">Configure and enable SMTP to invite users.</span>
        </div>
      </div>
      <form v-if="showCreateForm" class="create-form" @submit.prevent="handleCreateUser">
        <p class="form-hint">Create the account immediately and set its initial password here.</p>
        <label class="field"><span>Username</span><input v-model="createUsername" type="text" required autocomplete="username" /></label>
        <label class="field"><span>Email</span><input v-model="createEmail" type="email" required autocomplete="email" /></label>
        <label class="field"><span>Password</span><input v-model="createPassword" type="password" required autocomplete="new-password" /></label>
        <ToggleButton v-model="createIsAdmin" label="Grant admin access">Grant admin access</ToggleButton>
        <div v-if="createError" class="form-error">{{ createError }}</div>
        <button type="submit" class="primary-button" :disabled="creating">{{ creating ? "Creating user…" : "Create user" }}</button>
      </form>
      <p v-if="createMessage" class="form-success">{{ createMessage }}</p>
      <form v-if="showInviteForm" class="create-form" @submit.prevent="handleInviteUser">
        <p class="form-hint">We'll email the invitation link. The invited person chooses their password when they accept it.</p>
        <label class="field"><span>Username</span><input v-model="inviteUsername" type="text" required autocomplete="username" /></label>
        <label class="field"><span>Email</span><input v-model="inviteEmail" type="email" required autocomplete="email" /></label>
        <ToggleButton v-model="inviteIsAdmin" label="Grant admin access">Grant admin access</ToggleButton>
        <div v-if="inviteError" class="form-error">{{ inviteError }}</div>
        <button type="submit" class="primary-button" :disabled="inviting">{{ inviting ? "Sending invitation…" : "Send invitation" }}</button>
      </form>
      <p v-if="inviteMessage" class="form-success">{{ inviteMessage }}</p>
      <table class="user-table">
        <thead><tr><th>Username</th><th>Email</th><th>Role</th><th>Joined</th><th></th></tr></thead>
        <tbody><tr v-for="user in users" :key="user.id"><td>{{ user.username }}</td><td>{{ user.email }}</td><td><span class="role-badge" :class="{admin:user.is_admin}">{{ user.is_admin ? "Admin" : "User" }}</span></td><td class="joined">{{ user.created_at ? new Date(user.created_at * 1000).toLocaleDateString() : "N/A" }}</td><td class="actions"><button type="button" class="small-button" :disabled="user.id === currentUser?.id || togglingAdminId === user.id" @click="toggleAdmin(user)">{{ user.is_admin ? "Demote" : "Promote" }}</button><button type="button" class="small-button danger" :disabled="user.id === currentUser?.id" @click="deletingUser = user; deleteError = null">Delete</button></td></tr></tbody>
      </table>
      <div v-if="invitations.length" class="invitation-list">
        <div class="section-heading"><div><h3>Invitations</h3><p>Pending invitations expire after 7 days and can be resent or revoked.</p></div></div>
        <table class="user-table"><thead><tr><th>Username</th><th>Email</th><th>Role</th><th>Status</th><th></th></tr></thead><tbody>
          <tr v-for="invitation in invitations" :key="invitation.id"><td>{{ invitation.username }}</td><td>{{ invitation.email }}</td><td><span class="role-badge" :class="{admin:invitation.is_admin}">{{ invitation.is_admin ? "Admin" : "User" }}</span></td><td><span class="status-badge">{{ invitationStatus(invitation) }}</span></td><td class="actions" v-if="!invitation.accepted_at"><button type="button" class="small-button" :disabled="!!invitationActionId" @click="resend(invitation.id)">{{ invitationActionId === invitation.id ? "Working…" : "Resend" }}</button><button type="button" class="small-button danger" :disabled="!!invitationActionId || !!invitation.revoked_at" @click="revoke(invitation.id)">Revoke</button></td></tr>
        </tbody></table>
      </div>
    </template>
    <div v-if="deletingUser" class="confirm-backdrop" @click.self="deletingUser=null"><div class="confirm-dialog"><h3>Delete {{ deletingUser.username }}?</h3><p>This can't be undone: their data folder is removed too.</p><div v-if="deleteError" class="form-error">{{ deleteError }}</div><div class="confirm-actions"><button type="button" class="secondary-button" @click="deletingUser=null">Cancel</button><button type="button" class="danger-button" :disabled="deleting" @click="confirmDeleteUser">{{ deleting ? "Deleting…" : "Delete" }}</button></div></div></div>
    <div v-if="showSignOutConfirm" class="confirm-backdrop" @click.self="showSignOutConfirm=false"><div class="confirm-dialog"><h3>Sign out all users?</h3><p>This immediately invalidates every active session on this server, including your own. You will need to sign in again afterward.</p><div class="confirm-actions"><button type="button" class="secondary-button" @click="showSignOutConfirm=false">Cancel</button><button type="button" class="danger-button" :disabled="signingOut" @click="signOutEveryone">Sign out everyone</button></div></div></div>
  </section>
</template>

<style scoped>
.settings-section h2{margin:0 0 8px;padding-left:12px;border-left:3px solid #d68a34;font-size:1rem;color:#fff}.section-hint{color:#999;font-size:.82rem;line-height:1.6;margin:0 0 16px}.security-panel{display:flex;justify-content:space-between;align-items:center;gap:18px;background:rgba(220,38,38,.06);border:1px solid rgba(220,38,38,.25);border-radius:10px;padding:15px;margin-bottom:16px}.security-panel h3,.section-heading h3{margin:0 0 5px;color:#fff;font-size:.9rem}.security-panel p,.section-heading p,.form-hint{margin:0;color:#999;font-size:.8rem;line-height:1.5}.section-heading{display:flex;justify-content:space-between;align-items:center;gap:16px;margin:18px 0 10px}.heading-actions{display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end}.smtp-required{color:#999;font-size:.75rem}.user-table{width:100%;border-collapse:collapse;margin-bottom:16px;font-size:.85rem}.user-table th{text-align:left;color:#777;font-size:.72rem;text-transform:uppercase;padding:0 10px 8px;border-bottom:1px solid #2a2a2a}.user-table td{padding:10px;border-bottom:1px solid #232323;color:#ccc}.role-badge,.status-badge{font-size:11px;font-weight:700;padding:3px 10px;border-radius:999px;color:#999;background:rgba(255,255,255,.06)}.role-badge.admin{color:#d68a34;background:rgba(214,138,52,.14)}.joined{color:#999;font-size:.8rem}.actions{display:flex;gap:6px;justify-content:flex-end}.small-button,.secondary-button{background:rgba(255,255,255,.08);color:#fff;border:0;border-radius:6px;padding:6px 10px;font-size:12px;font-weight:600;cursor:pointer}.small-button:disabled,.danger-button:disabled{opacity:.4;cursor:not-allowed}.small-button.danger{color:#fca5a5}.secondary-button{border-radius:8px;padding:10px 18px}.secondary-button.compact{padding:9px 14px}.primary-button{background:#d68a34;color:#111;border:0;border-radius:8px;padding:11px;font-weight:600;cursor:pointer}.primary-button.compact{padding:9px 14px}.primary-button:disabled{opacity:.6}.create-form{display:flex;flex-direction:column;gap:14px;margin:0 0 18px;padding:16px;border:1px solid #2a2a2a;border-radius:10px;background:#151515}.field{display:flex;flex-direction:column;gap:6px;font-size:.85rem;color:#ccc}.field input{background:#111;border:1px solid #3a3a3a;border-radius:8px;color:#fff;padding:10px 12px;font:inherit}.form-error,.form-success{font-size:13px;border-radius:8px;padding:8px 10px}.form-error{color:#fca5a5;background:rgba(220,38,38,.1);border:1px solid rgba(220,38,38,.3)}.form-success{color:#86efac;background:rgba(34,197,94,.1);border:1px solid rgba(34,197,94,.3)}.invitation-list{border-top:1px solid #2a2a2a;padding-top:4px}.danger-button{background:rgba(220,38,38,.18);color:#fca5a5;border:0;border-radius:8px;padding:10px 14px;font-weight:600;cursor:pointer}.confirm-backdrop{position:fixed;inset:0;background:rgba(0,0,0,.65);display:flex;align-items:center;justify-content:center;z-index:60}.confirm-dialog{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:12px;padding:22px;max-width:360px;box-shadow:0 24px 64px rgba(0,0,0,.6)}.confirm-dialog h3{margin:0 0 8px;color:#fff}.confirm-dialog p{margin:0 0 18px;color:#999;font-size:.85rem}.confirm-actions{display:flex;justify-content:flex-end;gap:10px}
</style>
