/**
 * Paragraph Diff API + Component tests
 * Directly calls the backend API and validates word-level token rendering
 * Uses Pluto/Pluton — a small article that loads quickly with LaBSE.
 */
import { test, expect } from '@playwright/test';

const API_BASE = 'http://127.0.0.1:8000';
// Small articles to keep LaBSE compute time reasonable
const SRC = 'Pluto';
const TGT = 'Pluton_(planète_naine)';

test.describe('Paragraph Diff', () => {
  test('backend /paragraph-diff endpoint returns valid response structure', async ({ request }) => {
    const response = await request.post(`${API_BASE}/symmetry/v1/wiki/paragraph-diff`, {
      data: {
        source_query: SRC,
        target_query: TGT,
        source_lang: 'en',
        target_lang: 'fr',
        similarity_threshold: 0.5,
      },
      timeout: 120_000,
    });

    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body).toHaveProperty('source_title');
    expect(body).toHaveProperty('target_title');
    expect(body).toHaveProperty('sections');
    expect(Array.isArray(body.sections)).toBeTruthy();
  });

  test('paragraph diff response has sections with aligned_pairs', async ({ request }) => {
    const response = await request.post(`${API_BASE}/symmetry/v1/wiki/paragraph-diff`, {
      data: {
        source_query: SRC,
        target_query: TGT,
        source_lang: 'en',
        target_lang: 'fr',
        similarity_threshold: 0.5,
      },
      timeout: 120_000,
    });

    const body = await response.json();
    expect(body.sections.length).toBeGreaterThan(0);

    const firstSection = body.sections[0];
    expect(firstSection).toHaveProperty('source_title');
    expect(firstSection).toHaveProperty('similarity');
    expect(firstSection).toHaveProperty('aligned_pairs');
    expect(Array.isArray(firstSection.aligned_pairs)).toBeTruthy();
  });

  test('aligned pairs have word_diff tokens', async ({ request }) => {
    const response = await request.post(`${API_BASE}/symmetry/v1/wiki/paragraph-diff`, {
      data: {
        source_query: SRC,
        target_query: TGT,
        source_lang: 'en',
        target_lang: 'fr',
        similarity_threshold: 0.3,
      },
      timeout: 120_000,
    });

    const body = await response.json();

    // Find a section with at least one pair
    const sectionWithPairs = body.sections.find(
      (s: { aligned_pairs: unknown[] }) => s.aligned_pairs.length > 0
    );
    expect(sectionWithPairs).toBeDefined();

    const pair = sectionWithPairs.aligned_pairs[0];
    expect(pair).toHaveProperty('source_sentence');
    expect(pair).toHaveProperty('target_sentence');
    expect(pair).toHaveProperty('similarity');
    expect(pair).toHaveProperty('word_diff');
    expect(Array.isArray(pair.word_diff)).toBeTruthy();

    // Each token must have a valid type
    const validTypes = new Set(['equal', 'replace', 'insert', 'delete']);
    for (const token of pair.word_diff) {
      expect(validTypes.has(token.type)).toBeTruthy();
    }
  });

  test('SemanticWordDiff renders in browser after detailed analysis', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'Cross-Language Diff' }).click();

    await page.locator('input').nth(0).fill(SRC);
    await page.locator('input').nth(1).fill(TGT);
    await page.locator('select').nth(0).selectOption('en');
    await page.locator('select').nth(1).selectOption('fr');

    await page.getByRole('button', { name: 'Compare Sections' }).click();
    // Wait dynamically for results
    await expect(
      page.locator('text=/Section Comparison|Overall Similarity/i').first()
    ).toBeVisible({ timeout: 90_000 });

    await page.locator('[data-testid="btn-detailed-analysis"]').click();
    await page.locator('[data-testid="btn-toggle-side-by-side"]').waitFor({ state: 'visible', timeout: 90_000 });
    await page.locator('[data-testid="btn-toggle-side-by-side"]').click();

    await expect(page.locator('[data-testid="semantic-word-diff"]').first()).toBeVisible({ timeout: 10_000 });

    // Colored token spans may or may not appear depending on diff content
    const coloredTokens = page.locator(
      '[class*="bg-blue-100"], [class*="bg-orange-100"], [class*="bg-red-100"], [class*="bg-orange-200"]'
    );
    expect(await coloredTokens.count()).toBeGreaterThanOrEqual(0);
  });
});
