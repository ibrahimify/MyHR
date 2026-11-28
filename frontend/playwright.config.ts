import { defineConfig } from "@playwright/test";

const frontendPort = 3100;
const apiPort = 8100;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? "github" : "line",
  use: {
    baseURL: `http://127.0.0.1:${frontendPort}`,
    trace: "retain-on-failure",
    screenshot: process.env.CAPTURE_UI ? "on" : "only-on-failure",
  },
  webServer: [
    {
      command: "node scripts/start-test-backend.mjs",
      url: `http://127.0.0.1:${apiPort}/health`,
      timeout: 120_000,
      reuseExistingServer: false,
      env: { E2E_API_PORT: String(apiPort) },
    },
    {
      command: `npm run dev -- --hostname 127.0.0.1 --port ${frontendPort}`,
      url: `http://127.0.0.1:${frontendPort}`,
      timeout: 120_000,
      reuseExistingServer: false,
      env: {
        NEXT_PUBLIC_API_URL: `http://127.0.0.1:${apiPort}`,
        NEXT_PUBLIC_AUTH_MODE: "local",
      },
    },
  ],
});
