/**
 * Error states tests
 * Validates graceful error handling across the app
 */
import { test, expect } from '@playwright/test';

test.describe('Error States', () => {
  test('invalid Wikipedia URL shows an error message', async ({ page }) => {
    await page.goto('/');
    // Structured Article tab is default
    await page.getByPlaceholder('Enter Wikipedia article title or URL').fill('https://not-wikipedia.com/wiki/Foo');
    await page.getByRole('button', { name: 'Load Article' }).click();
    await page.waitForTimeout(8_000);
    const errorVisible =
      (await page.locator('[class*="red"], [class*="error"]').first().isVisible().catch(() => false)) ||
      (await page.locator('text=/error|invalid|not found|failed/i').first().isVisible().catch(() => false));
    expect(errorVisible).toBeTruthy();
  });

  test('nonexistent Wikipedia article shows error', async ({ page }) => {
    await page.goto('/');
    await page.getByPlaceholder('Enter Wikipedia article title or URL').fill('ThisArticleDefinitelyDoesNotExist_XYZ_12345_Garbage');
    await page.getByRole('button', { name: 'Load Article' }).click();
    await page.waitForTimeout(15_000);
    const errorVisible =
      (await page.locator('[class*="red"], [class*="error"]').first().isVisible().catch(() => false)) ||
      (await page.locator('text=/not found|error|failed/i').first().isVisible().catch(() => false));
    expect(errorVisible).toBeTruthy();
  });

  test('cross-language comparison with empty inputs shows validation error or disabled button', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'Cross-Language Diff' }).click();
    // Clear both text inputs
    await page.locator('input').nth(0).fill('');
    await page.locator('input').nth(1).fill('');
    const compareBtn = page.getByRole('button', { name: 'Compare Sections' });
    await expect(compareBtn).toBeDisabled();
  });

  test('app navigates between tabs without crashing', async ({ page }) => {
    await page.goto('/');
    const tabNames = ['Cross-Language Diff', 'Through-Time Diff', 'Structured Article'];
    for (const name of tabNames) {
      await page.getByRole('button', { name }).click();
      await page.waitForTimeout(300);
      const fatalError = await page.locator('text=/something went wrong|fatal error|uncaught/i').first().isVisible().catch(() => false);
      expect(fatalError).toBeFalsy();
    }
  });
});
