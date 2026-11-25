import { expect, test } from '@playwright/test'

// The landing page needs no backend. It checks the walkthrough's chapter switching, the pause control,
// and that nothing makes the page wider than a phone screen.
test('landing walkthrough switches chapters and can be paused', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { level: 1 })).toContainText('knows where you stand')

  const stage = page.locator('#walkthrough-stage')
  await page.getByRole('tab', { name: /Practise interviews/ }).click()
  await expect(page.getByRole('tab', { name: /Practise interviews/ })).toHaveAttribute('aria-selected', 'true')
  await expect(stage).toContainText('/dashboard/interview')
  await expect(stage).toContainText('What happens during a context switch?')

  await page.getByRole('button', { name: 'Pause' }).click()
  await expect(page.getByRole('button', { name: 'Play' })).toBeVisible()
})

test('landing fits a phone screen', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 })
  await page.goto('/')
  const width = await page.evaluate(() => document.documentElement.scrollWidth)
  expect(width).toBeLessThanOrEqual(375)
})
