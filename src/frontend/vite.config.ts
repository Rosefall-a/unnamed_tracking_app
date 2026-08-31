import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import fileURLToPath from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath.fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://app:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
})