<script setup lang="ts">
import { onMounted } from "vue";
import { startOidcLogin } from "../services/oidc";

onMounted(() => startOidcLogin());
</script>

<template><main class="oidc-start">Starting SSO…</main></template>

<style scoped>
.oidc-start{min-height:100vh;display:flex;align-items:center;justify-content:center;background:#121212;color:#aaa;font-family:system-ui,sans-serif}
</style>
