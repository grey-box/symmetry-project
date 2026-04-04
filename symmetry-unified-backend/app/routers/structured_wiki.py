import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from fastapi import APIRouter, Query, HTTPException

from app.ai.translations import translate
from app.ai.fact_extraction import extract_facts, get_available_models, get_model_config, validate_model
from app.ai.similarity_scoring import score_article_pair
from app.models.wiki_structure import Section

from app.models import (
    StructuredArticleResponse,
    StructuredSectionResponse,
    StructuredCitationResponse,
    StructuredReferenceResponse,
    FactExtractionRequest,
    FactExtractionResponse,
    Revision,
    LagReport,
    SectionChange,
    RevisionDiffResponse,
)
from app.services.article_parser import article_fetcher, revision_fetcher
from app.services.wiki_utils import detect_language_lag

router = APIRouter(prefix="/symmetry/v1/wiki", tags=["structured-wiki"])

structured_cache: Dict[str, Dict] = {}


@router.get(
    "/structured-article",
    response_model=StructuredArticleResponse,
    summary="Get Structured Wikipedia Article",
    description="Parses a Wikipedia article into structured data including sections, citations, and references. Provides metadata like section counts and citation statistics.",
)
async def get_structured_article(
    query: Optional[str] = Query(
        None,
        description="Either a full Wikipedia URL (e.g., https://en.wikipedia.org/wiki/Python) or a keyword/title (e.g., 'Python')",
    ),
    lang: Optional[str] = Query(
        None,
        description="Article language code (e.g., 'en', 'fr', 'es'). Defaults to 'en' if not provided",
    ),
):
    logging.info(
        "Calling structured article endpoint (query='%s', lang='%s')", query, lang
    )

    if not query:
        raise HTTPException(status_code=400, detail="Query parameter is required.")

    if "://" in query:
        try:
            lang, title = await parse_wikipedia_url(query)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Wikipedia URL format.")
    else:
        title = query
        if not lang:
            lang = "en"

    cache_key = f"{lang}.{title}"
    if cache_key in structured_cache:
        logging.info("Returning cached structured article: %s", cache_key)
        return structured_cache[cache_key]

    try:
        article = article_fetcher(title, lang)

        total_citations = sum(
            len(section.citations or []) for section in article.sections
        )
        total_references = len(article.references)

        response = StructuredArticleResponse(
            title=article.title,
            lang=article.lang,
            source=article.source,
            sections=article.sections,
            references=article.references,
            total_sections=len(article.sections),
            total_citations=total_citations,
            total_references=total_references,
        )

        structured_cache[cache_key] = response

        logging.info(
            "Successfully parsed structured article: %s (%d sections, %d citations)",
            title,
            len(article.sections),
            total_citations,
        )

        return response

    except Exception as e:
        logging.error("Error parsing structured article '%s': %s", title, str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to parse article: {str(e)}"
        )


