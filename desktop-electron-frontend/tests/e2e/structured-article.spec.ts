/**
 * Structured Article Viewer tests
 * Target: Climate_change Wikipedia EN page via Vite dev server (http://localhost:5173)
 */
import { test, expect } from '@playwright/test';

const ARTICLE_TITLE = 'Climate_change';

/** Navigate to a tab by its label text */
async function goToTab(page: import('@playwright/test').Page, label: string) {
  await page.goto('/');
  await page.getByRole('button', { name: label }).click();
}

test.describe('Structured Article Viewer', () => {
  test.beforeEach(async ({ page }) => {
    // Structured Article is the default tab — just navigate to /
    await page.goto('/');
  });

  test('loads Climate_change article and displays sections', async ({ page }) => {
    await page.getByPlaceholder('Enter Wikipedia article title or URL').fill(ARTICLE_TITLE);
    await page.getByRole('button', { name: 'Load Article' }).click();
    // Wait for the article content to appear
    await expect(page.locator('.structured-article-viewer h2, .structured-article-viewer h3').first()).toBeVisible({ timeout: 30_000 });
  });

  test('article has more than 5 section cards', async ({ page }) => {
    await page.getByPlaceholder('Enter Wikipedia article title or URL').fill(ARTICLE_TITLE);
    await page.getByRole('button', { name: 'Load Article' }).click();
    await page.waitForTimeout(20_000);
    // Section content cards
    const sections = page.locator('[class*="border"][class*="rounded"]');
    expect(await sections.count()).toBeGreaterThan(5);
  });

  test('shows article statistics after loading', async ({ page }) => {
    await page.getByPlaceholder('Enter Wikipedia article title or URL').fill(ARTICLE_TITLE);
    await page.getByRole('button', { name: 'Load Article' }).click();
    await page.waitForTimeout(20_000);
    // Look for any numeric stats
    const statsText = await page.locator('text=/sections|citations|references|words/i').first().isVisible().catch(() => false);
    expect(statsText).toBeTruthy();
  });

  test('handles invalid URL gracefully', async ({ page }) => {
    await page.getByPlaceholder('Enter Wikipedia article title or URL').fill('https://not-wikipedia.com/wiki/Something');
    await page.getByRole('button', { name: 'Load Article' }).click();
    await page.waitForTimeout(8_000);
    const errorVisible =
      (await page.locator('[class*="red"], [class*="error"]').first().isVisible().catch(() => false)) ||
      (await page.locator('text=/error|invalid|not found/i').first().isVisible().catch(() => false));
    expect(errorVisible).toBeTruthy();
  });
});
