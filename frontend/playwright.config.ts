import { defineConfig, devices } from "@playwright/test"

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  fullyParallel: false,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:8000",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "mobile-chrome",
      use: { ...devices["Pixel 7"], channel: "chrome", reducedMotion: "reduce" },
    },
  ],
  webServer: {
    command: "python -m uvicorn app.main:app --host 127.0.0.1 --port 8000",
    cwd: "../backend",
    url: "http://127.0.0.1:8000/health",
    reuseExistingServer: true,
    timeout: 120_000,
  },
})
