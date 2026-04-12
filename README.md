<p align="center">
    <img width="200" alt="Grey-box Logo" src="https://www.grey-box.ca/wp-content/uploads/2018/05/logoGREY-BOX.jpg">
</p>

<h1 align="center">Project Symmetry - Cross-Language Wikipedia Article Gap Analysis Tool</h1>

<p align="center">
  <a href="https://github.com/grey-box/symmetry-project/actions/workflows/ci.yml"><img src="https://github.com/grey-box/symmetry-project/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/grey-box/symmetry-project/actions/workflows/release.yml"><img src="https://github.com/grey-box/symmetry-project/actions/workflows/release.yml/badge.svg" alt="Release"></a>
  <a href="https://github.com/grey-box/symmetry-project/releases/latest"><img src="https://img.shields.io/github/v/release/grey-box/symmetry-project" alt="Latest Release"></a>
</p>

<p align="center">
  <img alt="Project-Symmetry: Cross-Language Wikipedia Article Semantic Analysis Tool"
       src="extras/symmetrydemo2.png">
</p>

<p align="center">
  <strong>A semantic analysis tool that compares Wikipedia articles across languages section-by-section and paragraph-by-paragraph to identify content gaps, missing information, and added content.</strong>
</p>

## Quick Start

### Prerequisites
- [Node.js](https://nodejs.org/) (v18+)
- [Python](https://www.python.org/) (3.8-3.11)
- [npm](https://www.npmjs.com/) / [yarn](https://yarnpkg.com/)
- [Docker](https://www.docker.com/) (optional, for containerized deployment)

### Start Everything (Local Development)
```bash
# Start both backend and frontend
./start.sh all

# Start with frontend in development mode
./start.sh all --dev
```

### Using Docker Compose
```bash
./start.sh docker       # Foreground
./start.sh docker-up    # Detached
./start.sh docker-down  # Stop
```

### Manual Installation

#### Backend
```bash
cd symmetry-unified-backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

#### Frontend
```bash
cd desktop-electron-frontend
yarn install
yarn start
```

### Access Points
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation (Swagger)**: http://localhost:8000/docs

## Project Overview

Project Symmetry uses AI to accelerate Wikipedia's translation efforts in less-represented languages (< 1M articles) by analyzing semantic gaps between articles in different languages and providing targeted comparison.

The application helps identify critical information lost or added between language versions of Wikipedia articles.

### Primary Workflow: Structured Article Comparison

The main feature is **section-by-section, paragraph-by-paragraph semantic comparison** of Wikipedia articles across languages:

1. Load a Wikipedia article via the Structured Article viewer
2. Select a target language and click "Compare Sections"
3. View a structured diff showing:
   - **Matched sections** with paragraph-level alignment
   - **Missing sections** (present in source, absent in target)
   - **Added sections** (present in target, absent in source)
   - Similarity scores for each match (semantic + Levenshtein disambiguation)

### Legacy Workflows

The application also includes legacy workflows accessible from labeled tabs:
- **Translation (Legacy)**: Fetch and translate Wikipedia articles using MarianMT models
- **AI Comparison (Legacy)**: Plain-text semantic comparison using sentence embeddings

## Architecture

### Tech Stack
- **Frontend**: Electron 26 + React 18 + TypeScript + Vite + Tailwind CSS + shadcn/ui
- **Backend**: Python + FastAPI + sentence-transformers + spaCy + MarianMT
- **Comparison Engine**: LaBSE sentence embeddings (cosine similarity) + Levenshtein distance for disambiguation

### Project Structure

```
symmetry-project-202512/
├── symmetry-unified-backend/       # FastAPI backend
│   ├── app/
│   │   ├── ai/                     # AI / ML components
│   │   │   ├── model_registry.py   # Central registry of comparison models
│   │   │   ├── semantic_comparison.py  # Sentence-level semantic comparison
│   │   │   ├── translation.py      # MarianMT translation (Helsinki-NLP)
│   │   │   └── translations.py     # Bridge: translate(text, src, tgt) interface
│   │   ├── models/                 # Pydantic v2 models
│   │   │   ├── wiki_structure.py   # Article, Section, Citation, Reference
│   │   │   ├── comparison.py       # CompareRequest/Response (legacy)
│   │   │   ├── section_comparison.py # SectionCompareRequest/Response (new)
│   │   │   ├── structured_response.py
│   │   │   └── ...
│   │   ├── routers/                # API route handlers
│   │   │   ├── comparison.py       # /articles/compare, /articles/compare-sections
│   │   │   ├── structured_wiki.py  # /wiki/structured-article, citations, refs
│   │   │   ├── wiki_articles.py    # /wiki/articles (plain text fetch)
│   │   │   ├── structural_analysis.py
│   │   │   └── models.py           # Model management endpoints
│   │   ├── services/               # Business logic
│   │   │   ├── article_parser.py   # Wikipedia HTML → structured Article
│   │   │   ├── section_comparison.py # Section/paragraph semantic diff engine
│   │   │   ├── similarity_scoring.py # Levenshtein + linguistic scoring
│   │   │   ├── chunking.py
│   │   │   └── wiki_utils.py
│   │   └── main.py
│   ├── tests/
│   └── requirements.txt
├── desktop-electron-frontend/      # Electron + React frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── StructuredArticleViewer.tsx  # Main article viewer + comparison
│   │   │   ├── SectionComparisonView.tsx   # Paragraph-level diff UI
│   │   │   ├── TranslationSection.tsx      # Legacy translation workflow
│   │   │   ├── ComparisonSection.tsx       # Legacy comparison workflow
│   │   │   └── Layout.tsx, PageHeader.tsx, Navbar.tsx
│   │   ├── services/
│   │   │   ├── structuredWikiService.ts    # Structured wiki + comparison API
│   │   │   ├── fetchArticle.ts             # Legacy article fetch
│   │   │   ├── compareArticles.ts          # Legacy comparison
│   │   │   └── translateArticle.ts         # Legacy translation
│   │   ├── models/
│   │   │   ├── structured-wiki.ts          # TypeScript interfaces (articles, diffs)
│   │   │   └── Phase.ts                    # Tab navigation enum
│   │   └── pages/
│   │       └── Home.tsx                    # Tab-based page layout
│   └── package.json
├── CLAUDE.md                       # Agent development instructions
└── README.md
```

## Key API Endpoints

### Section Comparison (Primary)
- `POST /symmetry/v1/articles/compare-sections` - Compare two Wikipedia articles section-by-section with paragraph-level diffs

### Structured Wiki
- `GET /symmetry/v1/wiki/structured-article` - Parse article into sections/citations/references
- `GET /symmetry/v1/wiki/structured-section` - Get specific section with metadata
- `GET /symmetry/v1/wiki/citation-analysis` - Citation statistics
- `GET /symmetry/v1/wiki/reference-analysis` - Reference statistics
- `GET /symmetry/v1/wiki/structured-translated-article` - Translate structured article

### Legacy Comparison
- `POST /symmetry/v1/articles/compare` - Plain-text semantic comparison
- `GET/POST /symmetry/v1/comparison/semantic` - Semantic comparison endpoints
- `GET /symmetry/v1/wiki_translate/source_article` - Cross-language article fetch

### Models Management
- `GET /models/comparison` - List comparison models
- `GET /models/translation` - List translation models

## Comparison Engine

The section comparison uses a two-tier approach:

1. **Semantic similarity (primary)**: LaBSE sentence-transformer embeddings with cosine similarity for cross-language paragraph matching
2. **Levenshtein disambiguation (secondary)**: When two candidate paragraph matches have semantic scores within 0.08 of each other, normalized Levenshtein distance breaks the tie

The engine:
- Fetches both articles as structured data (sections, paragraphs, citations)
- Matches sections using title + content preview embeddings (greedy best-match)
- Within matched sections, aligns paragraphs using the two-tier approach
- Reports unmatched sections/paragraphs as "missing" or "added"

## Testing

```bash
cd symmetry-unified-backend
source venv/bin/activate
pytest              # Run all tests
pytest -v           # Verbose
pytest --cov=app    # With coverage
```

## CI/CD

The project uses GitHub Actions for continuous integration and automated releases.

### Workflows

| Workflow | Trigger | What it does |
|----------|---------|--------------|
| **CI** (`.github/workflows/ci.yml`) | Push/PR to `main` or `develop` | Runs backend tests, builds frontend web bundle, builds & smoke-tests frontend Docker image, runs docker-compose integration |
| **Release** (`.github/workflows/release.yml`) | Push to `main` | Runs full CI → bumps version (semver) → creates git tag → creates GitHub release → publishes Docker images to GHCR |

### CI Pipeline

```
┌─────────────────┐   ┌──────────────────┐
│  backend-test   │   │  frontend-build  │
│  (pytest, py11) │   │  (vite build)    │
└────────┬────────┘   └────────┬─────────┘
         │                     │
         └──────────┬──────────┘
                    │
         ┌──────────▼──────────┐    ┌──────────────────┐
         │  integration-test   │    │  frontend-docker  │
         │  (docker compose)   │    │  (build + smoke)  │
         └─────────────────────┘    └──────────────────┘
```

- **backend-test** — Installs Python 3.11 deps, downloads spaCy model, runs `pytest` (excluding slow/external tests)
- **frontend-build** — Installs Node 18 deps, runs `npm run build:web` (Vite production build, non-Electron)
- **frontend-docker** — Builds Docker image, starts container, verifies HTTP response on port 5173
- **integration-test** — Starts full stack via `docker compose`, waits for backend health check, verifies frontend and API docs are accessible

### Release Pipeline

When a push lands on `main` (typically via PR merge):

1. **All CI checks run and must pass**
2. **Version is determined** from commit messages since the last tag using [Conventional Commits](https://www.conventionalcommits.org/):
   - `fix:` → **patch** bump (e.g., `v1.0.5` → `v1.0.6`)
   - `feat:` → **minor** bump (e.g., `v1.0.5` → `v1.1.0`)
   - `feat!:` or `BREAKING CHANGE:` → **major** bump (e.g., `v1.0.5` → `v2.0.0`)
   - No conventional prefix → defaults to **patch**
3. **Git tag** is created (e.g., `v1.1.0`)
4. **GitHub Release** is published with auto-generated changelog
5. **Docker images** are built and pushed to GitHub Container Registry:
   - `ghcr.io/grey-box/symmetry-project/backend:1.1.0`
   - `ghcr.io/grey-box/symmetry-project/frontend:1.1.0`
   - Also tagged with `latest` and `major.minor`

### Conventional Commits

Use these prefixes in commit messages to control versioning:

```bash
# Patch release (bug fixes)
git commit -m "fix: correct similarity threshold for short paragraphs"

# Minor release (new features)
git commit -m "feat: add support for Japanese article parsing"

# Major release (breaking changes)
git commit -m "feat!: redesign comparison API response format"

# Non-release commits (still valid, default to patch on release)
git commit -m "docs: update API endpoint documentation"
git commit -m "chore: update dependencies"
git commit -m "refactor: extract article fetching into service"
```

### Docker Images

Released images are available from GHCR:

```bash
# Pull specific version
docker pull ghcr.io/grey-box/symmetry-project/backend:1.1.0
docker pull ghcr.io/grey-box/symmetry-project/frontend:1.1.0

# Pull latest
docker pull ghcr.io/grey-box/symmetry-project/backend:latest
docker pull ghcr.io/grey-box/symmetry-project/frontend:latest
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Install dependencies (see Quick Start)
4. Make changes and run tests
5. Use [Conventional Commits](https://www.conventionalcommits.org/) for your commit messages
6. Submit a pull request to `develop`
7. After review, PRs are merged to `develop`, then promoted to `main` for release

### Code Standards

**Python Backend**: PEP 8 (88 char max), type hints, docstrings, snake_case
**TypeScript Frontend**: ESLint + Prettier, 2-space indent, PascalCase components, camelCase utilities

## Community

- **Project Website**: [Project-Symmetry](https://www.grey-box.ca/project-symmetry/)
- **GitHub Issues**: [Report Issues](https://github.com/grey-box/Project-Symmetry-AI/issues)
- **Design Resources**: [Figma UX](https://www.figma.com/design/yN89gDcV3rdbje70X9RJGL/Project-Symmetry?node-id=199-529&t=MbzAcPzTNmWPFh8w-0)

## License

This project is licensed under the appropriate license. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **Grey Box**: Project development and maintenance
- **Wikipedia**: Source content and API access
- **Open Source Community**: Libraries and tools

---

**Last Updated**: March 2026
**Version**: 2.0.0
**Maintainers**: [grey-box](https://github.com/grey-box)
