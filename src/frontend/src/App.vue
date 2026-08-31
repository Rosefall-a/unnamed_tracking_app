<script setup lang="ts">
import { RouterView, RouterLink } from 'vue-router'
</script>

<template>
  <div id="app-root">
    <header class="navbar">
      <nav class="nav-inner">
        <RouterLink to="/" class="brand">🎮 My Games</RouterLink>
      </nav>
    </header>

    <main class="content">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
#app-root {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: #121212;
  color: #fff;
  font-family: system-ui, -apple-system, sans-serif;
}

.navbar {
  background: #1e1e1e;
  border-bottom: 1px solid #2a2a2a;
  padding: 12px 24px;
}

.nav-inner {
  max-width: 1600px;
  margin: 0 auto;
}

.brand {
  color: #fff;
  font-size: 1.2rem;
  font-weight: 700;
  text-decoration: none;
}

.content {
  flex: 1;
}
</style>