import { readFileSync } from 'node:fs'
import path from 'node:path'

import { expect, test } from '@playwright/test'

const fixtures = path.join(__dirname, 'fixtures')

test('upload -> parse health -> general review -> JD match', async ({ page }) => {
  await page.goto('/dashboard/resume')
  await expect(page.getByRole('heading', { name: 'Resume Screener' })).toBeVisible()

  // Upload: the dropzone wraps a hidden <input type=file>.
  await page.locator('[data-testid=upload-dropzone] input[type=file]')
    .setInputFiles(path.join(fixtures, 'Asha_Verma_Resume.pdf'))
  await expect(page).toHaveURL(/\/dashboard\/resume\/[\w-]+$/)
  const resumeUrl = page.url()

  // Parse health appears once background processing finishes.
  const health = page.getByTestId('parse-health')
  await expect(health).toBeVisible()
  await expect(health).toContainText('checks passed')
  await page.getByText('Show the text a parser extracts').click()
  await expect(health).toContainText('Built a FastAPI service for invoice reconciliation')

  // General review.
  await page.getByTestId('run-analysis').click()
  await expect(page).toHaveURL(/\/analysis\//)
  await expect(page.getByTestId('overall-score')).toBeVisible()
  const weakBullet = page.getByTestId('bullet-feedback').filter({ hasText: 'Responsible for writing unit tests' })
  await expect(weakBullet).toContainText('Weak opening verb')
  await expect(weakBullet.locator('mark')).toHaveText('[X]')   // placeholder, never an invented number

  // JD match.
  await page.goto(resumeUrl)
  await page.getByRole('button', { name: 'Match a job' }).click()
  await page.getByTestId('jd-input').fill(readFileSync(path.join(fixtures, 'sample_jd.txt'), 'utf-8'))
  await page.getByRole('button', { name: 'Save job description' }).click()
  await expect(page.getByTestId('run-analysis')).toHaveText('Match against this job')
  await page.getByTestId('run-analysis').click()

  await expect(page.getByTestId('tier')).toBeVisible()
  const python = page.getByTestId('requirement').filter({ hasText: 'Strong programming skills in Python' })
  await expect(python).toContainText('Proven')
  await expect(python.locator('blockquote')).toContainText('FastAPI')  // the bullet that proves it
  await expect(page.getByTestId('requirement').filter({ hasText: 'Kafka' })).toContainText('Missing')
  await expect(page.getByTestId('knockouts')).toContainText('Bengaluru')
})
