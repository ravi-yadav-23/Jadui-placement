import { expect, test } from '@playwright/test'

// Runs against the memory-DB + fake-LLM backend. The fake judge credits a key point only when the
// answer shares its words, so a vague answer always misses points and earns a follow-up.
const VAGUE = 'I am not completely sure about this one, I would need to look it up.'

test('fundamentals interview: answer -> follow-up -> next question -> end -> report', async ({ page }) => {
  page.on('dialog', (dialog) => dialog.accept())   // "End the interview now?"
  await page.goto('/dashboard/interview')
  await expect(page.getByRole('heading', { name: 'Mock interviews' })).toBeVisible()

  await page.getByTestId('track-fundamentals').click()
  await page.getByRole('button', { name: 'Practice mode' }).click()
  await page.locator('input[type=range]').fill('3')
  await page.getByTestId('start-interview').click()

  await expect(page).toHaveURL(/\/dashboard\/interview\/[\w-]+$/)
  await expect(page.getByTestId('progress')).toHaveText('Question 1 of 3')

  // A vague answer misses key points -> the interviewer asks one follow-up.
  await page.getByTestId('answer-box').fill(VAGUE)
  await page.getByTestId('submit-answer').click()
  await expect(page.getByText('Follow-up question')).toBeVisible()
  await expect(page.getByTestId('turn-feedback')).toBeVisible()      // practice mode: feedback right away

  // Answering the follow-up moves on (never a second follow-up).
  await page.getByTestId('answer-box').fill(VAGUE)
  await page.getByTestId('submit-answer').click()
  await expect(page.getByTestId('progress')).toHaveText('Question 2 of 3')

  // End early: the report covers the answered question only.
  await page.getByTestId('finish-interview').click()
  const report = page.getByTestId('interview-report')
  await expect(report).toBeVisible()
  await expect(page.getByTestId('interview-score')).toBeVisible()
  await expect(report).toContainText('A strong answer covers')
  await expect(report).toContainText('Follow-up:')

  await page.getByRole('link', { name: 'All interviews' }).click()
  await expect(page.getByText('CS fundamentals').last()).toBeVisible()
})
