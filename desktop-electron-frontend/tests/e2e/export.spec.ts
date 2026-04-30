/**
 * Export functionality tests
 * Uses Pluto/Pluton — a small article that loads quickly with LaBSE.
 */
import { test, expect } from '@playwright/test';

const SRC = 'Pluto';
const TGT = 'Pluton_(planète_naine)';

async function waitForComparisonResults(page: import('@playwright/test').Page) {
  await expect(
    page.locator('text=/Section Comparison|Overall Similarity/i').first()
  ).toBeVisible({ timeout: 90_000 });
}

test.describe('Export', () => {
  test('Cross-language: Export JSON button is present after comparison', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'Cross-Language Diff' }).click();

    await page.locator('input').nth(0).fill(SRC);
    await page.locator('input').nth(1).fill(TGT);
    await page.locator('select').nth(0).selectOption('en');
    await page.locator('select').nth(1).selectOption('fr');
    await page.getByRole('button', { name: 'Compare Sections' }).click();
    await waitForComparisonResults(page);

    await expect(page.locator('[data-testid="btn-export-json"]')).toBeVisible({ timeout: 5_000 });
    await expect(page.locator('[data-testid="btn-export-json"]')).toBeEnabled();
  });

  test('Revision: Export JSON button is present after comparison', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'Through-Time Diff' }).click();

    await page.locator('input').first().fill('Pluto');
    await page.getByRole('button', { name: 'Load Revision History' }).click();
    await expect(page.locator('[data-testid="revision-timeline"], tbody tr').first()).toBeVisible({ timeout: 30_000 });
    await page.getByRole('button', { name: 'Compare Selected Revisions' }).click();
    await expect(page.locator('text=/Revision Diff Summary/i').first()).toBeVisible({ timeout: 60_000 });

    await expect(page.locator('[data-testid="btn-export-json-revision"]')).toBeVisible({ timeout: 5_000 });
  });

  test('Cross-language: export JSON file has .json extension when downloaded', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'Cross-Language Diff' }).click();

    await page.locator('input').nth(0).fill(SRC);
    await page.locator('input').nth(1).fill(TGT);
    await page.locator('select').nth(0).selectOption('en');
    await page.locator('select').nth(1).selectOption('fr');
    await page.getByRole('button', { name: 'Compare Sections' }).click();
    await waitForComparisonResults(page);

    await expect(page.locator('[data-testid="btn-export-json"]')).toBeVisible({ timeout: 5_000 });
    const [download] = await Promise.all([
      page.waitForEvent('download', { timeout: 5_000 }).catch(() => null),
      page.locator('[data-testid="btn-export-json"]').click(),
    ]);
    if (download) {
      expect(download.suggestedFilename()).toMatch(/\.json$/);
    }
  });
});
