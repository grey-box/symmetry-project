# Symmetry Unified Backend

A unified FastAPI application combining Wikipedia article semantic comparison and structural analysis capabilities.

## Overview

This backend consolidates three separate repositories:
- `backend-fastapi/` - AI-based semantic comparison and structured wiki parsing
- `fastapi/` - Core FastAPI application structure
- `wil-symmetry-ccsu-rawkit-2025/` - Structural analysis with router pattern

## Features

### Wikipedia Article Operations
- Fetch articles by URL or title with automatic language detection
- Get available translations for articles
- Parse structured articles with sections, citations, and references
- LRU cache with TTL for performance optimization

### Semantic Comparison
- **LLM-based comparison** (DeepSeek-r1 via Ollama)
  - Two-pass comparison using custom prompts
  - Returns missing_info and extra_info with suggested positions
- **Traditional semantic comparison** (Sentence Transformers)
  - Support for multiple models: LaBSE, XLM-RoBERTa, multi-qa-distilbert-cos-v1, etc.
  - Configurable similarity threshold
  - Cosine similarity-based sentence matching

### Structural Analysis
- Table analysis (count, rows, columns per table)
- Header analysis (H1-H6 counts)
- Infobox analysis (attribute extraction)
- Citation analysis (DOI, ISBN counts, external links)
- Image/media counting
- Multi-language quality scoring across 6 languages (en, es, fr, de, pt, ar)

## Quick Start

The easiest way to get started:

```bash
cd symmetry-unified-backend
./start.sh
```

This will:
1. Create a virtual environment (`venv/`) if it doesn't exist
2. Install all dependencies from `requirements.txt`
3. Start the FastAPI server at http://127.0.0.1:8000

Access interactive API documentation at: http://127.0.0.1:8000/docs

## Installation

### Automatic (Recommended)
Use the provided start script which handles virtual environment setup automatically.

### Manual Setup

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.template .env
# Edit .env as needed (LOG_LEVEL, FASTAPI_DEBUG)
```

## Running the Application

### Development Mode (with hot reload)
```bash
source venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Production Mode
```bash
source venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
```

## Architecture

### Router Pattern
API endpoints organized into logical routers:
- `wiki_articles.py` - Article fetching operations
- `structured_wiki.py` - Structured article data endpoints
- `comparison.py` - Semantic comparison endpoints
- `structural_analysis.py` - Multi-language structural analysis

### Directory Structure
```
symmetry-unified-backend/
├── app/
│   ├── ai/                    # AI comparison logic
│   │   ├── llm_comparison.py
│   │   ├── semantic_comparison.py
│   │   └── translations.py
│   ├── models/                # Pydantic v2 models
│   │   └── __init__.py
│   ├── prompts/               # LLM prompts
│   │   ├── first_pass.txt
│   │   └── second_pass.txt
│   ├── routers/               # API route handlers
│   │   ├── wiki_articles.py
│   │   ├── structured_wiki.py
│   │   ├── comparison.py
│   │   └── structural_analysis.py
│   ├── services/               # Business logic
│   │   ├── article_parser.py
│   │   ├── cache.py
│   │   ├── wiki_utils.py
│   │   ├── table_analysis.py
│   │   ├── header_analysis.py
│   │   ├── infobox_analysis.py
│   │   ├── citation_analysis.py
│   │   └── image_analysis.py
│   └── main.py
├── venv/                     # Virtual environment (auto-generated)
├── requirements.txt
├── .env.template
├── .env
├── start.sh
└── README.md
```

## API Endpoints

### Root & Health
- `GET /` - API information and endpoint overview
- `GET /health` - Health check

