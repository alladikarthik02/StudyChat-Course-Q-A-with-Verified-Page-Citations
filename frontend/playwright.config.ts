import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  use: {
    baseURL: "http://127.0.0.1:5173",
    headless: true,
    viewport: { width: 1440, height: 960 },
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      command: `${process.env.STUDYCHAT_PYTHON || "../.venv/bin/python"} ../scripts/browser_server.py`,
      url: "http://127.0.0.1:8000/ready",
      reuseExistingServer: false,
      timeout: 30000,
    },
    {
      command: "pnpm dev",
      url: "http://127.0.0.1:5173",
      reuseExistingServer: false,
      timeout: 30000,
    },
  ],
});
