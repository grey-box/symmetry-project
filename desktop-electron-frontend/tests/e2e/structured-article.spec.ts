/**
 * Structured Article Viewer tests
 * Target: Climate_change Wikipedia EN page via Vite dev server (http://localhost:5174)
 */
import { test, expect } from '@playwright/test';

const ARTICLE_TITLE = 'Climate_change';

test.describe('Structured Article Viewer', () => {
    test.beforeEach(async ({ page }) => {
        // Structured Article is the default tab — just navigate to /
        await page.goto('/');
    });

    test('loads Climate_change article and displays sections', async ({ page }) => {
        await page.getByPlaceholder('Enter Wikipedia article title or URL').fill(ARTICLE_TITLE);
        await page.getByRole('button', { name: 'Load Article' }).click();
        await expect(page.locator('.structured-article-viewer h2, .structured-article-viewer h3').first()).toBeVisible({ timeout: 30_000 });
    });

    test('article has more than 5 section cards', async ({ page }) => {
        await page.getByPlaceholder('Enter Wikipedia article title or URL').fill(ARTICLE_TITLE);
        await page.getByRole('button', { name: 'Load Article' }).click();
        const sections = page.locator('[class*="border"][class*="rounded"]');
        await expect(sections.first()).toBeVisible({ timeout: 30_000 });
        expect(await sections.count()).toBeGreaterThan(5);
    });

    test('shows article statistics after loading', async ({ page }) => {
        await page.getByPlaceholder('Enter Wikipedia article title or URL').fill(ARTICLE_TITLE);
        await page.getByRole('button', { name: 'Load Article' }).click();
        await expect(page.locator('text=/sections|citations|references|words/i').first()).toBeVisible({ timeout: 30_000 });
    });

    test('handles invalid URL gracefully', async ({ page }) => {
        await page.getByPlaceholder('Enter Wikipedia article title or URL').fill('https://not-wikipedia.com/wiki/Something');
        await page.getByRole('button', { name: 'Load Article' }).click();
        const errorAlert = page.locator('[class*="red"], [class*="error"], text=/error|invalid|not found/i').first();
        await expect(errorAlert).toBeVisible({ timeout: 30_000 });
    });
});
