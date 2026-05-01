#!/usr/bin/env node
/**
 * create-demo-video.mjs
 *
 * Captures a narrated demo video of Project Symmetry.
 *
 * What it does
 * ────────────
 * 1. Launches a headless Chromium browser via Playwright and navigates through
 *    each major feature of the app (Structured Article, Cross-Language Diff,
 *    Through-Time Diff, Paragraph Diff).
 * 2. Takes labeled screenshots at each key moment.
 * 3. Uses macOS `say` (built-in TTS) to synthesise a narration track for each
 *    slide, saved as a WAV file.
 * 4. Uses `ffmpeg` to combine each screenshot+audio pair into a video clip,
 *    then concatenates all clips into a final MP4.
 *
 * Prerequisites
 * ─────────────
 * - Backend running at http://127.0.0.1:8000
 * - Frontend dev server running at http://localhost:5174
 * - ffmpeg installed  (brew install ffmpeg)
 * - macOS (for the built-in `say` command)
 * - Playwright browsers installed  (npx playwright install chromium)
 *
 * Usage
 * ─────
 *   node scripts/create-demo-video.mjs [--out output.mp4] [--voice Samantha]
 *
 * Flags
 *   --out   <file>   Final video path  (default: artifacts/demo.mp4)
 *   --voice <name>   macOS voice name  (default: Samantha)
 *   --rate  <wpm>    Speech rate in words-per-minute (default: 170)
 *   --width <px>     Viewport width    (default: 1280)
 *   --height <px>    Viewport height   (default: 800)
 */

