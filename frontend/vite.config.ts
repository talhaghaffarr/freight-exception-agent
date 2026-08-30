import { fileURLToPath, URL } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  server: {
    host: true,
    port: 5173,
    // The console never learns the API host at build time; the dev server and
    // the production nginx config both proxy /api to the Flask service.
    proxy: {
      "/api": { target: process.env.VITE_API_ORIGIN ?? "http://localhost:8000", changeOrigin: true },
      "/healthz": { target: process.env.VITE_API_ORIGIN ?? "http://localhost:8000", changeOrigin: true },
    },
  },
  build: { outDir: "dist", sourcemap: true },
});
