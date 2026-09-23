import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vite";

const backendTarget = process.env.BACKEND_URL ||
  (process.env.APP_MODE === "both" ? "http://127.0.0.1:8000" : (process.env.DEFAULT_BACKEND_URL || "http://backend:8000"));

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    host: true, // listen on 0.0.0.0 so the container's port mapping works
    port: 80,
    watch: {
      // Docker Desktop on Windows doesn't forward native filesystem
      // change events across the bind mount, so Vite's watcher never
      // fires without polling — HMR silently stops working otherwise.
      usePolling: true,
    },
    proxy: {
      "/api": {
        target: backendTarget,
        changeOrigin: true,
      },
    },
  },
});
