import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// Backend lokal (uvicorn). Frontend memakai API_BASE kosong (same-origin),
// jadi /api dan /uploads di-proxy ke FastAPI agar tidak perlu CORS.
const backend = "http://127.0.0.1:8000";

const proxy = {
  "/api": { target: backend, changeOrigin: true },
  "/uploads": { target: backend, changeOrigin: true },
};

export default defineConfig({
  plugins: [vue()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    strictPort: true,
    allowedHosts: true,
    proxy,
  },
  preview: {
    host: "0.0.0.0",
    port: 4173,
    strictPort: true,
    allowedHosts: true,
    proxy,
  },
});
