import { expect, test } from '@playwright/test'

// Memory-DB + fake-LLM backend. The questionnaire's defaults are a 3rd-year student, 2 h weekdays, 4 h weekends.
test('questionnaire -> preview -> plan -> tick a task -> today dashboard', async ({ page }) => {
  await page.goto('/dashboard/planner/setup')   // (a re-run may already have a plan; setup works either way)

  await expect(page.getByRole('heading', { name: 'About you' })).toBeVisible()
  for (let step = 0; step < 5; step++) await page.getByTestId('wizard-next').click()
  const preview = page.getByTestId('plan-preview')
  await expect(preview).toBeVisible()
  await expect(preview).toContainText('Where your time goes')
  await expect(preview).toContainText('DSA')

  await page.getByTestId('create-plan').click()
  await expect(page).toHaveURL(/\/dashboard\/planner$/)
  const today = page.getByTestId('today-block')
  await expect(today.getByTestId('task-row').first()).toBeVisible()

  const first = today.getByTestId('task-row').first().getByRole('checkbox')
  await first.check()
  await expect(first).toBeChecked()

  await page.getByRole('tab', { name: 'Roadmap' }).click()
  await expect(page.getByText('Week by week')).toBeVisible()
  await page.getByRole('tab', { name: 'Progress' }).click()
  await expect(page.getByText('By subject')).toBeVisible()

  await page.getByRole('link', { name: 'Today' }).click()
  await expect(page.getByTestId('readiness')).toBeVisible()
  await expect(page.getByTestId('setup-checklist')).toContainText('Create your study plan')
})

test('coach answers from the plan and its action button works', async ({ page }) => {
  await page.goto('/dashboard/coach')
  await page.getByTestId('coach-input').fill('I finished my first task today.')
  await page.getByTestId('coach-input').press('Enter')
  const reply = page.getByTestId('coach-reply').last()
  await expect(reply).toContainText('Next up:')
  const done = reply.getByTestId('coach-action').filter({ hasText: 'Mark it done' })
  await done.click()
  await expect(done).toBeDisabled()
  await reply.getByTestId('coach-action').filter({ hasText: 'Open planner' }).click()
  await expect(page).toHaveURL(/\/dashboard\/planner/)
})
