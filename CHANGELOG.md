# Changelog

All notable changes to **Project Symmetry** are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/).

<!-- markdownlint-disable MD013 MD024 MD036 -->

---

## [Unreleased]

**Paragraph-Diff Service with Word-Level Semantic Diff UI — PR #41**

### Added

- **Backend**: new `/symmetry/v1/wiki/paragraph-diff` endpoint (`app/routers/structured_wiki.py`) backed by `ParagraphDiffService` (`app/services/paragraph_diff.py`). Returns section-level aligned sentence pairs with per-token `word_diff` (equal / insert / delete / replace).
- **Backend**: Pydantic models `AlignedSentencePair`, `ParagraphDiffSection`, `ParagraphDiffResponse`, `ParagraphDiffRequest` in `app/models/paragraph_diff.py`.
- **Frontend**: `SemanticWordDiff` component — renders colored token spans (blue inserts, red deletes, orange replaces) with a similarity progress bar per sentence pair.
- **Frontend**: `SideBySideComparisonView` component — synchronized dual-scroll panels for cross-language section comparison with `SemanticWordDiff` per section.
- **Frontend**: `ParagraphDiffResponse`, `ParagraphDiffRequest`, `WordToken`, `AlignedSentencePair`, `ParagraphDiffSection` TypeScript interfaces in `src/models/structured-wiki.ts`.
- **Frontend**: `structuredWikiService.getParagraphDiff()` method in `src/services/structuredWikiService.ts`.
- **Frontend**: "Detailed Analysis (word-level diff)" button in `CrossLanguageComparison` tab that loads the paragraph-diff and activates `SideBySideComparisonView`.
- **Tests (E2E)**: Playwright test suite with 26 tests across `home`, `cross-language`, `through-time`, `paragraph-diff`, `structured-article`, and `error-states` spec files (22 passing, 4 skipped due to Wikipedia rate-limiting).
- **Tests (E2E)**: `test:e2e` and `test:e2e:report` scripts added to `desktop-electron-frontend/package.json`.
- **CI**: Playwright report artifacts excluded from git via `.gitignore` (`test-results/`, `playwright-report/*`).

---

## [v0.9.0] – 2026-04-04

**Fact Extraction Implementation — merge PR #23**

### Added