import { chromium } from 'playwright';
import { execSync, spawnSync } from 'child_process';
import { mkdirSync, writeFileSync, existsSync, rmSync } from 'fs';
import { join, resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

// ─── CLI args ─────────────────────────────────────────────────────────────────
const argv = process.argv.slice(2);
const flag = (name, fallback) => {
    const idx = argv.indexOf(name);
    return idx !== -1 ? argv[idx + 1] : fallback;
};

const __dir = dirname(fileURLToPath(import.meta.url));
const ARTIFACTS = resolve(__dir, '..', 'artifacts');
const OUT_VIDEO = resolve(flag('--out', join(ARTIFACTS, 'demo.mp4')));
const VOICE = flag('--voice', 'Samantha');
const RATE = parseInt(flag('--rate', '170'), 10);
const WIDTH = parseInt(flag('--width', '1280'), 10);
const HEIGHT = parseInt(flag('--height', '800'), 10);
const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost:5174';

mkdirSync(ARTIFACTS, { recursive: true });

// ─── Slide definitions ────────────────────────────────────────────────────────
// Each slide: { id, narration, setup(page) }
//   setup(page) must leave the browser in the desired visual state and return
//   a screenshot path (string) or null to skip the slide.

const SLIDES = [
    // ── 0: Title card (no browser needed) ─────────────────────────────────────
    {
        id: 'title',
        narration: 'Welcome to Project Symmetry — a cross-language Wikipedia article analysis tool. In this demo we will walk through each major feature.',
        setup: null, // synthetic slide
    },

    // ── 1: Structured Article ──────────────────────────────────────────────────
    {
        id: 'structured-home',
        narration: 'The Structured Article Viewer displays a parsed outline of any Wikipedia page. Let\'s load the article on Climate Change.',
        setup: async (page) => {
            await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });
            await page.getByPlaceholder('Enter Wikipedia article title or URL').waitFor({ timeout: 40_000 });
        },
    },
    {
        id: 'structured-loading',
        narration: 'We enter the article title and press Load Article. The backend fetches and parses the Wikipedia page in real time.',
        setup: async (page) => {
            await page.getByPlaceholder('Enter Wikipedia article title or URL').fill('Climate_change');
            await page.getByRole('button', { name: 'Load Article' }).click();
        },
    },
    {
        id: 'structured-result',
        narration: 'The article is displayed as a hierarchy of sections with citation counts and a character breakdown. This gives researchers an instant structural overview.',
        setup: async (page) => {
            await page
                .locator('.structured-article-viewer h2, .structured-article-viewer h3')
                .first()
                .waitFor({ timeout: 40_000 })
                .catch(() => { });
        },
    },

    // ── 2: Cross-Language Diff ─────────────────────────────────────────────────
    {
        id: 'cross-lang-tab',
        narration: 'Moving to the Cross-Language Diff tab. Here we can compare two Wikipedia articles written in different languages.',
        setup: async (page) => {
            await page.getByRole('button', { name: 'Cross-Language Diff' }).click();
            await page.waitForTimeout(500);
        },
    },
    {
        id: 'cross-lang-filling',
        narration: 'We compare the English Pluto article with its French counterpart, Pluton. We select the source and target languages and press Compare Sections.',
        setup: async (page) => {
            await page.locator('input').nth(0).fill('Pluto');
            await page.locator('input').nth(1).fill('Pluton_(planète_naine)');
            await page.locator('select').nth(0).selectOption('en');
            await page.locator('select').nth(1).selectOption('fr');
            await page.getByRole('button', { name: 'Compare Sections' }).click();
        },
    },
    {
        id: 'cross-lang-result',
        narration: 'The heatmap shows per-section semantic similarity scores. Green means high similarity, red means the section differs significantly between languages.',
        setup: async (page) => {
            await page
                .locator('text=/Section Comparison|Overall Similarity/i')
                .first()
                .waitFor({ timeout: 90_000 })
                .catch(() => { });
        },
    },

    // ── 3: Through-Time Diff ──────────────────────────────────────────────────
    {
        id: 'through-time-tab',
        narration: 'The Through-Time Comparison feature lets us track how a Wikipedia article has changed across its revision history.',
        setup: async (page) => {
            await page.getByRole('button', { name: 'Through-Time Diff' }).click();
            await page.waitForTimeout(500);
        },
    },
    {
        id: 'through-time-loading',
        narration: 'We load the twenty most recent revisions of Pluto. The revision timeline appears at the top with each revision shown as a dot.',
        setup: async (page) => {
            await page.locator('input').first().fill('Pluto');
            await page.getByRole('button', { name: 'Load Revision History' }).click();
            await page
                .locator('[data-testid="revision-timeline"], tbody tr')
                .first()
                .waitFor({ timeout: 40_000 })
                .catch(() => { });
        },
    },
    {
        id: 'through-time-compare',
        narration: 'We compare the oldest and newest revisions. The summary card shows added, removed, and modified sections along with an overall similarity score.',
        setup: async (page) => {
            await page.getByRole('button', { name: 'Compare Selected Revisions' }).click();
            await page
                .locator('text=/Revision Diff Summary|Overall Similarity/i')
                .first()
                .waitFor({ timeout: 90_000 })
                .catch(() => { });
        },
    },

    // ── 4: Paragraph Diff (word-level) ────────────────────────────────────────
    {
        id: 'paragraph-diff-tab',
        narration: 'Back on the Cross-Language tab, the Detailed Analysis button triggers a word-level semantic diff that shows exactly which tokens changed between languages.',
        setup: async (page) => {
            await page.getByRole('button', { name: 'Cross-Language Diff' }).click();
            await page.locator('input').nth(0).fill('Pluto');
            await page.locator('input').nth(1).fill('Pluton_(planète_naine)');
            await page.locator('select').nth(0).selectOption('en');
            await page.locator('select').nth(1).selectOption('fr');
            await page.getByRole('button', { name: 'Compare Sections' }).click();
            await page
                .locator('text=/Section Comparison|Overall Similarity/i')
                .first()
                .waitFor({ timeout: 90_000 })
                .catch(() => { });
            await page.locator('[data-testid="btn-detailed-analysis"]').click().catch(() => { });
        },
    },
    {
        id: 'paragraph-diff-result',
        narration: 'Blue tokens are insertions, red are deletions, and orange marks replaced tokens. A similarity bar accompanies each aligned sentence pair.',
        setup: async (page) => {
            await page
                .locator('[data-testid="btn-toggle-side-by-side"]')
                .waitFor({ timeout: 90_000 })
                .catch(() => { });
        },
    },

    // ── 5: Closing ─────────────────────────────────────────────────────────────
    {
        id: 'closing',
        narration: 'Project Symmetry helps researchers quickly identify structural and semantic gaps between Wikipedia articles across languages and across time. Thank you for watching.',
        setup: null, // synthetic slide
    },
];

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Check that a required binary exists on PATH */
function requireBin(name) {
    const result = spawnSync('which', [name]);
    if (result.status !== 0) {
        console.error(`ERROR: '${name}' not found. Install it and try again.`);
        process.exit(1);
    }
}

/** Synthesise narration text to a WAV file using macOS `say` */
function synthesise(text, wavPath) {
    const aiffPath = wavPath.replace(/\.wav$/, '.aiff');
    execSync(`say -v "${VOICE}" -r ${RATE} -o "${aiffPath}" "${text.replace(/"/g, '\\"')}"`, { stdio: 'inherit' });
    // Convert AIFF → WAV so ffmpeg can mix without extra deps
    execSync(`ffmpeg -y -i "${aiffPath}" "${wavPath}" -loglevel error`);
}

// macOS system font guaranteed to exist as a plain TTF
const SYSTEM_FONT = '/System/Library/Fonts/Geneva.ttf';

/**
 * Build a static title-card PNG with white background and centred text.
 * Uses ImageMagick v7 (`magick`) when available, otherwise falls back to an
 * ffmpeg `drawtext` filter with the same system font.
 */
