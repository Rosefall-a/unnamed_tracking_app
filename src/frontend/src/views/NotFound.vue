<script setup lang="ts">
import { RouterLink } from "vue-router";
</script>

<template>
  <main class="not-found">
    <h1>Page not found</h1>
    <p>That address does not lead anywhere in this app.</p>
    <RouterLink to="/" class="home-link">Go to the home page</RouterLink>
  </main>
</template>

<style scoped>
.not-found {
  max-width: 480px;
  margin: 96px auto;
  padding: 0 24px;
  text-align: center;
  color: #e5e5e5;
}
h1 {
  font-size: 1.6rem;
  font-weight: 800;
  margin: 0 0 8px;
}
p {
  color: #9a9a9a;
  margin: 0 0 20px;
}
.home-link {
  color: #d68a34;
  font-weight: 700;
  text-decoration: none;
}
.home-link:hover {
  text-decoration: underline;
}
</style>