- Merged complete Fact Extraction feature branch into `develop` (PR #23).

---

## [v0.8.9] – 2026-04-04

### Fixed

- Restored spaCy sentence segmentation lost during a `rebase --ours` conflict resolution.

## [v0.8.8] – 2026-04-04

### Style

- Formatted parameters in `test_compare_semantic_get_invalid_threshold` and `test_wiki_translate_missing_params` for readability.

## [v0.8.7] – 2026-04-04

### Fixed

- Removed duplicate `useState` declarations in `StructuredArticleViewer` introduced by a merge conflict.

## [v0.8.6] – 2026-04-04

### Changed

- Refactored `structured_wiki.py` for improved readability and consistency in imports and function formatting.

## [v0.8.5] – 2026-04-04

### Changed

- Refactored `extract_facts_endpoint`: removed `async` keyword; removed `llama-cpp-python` from `requirements.txt`.

## [v0.8.4] – 2026-04-04

### Performance

- Moved `device = "cuda"` setup and `model.to(device)` to before the chunk loop in `fact_extraction.py`; configured `tokenizer.pad_token` once instead of per-chunk.

## [v0.8.3] – 2026-04-04

### Added

- Implemented spaCy sentence segmentation in fact extraction for improved accuracy.
- Added corresponding unit tests.

## [v0.8.2] – 2026-04-04

### Changed

- Refactored fact extraction module and tests for improved readability and consistency.

## [v0.8.1] – 2026-04-04

### Added

- Cache management for fact extraction models to prevent out-of-memory (OOM) errors.

## [v0.8.0] – 2026-03-31

### Added

- New UI features integrated with the Fact Extraction backend.

---

## [v0.7.2] – 2026-03-31

### Changed

- Edited model options panel so users can paste in a custom model name.

## [v0.7.1] – 2026-03-30

### Fixed

- Second patch to unify similarity threshold configuration
  across all comparison paths (PR #21).

## [v0.7.0] – 2026-03-30

### Fixed

- Unified threshold configuration so the value flows consistently
  from frontend → API → comparison engine (PR #20).

---

## [v0.6.7] – 2026-03-30

### Tests

- Added regression tests for long reference IDs in `wiki_structure`.

## [v0.6.6] – 2026-03-29

### CI

- Implemented GitHub Actions workflows for automated testing (PR #18).

## [v0.6.5] – 2026-03-28

### Fixed

- Fixed loanword suffix list and adjusted similarity family thresholds in `similarity_scoring.py`.

## [v0.6.4] – 2026-03-28

### Changed

- `CompareResponse` now includes raw comparisons; returned when available.

## [v0.6.3] – 2026-03-28

### Changed

- `semantic_comparison.py` uses `DEFAULT_MODEL` constant and safe
  `.get()` lookups for comparison keys.

## [v0.6.2] – 2026-03-28

### Added

- Exposed `model_name` and `similarity_threshold` as explicit API
  attributes (PR #16).

## [v0.6.1] – 2026-03-28

### Changed

- Moved model names out of source code and into `config.json`.

## [v0.6.0] – 2026-03-28

**Semantic Comparison — merge PR #9 (`asmi-semantic-wip`)**

### Added

- Full semantic comparison pipeline merged, including LaBSE-based article comparison.
- Renamed internal `a`/`b` variable names to `original`/`translated` for clarity.
- Refactored `compareArticles` frontend service (removed unnecessary
  try/catch, streamlined Axios retrieval).

---

## [v0.5.14] – 2026-03-28

### Changed

- Refactored `compareArticles`: removed unnecessary try block,
  streamlined Axios instance retrieval.

## [v0.5.13] – 2026-03-28

### Changed

- Renamed `a`/`b` variable names to `original`/`translated`
  throughout comparison pipeline.

## [v0.5.12] – 2026-03-28

### Chore

- Merged `develop` into `asmi-semantic-wip` branch.

## [v0.5.11] – 2026-03-28

### Documentation

- Added Summary of Changes document (PR #17).

## [v0.5.10] – 2026-03-28

### Changed

- Increased `reference_id` max size to 300 in `wiki_structure.py` (PR #15).

## [v0.5.9] – 2026-02-24

### Changed

- Additional chunking updates for semantic comparison pipeline.

## [v0.5.8] – 2026-03-28

### Chore

- Updated start script (cherry-pick duplicate).

## [v0.5.7] – 2026-03-24

### Changed

- `docker-compose.yml`: install spaCy language models on container
  startup (cherry-pick of #11/#13).

## [v0.5.6] – 2026-03-28

### Changed

- Updated `start.sh` with minor fixes.

## [v0.5.5] – 2026-03-24

### Changed

- `docker-compose.yml`: added automatic spaCy model
  installation on startup (PR #11, #13).

## [v0.5.4] – 2026-03-24

### Fixed

- Resolved merge conflict in `compareArticles`.

## [v0.5.3] – 2026-03-02

### Removed

- Deleted stray `tempCodeRunnerFile.py` from test directory.

## [v0.5.2] – 2026-03-02

### Added

- Translation feature added to the structured article view (PR #5).

## [v0.5.1] – 2026-03-02

### Changed

- Updated `semantic_comparison.py` (PR #7).

## [v0.5.0] – 2026-03-03

**Translation update — merge PR #6 (`update-translations`)**

### Added

- Merged translation update branch with improved MarianMT pipeline.

---

## [v0.4.10] – 2026-03-03

### Changed

- Applied suggestion from `@gemini-code-assist` bot.

## [v0.4.9] – 2026-03-03

### Chore

- Merged PR #8 (patch-5 from AruefliASU).

## [v0.4.8] – 2026-02-25

### Changed

- Updated `Dockerfile` for the backend service.

## [v0.4.7] – 2026-02-24

### Changed

- Additional chunking updates for the semantic comparison pipeline.

## [v0.4.6] – 2026-02-23

### Fixed

- Fixed language detection by switching to a proper language-code
  package instead of a hardcoded list.

## [v0.4.5] – 2026-02-23

### Fixed

- Aligned frontend API calls with current backend endpoints.
- Fixed launch issues when running in web (non-Electron) mode.

## [v0.4.4] – 2026-02-23

### Chore

- Merged PR #4 (translation patches from AruefliASU/patch-3).

## [v0.4.3] – 2026-02-19

### Changed

- Updated `translations.py`.

## [v0.4.2] – 2026-02-19

### Changed

- Updated `translation_models.json` with additional model entries.

## [v0.4.1] – 2026-02-17

### Changed

- WIP: initial semantic comparison implementation and chunking
  updates (in-progress at time of tag).

## [v0.4.0] – 2026-02-16

**Comparison API merged — PR #3 (`kkauserr/comparison-api`)**

### Added

- Full comparison API branch merged into `develop`.

---

## [v0.3.13] – 2026-02-16

### Chore

- Merged `develop` into `comparison-api` feature branch.

## [v0.3.12] – 2026-02-16

### Chore

- Merged PR #2 (similarity scoring from AruefliASU/patch-2).

## [v0.3.11] – 2026-02-14

### Added

- Implemented full similarity scoring algorithm
  (`similarity_scoring.py`) with Levenshtein distance, loanword
  detection, and language family heuristics.
- Added corresponding test file.

## [v0.3.10] – 2026-02-13

### Added

- Added `similarity_scoring.py` module skeleton.

## [v0.3.9] – 2026-02-13

### Added

- Added `translation_models.json` configuration file for available MarianMT models.

## [v0.3.8] – 2026-02-13

### Changed

- Updated `translations.py`.

## [v0.3.7] – 2026-02-13

### Changed

- Updated `structured_wiki.py`.

## [v0.3.6] – 2026-02-09

### Tests

- Added translation tests with inline comments.

## [v0.3.5] – 2026-02-09

### Chore

- Merged PR #1 (translation patches from AruefliASU/patch-1).

## [v0.3.4] – 2026-02-06

### Added

- `structured_wiki.py` now produces a full structured translated article.

## [v0.3.3] – 2026-02-06

### Changed

- Updated `translations.py` with improved translation flow.

## [v0.3.2] – 2026-02-03

### Fixed

- Fixed off-by-one citation indexes in parsed Wikipedia articles.

## [v0.3.1] – 2026-01-27

### Changed

- Updated `wiki_structure.py`: increased `max_length` parameter.

## [v0.3.0] – 2026-01-27

**Comparison API — initial feature branch**

### Added

- Initial comparison API implementation with semantic diff (`app/routers/comparison.py`).

---

## [v0.2.4] – 2026-01-01

### Chore

- Updated global `.gitignore`.

## [v0.2.3] – 2025-12-30

### Changed

- `start.sh` now forces a Python 3.13 virtual environment.

## [v0.2.2] – 2025-12-30

### Added

- Similarity threshold control added to the frontend app.

## [v0.2.1] – 2025-12-30

### Documentation

- Updated router documentation for backend endpoints.

## [v0.2.0] – 2025-12-30

**Unified startup system**

### Added

- Unified startup script (`start.sh`) covering both backend and frontend.
- Improved overall project architecture.

---

## [v0.1.2] – 2025-12-30

### Changed

- Updated Python and TypeScript library versions.
- Added separate startup scripts for running without the Electron app.
- Several small bug fixes.

## [v0.1.1] – 2025-12-29

### Documentation

- Updated `README.md` files to reflect the new merged project structure.

## [v0.1.0] – 2025-12-29

**Initial Release**

### Added

- Initial commit merging all sub-projects into a single monorepo.
- FastAPI backend (`symmetry-unified-backend/`) with Wikipedia article parsing, translation, and comparison services.
- Electron + React frontend (`desktop-electron-frontend/`) for article viewing and comparison.
- Docker Compose setup for containerised deployment.

---

## LLM Ingestion Instructions

**Purpose:** help an LLM ingest this changelog to (a) generate release notes, (b) suggest version bump levels, and (c) maintain an internal changelog index.

### Feed guidance

1. Provide the raw text of this file to the LLM (paste or stream as a context message).
2. Ask the LLM to parse sections by heading level 2 (`## [vX.Y.Z] – YYYY-MM-DD`).
3. Request output as a JSON array following this schema:

```jsonc
[
  {
    "version": "v0.9.0",
    "date": "2026-04-04",           // ISO date or null
    "sections": {
      "Added":         ["…"],
      "Changed":       ["…"],
      "Fixed":         ["…"],
      "Removed":       ["…"],
      "Security":      ["…"],
      "Performance":   ["…"],
      "Tests":         ["…"],
      "CI":            ["…"],
      "Style":         ["…"],
      "Documentation": ["…"],
      "Chore":         ["…"]
    },
    "recommended_bump": "patch",    // "major" | "minor" | "patch"
    "release_notes": "One-sentence summary."
  }
]
```

### Bump recommendation rules

| Rule | Bump |
| ------ | ------ |
| Breaking API or data-model changes | `major` |
| New features or new public API | `minor` |
| Bug fixes, docs, tests, refactors, style, chore | `patch` |

### Example LLM prompt

```text
Parse the following CHANGELOG.md and output a JSON array matching the schema in
the "LLM Ingestion Instructions" section. Determine the recommended semantic
version bump for each entry using conservative rules. Summarise release notes in
one sentence per version. If a version has no date, return null. Output only
valid JSON, no commentary.

[PASTE CHANGELOG HERE]
```

### Maintainer workflow

1. Add items under `## [Unreleased]` as work progresses.
2. At release time, rename the `[Unreleased]` heading to `## [vX.Y.Z] – YYYY-MM-DD`.
3. Create and push the matching git tag:

```bash
git tag -a vX.Y.Z -m "vX.Y.Z"
git push origin vX.Y.Z
```

1. Open a fresh `## [Unreleased]` section at the top of the file.
