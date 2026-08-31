<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>

<template>
  <div class="not-found-page">
    <h1>404</h1>
    <p>Page not found.</p>
    <RouterLink to="/" class="home-link">Back to Library</RouterLink>
  </div>
</template>

<style scoped>
.not-found-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 70vh;
  color: #fff;
  text-align: center;
}

h1 {
  font-size: 4rem;
  margin: 0;
  color: #f5c518;
}

p {
  color: #aaa;
  font-size: 1.2rem;
  margin-bottom: 24px;
}

.home-link {
  background: #f5c518;
  color: #111;
  padding: 10px 18px;
  border-radius: 8px;
  text-decoration: none;
  font-weight: 600;
}
</style>