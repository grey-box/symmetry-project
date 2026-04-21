# Agent & Developer Instructions

Instructions for LLM agents and developers working on Project Symmetry.

> **Note**: This file is also maintained at `CLAUDE.md` in the project root for agent tooling compatibility.

---

## Project Overview

Project Symmetry is a cross-language Wikipedia article gap analysis tool:

- **Frontend**: Electron 26 + React 18 + TypeScript + Vite + Tailwind CSS + shadcn/ui (`desktop-electron-frontend/`)
- **Backend**: Python FastAPI + sentence-transformers + spaCy + MarianMT (`symmetry-unified-backend/`)

The primary feature is **section-by-section, paragraph-by-paragraph semantic comparison** of Wikipedia articles across languages.

---

## Quick Commands

### Backend

```bash
cd symmetry-unified-backend
source venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
pytest                    # run tests
pytest -v --tb=short      # verbose with short tracebacks
```

### Frontend

```bash
cd desktop-electron-frontend
yarn install
yarn start                # dev mode
yarn build                # production build
```

---

## Architecture

### Backend Key Paths

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI app with CORS, exception handlers, router registration |
| `app/routers/comparison.py` | Article comparison endpoints (legacy + section-level) |
| `app/routers/structured_wiki.py` | Structured article parsing, citation/reference analysis |
| `app/services/section_comparison.py` | **Core**: Section/paragraph diff engine using semantic + Levenshtein |
| `app/services/article_parser.py` | Wikipedia Action API HTML parser → structured Article model |
| `app/services/similarity_scoring.py` | Levenshtein distance, loanword detection, language families |
| `app/ai/semantic_comparison.py` | Legacy sentence-level comparison using LaBSE |
| `app/ai/model_registry.py` | Single source of truth for supported comparison models |
| `app/ai/translation.py` | MarianMT translation (Helsinki-NLP models) |
| `app/ai/translations.py` | Bridge module: `translate(text, source_lang, target_lang)` |
| `app/models/section_comparison.py` | Pydantic models for section comparison |
| `app/models/wiki_structure.py` | Core Article/Section/Citation/Reference models |
| `app/core/settings.py` | All configurable thresholds (env-based) |

### Frontend Key Paths

| File | Purpose |
|------|---------|
| `src/pages/Home.tsx` | Tab-based layout (Structured Article first, then Legacy tabs) |
| `src/components/StructuredArticleViewer.tsx` | Main article viewer + comparison trigger |
| `src/components/SectionComparisonView.tsx` | Paragraph-level diff visualization |
| `src/components/TranslationSection.tsx` | Legacy translation workflow |
| `src/components/ComparisonSection.tsx` | Legacy plain-text comparison |
| `src/services/structuredWikiService.ts` | API service (structured wiki + section comparison) |
| `src/models/structured-wiki.ts` | TypeScript interfaces matching backend Pydantic models |

### API Base URL

The frontend `structuredWikiService.ts` hardcodes `API_BASE_URL = 'http://127.0.0.1:8000'`. The legacy services use Axios with IPC config from `src/services/axios.ts`.

---

## Key Design Decisions

1. **Tab order**: Structured Article (primary) → Translation (Legacy) → AI Comparison (Legacy)
2. **Comparison engine**: LaBSE embeddings for semantic matching, Levenshtein for disambiguation when top-2 candidates are within 0.08 margin
3. **Model registry**: `app/ai/model_registry.py` is the single source of truth for supported sentence-transformer models
4. **Translation bridge**: `translations.py` wraps `translation.py`'s `translate_text()` to provide the `translate(text, src, tgt)` interface expected by `structured_wiki.py`
5. **Article parsing**: Wikipedia Action API HTML → BeautifulSoup → Section/Citation/Reference models

---

## Common Pitfalls

- `structured_wiki.py` imports `translate` from `app.ai.translations` (plural), **not** `app.ai.translation` (singular)
- The frontend `structuredWikiService` uses raw `fetch()` while legacy services use Axios via `getAxiosInstance()` — do not mix the two
- `similarity_scoring.py` was previously dead code; it's now used by `section_comparison.py` for Levenshtein disambiguation
- spaCy models must be installed separately: `python -m spacy download en_core_web_sm` etc.
- MarianMT models are downloaded on first use (can be slow on first request)

---

## Conventions

### Python

- PEP 8 with 88 char max line length
- Type hints on all function signatures
- Docstrings on public functions
- `snake_case` for functions/variables, `PascalCase` for classes
- Pydantic v2 models with Field descriptions

### TypeScript

- 2-space indentation
- `PascalCase` for components and types
- `camelCase` for functions, variables, services
- Interfaces match backend Pydantic models (`snake_case` field names)

---

## Changelog & Versioning

The project uses **Semantic Versioning** (`vMAJOR.MINOR.PATCH`). All notable changes are recorded in `CHANGELOG.md`.

### Changelog Conventions

- Add items under `## [Unreleased]` while work is in progress
- When releasing: rename `[Unreleased]` → `## [vX.Y.Z] – YYYY-MM-DD`, then create and push the git tag

```bash
git tag -a vX.Y.Z -m "vX.Y.Z"
git push origin vX.Y.Z
```

- Bump rules: **major** = breaking change; **minor** = new feature; **patch** = fix / refactor / docs / chore

### LLM Agent Instructions for Changelog

1. Read `CHANGELOG.md` in full
2. Parse all `## [vX.Y.Z]` sections and apply the bump rules above
3. Output structured JSON before any prose summary
4. Do **not** modify `CHANGELOG.md` directly — propose the diff and let the maintainer confirm

---

## Testing

Backend tests are in `symmetry-unified-backend/tests/`. Run with `pytest`.
No frontend test suite is currently configured.
