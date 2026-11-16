/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The app calls /api/v1 on its own origin and the backend sends no CORS
// headers. The dev server (and `npm run preview`, which reuses server.proxy)
// therefore proxies /api to the local FastAPI backend (uvicorn app.main:app
// --port 8000); override the target with LEXGRAPH_API_PROXY if your backend
// runs elsewhere. In production the backend itself serves the built dist/ on
// the API's origin (backend/app/main.py; docs/RUNBOOK.md "Serving the web
// app in production").
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: process.env.LEXGRAPH_API_PROXY ?? "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    globals: true,
    css: false,
  },
});
