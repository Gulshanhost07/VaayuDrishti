import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";

const root = import.meta.dirname;

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: resolve(root, "..", "frontend"),
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: resolve(root, "index.html"),
        report: resolve(root, "report.html"),
        submit: resolve(root, "submit.html"),
        admin: resolve(root, "admin.html"),
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
      "/docs": "http://localhost:8000",
      "/openapi.json": "http://localhost:8000",
    },
  },
});
