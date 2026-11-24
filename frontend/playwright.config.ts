import { defineConfig } from '@playwright/test'

/**
 * E2E runs against a backend started with DATABASE_BACKEND=memory and LLM_PROVIDER=fake
 * (deterministic answers), and a frontend built with NEXT_PUBLIC_E2E_ACCESS_TOKEN.
 * See docs/learn/resume-screener-guide.md ("Running the E2E test").
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:3100',
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
  reporter: [['list']],
})
