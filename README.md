# Project Symmetry — Cross-Language Wikipedia Article Gap Analysis Tool

![Grey-box Logo](https://www.grey-box.ca/wp-content/uploads/2018/05/logoGREY-BOX.jpg)

![CI](https://github.com/grey-box/symmetry-project/actions/workflows/ci.yml/badge.svg) ![Release](https://github.com/grey-box/symmetry-project/actions/workflows/release.yml/badge.svg) ![Latest Release](https://img.shields.io/github/v/release/grey-box/symmetry-project)

**A semantic analysis tool that compares Wikipedia articles across languages section-by-section and paragraph-by-paragraph to identify content gaps, missing information, and added content. Features word-level diff, revision risk flagging, and language-lag detection.**

Python FastAPI backend in `symmetry-unified-backend` and a desktop Electron frontend in `desktop-electron-frontend`.

---

## Table of Contents

- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Access Points](#access-points)
- [Docker Images](#docker-images)
- [Backend](#backend)
  - [Architecture](#backend-architecture)
  - [API Endpoints](#api-endpoints)
  - [Configuration](#backend-configuration)
  - [Troubleshooting](#backend-troubleshooting)
- [Frontend](#frontend)
  - [Architecture](#frontend-architecture)
  - [Available Scripts](#available-scripts)
  - [Configuration](#frontend-configuration)
  - [Building for Distribution](#building-for-distribution)
  - [Troubleshooting](#frontend-troubleshooting)
- [Testing](#testing)
- [CI/CD](#cicd)
- [Contributing](#contributing)
- [Community](#community)

---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| Frontend | Electron 26 + React 18 + TypeScript + Vite + Tailwind CSS + shadcn/ui |
| Backend | Python + FastAPI + sentence-transformers + spaCy + MarianMT |
| Comparison Engine | LaBSE sentence embeddings (cosine similarity) + Levenshtein distance |

---

## Prerequisites

- Node.js v18+
- Python 3.8–3.11
- npm
- Docker (optional, for containerized deployment)

---

## Quick Start

### Unified Script (Recommended)

```bash
# Start both backend and frontend
./start.sh all

# Start with frontend in development mode
./start.sh all --dev

# Start backend only
./start.sh backend
```

### Docker Compose

```bash
./start.sh docker       # Foreground
./start.sh docker-up    # Detached
./start.sh docker-down  # Stop
```

### Manual — Backend

```bash
cd symmetry-unified-backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Manual — Frontend

```bash
cd desktop-electron-frontend
npm install
npm start
```

---

## Access Points

- **Frontend**: <http://localhost:5173>
- **Backend API**: <http://localhost:8000>
- **API Documentation (Swagger)**: <http://localhost:8000/docs>

---

## Docker Images

Released images are available from GHCR:

```bash
# Pull specific version
docker pull ghcr.io/grey-box/symmetry-project/backend:1.1.0
docker pull ghcr.io/grey-box/symmetry-project/frontend:1.1.0

# Pull latest
docker pull ghcr.io/grey-box/symmetry-project/backend:latest
docker pull ghcr.io/grey-box/symmetry-project/frontend:latest
```

---

## Backend

FastAPI application combining Wikipedia article semantic comparison and structural analysis.

**Source**: `symmetry-unified-backend/`

### Backend Architecture

#### Router Pattern

Endpoints are organized into logical routers under `app/routers/`:

| Router | Purpose |
|--------|---------|
| `wiki_articles.py` | Article fetching operations |
| `structured_wiki.py` | Structured article data endpoints |
| `comparison.py` | Semantic comparison endpoints |
| `structural_analysis.py` | Multi-language structural analysis |

#### Directory Structure

```
symmetry-unified-backend/
├── app/
│   ├── ai/                    # AI comparison logic
│   │   ├── comparison.py
│   │   └── translation.py     # MarianMT translation
│   ├── models/                # Pydantic v2 models
│   │   └── comparison/
│   │       └── registry.py    # Single source of truth for models
│   ├── core/
│   │   └── settings.py        # All configurable thresholds
│   ├── engines/               # Model adapters behind one interface
│   │   ├── base.py            # ModelAdapter, GenerationRequest/Result
│   │   ├── local_slm.py       # Local SLM via an OpenAI-compatible server (Ollama)
│   │   ├── cloud_llm.py       # Hosted LLM via any OpenAI-compatible endpoint
│   │   └── selection.py       # Cheapest-model selector with per-language-pair overrides
│   ├── routers/               # API route handlers
│   ├── services/              # Business logic
│   │   ├── article_parser.py        # Wikipedia HTML → Article model
│   │   ├── section_comparison.py    # Core section/paragraph diff engine
│   │   ├── similarity_scoring.py    # Levenshtein + language family utils
│   │   └── similarity_prototype/    # Phase 1+2+3 custom NLP prototype
│   └── main.py
├── tests/
├── requirements.txt
└── .env.template
```

#### Key Design Decisions

- **`translation.py`** is the translation entrypoint. Import from `app.ai.translation` (singular), not `app.ai.translations` (plural).
- **`app/models/comparison/registry.py`** is the single source of truth for all supported sentence-transformer models.
- **`similarity_scoring.py`** provides Levenshtein disambiguation and language-family threshold selection, used by `section_comparison.py`.
- **spaCy models** must be installed separately: `python -m spacy download en_core_web_sm`.
- **MarianMT models** are downloaded on first use (can be slow on first request).

---

### API Endpoints

#### Root & Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | API information and endpoint overview |
| GET | `/health` | Health check |

#### Wiki Articles

| Method | Path | Description |
|--------|------|-------------|
| GET | `/symmetry/v1/wiki/articles` | Fetch Wikipedia article by URL or title |
| GET | `/symmetry/v1/wiki/structured-article` | Structured article with sections, citations, references |
| GET | `/symmetry/v1/wiki/structured-section` | Specific section with metadata |
| GET | `/symmetry/v1/wiki/citation-analysis` | Analyze citations |
| GET | `/symmetry/v1/wiki/reference-analysis` | Analyze references |

#### Comparison

| Method | Path | Description |
|--------|------|-------------|
| POST | `/symmetry/v1/articles/compare-sections` | **Primary**: Section-by-section comparison with paragraph diffs |
| POST | `/symmetry/v1/articles/compare` | Legacy plain-text semantic comparison |
| POST | `/symmetry/v1/comparison/semantic` | Semantic comparison (POST) |
| GET | `/symmetry/v1/comparison/translate_text` | Translate text (GET) |

#### Models Management

| Method | Path | Description |
|--------|------|-------------|
| GET | `/models/comparison` | List available comparison models |
| GET | `/models/comparison/selected` | Get selected model |
| GET | `/models/comparison/select` | Select comparison model |
| GET | `/models/translation` | List available translation models |
| GET | `/models/translation/import` | Import model from HuggingFace |

#### Structural Analysis

| Method | Path | Description |
|--------|------|-------------|
| GET | `/operations/{source_language}/{title}` | Analyze article across 6 languages with quality scoring |

#### API v2

All v2 endpoints accept the same `ComparisonRequest` and return the published `ComparisonResponse` described in [docs/api-v2/api-v2-response-schema.md](docs/api-v2/api-v2-response-schema.md). Failures return an `ErrorResponse`, and every response carries an `X-Request-ID` header.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/symmetry/v2/compare/llm-vs-wikipedia` | Label each statement of an LLM answer as `supported`, `contradicted` or `not_found` against a Wikipedia article, with confidence and quoted evidence |
| POST | `/symmetry/v2/compare` | Generic comparison (`501` until implemented) |
| POST | `/symmetry/v2/compare/llm-vs-llm` | Compare two or more LLM answers to one prompt and highlight where they disagree |

**LLM vs Wikipedia.** Send one `llm_output` source with the answer as `text` and one `wikipedia` source by `url` (or `title` plus `language`, optionally `revision_id`):

```json
{
  "mode": "llm_vs_wikipedia",
  "sources": [
    {"id": "a", "kind": "llm_output", "text": "The Eiffel Tower was completed in 1889. It is 400 metres tall."},
    {"id": "b", "kind": "wikipedia", "url": "https://en.wikipedia.org/wiki/Eiffel_Tower"}
  ]
}
```

- **Choose the check with `strategy`; the route stays the same.** `null` means the default.

  | `strategy` | What it does | Needs | `score_basis` |
  |---|---|---|---|
  | `factual_consistency` (default) | A language model labels each statement `supported`, `contradicted` or `not_found`, with its confidence and a quoted passage | A model in `llm_models.toml` (see the model selection section below); `engines` lists catalog ids, empty means the cheapest usable model | `model_reported` |
  | `semantic_similarity` | The embedding model (LaBSE by default) finds each statement's closest article sentence: `supported` at or above `options.similarity_threshold` (default `SIMILARITY_THRESHOLD`), `partial` above `options.partial_threshold` if set, otherwise `not_found` | Nothing extra: no API key. `engines` must be empty | `cosine_similarity` |

  `semantic_similarity` measures similar meaning, not truth: "400 metres tall" and "330 metres tall" score high, so it never reports `contradicted`. An unknown strategy, or one the requested engines cannot run, gets `422 unsupported_strategy` with the available ids in `details`.
- **Adding a strategy:** register it in `app/strategies/` and add a `StrategyProfile` in `app/services/v2_strategies.py`. No route or schema change is needed, and the Swagger description lists it automatically.
- `not_found` means the article did not address the statement. **It does not mean the statement is false.**
- If one of several engines fails, the response is `200` with `status: "partial"` and the failure in `errors`. If every engine fails, the article is missing (`404`), or no engine is configured (`503`), an `ErrorResponse` is returned.
- Limits: `factual_consistency` checks only the first 12,000 characters of the article, so a claim backed later in a long article can come back `not_found`. `generate_with`, `pivot_language` and direction `both` are not supported yet. Statements are not aligned to Wikipedia sentences yet (`alignments` is empty).
- Wikipedia text is CC BY-SA 4.0. Show the source's `attribution` wherever its text or evidence is displayed.

**LLM vs LLM.** Send two or more `llm_output` sources, each with an answer as `text` (the `prompt` is optional and echoed back):

```json
{
  "mode": "llm_vs_llm",
  "prompt": "Tell me about the Eiffel Tower.",
  "sources": [
    {"id": "a", "kind": "llm_output", "text": "The Eiffel Tower was completed in 1889. It is about 330 metres tall."},
    {"id": "b", "kind": "llm_output", "text": "The tower was finished in 1889. It was designed by Gustave Eiffel's company."}
  ]
}
```

- Every pair of answers gets one result (3 answers give 3 pairs). Within a pair, every sentence of both answers is labelled against the other answer (`direction: "both"`): `supported`, `partial` (only with `options.partial_threshold`) or `not_found`, with `best_match_similarity` and the matching sentence of the other answer as `counterpart_statement` evidence. `overall_score` is the mean similarity.
- The pair's `alignments` are the disagreements to highlight: `equal` and `modified` pair two sentences, `missing` is only in the first answer, `added` only in the second.
- The strategy is `semantic_similarity` (the default, and the only one offered here so far). It needs no API key and `engines` must be empty. **Similar meaning is not agreement on facts**: "located in Paris" and "located in Berlin" score as similar, and agreement between models is not proof that they are right.
- If one pair cannot be compared, the response is `200` with `status: "partial"`; if none can be, an `ErrorResponse` is returned.
- Not supported yet: generating the answers on the server (`generate_with`), which needs the multi-engine fan-out with per-engine errors; direction `first_to_second`; `pivot_language`.

---

### Backend Configuration

All thresholds are read from environment variables (or `.env` file). Create `symmetry-unified-backend/.env`:

```env
SIMILARITY_THRESHOLD=0.65
LEVENSHTEIN_DISAMBIGUATION_MARGIN=0.08
FAMILY_THRESHOLD_SAME=0.50
FAMILY_THRESHOLD_IE_BRANCHES=0.60
FAMILY_THRESHOLD_UNRELATED=0.70
LOG_LEVEL=INFO
FASTAPI_DEBUG=false
```

See [docs/similarity-threshold-algorithm.md](docs/similarity-threshold-algorithm.md) for the full threshold reference.

#### Local SLM engine

The `local_slm` adapter (`app/engines/local_slm.py`) runs a small language model on your machine through any OpenAI-compatible server (Ollama, LM Studio, llama.cpp). Set the endpoint in `.env`:

```env
LOCAL_SLM_BASE_URL=http://localhost:11434/v1
```

With Ollama, pull a model first (`ollama pull qwen2.5:1.5b`), then build the adapter with `get_adapter("local_slm", "qwen2.5:1.5b")`. Failures raise typed `AdapterError`s: an unreachable server or a rejected request, a timeout or 5xx/429 (retryable), and a bad model name or refused credentials (config errors).

To run the live test against a real server: `LOCAL_SLM_TEST_MODEL=qwen2.5:1.5b python -m pytest tests/test_local_slm_adapter.py -m integration`.

#### Cloud LLM engine and model selection

The `cloud_llm` adapter (`app/engines/cloud_llm.py`) calls a hosted model through any OpenAI-compatible endpoint (OpenAI, Mistral, Qwen, OpenRouter, ...). The provider is configuration, not code:

```python
get_adapter(
    "cloud_llm", "<model name>",
    base_url="https://api.mistral.ai/v1",   # required
    api_key_env="MISTRAL_API_KEY",           # the NAME of the environment variable
    price_per_1m_input=0.0, price_per_1m_output=0.0,  # optional; adds usage["cost_usd"]
)
```

- **API keys are read from environment variables only.** `api_key_env` names the variable. A raw `api_key` argument is refused, and the key never appears in errors, logs or the adapter's config. Put keys in `.env` (git-ignored) or your shell, never in a committed file.
- A missing key raises `AdapterConfigError` naming the variable. 429 and 5xx are retryable; 401/403 and 404 are config errors.
- Models that need `max_completion_tokens` or reject a temperature value are supported with `max_tokens_param="max_completion_tokens"` and `omit_temperature=True`.
- To run the opt-in live tests against a real endpoint (the key comes from `.env` or your shell): `CLOUD_LLM_TEST_MODEL=<model id> CLOUD_LLM_TEST_BASE_URL=<endpoint> CLOUD_LLM_TEST_KEY_ENV=<key variable name> python -m pytest tests/test_cloud_llm_live.py`. Checked against NVIDIA's free hosted API (`https://integrate.api.nvidia.com/v1`, key variable `NVIDIA_API_KEY`).

**Cost-based selection.** `ModelSelector` (`app/engines/selection.py`) calls the cheapest model by default (input price plus output price per 1M tokens) and uses a higher-tier model only for the language pairs you list as overrides. Copy `symmetry-unified-backend/llm_models.example.toml` to `llm_models.toml`, fill in the model names and the prices from each provider's pricing page, then:

```python
selector = load_selector()                       # reads llm_models.toml (or LLM_MODELS_PATH)
result = await selector.generate(request, "en", "sw")                  # cheapest, or the override
result = await selector.generate(request, "en", "sw", fallback=True)   # on failure, try the next model
```

- A language pair with an override (`"en->sw" = ["strong-model"]`) uses only the models listed for it. Every other pair uses the cheapest model. Models whose key is not set are skipped.
- Fallback is off by default, because moving to a pricier model silently raises cost. With `fallback=True` any failure (bad key, unknown model, unreachable server, timeout, rate limit) moves to the next model. If every model fails, the last error is raised and its message lists the earlier failures.
- `result.model` names the model that answered. Prices are required for every non-local model, so a forgotten price is an error, not a free model.

#### Dependencies

| Category | Packages |
|----------|---------|
| Core | fastapi, uvicorn, pydantic v2, requests |
| Wikipedia | wikipedia-api, wikipedia, beautifulsoup4, lxml |
| AI/ML | sentence-transformers, scikit-learn, spaCy, transformers |

---

### Backend Troubleshooting

| Problem | Solution |
|---------|---------|
| `python3: command not found` | Change `python3` to `python` in `start.sh` |
| Permission denied on `start.sh` | Run `chmod +x start.sh` |
| Virtual environment issues | `deactivate && rm -rf venv/ && ./start.sh` |
| Model loading issues | Models auto-download on first use and are cached locally |
| Python version error | Ensure Python 3.8+ is installed: `python3 --version` |

---

## Frontend

Cross-platform desktop application built with Electron, React, and TypeScript.

**Source**: `desktop-electron-frontend/`

### Frontend Architecture

The application follows Electron's multi-process architecture.

#### Main Process (`src/main.ts`)

- Application lifecycle and window management
- Backend process management
- IPC (Inter-Process Communication) handlers
- File system access

#### Preload Script (`src/preload.ts`)

- Exposes safe APIs to renderer via `contextBridge`
- Provides bridge for IPC communication
- Manages config access

#### Renderer Process (React)

- Entry: `src/index.tsx` → `src/App.tsx`
- UI rendering and user interaction
- API communication via services
- State management via React Context (`AppContext.tsx`)
- Routing via React Router (HashRouter, required for Electron)

#### Directory Structure

```
desktop-electron-frontend/
├── src/
│   ├── main.ts                    # Electron main process
│   ├── preload.ts                 # Preload script
│   ├── index.tsx                  # Renderer entry point
│   ├── App.tsx                    # Root React component
│   ├── components/
│   │   ├── ui/                    # shadcn/ui components
│   │   ├── ComparisonSection.tsx  # Legacy plain-text comparison
│   │   ├── Layout.tsx
│   │   ├── Navbar.tsx
│   │   ├── PageHeader.tsx
│   │   ├── SectionComparisonView.tsx    # Paragraph-level diff visualization
│   │   ├── StructuredArticleViewer.tsx  # Main article viewer + comparison trigger
│   │   └── TranslationSection.tsx       # Legacy translation workflow
│   ├── constants/
│   │   ├── AppConstants.ts        # Config loader
│   │   └── ROUTES.ts              # Route definitions
│   ├── context/
│   │   └── AppContext.tsx         # Global state management
│   ├── models/
│   │   ├── apis/                  # API request/response types
│   │   ├── enums/                 # Enum definitions
│   │   └── structured-wiki.ts     # TypeScript interfaces matching backend Pydantic models
│   ├── pages/
│   │   ├── Home.tsx               # Tab-based layout (primary tab first)
│   │   └── Settings.tsx
│   └── services/
│       ├── axios.ts               # Axios instance with IPC config
│       ├── compareArticles.ts     # Legacy comparison API calls
│       ├── fetchArticle.ts        # Article fetching API
│       ├── structuredWikiService.ts  # Primary API service (uses raw fetch())
│       └── translateArticle.ts    # Translation API calls
├── forge.config.js                # Electron Forge configuration
├── package.json
├── tailwind.config.js
└── tsconfig.json
```

#### Key Design Decisions

- **Tab order**: Structured Article (primary) → Translation (Legacy) → AI Comparison (Legacy)
- **API base URL**: `structuredWikiService.ts` hardcodes `API_BASE_URL = 'http://127.0.0.1:8000'`. Legacy services use Axios via `getAxiosInstance()` with IPC config.
- **`structuredWikiService`** uses raw `fetch()` while legacy services use Axios — do not mix the two patterns.
- **TypeScript models** in `src/models/structured-wiki.ts` mirror backend Pydantic models using `snake_case` field names.

#### Conventions

- 2-space indentation
- `PascalCase` for components and types
- `camelCase` for functions, variables, services
- Interfaces match backend Pydantic models (`snake_case` field names)

---

### Available Scripts

```bash
npm start               # Start development server (Electron + React dev server)
npm run build           # Production build
npm run build:web       # Build web bundle only (Vite renderer)
npm run package         # Package application for distribution
npm run make            # Create platform-specific installers
npm run publish         # Publish release to GitHub
npm test                # Run tests
```

---

### Frontend Configuration

The frontend reads settings from `config.json` (loaded via Electron IPC from `AppConstants.ts`). Defaults are in `config.default.json` at the project root:

```json
{
  "BACKEND_BASE_URL": "http://127.0.0.1:8000",
  "BACKEND_PORT": 8000,
  "FRONTEND_PORT": 5173,
  "OLLAMA_BASE_URL": "http://localhost:11434",
  "DEFAULT_TIMEOUT": 30000,
  "SIMILARITY_THRESHOLD": 0.65,
  "COMPARISON_MODELS": [
    { "value": "sentence-transformers/LaBSE", "label": "LaBSE (multilingual embeddings)" },
    { "value": "similarity_prototype", "label": "Similarity Prototype (Phase 1/2/3 — English only, auto-translates)" }
  ]
}
```

---

### Building for Distribution

```bash
npm run package    # Unpacked application in out/
npm run make       # Platform-specific installers in out/make/:
                   #   Windows: .exe (via Squirrel)
                   #   macOS: .dmg or .zip
                   #   Linux: .deb and .rpm
npm run publish    # Publish to GitHub (requires token + forge.config.js)
```

---

### Frontend Troubleshooting

| Problem | Solution |
|---------|---------|
| Backend not starting | Check Python 3 install, verify backend path in `src/main.ts`, check DevTools console (Cmd+Opt+I) |
| `window.electronAPI` undefined | Ensure preload script is loaded in `main.ts` and `contextBridge` is configured |
| Vite build fails | `rm -rf node_modules && npm install`, then `npx tsc --noEmit` to check TypeScript errors |
| Hot reload not working | Restart `npm start` |
| Port 8000 in use | `lsof -ti:8000 \| xargs kill -9` or change port in `config.json` |

---

## Testing

### Backend

```bash
cd symmetry-unified-backend
source venv/bin/activate
python -m pytest -m "not slow and not external" --tb=short    # CI-equivalent
python -m pytest -v --tb=short                                 # Verbose
python -m pytest --cov=app                                     # With coverage
```

Key test files:

| File | What it tests |
|------|--------------|
| `test_comparison.py` | Article comparison endpoints |
| `test_similarity_scoring.py` | Levenshtein + language family logic |
| `test_structured_wiki.py` | Article parsing |
| `test_semantic_comparison.py` | LaBSE embedding comparison |
| `test_revision_flagging.py` | Revision flagging logic |
| `test_synonym_matcher.py` | Phase 2 WordNet matching |
| `test_structural_analysis.py` | Structural analysis router |

### Frontend

```bash
cd desktop-electron-frontend
npm test
```

---

## CI/CD

GitHub Actions workflows:

| Workflow | Trigger | What it does |
|----------|---------|-------------|
| **CI** (`.github/workflows/ci.yml`) | Push/PR to `main` or `develop` | Runs backend tests, builds frontend web bundle, builds & smoke-tests frontend Docker image, runs docker-compose integration |
| **Release** (`.github/workflows/release.yml`) | Push to `main` | Runs full CI → bumps version (semver) → creates git tag → creates GitHub release → publishes Docker images to GHCR |

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Install dependencies (see [Quick Start](#quick-start))
4. Make changes and run tests
5. Use [Conventional Commits](https://www.conventionalcommits.org/) for commit messages
6. Submit a pull request to `develop`
7. After review, PRs are merged to `develop`, then promoted to `main` for release

See [CONTRIBUTING.md](CONTRIBUTING.md) for more details.

---

## Community

- **Project Website**: <https://www.grey-box.ca/project-symmetry/>
- **GitHub Issues**: <https://github.com/grey-box/Project-Symmetry-AI/issues>
- **Design Resources (Figma)**: <https://www.figma.com/design/yN89gDcV3rdbje70X9RJGL/Project-Symmetry>

---

**Last Updated**: May 2026 | **Version**: 2.0.0 | **Maintainers**: [grey-box](https://github.com/grey-box)
