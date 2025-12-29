# Structured Wiki Integration Guide

This document describes the integration of `wiki_structure.py` and `article_parser.py` into the Project-Symmetry-AI codebase.

## Overview

The integration adds structured Wikipedia article parsing capabilities with rich metadata including:
- Section-by-section content breakdown
- Internal citations and their positions
- Full reference list with URLs
- Comprehensive article statistics

## Files Added

### Backend Files

1. **`backend-fastapi/app/models/wiki_structure.py`**
   - Pydantic models for structured data: `Citation`, `Reference`, `Section`, `Article`
   - Mirrors the original structure exactly

2. **`backend-fastapi/app/services/article_parser.py`**
   - Original `article_fetcher` function
   - Uses MediaWiki Action API + BeautifulSoup for rich parsing
   - Returns structured Article objects with metadata

3. **`backend-fastapi/app/model/structured_response.py`**
   - API response models for structured data
   - `StructuredArticleResponse`, `StructuredSectionResponse`, etc.
   - Enhanced with statistics and analysis data

4. **`backend-fastapi/app/api/structured_wiki.py`**
   - New API endpoints for structured data
   - `/symmetry/v1/wiki/structured-article`
   - `/symmetry/v1/wiki/structured-section`
   - `/symmetry/v1/wiki/citation-analysis`
   - `/symmetry/v1/wiki/reference-analysis`

5. **`backend-fastapi/test_structured_integration.py`**
   - Comprehensive test script for the integration
   - Tests article parser, URL parsing, and API endpoints

### Frontend Files

6. **`ui/src/models/structured-wiki.ts`**
   - TypeScript interfaces matching Python Pydantic models
   - Provides type safety for frontend-backend communication

7. **`ui/src/services/structuredWikiService.ts`**
   - Service layer for structured wiki API calls
   - Uses fetch API (no external dependencies)
   - Utility functions for data processing

8. **`ui/src/components/StructuredArticleViewer.tsx`**
   - React component for displaying structured articles
   - Shows section navigation, citations, references
   - Rich UI with statistics and analysis

## API Endpoints

### New Structured Endpoints

```
GET /symmetry/v1/wiki/structured-article
    query: string (required) - Wikipedia title or URL
    lang: string (optional) - Language code (default: en)

GET /symmetry/v1/wiki/structured-section
    query: string (required) - Wikipedia title or URL
    lang: string (optional) - Language code
    section_title: string (required) - Specific section to retrieve

GET /symmetry/v1/wiki/citation-analysis
    query: string (required) - Wikipedia title or URL
    lang: string (optional) - Language code

GET /symmetry/v1/wiki/reference-analysis
    query: string (required) - Wikipedia title or URL
    lang: string (optional) - Language code
```

### Response Examples

#### Structured Article Response
```json
{
  "title": "Albert Einstein",
  "lang": "en",
  "source": "action_api",
  "sections": [
    {
      "title": "Early life",
      "raw_content": "...",
      "clean_content": "Albert Einstein was born...",
      "citations": [
        {
          "label": "Born",
          "url": "https://en.wikipedia.org/wiki/Albert_Einstein"
        }
      ],
      "citation_position": ["Born:15", "family:45"]
    }
  ],
  "references": [
    {
      "label": "Einstein, Albert (1979). Autobiographical Notes...",
      "id": "cite_note-1",
      "url": "https://books.google.com/..."
    }
  ],
  "total_sections": 5,
  "total_citations": 23,
  "total_references": 15
}
```

## Usage Examples

### Backend Usage

```python
from app.services.article_parser import article_fetcher

# Get structured article
article = article_fetcher("Albert Einstein", "en")

# Access sections
for section in article.sections:
    print(f"Section: {section.title}")
    print(f"Content: {section.clean_content[:200]}...")
    print(f"Citations: {len(section.citations or [])}")

# Access references
for reference in article.references:
    print(f"Reference: {reference.label[:100]}...")
```

### Frontend Usage

```typescript
import { structuredWikiService } from './services/structuredWikiService';

// Get structured article
const article = await structuredWikiService.getStructuredArticleFromTitle(
  "Albert Einstein", 
  "en"
);

console.log(`Article has ${article.total_sections} sections`);
console.log(`Total citations: ${article.total_citations}`);

// Get statistics
const stats = structuredWikiService.getArticleStats(article);
console.log(`Reference density: ${stats.referenceDensity} per 1000 words`);
```

## Testing

Run the test script to verify integration:

```bash
cd backend-fastapi
python test_structured_integration.py
```

This will test:
- ✅ Article parser functionality
- ✅ URL parsing
- ✅ API endpoints (if server is running)

## Benefits

1. **Rich Metadata**: Full citation and reference tracking
2. **Structured Content**: Section-based organization
3. **Enhanced UI**: Better user experience with detailed views
4. **Analysis Tools**: Citation and reference density calculations
5. **Scalability**: Clean separation of concerns
6. **Type Safety**: Full TypeScript/Python type consistency

## Migration Path

The integration adds new endpoints alongside existing ones:

- **Existing**: `/get_article` - Simple text extraction
- **New**: `/symmetry/v1/wiki/structured-article` - Rich structured data

This allows gradual migration without breaking existing functionality.

## Future Enhancements

1. **Caching**: Implement structured data caching
2. **Search**: Full-text search within articles
3. **Export**: Export to various formats (PDF, JSON, etc.)
4. **Analysis**: Advanced citation network analysis
5. **Comparison**: Compare citation patterns between languages

## Dependencies Added

- `beautifulsoup4` - HTML parsing (already in requirements.txt)
- `requests` - HTTP client (already in requirements.txt)

No new dependencies were required, maintaining the project's lightweight footprint.
