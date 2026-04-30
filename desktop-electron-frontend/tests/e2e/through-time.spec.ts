/**
 * Through-Time Comparison tests
 * Validates RevisionTimeline, SectionHeatmap, and Export
 * Uses Pluto — a small article with a shorter diff to keep tests fast.
 */
import { test, expect } from '@playwright/test';

const ARTICLE = 'Pluto';

/** Load revision history and wait for the timeline to appear */
async function loadRevisions(page: import('@playwright/test').Page) {
  await page.locator('input').first().fill(ARTICLE);
  await page.getByRole('button', { name: 'Load Revision History' }).click();
  await expect(
    page.locator('[data-testid="revision-timeline"], tbody tr').first()
  ).toBeVisible({ timeout: 30_000 });
}

test.describe('Through-Time Comparison', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'Through-Time Diff' }).click();
  });

  test('loads revisions of Pluto', async ({ page }) => {
    await loadRevisions(page);
  });

  test('RevisionTimeline component renders dots after loading', async ({ page }) => {
    await loadRevisions(page);
    await expect(page.locator('[data-testid="revision-timeline"]')).toBeVisible({ timeout: 5_000 });
    const dots = page.locator('[data-testid^="revision-dot-"]');
    expect(await dots.count()).toBeGreaterThan(1);
  });

  test('comparing two revisions shows section diff results', async ({ page }) => {
    await loadRevisions(page);
    await page.getByRole('button', { name: 'Compare Selected Revisions' }).click();
    await expect(
      page.locator('text=/Revision Diff Summary|Overall Similarity/i').first()
    ).toBeVisible({ timeout: 60_000 });
  });

  test('SectionHeatmap appears when sections were modified', async ({ page }) => {
    await loadRevisions(page);
    await page.getByRole('button', { name: 'Compare Selected Revisions' }).click();
    await expect(
      page.locator('text=/Revision Diff Summary|Overall Similarity/i').first()
    ).toBeVisible({ timeout: 60_000 });
    // Heatmap is conditional on modified sections existing
    const modifiedText = await page.locator('text=/Modified Sections/i').first().isVisible().catch(() => false);
    if (modifiedText) {
      await expect(page.locator('[data-testid="section-heatmap"]')).toBeVisible({ timeout: 5_000 });
    }
  });

  test('Export JSON button is present after comparison', async ({ page }) => {
    await loadRevisions(page);
    await page.getByRole('button', { name: 'Compare Selected Revisions' }).click();
    await expect(
      page.locator('text=/Revision Diff Summary|Overall Similarity/i').first()
    ).toBeVisible({ timeout: 60_000 });
    await expect(page.locator('[data-testid="btn-export-json-revision"]')).toBeVisible({ timeout: 5_000 });
  });
});
