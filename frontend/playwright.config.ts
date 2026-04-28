import { defineConfig } from "@playwright/test";

// Manual pre-deploy check. Use `npm run e2e -- --headed` for debug.
export default defineConfig({
  testDir: "./tests/e2e",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:5173",
    trace: "on-first-retry",
  },
});