function makeTitleCard(text, pngPath, w, h) {
    const hasMagick = spawnSync('which', ['magick']).status === 0;
    // Escape text for shell: single-quote each line
    const safeText = text.replace(/"/g, '\\"');
    if (hasMagick) {
        execSync(
            `magick -size ${w}x${h} xc:white ` +
            `-gravity Center -pointsize 52 -font "${SYSTEM_FONT}" ` +
            `-fill "#1e293b" -annotate 0 "${safeText}" ` +
            `"${pngPath}"`,
            { stdio: 'inherit' },
        );
    } else {
        // Fallback: ffmpeg drawtext (no ImageMagick needed)
        // Replace newlines with spaces for the single drawtext call
        const oneLine = text.replace(/\n/g, '  ');
        execSync(
            `ffmpeg -y -f lavfi -i color=c=white:s=${w}x${h}:d=1 ` +
            `-vf "drawtext=fontfile='${SYSTEM_FONT}':text='${oneLine.replace(/'/g, "\\'")}':` +
            `fontsize=52:fontcolor=#1e293b:x=(w-text_w)/2:y=(h-text_h)/2" ` +
            `-vframes 1 "${pngPath}" -loglevel error`,
        );
    }
}

/** Create a video clip from a screenshot PNG + WAV audio */
function makeClip(pngPath, wavPath, clipPath, w, h) {
    // Get audio duration via ffprobe
    const probe = execSync(
        `ffprobe -v error -show_entries format=duration -of csv=p=0 "${wavPath}"`,
    )
        .toString()
        .trim();
    const duration = Math.max(parseFloat(probe) || 3, 3);

    execSync(
        `ffmpeg -y ` +
        `-loop 1 -framerate 1 -i "${pngPath}" ` +
        `-i "${wavPath}" ` +
        `-c:v libx264 -tune stillimage -preset fast ` +
        `-vf "scale=${w}:${h}:force_original_aspect_ratio=decrease,` +
        `pad=${w}:${h}:(ow-iw)/2:(oh-ih)/2:white" ` +
        `-c:a aac -b:a 128k ` +
        `-t ${duration} -pix_fmt yuv420p ` +
        `"${clipPath}" -loglevel error`,
    );
}

/** Concatenate clip files into a single MP4 using the concat demuxer */
function concatenateClips(clipPaths, outputPath) {
    const listPath = join(ARTIFACTS, '_concat_list.txt');
    const content = clipPaths.map((p) => `file '${p}'`).join('\n');
    writeFileSync(listPath, content);
    execSync(
        `ffmpeg -y -f concat -safe 0 -i "${listPath}" -c copy "${outputPath}" -loglevel error`,
    );
}

// ─── Main ─────────────────────────────────────────────────────────────────────

async function main() {
    requireBin('ffmpeg');
    requireBin('say');

    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({
        viewport: { width: WIDTH, height: HEIGHT },
        deviceScaleFactor: 1,
    });
    const page = await context.newPage();

    const clipPaths = [];

    for (const [i, slide] of SLIDES.entries()) {
        const prefix = join(ARTIFACTS, `slide-${String(i).padStart(2, '0')}-${slide.id}`);
        const pngPath = `${prefix}.png`;
        const wavPath = `${prefix}.wav`;
        const clipPath = `${prefix}.mp4`;

        console.log(`\n─── Slide ${i + 1}/${SLIDES.length}: ${slide.id} ───`);

        // 1. Capture screenshot
        if (slide.setup === null) {
            // Synthetic title/closing card — generate a PNG
            const label =
                slide.id === 'title'
                    ? 'Project Symmetry\nDemo'
                    : 'Thank you\nProject Symmetry';
            makeTitleCard(label, pngPath, WIDTH, HEIGHT);
        } else {
            await slide.setup(page);
            await page.waitForTimeout(800); // let animations settle
            await page.screenshot({ path: pngPath, fullPage: false });
        }
        console.log(`  Screenshot → ${pngPath}`);

        // 2. Synthesise narration
        synthesise(slide.narration, wavPath);
        console.log(`  Audio      → ${wavPath}`);

        // 3. Make clip
        makeClip(pngPath, wavPath, clipPath, WIDTH, HEIGHT);
        console.log(`  Clip       → ${clipPath}`);

        clipPaths.push(clipPath);
    }

    await browser.close();

    // 4. Concatenate all clips
    console.log(`\nConcatenating ${clipPaths.length} clips → ${OUT_VIDEO}`);
    concatenateClips(clipPaths, OUT_VIDEO);

    console.log(`\n✅  Demo video saved to:\n   ${OUT_VIDEO}\n`);
}

main().catch((err) => {
    console.error(err);
    process.exit(1);
});