@router.get(
    "/structured-section",
    response_model=StructuredSectionResponse,
    summary="Get Specific Article Section",
    description="Retrieves a specific section from a Wikipedia article with metadata including word count, citation count, and citation positions.",
)
async def get_structured_section(
    query: str = Query(
        ...,
        description="Wikipedia article title or URL (e.g., 'Python' or https://en.wikipedia.org/wiki/Python)",
    ),
    lang: Optional[str] = Query(
        None,
        description="Article language code (e.g., 'en', 'fr', 'es'). Defaults to 'en' if not provided",
    ),
    section_title: str = Query(
        ...,
        description="Title of the specific section to retrieve (e.g., 'History', 'Uses')",
    ),
):
    logging.info(
        "Calling structured section endpoint (query='%s', section='%s')",
        query,
        section_title,
    )

    if "://" in query:
        try:
            lang, title = await parse_wikipedia_url(query)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Wikipedia URL format.")
    else:
        title = query
        if not lang:
            lang = "en"

    try:
        article = article_fetcher(title, lang)

        target_section = None
        for section in article.sections:
            if section.title.lower() == section_title.lower():
                target_section = section
                break

        if not target_section:
            raise HTTPException(
                status_code=404, detail=f"Section '{section_title}' not found."
            )

        word_count = len(target_section.clean_content.split())
        citation_count = len(target_section.citations or [])

        response = StructuredSectionResponse(
            title=target_section.title,
            raw_content=target_section.raw_content,
            clean_content=target_section.clean_content,
            citations=target_section.citations,
            citation_position=target_section.citation_position,
            word_count=word_count,
            citation_count=citation_count,
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logging.error(
            "Error parsing section '%s' from article '%s': %s",
            section_title,
            title,
            str(e),
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to parse section: {str(e)}"
        )


@router.get(
    "/citation-analysis",
    response_model=StructuredCitationResponse,
    summary="Analyze Article Citations",
    description="Provides detailed analysis of all citations in a Wikipedia article, including total citations, unique citation targets, and most cited articles.",
)
async def get_citation_analysis(
    query: str = Query(
        ...,
        description="Wikipedia article title or URL (e.g., 'Python' or https://en.wikipedia.org/wiki/Python)",
    ),
    lang: Optional[str] = Query(
        None,
        description="Article language code (e.g., 'en', 'fr', 'es'). Defaults to 'en' if not provided",
    ),
):
    logging.info("Calling citation analysis endpoint (query='%s')", query)

    if "://" in query:
        try:
            lang, title = await parse_wikipedia_url(query)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Wikipedia URL format.")
    else:
        title = query
        if not lang:
            lang = "en"

    try:
        article = article_fetcher(title, lang)

        all_citations = []
        for section in article.sections:
            if section.citations:
                all_citations.extend(section.citations)

        total_citations = len(all_citations)
        unique_targets = len(set(cit.url for cit in all_citations if cit.url))

        citation_counts = {}
        for citation in all_citations:
            if citation.url:
                citation_counts[citation.url] = citation_counts.get(citation.url, 0) + 1

        url_to_title = {cit.url: cit.label for cit in all_citations if cit.url}
        most_cited = [
            {"title": url_to_title.get(url, "Unknown"), "count": count}
            for url, count in sorted(
                citation_counts.items(), key=lambda x: x[1], reverse=True
            )[:10]
        ]

        response = StructuredCitationResponse(
            citations=all_citations,
            total_citations=total_citations,
            unique_targets=unique_targets,
            most_cited_articles=most_cited,
        )

        return response

    except Exception as e:
        logging.error("Error analyzing citations for '%s': %s", title, str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to analyze citations: {str(e)}"
        )


@router.get(
    "/reference-analysis",
    response_model=StructuredReferenceResponse,
    summary="Analyze Article References",
    description="Analyzes reference statistics for a Wikipedia article, including total references, references with URLs, and reference density (references per 1000 words).",
)
async def get_reference_analysis(
    query: str = Query(
        ...,
        description="Wikipedia article title or URL (e.g., 'Python' or https://en.wikipedia.org/wiki/Python)",
    ),
    lang: Optional[str] = Query(
        None,
        description="Article language code (e.g., 'en', 'fr', 'es'). Defaults to 'en' if not provided",
    ),
):
    logging.info("Calling reference analysis endpoint (query='%s')", query)

    if "://" in query:
        try:
            lang, title = await parse_wikipedia_url(query)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Wikipedia URL format.")
    else:
        title = query
        if not lang:
            lang = "en"

    try:
        article = article_fetcher(title, lang)

        total_references = len(article.references)
        references_with_urls = sum(1 for ref in article.references if ref.url)

        total_words = sum(
            len(section.clean_content.split()) for section in article.sections
        )
        reference_density = (
            (total_references / total_words * 1000) if total_words > 0 else 0
        )

        response = StructuredReferenceResponse(
            references=article.references,
            total_references=total_references,
            references_with_urls=references_with_urls,
            reference_density=round(reference_density, 2),
        )

        return response

    except Exception as e:
        logging.error("Error analyzing references for '%s': %s", title, str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to analyze references: {str(e)}"
        )


async def parse_wikipedia_url(url: str) -> tuple[str, str]:
    parsed_url = urlparse(url)

    if not parsed_url.netloc.endswith(".wikipedia.org"):
        raise ValueError("Invalid domain - must be Wikipedia")

    parts = parsed_url.netloc.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid URL format")

    lang = parts[0]
    if not lang.isalpha() or len(lang) > 2:
        raise ValueError("Invalid language code")

    if not parsed_url.path.startswith("/wiki/"):
        raise ValueError("Invalid article path")

    title = parsed_url.path[6:].replace("_", " ")

    if not title:
        raise ValueError("Empty article title")

    return lang, title


@router.get("/structured-translated-article", response_model=StructuredArticleResponse)
async def structured_translated_article(
    source_lang: str = "en",
    target_lang: str = "es",
    url: str | None = None,
    title: str | None = None,
):
    logging.info(
        "Calling structured translated article endpoint (source='%s', target='%s', url='%s', title='%s')",
        source_lang,
        target_lang,
        url,
        title,
    )

    # 1. Resolve title
    if url:
        try:
            parsed_lang, parsed_title = await parse_wikipedia_url(url)
            source_lang = parsed_lang
            title = parsed_title
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Wikipedia URL format.")

    if not title:
        raise HTTPException(status_code=400, detail="Title or URL required.")

    try:
        # 2. Fetch original article
        article = article_fetcher(title, source_lang)

        # 3. Translate + build response (delegated)
        response = translate_article(article, source_lang, target_lang)

        logging.info(
            "Successfully translated article: %s (%d sections, %d citations)",
            title,
            response.total_sections,
            response.total_citations,
        )

        return response

    except Exception as e:
        logging.error(
            "Error translating structured article '%s': %s",
            title,
            str(e),
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to translate article: {str(e)}"
        )


def translate_article(
    article,
    source_lang: str,
    target_lang: str,
) -> StructuredArticleResponse:
    """
    Translates an Article object and builds a StructuredArticleResponse.
    """

    translated_sections: List[Section] = []

    for section in article.sections:
        translated_sections.append(
            Section(
                title=translate(section.title, source_lang, target_lang),
                raw_content=translate(section.raw_content, source_lang, target_lang),
                clean_content=translate(
                    section.clean_content, source_lang, target_lang
                ),
                citations=section.citations,
                citation_position=section.citation_position,
            )
        )

    total_citations = sum(
        len(section.citations or []) for section in translated_sections
    )

    return StructuredArticleResponse(
        title=translate(article.title, source_lang, target_lang),
        lang=target_lang,
        source=f"wikipedia+model({source_lang}->{target_lang})",
        sections=translated_sections,
        references=article.references,
        total_sections=len(translated_sections),
        total_citations=total_citations,
        total_references=len(article.references),
    )


@router.get("/fact-extraction-models", response_model=List[Dict[str, Any]])
async def get_fact_extraction_models():
    """
    Get list of available fact extraction models.
    Returns model configurations that can be used with the extract-facts endpoint.
    """
    logging.info("Calling fact extraction models endpoint")
    try:
        models = get_available_models()
        return models
    except Exception as e:
        logging.error("Error fetching fact extraction models: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Failed to fetch models: {str(e)}")


# ---------------------------------------------------------------------------
# Revision history
# ---------------------------------------------------------------------------

@router.get(
    "/revision-history",
    response_model=List[Revision],
    summary="Get Article Revision History",
    description=(
        "Returns the most recent revisions for a Wikipedia article, newest first. "
        "Accepts either a Wikipedia URL or a plain article title."
    ),
)
async def get_revision_history(
    query: str = Query(
        ...,
        description="Wikipedia article title or URL",
    ),
    lang: Optional[str] = Query(
        None,
        description="Language code (e.g. 'en'). Inferred from URL if omitted.",
    ),
    limit: int = Query(
        20,
        ge=1,
        le=100,
        description="Number of revisions to return (1–100, default 20).",
    ),
):
    logging.info("Calling revision-history endpoint (query='%s')", query)

    if "://" in query:
        try:
            lang, title = await parse_wikipedia_url(query)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Wikipedia URL format.")
    else:
        title = query
        if not lang:
            lang = "en"

    try:
        revisions = _fetch_revisions(title, lang, limit)
    except Exception as e:
        logging.error("Error fetching revisions for '%s': %s", title, str(e))
        raise HTTPException(status_code=500, detail=f"Failed to fetch revisions: {str(e)}")

    return revisions


# ---------------------------------------------------------------------------
# Language lag detection
# ---------------------------------------------------------------------------

@router.get(
    "/lag",
    response_model=List[LagReport],
    summary="Detect Language Lag",
    description=(
        "Compares the latest revision timestamp of a source-language Wikipedia article "
        "against one or more target languages. Returns a lag report for each target language "
        "indicating whether the translation is behind the source and by how many days."
    ),
)
async def get_language_lag(
    title: str = Query(..., description="Wikipedia article title (e.g. 'Python')"),
    source_lang: str = Query("en", description="Source language code (default 'en')"),
    target_langs: List[str] = Query(..., description="Target language codes to compare (e.g. 'fr', 'es')"),
):
    logging.info(
        "Calling lag endpoint (title='%s', source='%s', targets=%s)",
        title, source_lang, target_langs,
    )
    try:
        reports = detect_language_lag(title, source_lang, target_langs)
    except Exception as e:
        logging.error("Error detecting language lag for '%s': %s", title, str(e))
        raise HTTPException(status_code=500, detail=f"Failed to detect language lag: {str(e)}")
    return reports


@router.get("/fact-extraction-validate")
async def validate_fact_extraction_model(
    model_id: str = Query(
        ..., description="Model ID to validate (predefined or HuggingFace model name)"
    ),
):
    """
    Validate a fact extraction model ID.
    Checks if the model exists either in the predefined config or on HuggingFace Hub.

    Args:
        model_id: The model ID to validate

    Returns:
        Dictionary with validation result and model info if valid
    """
    logging.info("Validating fact extraction model: %s", model_id)

    try:
        config = validate_model(model_id)
        return {"valid": True, "model": config}
    except ValueError as e:
        logging.warning("Model validation failed for %s: %s", model_id, str(e))
        return {"valid": False, "error": str(e)}
    except Exception as e:
        logging.error("Error validating model %s: %s", model_id, str(e))
        raise HTTPException(status_code=500, detail=f"Validation error: {str(e)}")


@router.post("/extract-facts", response_model=FactExtractionResponse)
def extract_facts_endpoint(request: FactExtractionRequest):
    """
    Extract facts from a section's content using the specified LLM model.

    - **section_content**: The text content to extract facts from
    - **model_id**: The ID of the model to use (from /fact-extraction-models endpoint)
    - **section_title**: The title of the section being processed (optional)
    - **num_facts**: Number of facts to extract (also determines number of model calls via chunking). Default is 1.
    """
    logging.info(
        "Calling extract facts endpoint (model='%s', content_length=%d, section_title='%s', num_facts=%d)",
        request.model_id,
        len(request.section_content),
        request.section_title,
        request.num_facts,
    )

    try:
        facts, chunks = extract_facts(
            request.section_content, request.model_id, num_facts=request.num_facts
        )

        config = get_model_config(request.model_id)
        model_name = config["name"]

        response = FactExtractionResponse(
            facts=facts,
            model_used=model_name,
            section_title=request.section_title,
            chunks=chunks,
        )

        logging.info(
            "Successfully extracted %d facts using model %s for section '%s'",
            len(facts),
            request.model_id,
            request.section_title,
        )

        return response
    except ValueError as e:
        logging.error("ValueError in fact extraction: %s", str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error("Error extracting facts: %s", str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to extract facts: {str(e)}"
        )


# ---------------------------------------------------------------------------
# Revision-to-revision diff
# ---------------------------------------------------------------------------

@router.get(
    "/diff",
    response_model=RevisionDiffResponse,
    summary="Diff Two Revision Snapshots",
    description=(
        "Given two revision IDs for the same article, fetches both snapshots and returns "
        "a structured diff: sections added, removed, or modified, each with a similarity "
        "score, plus an overall similarity score for the full article."
    ),
)
async def get_diff(
    revid_a: int = Query(..., description="First (older) revision ID"),
    revid_b: int = Query(..., description="Second (newer) revision ID"),
    title: str = Query(..., description="Wikipedia article title (e.g. 'Python')"),
    lang: Optional[str] = Query(None, description="Language code (default 'en')"),
):
    logging.info(
        "Calling diff endpoint (title='%s', revid_a=%d, revid_b=%d)",
        title, revid_a, revid_b,
    )

    if not lang:
        lang = "en"

    try:
        article_a = revision_fetcher(revid_a, lang)
        article_b = revision_fetcher(revid_b, lang)
    except Exception as e:
        logging.error("Error fetching revisions: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Failed to fetch revisions: {str(e)}")

    sections_a = {s.title: s.clean_content for s in article_a.sections}
    sections_b = {s.title: s.clean_content for s in article_b.sections}

    titles_a = set(sections_a)
    titles_b = set(sections_b)

    sections_added = [
        SectionChange(section_title=t, old_content=None, new_content=sections_b[t], similarity_score=0.0)
        for t in titles_b - titles_a
    ]
    sections_removed = [
        SectionChange(section_title=t, old_content=sections_a[t], new_content=None, similarity_score=0.0)
        for t in titles_a - titles_b
    ]
    sections_modified = [
        SectionChange(
            section_title=t,
            old_content=sections_a[t],
            new_content=sections_b[t],
            similarity_score=round(score_article_pair(sections_a[t], sections_b[t]), 4),
        )
        for t in titles_a & titles_b
        if score_article_pair(sections_a[t], sections_b[t]) < 0.99
    ]

    full_text_a = " ".join(sections_a.values())
    full_text_b = " ".join(sections_b.values())
    overall_similarity = round(score_article_pair(full_text_a, full_text_b), 4)

    return RevisionDiffResponse(
        revid_a=revid_a,
        revid_b=revid_b,
        title=title,
        lang=lang,
        sections_added=sections_added,
        sections_removed=sections_removed,
        sections_modified=sections_modified,
        overall_similarity=overall_similarity,
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _fetch_revisions(title: str, lang: str, limit: int = 20) -> List[Revision]:
    """Call the MediaWiki API to retrieve recent revisions for *title*."""
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "titles": title,
        "prop": "revisions",
        "rvprop": "ids|timestamp|user|comment|size",
        "rvlimit": limit,
        "rvdir": "older",
        "format": "json",
    }
    r = requests.get(url, params=params, headers={"User-Agent": "SymmetryUnified/1.0"})
    r.raise_for_status()
    data = r.json()

    pages = data.get("query", {}).get("pages", {})
    if not pages:
        return []

    page = next(iter(pages.values()))
    raw_revisions = page.get("revisions", [])

    revisions: List[Revision] = []
    for rev in raw_revisions:
        revisions.append(
            Revision(
                revid=rev.get("revid", 0),
                parentid=rev.get("parentid", 0),
                timestamp=rev.get("timestamp", ""),
                user=rev.get("user", ""),
                comment=rev.get("comment", ""),
                size=rev.get("size", 0),
            )
        )
    return revisions
