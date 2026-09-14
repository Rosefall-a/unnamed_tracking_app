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
      <div class="oidc-start-spinner" aria-hidden="true"></div>
      <h1>Starting sign-in…</h1>
      <p>Redirecting you to your identity provider.</p>
    </div>
  </main>
</template>

<style scoped>
.oidc-start {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: #121212;
  color: #aaa;
  font-family: system-ui, sans-serif;
}

.oidc-start-card {
  width: min(420px, 100%);
  padding: 32px;
  border: 1px solid #2d2d2d;
  border-radius: 16px;
  background: #1b1b1b;
  text-align: center;
  box-shadow: 0 18px 50px rgb(0 0 0 / 30%);
}

.oidc-start-card h1 {
  margin: 18px 0 8px;
  color: #f1f1f1;
  font-size: 1.25rem;
}

.oidc-start-card p {
  margin: 0;
  color: #999;
}

.oidc-start-spinner {
  width: 28px;
  height: 28px;
  margin: 0 auto;
  border: 3px solid #3a3a3a;
  border-top-color: #aaa;
  border-radius: 50%;
  animation: oidc-spin 0.8s linear infinite;
}

@keyframes oidc-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
