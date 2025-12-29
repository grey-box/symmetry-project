# Testing Strategy for Symmetry Unified Backend

This directory contains comprehensive tests for the Symmetry Unified Backend API endpoints.

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and test utilities
├── data/                    # Test data files
│   ├── obama_A.txt         # Sample article text for comparison tests
│   ├── obama_B.txt         # Sample article text for comparison tests
│   ├── missingno_en.txt     # Sample English article
│   └── missingno_fr.txt     # Sample French article
├── test_wiki_articles.py    # Tests for wiki_articles router
├── test_comparison.py       # Tests for comparison router
├── test_structured_wiki.py  # Tests for structured_wiki router
└── test_structural_analysis.py  # Tests for structural_analysis router
```

## Test Categories

### Unit Tests
- Test individual functions and methods
- Mock external dependencies
- Fast execution

### Integration Tests
- Test router endpoints
- Test interaction between components
- May use mocked external services

### External Tests
- Tests that require external services (e.g., Wikipedia API)
- Marked with `@pytest.mark.external`
- Should be skipped in CI/CD without proper configuration

## Running Tests

### Run all tests
```bash
pytest
```

### Run specific test file
```bash
pytest tests/test_wiki_articles.py
```

### Run specific test class
```bash
pytest tests/test_comparison.py::TestComparisonRouter
```

### Run specific test
```bash
pytest tests/test_wiki_articles.py::TestWikiArticlesRouter::test_get_article_with_title
```

### Run only unit tests
```bash
pytest -m unit
```

### Skip slow tests
```bash
pytest -m "not slow"
```

### Run with coverage
```bash
pytest --cov=app --cov-report=html
```

### Run with verbose output
```bash
pytest -v
```

## Test Data

The `data/` directory contains sample article texts used for testing:
- `obama_A.txt` and `obama_B.txt`: Obama biographical articles for comparison tests
- `missingno_en.txt` and `missingno_fr.txt`: MissingNo. articles in English and French

## Fixtures

The `conftest.py` file provides shared fixtures:
- `client`: FastAPI test client
- `mock_wikipediaapi`: Mocked Wikipedia API client
- `sample_obama_text_a/b`: Sample article texts
- `valid_compare_request`: Valid comparison request payload
- `mock_article_parser`: Mocked article parser service
- And more...

See `conftest.py` for the complete list of available fixtures.

## Test Coverage

The current test suite covers:
- ✅ Wiki article retrieval (GET /symmetry/v1/wiki/articles)
- ✅ Article comparison (POST /symmetry/v1/articles/compare)
- ✅ LLM comparison (GET/POST /symmetry/v1/comparison/llm)
- ✅ Semantic comparison (GET/POST /symmetry/v1/comparison/semantic)
- ✅ Wiki translation (GET /symmetry/v1/wiki_translate/source_article)
- ✅ Structured article retrieval (GET /symmetry/v1/wiki/structured-article)
- ✅ Structured section retrieval (GET /symmetry/v1/wiki/structured-section)
- ✅ Citation analysis (GET /symmetry/v1/wiki/citation-analysis)
- ✅ Reference analysis (GET /symmetry/v1/wiki/reference-analysis)
- ✅ Structural analysis (GET /operations/{language}/{title})

## CI/CD Integration

These tests are designed to run in CI/CD pipelines. External service dependencies are mocked to ensure tests run reliably in isolated environments.

## Contributing

When adding new endpoints:
1. Create tests in the appropriate test file (or create a new one)
2. Use existing fixtures when possible
3. Mock external dependencies
4. Test both success and failure cases
5. Add documentation for new fixtures
