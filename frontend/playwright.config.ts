import { defineConfig, devices } from "@playwright/test";

/**
 * E2E config. Auto-start cả FE (Next dev) + BE (Django runserver).
 * YÊU CẦU: Docker (postgres+redis+minio) đang chạy + superuser `smoke`
 * tồn tại trong dev DB.
 *
 * BE health check dùng /api/docs/ (200, không cần auth) thay vì
 * /api/v1/catalog/products/ (401).
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  reporter: "list",
  timeout: 30_000,
  use: {
    baseURL: "http://localhost:3000",
    headless: true,
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: "npm run dev",
      url: "http://localhost:3000",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command:
        ".venv\\Scripts\\python.exe manage.py runserver 8000 --noreload",
      cwd: "../backend",
      url: "http://localhost:8000/api/docs/",
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
  ],
});
