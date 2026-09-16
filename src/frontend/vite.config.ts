import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vite";

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
        // Docker Compose overrides this with the backend service name;
        // the central image uses localhost because both processes share
        // the same network namespace.
        target: process.env.BACKEND_URL || "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
