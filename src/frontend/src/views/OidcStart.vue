<script setup lang="ts">
import { onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { oidcLoginStatus, startOidcLogin } from "../services/oidc";
import { rememberReturnPath } from "../state/startup";

const route = useRoute();
const router = useRouter();
onMounted(async () => {
  try {
    if (!(await oidcLoginStatus()).enabled) {
      await router.replace({
        path: "/login",
        query: { oidc_error: "not_configured" },
      });
      return;
    }
    rememberReturnPath(route.query.return_to);
    startOidcLogin();
  } catch {
    await router.replace({
      path: "/login",
      query: { oidc_error: "provider_unavailable" },
    });
  }
});
</script>

<template>
  <main class="oidc-start" aria-live="polite">Starting SSO…</main>
</template>

<style scoped>
.oidc-start {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--ui-bg);
  color: var(--ui-dim);
  font-family: var(--ui-font-family);
}
</style>
