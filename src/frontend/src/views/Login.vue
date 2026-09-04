<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { login } from '../services/auth'
import { checkAuth } from '../state/auth'

const router = useRouter()

const usernameOrEmail = ref('')
const password = ref('')
const error = ref<string | null>(null)
const loading = ref(false)

async function submit() {
  if (!usernameOrEmail.value.trim() || !password.value) {
    error.value = 'Enter your username/email and password.'
    return
  }

  loading.value = true
  error.value = null

  try {
    await login(usernameOrEmail.value.trim(), password.value)
    await checkAuth()
    router.push('/')
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Login failed'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="login-page">
    <form class="login-card" @submit.prevent="submit">
      <div class="login-brand">
        <span class="brand-icon">🎮</span>
        <h1>Archive</h1>
      </div>
      <p class="login-subtitle">Sign in to your library</p>

      <label class="field">
        <span>Username or email</span>
        <input v-model="usernameOrEmail" type="text" autocomplete="username" required />
      </label>

      <label class="field">
        <span>Password</span>
        <input v-model="password" type="password" autocomplete="current-password" required />
      </label>

      <div v-if="error" class="login-error">{{ error }}</div>

      <button type="submit" class="login-button" :disabled="loading">
        {{ loading ? 'Signing in…' : 'Sign in' }}
      </button>
    </form>
  </main>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #121212;
  font-family: system-ui, sans-serif;
  position: relative;
  overflow: hidden;
}
.login-page::before {
  content: '';
  position: absolute;
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(214, 138, 52, 0.18) 0%, transparent 70%);
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 0;
}
.login-card {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 360px;
  background: rgba(26, 26, 26, 0.9);
  backdrop-filter: blur(12px);
  border: 1px solid #2a2a2a;
  border-radius: 14px;
  padding: 32px;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.login-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  justify-content: center;
}
.brand-icon {
  font-size: 26px;
}
.login-brand h1 {
  margin: 0;
  color: #fff;
  font-size: 1.4rem;
}
.login-subtitle {
  margin: -8px 0 4px;
  color: #999;
  font-size: 13px;
  text-align: center;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 0.85rem;
  color: #ccc;
}
.field input {
  background: #111;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  color: #fff;
  padding: 10px 12px;
  font: inherit;
  transition: border-color 0.15s ease;
}
.field input:focus {
  outline: none;
  border-color: #d68a34;
}
.login-error {
  color: #fca5a5;
  font-size: 13px;
  background: rgba(220, 38, 38, 0.1);
  border: 1px solid rgba(220, 38, 38, 0.3);
  border-radius: 8px;
  padding: 8px 10px;
}
.login-button {
  background: #d68a34;
  color: #111;
  border: none;
  border-radius: 8px;
  padding: 11px;
  font-weight: 600;
  cursor: pointer;
  margin-top: 4px;
  transition: background 0.15s ease;
}
.login-button:hover:not(:disabled) {
  background: #e6994a;
}
.login-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>