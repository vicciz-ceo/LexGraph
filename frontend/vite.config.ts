/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Scaffolding only (sprint 2026-07-25-collaborative-assertions, Planner
// pass). No app entry/business logic configured beyond the React plugin —
// Developer UI tracks (UI1-UI3) add components under src/components/.
export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    globals: true,
    css: false,
  },
});
