#!/usr/bin/env node
import { chromium } from 'playwright';

const args = new Set(process.argv.slice(2));
const BASE_URL = process.env.E2E_BASE_URL || 'http://127.0.0.1:5173';
const HEADLESS = args.has('--headless');
const SLOW_MO = args.has('--slow') ? 150 : 0;

const results = [];

function record(name, ok, detail = '') {
    results.push({ name, ok, detail });
    const icon = ok ? 'PASS' : 'FAIL';
    console.log(`[${icon}] ${name}${detail ? ` - ${detail}` : ''}`);
}

async function clickTab(page, label) {
    await page.getByRole('button', { name: label, exact: true }).click();
}

async function scenarioStructured(page) {
    const name = 'Structured Article translation scenarios';
    try {
        await clickTab(page, 'Structured Article');

        await page.getByPlaceholder('Enter Wikipedia article title or URL').fill('https://en.wikipedia.org/wiki/A');
        await page.getByRole('button', { name: 'Load Article' }).click();

        await page.locator('h3').filter({ hasText: 'Sections' }).first().waitFor({ timeout: 45000 });

        const targetSelect = page
            .locator('select')
            .filter({ has: page.locator('option[value="fr"]') })
            .first();

        for (const lang of ['fr', 'es', 'de']) {
            await targetSelect.selectOption(lang);
            await page.getByRole('button', { name: 'Translate', exact: true }).click();
            await page.getByText('Translated Article Preview', { exact: true }).waitFor({ timeout: 30000 });
            await page.getByRole('button', { name: 'Clear', exact: true }).nth(0).click();
        }

        record(name, true);
    } catch (error) {
        await page.screenshot({ path: 'artifacts/rpa-structured-failure.png', fullPage: true }).catch(() => { });
        record(name, false, String(error));
    }
}

async function scenarioTranslationToComparison(page) {
    const name = 'Translation Legacy to AI Comparison handoff';
    try {
        await clickTab(page, 'Translation (Legacy)');

        await page.getByPlaceholder('Enter a URL').fill('https://en.wikipedia.org/wiki/A');
        await page.getByRole('button', { name: 'Submit', exact: true }).click();

        await page.getByText('Source Content', { exact: true }).waitFor({ timeout: 45000 });

        await page.locator('button[role="combobox"]').nth(0).click();
        const options = page.locator('[role="option"]');
        await options.first().waitFor({ timeout: 15000 });

        const count = await options.count();
        let selected = false;
        const preferred = ['fr', 'es', 'de', 'it', 'pt'];
        for (const pref of preferred) {
            for (let i = 0; i < count; i += 1) {
                const txt = (await options.nth(i).textContent())?.trim()?.toLowerCase() || '';
                if (txt === pref) {
                    await options.nth(i).click();
                    selected = true;
                    break;
                }
            }
            if (selected) {
                break;
            }
        }

        if (!selected) {
            await page.keyboard.press('Escape');
            throw new Error('No supported target language found in dropdown (expected one of: fr, es, de, it, pt).');
        }

        await page.getByText('Translated Content', { exact: true }).waitFor({ timeout: 60000 });

        await page.getByRole('button', { name: /^Compare$/ }).click();

        await page.getByRole('heading', { name: 'AI Comparison' }).waitFor({ timeout: 10000 });

        record(name, true);
    } catch (error) {
        await page.screenshot({ path: 'artifacts/rpa-translation-failure.png', fullPage: true }).catch(() => { });
        record(name, false, String(error));
    }
}

async function scenarioAiComparison(page) {
    const name = 'AI Comparison submit smoke';
    try {
        await clickTab(page, 'AI Comparison (Legacy)');

        await page.getByPlaceholder('Paste source text here or fetch from URL above...').fill('Canada is a country in North America. It has ten provinces.');
        await page.getByPlaceholder('Paste translated text here...').fill('Le Canada est un pays en Amerique du Nord. Il compte dix provinces.');

        await page.getByRole('button', { name: 'Compare Articles', exact: true }).click();

        await Promise.race([
            page.getByText('Comparison Results', { exact: true }).waitFor({ timeout: 60000 }),
            page.getByText('No significant differences found between the texts.', { exact: true }).waitFor({ timeout: 60000 }),
        ]);

        record(name, true);
    } catch (error) {
        await page.screenshot({ path: 'artifacts/rpa-ai-comparison-failure.png', fullPage: true }).catch(() => { });
        record(name, false, String(error));
    }
}

async function main() {
    const browser = await chromium.launch({ headless: HEADLESS, slowMo: SLOW_MO });
    const context = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
    const page = await context.newPage();

    page.on('dialog', async (dialog) => {
        console.log(`[DIALOG] ${dialog.message()}`);
        await dialog.accept();
    });

    console.log(`Opening ${BASE_URL}`);
    await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });

    await scenarioStructured(page);
    await scenarioTranslationToComparison(page);
    await scenarioAiComparison(page);

    await browser.close();

    const failed = results.filter((r) => !r.ok);
    console.log('\n=== RPA SUMMARY ===');
    for (const r of results) {
        console.log(`${r.ok ? 'PASS' : 'FAIL'} | ${r.name}`);
    }

    if (failed.length > 0) {
        process.exitCode = 1;
    }
}

main().catch((error) => {
    console.error(error);
    process.exit(1);
});
