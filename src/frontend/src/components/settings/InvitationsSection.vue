<script setup lang="ts">
import { onMounted, ref } from "vue";
import {
  createInvitation,
  listInvitations,
  resendInvitation,
  revokeInvitation,
  type Invitation,
} from "../../services/invitations";

const invitations = ref<Invitation[]>([]);
const username = ref("");
const email = ref("");
const isAdmin = ref(false);
const busy = ref(false);
const error = ref<string | null>(null);

async function refresh() {
  invitations.value = await listInvitations();
}
async function invite() {
  busy.value = true;
  error.value = null;
  try {
    await createInvitation({
      username: username.value.trim(),
      email: email.value.trim(),
      isAdmin: isAdmin.value,
    });
    username.value = "";
    email.value = "";
    isAdmin.value = false;
    await refresh();
  } catch (err) {
    error.value =
      err instanceof Error ? err.message : "Failed to send invitation.";
  } finally {
    busy.value = false;
  }
}
async function resend(id: string) {
  busy.value = true;
  try {
    await resendInvitation(id);
    await refresh();
  } finally {
    busy.value = false;
  }
}
async function revoke(item: Invitation) {
  if (!window.confirm(`Revoke the invitation for ${item.email}?`)) return;
  busy.value = true;
  try {
    await revokeInvitation(item.id);
    await refresh();
  } finally {
    busy.value = false;
  }
}
onMounted(
  () =>
    void refresh().catch(() => (error.value = "Failed to load invitations.")),
);
</script>

<template>
  <section class="section">
    <h2>User invitations</h2>
    <form class="invite-form" @submit.prevent="invite">
      <input v-model="username" placeholder="Username" required />
      <input v-model="email" type="email" placeholder="Email" required />
      <label><input v-model="isAdmin" type="checkbox" /> Administrator</label>
      <button :disabled="busy">Send invitation</button>
    </form>
    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="!invitations.length" class="empty">No invitations yet.</p>
    <div v-else class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>User</th>
            <th>Email</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in invitations" :key="item.id">
            <td>{{ item.username }}</td>
            <td>{{ item.email }}</td>
            <td>
              {{
                item.accepted_at
                  ? "Accepted"
                  : item.revoked_at
                    ? "Revoked"
                    : "Pending"
              }}
            </td>
            <td>
              <button
                :disabled="busy || Boolean(item.accepted_at)"
                @click="resend(item.id)"
              >
                Resend</button
              ><button
                :disabled="busy || Boolean(item.accepted_at || item.revoked_at)"
                @click="revoke(item)"
              >
                Revoke
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<style scoped>
.section {
  display: grid;
  gap: 16px;
}
.invite-form {
  display: grid;
  grid-template-columns: 1fr 1fr auto auto;
  gap: 10px;
  align-items: center;
}
.invite-form input {
  padding: 9px;
  background: #111;
  color: #fff;
  border: 1px solid #444;
  border-radius: 8px;
}
.section button {
  padding: 8px 10px;
  border: 1px solid #555;
  border-radius: 8px;
  background: #292929;
  color: #fff;
  cursor: pointer;
}
.table-wrap {
  overflow-x: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
}
th,
td {
  padding: 10px;
  text-align: left;
  border-bottom: 1px solid #333;
}
td button + button {
  margin-left: 8px;
}
.error {
  color: #fca5a5;
}
.empty {
  color: #888;
}
@media (max-width: 760px) {
  .invite-form {
    grid-template-columns: 1fr;
  }
}
</style>
