<script setup lang="ts">
import { onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { oidcLoginStatus, startOidcLogin } from "../services/oidc";

const route = useRoute();
const router = useRouter();

onMounted(async () => {
  const requestedProvider =
    typeof route.params.provider === "string" && route.params.provider.trim()
      ? route.params.provider.trim()
      : undefined;

  // The original /login/oidcstart flow works by immediately handing control
  // to the backend OIDC endpoint. Keep that exact mechanism for named
  // providers too; the backend is responsible for validating the slug and
  // enforcing the provider's autostart setting.
  if (requestedProvider && requestedProvider !== "default") {
    startOidcLogin(requestedProvider);
    return;
  }

  try {
    const status = await oidcLoginStatus();
    if (status.enabled) {
      startOidcLogin();
      return;
    }
  } catch {
    // Fall through to the normal login page.
  }

  await router.replace("/login");
});
</script>

<template>
  <main class="oidc-start">
    <div class="oidc-start-card">
      <div class="spinner" aria-hidden="true"></div>
      <h1>Starting sign-in…</h1>
      <p>Redirecting to your identity provider.</p>
    </div>
  </main>
</template>

<style scoped>
.oidc-start {
  min-height: 100vh;
  display: grid;
  place-items: center;
  background: #121212;
  color: #fff;
  font-family: system-ui, sans-serif;
}

.oidc-start-card {
  width: min(360px, calc(100% - 40px));
  padding: 32px;
  text-align: center;
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  border-radius: 14px;
  box-shadow: 0 24px 64px rgba(0, 0, 0, .5);
}

.oidc-start-card h1 {
  margin: 14px 0 6px;
  font-size: 1.15rem;
}

.oidc-start-card p {
  margin: 0;
  color: #999;
  font-size: .9rem;
}

.spinner {
  width: 28px;
  height: 28px;
  margin: 0 auto;
  border: 3px solid #3a3a3a;
  border-top-color: #d68a34;
  border-radius: 50%;
  animation: spin .8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>