import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vite";

// https://vite.dev/config/
const backendUrl =
  process.env.BACKEND_URL ||
  (process.env.APP_MODE === "both" ? "http://127.0.0.1:8000" : "http://backend:8000");

export default defineConfig({
  plugins: [vue()],
  server: {
    host: true,
    port: 80,
    watch: {
      // Docker Desktop on Windows doesn't forward native filesystem
      // change events across the bind mount, so Vite's watcher never
      // fires without polling — HMR silently stops working otherwise.
      usePolling: true,
    },
    proxy: {
      "/api": {
        target: backendUrl,
        // Keep the browser-facing Host header. OIDC uses the request host
        // when a named provider has no explicit redirect URI, so changing
        // the host to backend:8000 would generate an unusable callback URL.
        changeOrigin: false,
      },
    },
  },
});
