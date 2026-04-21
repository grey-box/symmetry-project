# Backend — Symmetry Unified Backend

FastAPI application combining Wikipedia article semantic comparison and structural analysis.

**Source**: `symmetry-unified-backend/`

---

## Quick Start

```bash
# From project root (recommended)
./start.sh backend

# Or start both backend and frontend
./start.sh all
```

### Manual Setup

```bash
cd symmetry-unified-backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.template .env
# Edit .env as needed

# Development mode (with hot reload)
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Production mode
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
```

---

## Architecture

### Router Pattern

Endpoints are organized into logical routers under `app/routers/`:

| Router | Purpose |
|--------|---------|
| `wiki_articles.py` | Article fetching operations |
| `structured_wiki.py` | Structured article data endpoints |
| `comparison.py` | Semantic comparison endpoints |
| `structural_analysis.py` | Multi-language structural analysis |

### Directory Structure

```
symmetry-unified-backend/
├── app/
│   ├── ai/                    # AI comparison logic
│   │   ├── semantic_comparison.py
│   │   ├── model_registry.py  # Single source of truth for models
│   │   ├── translation.py     # MarianMT translation
│   │   └── translations.py    # Bridge: translate(text, src, tgt)
│   ├── core/
│   │   └── settings.py        # All configurable thresholds
│   ├── models/                # Pydantic v2 models
│   │   ├── section_comparison.py
│   │   └── wiki_structure.py
│   ├── routers/               # API route handlers
│   ├── services/              # Business logic
│   │   ├── article_parser.py     # Wikipedia HTML → Article model
│   │   ├── section_comparison.py # Core section/paragraph diff engine
│   │   ├── similarity_scoring.py # Levenshtein + language family utils
│   │   └── similarity_prototype/ # Phase 1+2+3 custom NLP prototype
│   └── main.py
├── tests/
├── requirements.txt
└── .env.template
```

---

## API Endpoints

### Root & Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | API information and endpoint overview |
| GET | `/health` | Health check |

### Wiki Articles

| Method | Path | Description |
|--------|------|-------------|
| GET | `/symmetry/v1/wiki/articles` | Fetch Wikipedia article by URL or title |
| GET | `/symmetry/v1/wiki/structured-article` | Structured article with sections, citations, references |
| GET | `/symmetry/v1/wiki/structured-section` | Specific section with metadata |
| GET | `/symmetry/v1/wiki/citation-analysis` | Analyze citations |
| GET | `/symmetry/v1/wiki/reference-analysis` | Analyze references |

### Comparison

| Method | Path | Description |
|--------|------|-------------|
| POST | `/symmetry/v1/articles/compare-sections` | **Primary**: Section-by-section comparison with paragraph diffs |
| POST | `/symmetry/v1/articles/compare` | Legacy plain-text semantic comparison |
| GET | `/symmetry/v1/comparison/semantic` | Semantic comparison (GET) |
| POST | `/symmetry/v1/comparison/semantic` | Semantic comparison (POST) |
| GET | `/symmetry/v1/comparison/translate_text` | Translate text (GET) |
| POST | `/symmetry/v1/comparison/translate_text` | Translate text (POST) |

### Models Management

| Method | Path | Description |
|--------|------|-------------|
| GET | `/models/comparison` | List available comparison models |
| GET | `/models/comparison/selected` | Get selected model |
| GET | `/models/comparison/select` | Select comparison model |
| GET | `/models/translation` | List available translation models |
| GET | `/models/translation/import` | Import model from HuggingFace |

### Structural Analysis

| Method | Path | Description |
|--------|------|-------------|
| GET | `/operations/{source_language}/{title}` | Analyze article across 6 languages with quality scoring |

---

## Configuration

All thresholds are read from environment variables (or `.env` file). See [similarity-threshold-algorithm.md](./similarity-threshold-algorithm.md#similarity-threshold-settings) for the full reference.

Create `symmetry-unified-backend/.env`:

```env
SIMILARITY_THRESHOLD=0.65
LEVENSHTEIN_DISAMBIGUATION_MARGIN=0.08
FAMILY_THRESHOLD_SAME=0.50
FAMILY_THRESHOLD_IE_BRANCHES=0.60
FAMILY_THRESHOLD_UNRELATED=0.70
LOG_LEVEL=INFO
FASTAPI_DEBUG=false
```

---

## Testing

```bash
cd symmetry-unified-backend
source venv/bin/activate
pytest                    # Run all tests
pytest -v --tb=short      # Verbose with short tracebacks
pytest --cov=app          # With coverage
```

Tests are in `tests/`. Key test files:

| File | What it tests |
|------|--------------|
| `test_comparison.py` | Article comparison endpoints |
| `test_similarity_scoring.py` | Levenshtein + language family logic |
| `test_structured_wiki.py` | Article parsing |
| `test_semantic_comparison.py` | LaBSE embedding comparison |
| `test_revision_flagging.py` | Revision flagging logic |
| `test_synonym_matcher.py` | Phase 2 WordNet matching |
| `test_structural_analysis.py` | Structural analysis router |

---

## Key Design Decisions

- **`translations.py`** wraps `translation.py`'s `translate_text()` to provide the `translate(text, src, tgt)` interface expected by `structured_wiki.py`. Import from `app.ai.translations` (plural), not `app.ai.translation` (singular).
- **`model_registry.py`** is the single source of truth for all supported sentence-transformer models.
- **`similarity_scoring.py`** provides Levenshtein disambiguation and language-family threshold selection, used by `section_comparison.py`.
- **spaCy models** must be installed separately: `python -m spacy download en_core_web_sm`.
- **MarianMT models** are downloaded on first use (can be slow on first request).
