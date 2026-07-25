import { defineConfig, devices } from '@playwright/test'

const backendPython = process.env.PLAYWRIGHT_PYTHON ?? 'E:\\Anaconda3\\envs\\ml2025\\python.exe'

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
    { name: 'desktop-chrome', use: { ...devices['Desktop Chrome'], channel: 'chrome' } },
    { name: 'narrow-chrome', use: { viewport: { width: 430, height: 900 }, channel: 'chrome' } },
  ],
  webServer: {
    command: `"${backendPython}" -m uvicorn app.main:app --host 127.0.0.1 --port 8000`,
    cwd: "../backend",
    url: "http://127.0.0.1:8000/health",
    reuseExistingServer: true,
    timeout: 120_000,
  },
})