### Wiki Articles
- `GET /symmetry/v1/wiki/articles?query={url|title}&lang={code}` - Fetch Wikipedia article
- `GET /symmetry/v1/wiki/structured-article?query={url|title}&lang={code}` - Get structured article with sections, citations, references
- `GET /symmetry/v1/wiki/structured-section?query={url|title}&section={name}` - Get specific section with metadata
- `GET /symmetry/v1/wiki/citation-analysis?query={url|title}` - Analyze citations
- `GET /symmetry/v1/wiki/reference-analysis?query={url|title}` - Analyze references
- `GET /wiki_translate/source_article?url={url}&title={title}&language={code}` - Get translated article

### Comparison
- `POST /symmetry/v1/articles/compare` - Compare two articles (traditional semantic)
- `GET /symmetry/v1/comparison/llm?text_a={text}&text_b={text}` - LLM comparison (GET)
- `POST /symmetry/v1/comparison/llm` - LLM comparison (POST)
- `GET /symmetry/v1/comparison/semantic?text_a={text}&text_b={text}&threshold={float}&model={name}` - Semantic comparison (GET)
- `POST /symmetry/v1/comparison/semantic` - Semantic comparison (POST)

### Structural Analysis
- `GET /operations/{source_language}/{title}` - Analyze article across 6 languages with quality scoring

## Configuration

Environment variables in `.env`:
```
LOG_LEVEL=INFO          # DEBUG, INFO, WARNING, ERROR
FASTAPI_DEBUG=False     # Enable/disable debug mode and stack traces
```

## Dependencies

### Core
- fastapi>=0.104.0
- uvicorn[standard]>=0.24.0
- pydantic>=2.0.0
- requests>=2.31.0

### Wikipedia APIs
- wikipedia-api
- wikipedia>=1.4.0
- beautifulsoup4>=4.12.0
- lxml>=4.9.0

### AI/ML
- sentence-transformers>=2.2.0
- scikit-learn>=1.3.0
- spacy>=3.7.0
- transformers>=4.35.0
- ollama>=0.1.0

## Troubleshooting

### "python3: command not found"
Edit `start.sh` and change `python3` to `python`.

### Permission denied on start.sh
```bash
chmod +x start.sh
```

### Virtual environment issues
Rebuild from scratch:
```bash
deactivate
rm -rf venv/
./start.sh
```

### Ollama not running for LLM comparison
Make sure Ollama is installed and running:
```bash
ollama serve
# In another terminal, pull the model:
ollama pull deepseek-r1
```

### Dependencies fail to install
Ensure Python 3.8+ is installed:
```bash
python3 --version
```

## Development

### Adding New Endpoints
1. Create Pydantic models in `app/models/__init__.py`
2. Implement business logic in `app/services/`
3. Add route handler in appropriate router in `app/routers/`
4. Include router in `app/main.py`

### Testing
```bash
source venv/bin/activate
pytest
```

## Next Steps

### Before Deleting Old Repositories

1. **Test the unified application**:
   ```bash
   ./start.sh
   # Access http://127.0.0.1:8000/docs
   # Test key endpoints with your frontend
   ```

2. **Verify all features work**:
   - Wiki article fetching and translation
   - Structured article parsing
   - LLM comparison (requires Ollama)
   - Semantic comparison
   - Structural analysis across languages

3. **Update frontend configurations** to point to new backend URL if needed

### Delete Old Repositories
After verification, remove the original three repositories:
```bash
cd /Users/francois/git/symmetry-project-202512/article-compare-backend
rm -rf backend-fastapi/ fastapi/ wil-symmetry-ccsu-rawkit-2025/
```

## Best Practices Implemented

- **Pydantic v2** for type-safe request/response validation
- **Service Layer** - Business logic separated from route handlers
- **LRU Cache** - Wikipedia articles cached with automatic expiration
- **Global Exception Handling** - Consistent error responses with debug mode
- **CORS Middleware** - Configured for cross-origin requests
- **Virtual Environments** - Isolated dependencies for reproducibility
- **Router Pattern** - Logical organization of API endpoints
- **Type Hints** - Full typing support throughout codebase
- **Async/Await** - Non-blocking I/O where applicable

## License

[Your License Here]
